package preview

import (
	"context"
	"fmt"
	"os"
	"os/exec"
	"os/signal"
	"path/filepath"
	"syscall"

	"github.com/Rapid-Vision/rv/cmd/internal/utils"
	"github.com/Rapid-Vision/rv/cmd/internal/watcher"
)

func Preview(scriptPath string) {
	blenderPath, err := utils.GetBlenderPath()
	if err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(1)
	}

	libPath, err := utils.GetLibPath()
	if err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(1)
	}

	port, err := utils.GetPort()
	if err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(1)
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
	)
	cmd.Stdout = os.Stdout
	cmd.Stderr = os.Stderr

	if err = cmd.Start(); err != nil {
		fmt.Fprintln(os.Stderr, "failed to start blender:", err)
		os.Exit(1)
	}
	fmt.Printf("Blender started (PID %d) on port %d\n", cmd.Process.Pid, port)

	// Context for shutdown
	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()

	client := newPreviewClient(port)

	// Watcher goroutine
	go func() {
		if err := watcher.WatchFile(ctx, scriptPath, client.requestRerun); err != nil {
			fmt.Fprintln(os.Stderr, "watch error:", err)
		}
	}()

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
