package render

import (
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"os"
	"os/exec"
	"os/signal"
	"path/filepath"
	"slices"
	"strings"
	"syscall"

	"github.com/Rapid-Vision/rv/internal/generator"
	"github.com/Rapid-Vision/rv/internal/logs"
	"github.com/Rapid-Vision/rv/internal/seed"
	"github.com/Rapid-Vision/rv/internal/utils"
)

type RenderOptions struct {
	ScriptPath            string
	Cwd                   string
	GenBaseDir            string
	WorkDir               string
	GenRetain             utils.GeneratorRetention
	ImageNum              int
	Procs                 int
	Resolution            [2]int
	OutputDir             string
	GPUBackend            string
	TimeLimit             *float64
	MaxSamples            *int
	MinSamples            *int
	NoiseThresholdEnabled *bool
	NoiseThreshold        *float64
	Seed                  seed.Config
	GeneratorPort         int
}

type RenderResult struct {
	OutputDir string
}

type datasetMeta struct {
	Resolution   [2]int             `json:"resolution"`
	RenderParams datasetRenderParms `json:"render_params"`
	SampleFiles  []string           `json:"sample_files"`
}

type datasetRenderParms struct {
	ScriptPath            string   `json:"script_path"`
	Cwd                   string   `json:"cwd"`
	Number                int      `json:"number"`
	Procs                 int      `json:"procs"`
	GPUBackend            string   `json:"gpu_backend,omitempty"`
	TimeLimit             *float64 `json:"time_limit,omitempty"`
	MaxSamples            *int     `json:"max_samples,omitempty"`
	MinSamples            *int     `json:"min_samples,omitempty"`
	NoiseThresholdEnabled *bool    `json:"noise_threshold_enabled,omitempty"`
	NoiseThreshold        *float64 `json:"noise_threshold,omitempty"`
	SeedMode              string   `json:"seed_mode,omitempty"`
	SeedValue             *int64   `json:"seed_value,omitempty"`
}

func normalizedGPUBackend(value string) string {
	if value == "" {
		return "auto"
	}
	return strings.ToLower(value)
}

func applyDefaultGeneratorOptions(opts *RenderOptions) error {
	if opts.GenBaseDir == "" {
		generatorPaths, err := utils.ResolveGeneratorPaths(opts.Cwd, "")
		if err != nil {
			return fmt.Errorf("resolve generator paths: %w", err)
		}
		opts.GenBaseDir = generatorPaths.GenBaseDir
	}
	if opts.GenRetain == "" {
		opts.GenRetain = utils.GeneratorRetainNone
	}
	return nil
}

