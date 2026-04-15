package utils

import (
	"errors"
	"os"
	"path/filepath"
	"runtime"
	"strings"
	"testing"
)

func TestResolveRuntimePaths_DefaultsToScriptDir(t *testing.T) {
	tmp := t.TempDir()
	scriptDir := filepath.Join(tmp, "scenes")
	if err := os.MkdirAll(scriptDir, 0o755); err != nil {
		t.Fatalf("mkdir script dir: %v", err)
	}
	scriptPath := filepath.Join(scriptDir, "scene.py")
	if err := os.WriteFile(scriptPath, []byte("print('ok')"), 0o644); err != nil {
		t.Fatalf("write script: %v", err)
	}

	oldWD, err := os.Getwd()
	if err != nil {
		t.Fatalf("getwd: %v", err)
	}
	defer func() { _ = os.Chdir(oldWD) }()
	if err := os.Chdir(tmp); err != nil {
		t.Fatalf("chdir: %v", err)
	}

	paths, err := ResolveRuntimePaths(filepath.Join("scenes", "scene.py"), "")
	if err != nil {
		t.Fatalf("resolve runtime paths: %v", err)
	}
	if !samePath(paths.ScriptPath, scriptPath) {
		t.Fatalf("unexpected script path: got=%q want=%q", paths.ScriptPath, scriptPath)
	}
	if !samePath(paths.Cwd, scriptDir) {
		t.Fatalf("unexpected cwd: got=%q want=%q", paths.Cwd, scriptDir)
	}
}

func TestResolveRenderPaths_WithExplicitCwd(t *testing.T) {
	tmp := t.TempDir()
	cwd := filepath.Join(tmp, "work")

	oldWD, err := os.Getwd()
	if err != nil {
		t.Fatalf("getwd: %v", err)
	}
	defer func() { _ = os.Chdir(oldWD) }()
	if err := os.Chdir(tmp); err != nil {
		t.Fatalf("chdir: %v", err)
	}

	paths, err := ResolveRenderPaths("scripts/scene.py", "./out", cwd)
	if err != nil {
		t.Fatalf("resolve render paths: %v", err)
	}

	wantScript := filepath.Join(cwd, "scripts", "scene.py")
	wantOutput, err := filepath.Abs("./out")
	if err != nil {
		t.Fatalf("resolve expected output path: %v", err)
	}
	wantCwd := cwd

	if !samePath(paths.ScriptPath, wantScript) {
		t.Fatalf("unexpected script path: got=%q want=%q", paths.ScriptPath, wantScript)
	}
	if !samePath(paths.OutputDir, wantOutput) {
		t.Fatalf("unexpected output dir: got=%q want=%q", paths.OutputDir, wantOutput)
	}
	if !samePath(paths.Cwd, wantCwd) {
		t.Fatalf("unexpected cwd: got=%q want=%q", paths.Cwd, wantCwd)
	}
}

func TestResolveExportPaths_WithExplicitCwd(t *testing.T) {
	tmp := t.TempDir()
	cwd := filepath.Join(tmp, "work")

	oldWD, err := os.Getwd()
	if err != nil {
		t.Fatalf("getwd: %v", err)
	}
	defer func() { _ = os.Chdir(oldWD) }()
	if err := os.Chdir(tmp); err != nil {
		t.Fatalf("chdir: %v", err)
	}

	paths, err := ResolveExportPaths("scripts/scene.py", "./out/scene.blend", cwd)
	if err != nil {
		t.Fatalf("resolve export paths: %v", err)
	}

	wantScript := filepath.Join(cwd, "scripts", "scene.py")
	wantOutput, err := filepath.Abs("./out/scene.blend")
	if err != nil {
		t.Fatalf("resolve expected output path: %v", err)
	}
	wantCwd := cwd

	if !samePath(paths.ScriptPath, wantScript) {
		t.Fatalf("unexpected script path: got=%q want=%q", paths.ScriptPath, wantScript)
	}
	if !samePath(paths.OutputPath, wantOutput) {
		t.Fatalf("unexpected output path: got=%q want=%q", paths.OutputPath, wantOutput)
	}
	if !samePath(paths.Cwd, wantCwd) {
		t.Fatalf("unexpected cwd: got=%q want=%q", paths.Cwd, wantCwd)
	}
}

func TestResolveGeneratorPaths_DefaultsToRootGenerated(t *testing.T) {
	rootDir := filepath.Join(t.TempDir(), "scene-root")
	paths, err := ResolveGeneratorPaths(rootDir, "")
	if err != nil {
		t.Fatalf("resolve generator paths: %v", err)
	}

	if !samePath(paths.RootDir, rootDir) {
		t.Fatalf("unexpected root dir: got=%q want=%q", paths.RootDir, rootDir)
	}
	if !samePath(paths.GenBaseDir, filepath.Join(rootDir, "generated")) {
		t.Fatalf("unexpected generator base dir: got=%q", paths.GenBaseDir)
	}
}

