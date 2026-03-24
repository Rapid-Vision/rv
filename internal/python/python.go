package python

import (
	"bytes"
	"errors"
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"runtime"
	"strings"

	"github.com/Rapid-Vision/rv/rvlib"
)

type InstallOptions struct {
	PythonPath string
}

type InstallResult struct {
	PythonPath      string
	SitePackagesDir string
	InstalledPath   string
}

func Install(opts InstallOptions) (InstallResult, error) {
	pythonPath := opts.PythonPath
	if pythonPath == "" {
		var err error
		pythonPath, err = activeVenvPythonPath()
		if err != nil {
			return InstallResult{}, err
		}
	}

	sitePackagesDir, err := sitePackagesPath(pythonPath)
	if err != nil {
		return InstallResult{}, err
	}

	rvSource, err := rvlib.ReadEmbeddedFile("rv.py")
	if err != nil {
		return InstallResult{}, err
	}

	packageDir := filepath.Join(sitePackagesDir, "rv")
	if err := os.MkdirAll(packageDir, 0o755); err != nil {
		return InstallResult{}, fmt.Errorf("create package directory: %w", err)
	}

	installedPath := filepath.Join(packageDir, "__init__.py")
	if err := os.WriteFile(installedPath, rvSource, 0o644); err != nil {
		return InstallResult{}, fmt.Errorf("write rv package: %w", err)
	}

	return InstallResult{
		PythonPath:      pythonPath,
		SitePackagesDir: sitePackagesDir,
		InstalledPath:   installedPath,
	}, nil
}

func activeVenvPythonPath() (string, error) {
	virtualEnv := strings.TrimSpace(os.Getenv("VIRTUAL_ENV"))
	if virtualEnv == "" {
		return "", errors.New("no active virtual environment found; activate a venv first")
	}

	pythonPath := filepath.Join(virtualEnv, "bin", "python")
	if runtime.GOOS == "windows" {
		pythonPath = filepath.Join(virtualEnv, "Scripts", "python.exe")
	}
	if _, err := os.Stat(pythonPath); err != nil {
		return "", fmt.Errorf("python executable was not found in active virtual environment: %w", err)
	}

	return pythonPath, nil
}

func sitePackagesPath(pythonPath string) (string, error) {
	cmd := exec.Command(
		pythonPath,
		"-c",
		"import sysconfig; print(sysconfig.get_paths()['purelib'])",
	)
	var stdout bytes.Buffer
	var stderr bytes.Buffer
	cmd.Stdout = &stdout
	cmd.Stderr = &stderr

	if err := cmd.Run(); err != nil {
		msg := strings.TrimSpace(stderr.String())
		if msg == "" {
			msg = err.Error()
		}
		return "", fmt.Errorf("resolve site-packages with %q: %s", pythonPath, msg)
	}

	sitePackagesDir := filepath.Clean(strings.TrimSpace(stdout.String()))
	if sitePackagesDir == "" {
		return "", errors.New("python returned an empty site-packages path")
	}
	return sitePackagesDir, nil
}
