package render

import (
	"context"
	"fmt"
	"log"
	"os"
	"os/exec"
	"os/signal"
	"path/filepath"
	"syscall"

	"github.com/Rapid-Vision/rv/cmd/internal/utils"
)

func Render(scriptPath string, imgNum int, procs int, outputDir string) {
	blenderPath, err := utils.GetBlenderPath()
	if err != nil {
		log.Fatalln(err)
	}

	libPath, err := utils.GetLibPath()
	if err != nil {
		log.Fatalln(err)
	}

	fmt.Println("librv path: ", libPath)

	seqOutDir, err := utils.GetSequentialOutputDir(outputDir)
	if err != nil {
		log.Fatalln("Can't create new output directory: ", err)
	}

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
		"--number", fmt.Sprintf("%d", imgNum),
		"--output", seqOutDir,
	)
	cmd.Stdout = os.Stdout
	cmd.Stderr = os.Stderr

	if err = cmd.Start(); err != nil {
		log.Fatalln("failed to start blender:", err)
	}
	fmt.Printf("Blender started (PID %d)\n", cmd.Process.Pid)

	// Context for shutdown
	_, cancel := context.WithCancel(context.Background())
	defer cancel()

	// Handle Ctrl-C
	sigCh := make(chan os.Signal, 1)
	signal.Notify(sigCh, os.Interrupt, syscall.SIGTERM)

	// Wait for either Blender exit or signal
	select {
	case <-sigCh:
		fmt.Println("Interrupt received — terminating Blender…")
		_ = cmd.Process.Signal(syscall.SIGTERM)
	case err = <-utils.WaitCmd(cmd):
		if err != nil {
			fmt.Fprintln(os.Stderr, "Blender exited with error:", err)
		} else {
			fmt.Println("Blender exited.")
		}
	}

	cancel()
}