func TestResolveGeneratorPaths_ResolvesRelativeGenDirAgainstRoot(t *testing.T) {
	rootDir := filepath.Join(t.TempDir(), "scene-root")
	paths, err := ResolveGeneratorPaths(rootDir, "cache/gen")
	if err != nil {
		t.Fatalf("resolve generator paths: %v", err)
	}

	wantBase := filepath.Join(rootDir, "cache", "gen")
	if !samePath(paths.GenBaseDir, wantBase) {
		t.Fatalf("unexpected generator base dir: got=%q want=%q", paths.GenBaseDir, wantBase)
	}
}

func TestResolveGeneratorPaths_AllowsAbsoluteGenDir(t *testing.T) {
	tmp := t.TempDir()
	rootDir := filepath.Join(tmp, "scene-root")
	genDir := filepath.Join(tmp, "shared-gen")

	paths, err := ResolveGeneratorPaths(rootDir, genDir)
	if err != nil {
		t.Fatalf("resolve generator paths: %v", err)
	}

	if !samePath(paths.GenBaseDir, genDir) {
		t.Fatalf("unexpected generator base dir: got=%q want=%q", paths.GenBaseDir, genDir)
	}
}

func TestAllocateGeneratorWorkDir_CreatesUUIDSubdir(t *testing.T) {
	genBaseDir := filepath.Join(t.TempDir(), "generated")

	workDir, err := AllocateGeneratorWorkDir(genBaseDir)
	if err != nil {
		t.Fatalf("allocate generator work dir: %v", err)
	}

	if !strings.HasPrefix(workDir, genBaseDir+string(filepath.Separator)) {
		t.Fatalf("unexpected work dir: got=%q", workDir)
	}
	if !strings.HasPrefix(filepath.Base(workDir), generatorWorkDirPrefix) {
		t.Fatalf("expected work dir name to start with %q, got %q", generatorWorkDirPrefix, filepath.Base(workDir))
	}
	if _, err := os.Stat(workDir); err != nil {
		t.Fatalf("stat work dir: %v", err)
	}
}

func TestParseGeneratorRetention(t *testing.T) {
	for _, raw := range []string{"all", "last", "none", " LAST "} {
		if _, err := ParseGeneratorRetention(raw); err != nil {
			t.Fatalf("parse retention %q: %v", raw, err)
		}
	}
	if _, err := ParseGeneratorRetention("bad"); err == nil {
		t.Fatal("expected invalid retention error")
	}
}

func TestCleanupGeneratorWorkDirs_RetainAll(t *testing.T) {
	genBaseDir := filepath.Join(t.TempDir(), "generated")
	keepDir := mustMkdirAll(t, filepath.Join(genBaseDir, "keep"))
	otherDir := mustMkdirAll(t, filepath.Join(genBaseDir, "other"))

	if err := CleanupGeneratorWorkDirs(genBaseDir, GeneratorRetainAll, keepDir); err != nil {
		t.Fatalf("cleanup retain all: %v", err)
	}
	assertExists(t, keepDir)
	assertExists(t, otherDir)
}

func TestCleanupGeneratorWorkDirs_RetainLast(t *testing.T) {
	genBaseDir := filepath.Join(t.TempDir(), "generated")
	keepDir := mustMkdirAll(t, filepath.Join(genBaseDir, generatorWorkDirPrefix+"keep"))
	otherDir := mustMkdirAll(t, filepath.Join(genBaseDir, generatorWorkDirPrefix+"other"))
	unmanagedDir := mustMkdirAll(t, filepath.Join(genBaseDir, "other"))

	if err := CleanupGeneratorWorkDirs(genBaseDir, GeneratorRetainLast, keepDir); err != nil {
		t.Fatalf("cleanup retain last: %v", err)
	}
	assertExists(t, keepDir)
	assertNotExists(t, otherDir)
	assertExists(t, unmanagedDir)
}

func TestCleanupGeneratorWorkDirs_RetainNone(t *testing.T) {
	genBaseDir := filepath.Join(t.TempDir(), "generated")
	keepDir := mustMkdirAll(t, filepath.Join(genBaseDir, generatorWorkDirPrefix+"keep"))
	otherDir := mustMkdirAll(t, filepath.Join(genBaseDir, generatorWorkDirPrefix+"other"))
	unmanagedDir := mustMkdirAll(t, filepath.Join(genBaseDir, "other"))

	if err := CleanupGeneratorWorkDirs(genBaseDir, GeneratorRetainNone, keepDir); err != nil {
		t.Fatalf("cleanup retain none: %v", err)
	}
	assertNotExists(t, keepDir)
	assertNotExists(t, otherDir)
	assertExists(t, unmanagedDir)
}

