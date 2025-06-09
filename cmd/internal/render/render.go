package render

import (
	"fmt"
	"os"
	"os/exec"
	"os/signal"
	"path/filepath"
	"syscall"

	"github.com/Rapid-Vision/rv/cmd/internal/logs"
	"github.com/Rapid-Vision/rv/cmd/internal/utils"
)

func Render(scriptPathRel string, imgNum int, procs int, outputDir string) {
	scriptPath, err := filepath.Abs(scriptPathRel)
	if err != nil {
		logs.Err.Fatalln("Failed to get script absolute path:", err)
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

	cwdAbs, err := utils.GetAbsCwdPath()
	if err != nil {
		logs.Err.Fatalln("Can't get current working directory path:", err)
	}

	var cmdBuff [](*exec.Cmd)

	if imgNum < 1 {
		logs.Err.Fatalln("--number is less then one")
	}

	if procs < 0 {
		procs = 1
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
			} else {
				logs.Info.Println("Blender exited.")
			}
		}
	}
}
