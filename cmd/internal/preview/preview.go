package preview

import (
	"context"
	"fmt"
	"os"
	"os/exec"
	"os/signal"
	"path/filepath"
	"syscall"

	"github.com/Rapid-Vision/rv/cmd/internal/logs"
	"github.com/Rapid-Vision/rv/cmd/internal/utils"
	"github.com/Rapid-Vision/rv/cmd/internal/watcher"
)

func Preview(scriptPathRel string) {
	scriptPath, err := filepath.Abs(scriptPathRel)
	if err != nil {
		logs.Err.Fatalln("Failed to get script absolute path:", err)
	}

	blenderPath, err := utils.GetBlenderPath()
	if err != nil {
		logs.Err.Fatalln("Can't find blender path: ", err)
	}

	libPath, err := utils.GetLibPath()
	if err != nil {
		logs.Err.Fatalln("Can't find rvlib: ", err)
	}

	port, err := utils.GetPort()
	if err != nil {
		logs.Err.Fatalln("Can't allocate a port: ", err)
	}

	if info, err := os.Stat(scriptPath); err != nil {
		if os.IsNotExist(err) {
			logs.Err.Fatalln("Script path does not exist:", scriptPath)
		} else {
			logs.Err.Fatalln("Error checking script path:", err)
		}
	} else if info.IsDir() {
		logs.Err.Fatalln("Script path is a directory, not a file:", scriptPath)
	}

	cwdAbs, err := utils.GetAbsCwdPath()
	if err != nil {
		logs.Err.Fatalln("Can't get current working directory path:", err)
	}

	// Start Blender
	cmd := exec.Command(
		blenderPath,
		filepath.Join(libPath, "template.blend"),
		"--factory-startup",
		"--python", filepath.Join(libPath, "preview.py"),
		"--",
		"--port", fmt.Sprintf("%d", port),
		"--script", scriptPath,
		"--libpath", libPath,
		"--cwd", cwdAbs,
	)
	cmd.Stdout = os.Stdout
	cmd.Stderr = os.Stderr

	if err = cmd.Start(); err != nil {
		logs.Err.Fatalln("Failed to start blender:", err)
	}
	logs.Info.Printf("Blender started (PID %d) on port %d\n", cmd.Process.Pid, port)

	// Context for shutdown
	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()

	client := newPreviewClient(port)

	// Watcher goroutine
	go func() {
		if err := watcher.WatchFile(ctx, scriptPath, client.requestRerun); err != nil {
			logs.Warn.Println("Watch error:", err)
		}
	}()

	// Handle Ctrl-C
	sigCh := make(chan os.Signal, 1)
	signal.Notify(sigCh, os.Interrupt, syscall.SIGTERM)

	// Wait for either Blender exit or signal
	select {
	case <-sigCh:
		logs.Info.Println("Interrupt received — terminating Blender…")
		_ = cmd.Process.Signal(syscall.SIGTERM)
	case err = <-utils.WaitCmd(cmd):
		if err != nil {
			logs.Info.Println("Blender exited with error:", err)
		} else {
			logs.Info.Println("Blender exited.")
		}
	}

	cancel()
}
