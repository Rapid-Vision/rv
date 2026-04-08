package export

import (
	"errors"
	"fmt"
	"os"
	"os/exec"
	"path/filepath"

	"github.com/Rapid-Vision/rv/internal/seed"
	"github.com/Rapid-Vision/rv/internal/utils"
)

type Options struct {
	ScriptPath    string
	Cwd           string
	OutputPath    string
	FreezePhysics bool
	PackResources bool
	Seed          seed.Config
}

func Export(opts Options) error {
	if opts.ScriptPath == "" {
		return errors.New("script path is required")
	}
	if opts.Cwd == "" {
		return errors.New("cwd is required")
	}
	if opts.OutputPath == "" {
		return errors.New("output path is required")
	}
	if filepath.Ext(opts.OutputPath) != ".blend" {
		return errors.New("--output must end with .blend")
	}

	blenderPath, err := utils.GetBlenderPath()
	if err != nil {
		return fmt.Errorf("can't find blender path: %w", err)
	}

	libPath, err := utils.GetLibPath()
	if err != nil {
		return fmt.Errorf("can't find rvlib: %w", err)
	}

	if err := os.MkdirAll(filepath.Dir(opts.OutputPath), 0o755); err != nil {
		return fmt.Errorf("create output directory: %w", err)
	}

	cmd := exec.Command(blenderPath, buildBlenderExportArgs(opts, libPath)...)
	cmd.Env = utils.BlenderCommandEnv()
	cmd.Stdout = os.Stdout
	cmd.Stderr = os.Stderr

	if err := cmd.Run(); err != nil {
		return fmt.Errorf("failed to export scene: %w", err)
	}

	return nil
}

func buildBlenderExportArgs(opts Options, libPath string) []string {
	opts.Seed = seed.Normalize(opts.Seed)
	args := []string{
		filepath.Join(libPath, "template.blend"),
		"--factory-startup",
		"--background",
		"--python-exit-code", "1",
		"--python", filepath.Join(libPath, "export.py"),
		"--",
		"--script", opts.ScriptPath,
		"--libpath", libPath,
		"--output", opts.OutputPath,
		"--cwd", opts.Cwd,
		"--seed-mode", string(opts.Seed.Mode),
	}
	if opts.Seed.Mode == seed.FixedMode {
		args = append(args, "--seed-value", fmt.Sprintf("%d", opts.Seed.Value))
	}
	if opts.FreezePhysics {
		args = append(args, "--freeze-physics")
	}
	if opts.PackResources {
		args = append(args, "--pack-resources")
	}
	return args
}
