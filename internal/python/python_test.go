package python

import (
	"os"
	"path/filepath"
	"runtime"
	"testing"
)

func TestInstall_WritesEmbeddedRVPackageToSitePackages(t *testing.T) {
	if runtime.GOOS == "windows" {
		t.Skip("fake interpreter test uses a POSIX shell script")
	}
	tmp := t.TempDir()
	pythonPath, sitePackagesDir := writeFakePython(t, tmp)

	result, err := Install(InstallOptions{PythonPath: pythonPath})
	if err != nil {
		t.Fatalf("Install() error = %v", err)
	}

	if result.SitePackagesDir != sitePackagesDir {
		t.Fatalf("SitePackagesDir = %q, want %q", result.SitePackagesDir, sitePackagesDir)
	}

	got, err := os.ReadFile(result.InstalledPath)
	if err != nil {
		t.Fatalf("read installed file: %v", err)
	}
	if len(got) == 0 {
		t.Fatal("expected installed rv package to be non-empty")
	}
	if filepath.Base(result.InstalledPath) != "__init__.py" {
		t.Fatalf("InstalledPath = %q, want rv/__init__.py", result.InstalledPath)
	}

	markerPath := filepath.Join(sitePackagesDir, "rv", "py.typed")
	marker, err := os.ReadFile(markerPath)
	if err != nil {
		t.Fatalf("read py.typed marker: %v", err)
	}
	if len(marker) != 0 {
		t.Fatalf("py.typed contents = %q, want empty file", string(marker))
	}
}

func TestInstall_UsesActiveVirtualEnvByDefault(t *testing.T) {
	if runtime.GOOS == "windows" {
		t.Skip("fake interpreter test uses a POSIX shell script")
	}
	tmp := t.TempDir()
	pythonPath, sitePackagesDir := writeFakeVenvPython(t, tmp)
	t.Setenv("VIRTUAL_ENV", tmp)

	result, err := Install(InstallOptions{})
	if err != nil {
		t.Fatalf("Install() error = %v", err)
	}

	if result.PythonPath != pythonPath {
		t.Fatalf("PythonPath = %q, want %q", result.PythonPath, pythonPath)
	}
	if result.SitePackagesDir != sitePackagesDir {
		t.Fatalf("SitePackagesDir = %q, want %q", result.SitePackagesDir, sitePackagesDir)
	}
}

func TestInstall_RequiresActiveVirtualEnvWhenPythonPathIsUnset(t *testing.T) {
	t.Setenv("VIRTUAL_ENV", "")

	_, err := Install(InstallOptions{})
	if err == nil {
		t.Fatal("expected error when no active virtual environment is set")
	}
}

func writeFakeVenvPython(t *testing.T, venvDir string) (string, string) {
	t.Helper()
	pythonDir := filepath.Join(venvDir, "bin")
	sitePackagesDir := filepath.Join(venvDir, "lib", "python3.12", "site-packages")
	pythonPath := filepath.Join(pythonDir, "python")
	writeFakePythonScript(t, pythonPath, sitePackagesDir)
	return pythonPath, sitePackagesDir
}

func writeFakePython(t *testing.T, root string) (string, string) {
	t.Helper()
	pythonPath := filepath.Join(root, "python")
	sitePackagesDir := filepath.Join(root, "site-packages")
	writeFakePythonScript(t, pythonPath, sitePackagesDir)
	return pythonPath, sitePackagesDir
}

func writeFakePythonScript(t *testing.T, pythonPath string, sitePackagesDir string) {
	t.Helper()
	if err := os.MkdirAll(filepath.Dir(pythonPath), 0o755); err != nil {
		t.Fatalf("mkdir python dir: %v", err)
	}
	if err := os.MkdirAll(sitePackagesDir, 0o755); err != nil {
		t.Fatalf("mkdir site-packages: %v", err)
	}

	script := "#!/bin/sh\nprintf '%s\\n' \"" + sitePackagesDir + "\"\n"
	if err := os.WriteFile(pythonPath, []byte(script), 0o755); err != nil {
		t.Fatalf("write fake python: %v", err)
	}
}