func Render(opts RenderOptions) (RenderResult, error) {
	opts.Seed = seed.Normalize(opts.Seed)

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
	if err := applyDefaultGeneratorOptions(&opts); err != nil {
		return RenderResult{}, err
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

	generatorCtx, cancelGenerator := context.WithCancel(context.Background())
	generatorService, err := generator.Start(generatorCtx)
	if err != nil {
		cancelGenerator()
		logs.Warn.Printf("Generator service unavailable; scenes using self.generators will fail: %v\n", err)
		opts.GeneratorPort = 0
	} else {
		opts.GeneratorPort = generatorService.Port()
		defer func() {
			cancelGenerator()
			generatorService.Wait()
		}()
	}

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
	opts.GPUBackend = normalizedGPUBackend(opts.GPUBackend)
	if err := validateOptionalRenderOptions(opts); err != nil {
		return RenderResult{}, err
	}

	workDir, err := utils.AllocateGeneratorWorkDir(opts.GenBaseDir)
	if err != nil {
		return RenderResult{}, err
	}
	opts.WorkDir = workDir
	if opts.GenRetain == utils.GeneratorRetainLast || opts.GenRetain == utils.GeneratorRetainNone {
		if err := utils.CleanupGeneratorWorkDirs(opts.GenBaseDir, utils.GeneratorRetainLast, opts.WorkDir); err != nil {
			return RenderResult{}, err
		}
	}
	defer func() {
		if err := utils.CleanupGeneratorWorkDirs(opts.GenBaseDir, opts.GenRetain, opts.WorkDir); err != nil {
			logs.Warn.Printf("Failed to clean generator work directories: %v\n", err)
		}
	}()

	if imgNum < procs {
		procs = imgNum
	}

	for i := 0; i < procs; i += 1 {
		part := utils.SplitTaskBetweenProcs(imgNum, procs, i)
		seedBase := renderSeedBase(imgNum, procs, i)

		// Start Blender
		cmd := exec.Command(
			blenderPath,
			buildBlenderRenderArgs(opts, libPath, seqOutDir, part, seedBase)...,
		)
		cmd.Env = utils.BlenderCommandEnv()
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
	if err := writeDatasetMetadata(seqOutDir, opts); err != nil {
		return RenderResult{}, fmt.Errorf("failed to write dataset metadata: %w", err)
	}

	return RenderResult{
		OutputDir: seqOutDir,
	}, nil
}

func buildBlenderRenderArgs(opts RenderOptions, libPath string, seqOutDir string, part int, seedBase int) []string {
	opts.Seed = seed.Normalize(opts.Seed)
	gpuBackend := normalizedGPUBackend(opts.GPUBackend)
	args := []string{
		filepath.Join(libPath, "template.blend"),
		"--factory-startup",
		"--background",
		"--python-exit-code", "1",
		"--python", filepath.Join(libPath, "render.py"),
		"--",
		"--script", opts.ScriptPath,
		"--libpath", libPath,
		"--number", fmt.Sprintf("%d", part),
		"--resolution", fmt.Sprintf("%d,%d", opts.Resolution[0], opts.Resolution[1]),
		"--output", seqOutDir,
		"--root-dir", opts.Cwd,
		"--work-dir", opts.WorkDir,
		"--gpu-backend", gpuBackend,
		"--seed-mode", string(opts.Seed.Mode),
		"--seed-base", fmt.Sprintf("%d", seedBase),
		"--generator-port", fmt.Sprintf("%d", opts.GeneratorPort),
	}
	if opts.Seed.Mode == seed.FixedMode {
		args = append(args, "--seed-value", fmt.Sprintf("%d", opts.Seed.Value))
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
		if *opts.NoiseThresholdEnabled {
			args = append(args, "--noise-threshold-enabled")
		} else {
			args = append(args, "--no-noise-threshold-enabled")
		}
	}
	if opts.NoiseThreshold != nil {
		args = append(args, "--noise-threshold", fmt.Sprintf("%g", *opts.NoiseThreshold))
	}

	return args
}

func renderSeedBase(imageNum int, procs int, procIndex int) int {
	base := 0
	for i := range procIndex {
		base += utils.SplitTaskBetweenProcs(imageNum, procs, i)
	}
	return base
}

func validateOptionalRenderOptions(opts RenderOptions) error {
	switch normalizedGPUBackend(opts.GPUBackend) {
	case "auto", "optix", "cuda", "hip", "oneapi", "metal", "cpu":
	default:
		return errors.New("--gpu-backend must be one of auto, optix, cuda, hip, oneapi, metal, cpu")
	}
	switch opts.Seed.Mode {
	case "", seed.RandomMode, seed.SeqMode, seed.FixedMode:
	default:
		return errors.New("invalid seed mode")
	}
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

func writeDatasetMetadata(seqOutDir string, opts RenderOptions) error {
	if err := os.MkdirAll(seqOutDir, os.ModePerm); err != nil {
		return err
	}

	entries, err := os.ReadDir(seqOutDir)
	if err != nil {
		return err
	}

	samples := make([]string, 0)
	sampleFiles := make([]string, 0)
	haveSampleFiles := false
	for _, entry := range entries {
		if !entry.IsDir() {
			continue
		}

		samplePath := filepath.Join(seqOutDir, entry.Name())
		if !haveSampleFiles {
			files, err := listFilesRecursive(samplePath)
			if err != nil {
				return err
			}
			sampleFiles = files
			haveSampleFiles = true
		}
		samples = append(samples, entry.Name())
	}
	slices.SortFunc(samples, strings.Compare)

	meta := datasetMeta{
		Resolution: opts.Resolution,
		RenderParams: datasetRenderParms{
			ScriptPath:            opts.ScriptPath,
			Cwd:                   opts.Cwd,
			Number:                opts.ImageNum,
			Procs:                 opts.Procs,
			GPUBackend:            normalizedGPUBackend(opts.GPUBackend),
			TimeLimit:             opts.TimeLimit,
			MaxSamples:            opts.MaxSamples,
			MinSamples:            opts.MinSamples,
			NoiseThresholdEnabled: opts.NoiseThresholdEnabled,
			NoiseThreshold:        opts.NoiseThreshold,
			SeedMode:              string(seed.Normalize(opts.Seed).Mode),
		},
		SampleFiles: sampleFiles,
	}
	normalizedSeed := seed.Normalize(opts.Seed)
	if normalizedSeed.Mode == seed.FixedMode {
		meta.RenderParams.SeedValue = &normalizedSeed.Value
	}

	f, err := os.Create(filepath.Join(seqOutDir, "_meta.json"))
	if err != nil {
		return err
	}
	defer func() { _ = f.Close() }()

	enc := json.NewEncoder(f)
	enc.SetIndent("", "    ")
	return enc.Encode(meta)
}

func listFilesRecursive(root string) ([]string, error) {
	files := make([]string, 0)
	err := filepath.WalkDir(root, func(path string, d os.DirEntry, err error) error {
		if err != nil {
			return err
		}
		if d.IsDir() {
			return nil
		}
		rel, err := filepath.Rel(root, path)
		if err != nil {
			return err
		}
		files = append(files, filepath.ToSlash(rel))
		return nil
	})
	if err != nil {
		return nil, err
	}
	slices.Sort(files)
	return files, nil
}
