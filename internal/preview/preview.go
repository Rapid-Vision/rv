package preview

import (
	"context"
	"errors"
	"fmt"
	"os"
	"os/exec"
	"os/signal"
	"path/filepath"
	"syscall"

	"github.com/Rapid-Vision/rv/internal/logs"
	"github.com/Rapid-Vision/rv/internal/utils"
	"github.com/Rapid-Vision/rv/internal/watcher"
)

type Options struct {
	ScriptPathArg string
	CwdArg        string
	PreviewFiles  bool
	PreviewOut    string
	NoWindow      bool
	Resolution    [2]int
	TimeLimit     *float64
}

func Preview(opts Options) {
	paths, err := utils.ResolveRuntimePaths(opts.ScriptPathArg, opts.CwdArg)
	if err != nil {
		logs.Err.Fatalln("Failed to resolve paths:", err)
	}
	scriptPath := paths.ScriptPath
	cwdAbs := paths.Cwd

	if err := validateOptions(opts); err != nil {
		logs.Err.Fatalln("Invalid preview options:", err)
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

	// Start Blender
	cmd := exec.Command(blenderPath, buildBlenderPreviewArgs(opts, scriptPath, cwdAbs, libPath, port)...)
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

func validateOptions(opts Options) error {
	if opts.NoWindow && !opts.PreviewFiles {
		return errors.New("--no-window requires --preview-files")
	}
	if opts.PreviewFiles && opts.PreviewOut == "" {
		return errors.New("--preview-out is required when --preview-files is enabled")
	}
	if opts.Resolution[0] <= 0 || opts.Resolution[1] <= 0 {
		return errors.New("--resolution must be WIDTH,HEIGHT with positive integers")
	}
	if opts.TimeLimit != nil && *opts.TimeLimit <= 0 {
		return errors.New("--time-limit must be > 0")
	}
	return nil
}

func buildBlenderPreviewArgs(opts Options, scriptPath string, cwdAbs string, libPath string, port int) []string {
	args := []string{
		filepath.Join(libPath, "template.blend"),
		"--factory-startup",
	}

	if opts.NoWindow {
		args = append(args, "--background")
	}

	args = append(
		args,
		"--python", filepath.Join(libPath, "preview.py"),
		"--",
		"--port", fmt.Sprintf("%d", port),
		"--script", scriptPath,
		"--libpath", libPath,
		"--cwd", cwdAbs,
		"--preview-files", fmt.Sprintf("%t", opts.PreviewFiles),
		"--no-window", fmt.Sprintf("%t", opts.NoWindow),
		"--resolution", fmt.Sprintf("%d,%d", opts.Resolution[0], opts.Resolution[1]),
	)

	if opts.PreviewFiles {
		args = append(args, "--preview-out", opts.PreviewOut)
	}
	if opts.TimeLimit != nil {
		args = append(args, "--time-limit", fmt.Sprintf("%g", *opts.TimeLimit))
	}

	return args
}
