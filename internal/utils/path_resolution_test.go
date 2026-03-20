package utils

import (
	"os"
	"path/filepath"
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
