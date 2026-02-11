package render

import (
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
	ScriptPath string
	Cwd        string
	ImageNum   int
	Procs      int
	OutputDir  string
}

func Render(opts RenderOptions) error {
	scriptPath := opts.ScriptPath
	imgNum := opts.ImageNum
	procs := opts.Procs
	outputDir := opts.OutputDir
	cwdAbs := opts.Cwd

	if scriptPath == "" {
		logs.Err.Fatalln("script path is required")
	}
	if outputDir == "" {
		logs.Err.Fatalln("output directory is required")
	}
	if cwdAbs == "" {
		logs.Err.Fatalln("cwd is required")
	}

	blenderPath, err := utils.GetBlenderPath()
	if err != nil {
		logs.Err.Fatalln("Can't find blender path:", err)
	}

	libPath, err := utils.GetLibPath()
	if err != nil {
		logs.Err.Fatalln("Can't find rvlib:", err)
	}

	logs.Info.Println("librv path: ", libPath)

	seqOutDir, err := utils.GetSequentialOutputDir(outputDir)
	if err != nil {
		logs.Err.Fatalln("Can't create new output directory:", err)
	}

	var cmdBuff [](*exec.Cmd)

	if imgNum < 1 {
		logs.Err.Fatalln("--number is less then one")
	}

	if procs < 1 {
		logs.Err.Fatalln("--procs must be at least 1")
	}

	if imgNum < procs {
		procs = imgNum
	}

	for i := 0; i < procs; i += 1 {
		part := utils.SplitTaskBetweenProcs(imgNum, procs, i)

		// Start Blender
		cmd := exec.Command(
			blenderPath,
			filepath.Join(libPath, "template.blend"),
			"--factory-startup",
			"--background",
			"--python", filepath.Join(libPath, "render.py"),
			"--",
			"--script", scriptPath,
			"--libpath", libPath,
			"--number", fmt.Sprintf("%d", part),
			"--output", seqOutDir,
			"--cwd", cwdAbs,
		)
		cmd.Stdout = os.Stdout
		cmd.Stderr = os.Stderr

		if err = cmd.Start(); err != nil {
			logs.Err.Fatalln("failed to start blender:", err)
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

	return renderErr
}
