package render

import (
	"errors"
	"fmt"
	"os"
	"os/exec"
	"os/signal"
	"path/filepath"
	"syscall"

	"github.com/Rapid-Vision/rv/internal/logs"
	"github.com/Rapid-Vision/rv/internal/utils"
)

type RenderOptions struct {
	ScriptPath            string
	Cwd                   string
	ImageNum              int
	Procs                 int
	Resolution            [2]int
	OutputDir             string
	TimeLimit             *float64
	MaxSamples            *int
	MinSamples            *int
	NoiseThresholdEnabled *bool
	NoiseThreshold        *float64
}

type RenderResult struct {
	OutputDir string
}

func Render(opts RenderOptions) (RenderResult, error) {
	scriptPath := opts.ScriptPath
	imgNum := opts.ImageNum
	procs := opts.Procs
	resolution := opts.Resolution
	outputDir := opts.OutputDir
	cwdAbs := opts.Cwd

	if scriptPath == "" {
		return RenderResult{}, errors.New("script path is required")
	}
	if outputDir == "" {
		return RenderResult{}, errors.New("output directory is required")
	}
	if cwdAbs == "" {
		return RenderResult{}, errors.New("cwd is required")
	}

	blenderPath, err := utils.GetBlenderPath()
	if err != nil {
		return RenderResult{}, fmt.Errorf("can't find blender path: %w", err)
	}

	libPath, err := utils.GetLibPath()
	if err != nil {
		return RenderResult{}, fmt.Errorf("can't find rvlib: %w", err)
	}

	logs.Info.Println("librv path: ", libPath)

	seqOutDir, err := utils.GetSequentialOutputDir(outputDir)
	if err != nil {
		return RenderResult{}, fmt.Errorf("can't create new output directory: %w", err)
	}

	var cmdBuff [](*exec.Cmd)

	if imgNum < 1 {
		return RenderResult{}, errors.New("--number is less then one")
	}

	if procs < 1 {
		return RenderResult{}, errors.New("--procs must be at least 1")
	}
	if resolution[0] <= 0 || resolution[1] <= 0 {
		return RenderResult{}, errors.New("--resolution must be WIDTH,HEIGHT with positive integers")
	}
	if err := validateOptionalRenderOptions(opts); err != nil {
		return RenderResult{}, err
	}

	if imgNum < procs {
		procs = imgNum
	}

	for i := 0; i < procs; i += 1 {
		part := utils.SplitTaskBetweenProcs(imgNum, procs, i)

		// Start Blender
		cmd := exec.Command(
			blenderPath,
			buildBlenderRenderArgs(opts, libPath, seqOutDir, part)...,
		)
		cmd.Stdout = os.Stdout
		cmd.Stderr = os.Stderr

		if err = cmd.Start(); err != nil {
			return RenderResult{}, fmt.Errorf("failed to start blender: %w", err)
		}
		logs.Info.Printf("Blender started (PID %d)\n", cmd.Process.Pid)

		cmdBuff = append(cmdBuff, cmd)
	}

	// Handle Ctrl-C
	sigCh := make(chan os.Signal, 1)
	signal.Notify(sigCh, os.Interrupt, syscall.SIGTERM)

	waitCh := utils.WaitCmdBuff(cmdBuff)
	var renderErr error

	// Wait for either all Blender instances exit or signal
	for i := 0; i < procs; i += 1 {
		select {
		case <-sigCh:
			logs.Info.Println("Interrupt received — terminating Blender…")

			for j := 0; j < procs; j += 1 {
				_ = cmdBuff[j].Process.Signal(syscall.SIGTERM)
			}
		case err = <-waitCh:
			if err != nil {
				logs.Info.Println("Blender exited with error:", err)
				if renderErr == nil {
					renderErr = err
				}
			} else {
				logs.Info.Println("Blender exited.")
			}
		}
	}

	if renderErr != nil {
		return RenderResult{}, renderErr
	}

	return RenderResult{
		OutputDir: seqOutDir,
	}, nil
}

func buildBlenderRenderArgs(opts RenderOptions, libPath string, seqOutDir string, part int) []string {
	args := []string{
		filepath.Join(libPath, "template.blend"),
		"--factory-startup",
		"--background",
		"--python", filepath.Join(libPath, "render.py"),
		"--",
		"--script", opts.ScriptPath,
		"--libpath", libPath,
		"--number", fmt.Sprintf("%d", part),
		"--resolution", fmt.Sprintf("%d,%d", opts.Resolution[0], opts.Resolution[1]),
		"--output", seqOutDir,
		"--cwd", opts.Cwd,
	}

	if opts.TimeLimit != nil {
		args = append(args, "--time-limit", fmt.Sprintf("%g", *opts.TimeLimit))
	}
	if opts.MaxSamples != nil {
		args = append(args, "--max-samples", fmt.Sprintf("%d", *opts.MaxSamples))
	}
	if opts.MinSamples != nil {
		args = append(args, "--min-samples", fmt.Sprintf("%d", *opts.MinSamples))
	}
	if opts.NoiseThresholdEnabled != nil {
		args = append(args, "--noise-threshold-enabled", fmt.Sprintf("%t", *opts.NoiseThresholdEnabled))
	}
	if opts.NoiseThreshold != nil {
		args = append(args, "--noise-threshold", fmt.Sprintf("%g", *opts.NoiseThreshold))
	}

	return args
}

func validateOptionalRenderOptions(opts RenderOptions) error {
	if opts.TimeLimit != nil && *opts.TimeLimit <= 0 {
		return errors.New("--time-limit must be > 0")
	}
	if opts.MaxSamples != nil && *opts.MaxSamples <= 0 {
		return errors.New("--max-samples must be > 0")
	}
	if opts.MinSamples != nil && *opts.MinSamples < 0 {
		return errors.New("--min-samples must be >= 0")
	}
	if opts.MinSamples != nil && opts.MaxSamples != nil && *opts.MinSamples > *opts.MaxSamples {
		return errors.New("--min-samples must be <= --max-samples")
	}
	if opts.NoiseThresholdEnabled != nil && *opts.NoiseThresholdEnabled {
		if opts.NoiseThreshold == nil {
			return errors.New("--noise-threshold is required when --noise-threshold-enabled=true")
		}
		if *opts.NoiseThreshold <= 0 {
			return errors.New("--noise-threshold must be > 0 when --noise-threshold-enabled=true")
		}
	}
	if opts.NoiseThreshold != nil {
		if opts.NoiseThresholdEnabled == nil || !*opts.NoiseThresholdEnabled {
			return errors.New("--noise-threshold requires --noise-threshold-enabled=true")
		}
	}
	return nil
}