func TestCleanupGeneratorWorkDirs_IgnoresUnmanagedDirectories(t *testing.T) {
	genBaseDir := filepath.Join(t.TempDir(), "generated")
	keepDir := mustMkdirAll(t, filepath.Join(genBaseDir, generatorWorkDirPrefix+"keep"))
	unmanagedDir := mustMkdirAll(t, filepath.Join(genBaseDir, "shared"))

	if err := CleanupGeneratorWorkDirs(genBaseDir, GeneratorRetainLast, keepDir); err != nil {
		t.Fatalf("cleanup retain last: %v", err)
	}

	assertExists(t, keepDir)
	assertExists(t, unmanagedDir)
}

func mustMkdirAll(t *testing.T, path string) string {
	t.Helper()
	if err := os.MkdirAll(path, 0o755); err != nil {
		t.Fatalf("mkdir %q: %v", path, err)
	}
	return path
}

func assertExists(t *testing.T, path string) {
	t.Helper()
	if _, err := os.Stat(path); err != nil {
		t.Fatalf("expected %q to exist: %v", path, err)
	}
}

func assertNotExists(t *testing.T, path string) {
	t.Helper()
	if _, err := os.Stat(path); !errors.Is(err, os.ErrNotExist) {
		t.Fatalf("expected %q not to exist, got err=%v", path, err)
	}
}

func samePath(a string, b string) bool {
	aEval, aErr := filepath.EvalSymlinks(a)
	if aErr != nil {
		aEval = filepath.Clean(a)
	}
	bEval, bErr := filepath.EvalSymlinks(b)
	if bErr != nil {
		bEval = filepath.Clean(b)
	}
	return aEval == bEval
}

func TestValidateRelativePath(t *testing.T) {
	if _, err := ValidateRelativePath("../escape.txt"); err == nil {
		t.Fatal("expected escape path validation error")
	}
	if _, err := ValidateRelativePath("/abs/path.txt"); err == nil {
		t.Fatal("expected absolute path validation error")
	}
	if got, err := ValidateRelativePath("assets/a.png"); err != nil || got != filepath.Clean("assets/a.png") {
		t.Fatalf("unexpected validation result: got=%q err=%v", got, err)
	}
}

func TestBlenderCommandEnv_RemovesVirtualEnvPythonOverrides(t *testing.T) {
	venvDir := filepath.Join(t.TempDir(), ".venv")
	venvBinDir := filepath.Join(venvDir, "bin")
	if runtime.GOOS == "windows" {
		venvBinDir = filepath.Join(venvDir, "Scripts")
	}

	t.Setenv("VIRTUAL_ENV", venvDir)
	t.Setenv("PYTHONHOME", "/tmp/python-home")
	t.Setenv("PYTHONPATH", "/tmp/python-path")
	t.Setenv("PYTHONSTARTUP", "/tmp/python-startup.py")
	t.Setenv("PYTHONUSERBASE", "/tmp/python-userbase")
	t.Setenv("__PYVENV_LAUNCHER__", "/tmp/pyvenv-launcher")
	t.Setenv("PATH", strings.Join([]string{venvBinDir, "/usr/bin", "/bin"}, string(os.PathListSeparator)))
	t.Setenv("HOME", "/tmp/home")

	env := BlenderCommandEnv()
	got := envMap(env)

	for _, key := range []string{
		"VIRTUAL_ENV",
		"PYTHONHOME",
		"PYTHONPATH",
		"PYTHONSTARTUP",
		"PYTHONUSERBASE",
		"__PYVENV_LAUNCHER__",
	} {
		if _, exists := got[key]; exists {
			t.Fatalf("did not expect %s in BlenderCommandEnv", key)
		}
	}

	if got["HOME"] != "/tmp/home" {
		t.Fatalf("expected unrelated env var to be preserved, got HOME=%q", got["HOME"])
	}
	if strings.Contains(got["PATH"], venvBinDir) {
		t.Fatalf("expected PATH not to include virtualenv bin dir, got %q", got["PATH"])
	}
	if !strings.Contains(got["PATH"], "/usr/bin") {
		t.Fatalf("expected PATH to keep non-venv entries, got %q", got["PATH"])
	}
}

func envMap(env []string) map[string]string {
	result := make(map[string]string, len(env))
	for _, entry := range env {
		key, value, found := strings.Cut(entry, "=")
		if !found {
			continue
		}
		result[key] = value
	}
	return result
}
