package render

import (
	"os"
	"os/exec"
	"path/filepath"
	"testing"
)

func TestRender_ReturnsSequentialOutputDir(t *testing.T) {
	blenderPath, err := exec.LookPath("true")
	if err != nil {
		t.Skip("true command is not available")
	}

	tmp := t.TempDir()
	scriptPath := filepath.Join(tmp, "scene.py")
	if err := os.WriteFile(scriptPath, []byte("print('ok')\n"), 0o644); err != nil {
		t.Fatalf("write script: %v", err)
	}
	libPath := filepath.Join(tmp, "rvlib")
	if err := os.MkdirAll(libPath, 0o755); err != nil {
		t.Fatalf("mkdir lib path: %v", err)
	}
	outputRoot := filepath.Join(tmp, "out")

	t.Setenv("BLENDER_PATH", blenderPath)
	t.Setenv("RVLIB_PATH", libPath)

	result, err := Render(RenderOptions{
		ScriptPath: scriptPath,
		Cwd:        tmp,
		ImageNum:   1,
		Procs:      1,
		OutputDir:  outputRoot,
	})
	if err != nil {
		t.Fatalf("Render() error = %v", err)
	}

	want := filepath.Join(outputRoot, "1")
	if result.OutputDir != want {
		t.Fatalf("OutputDir = %q, want %q", result.OutputDir, want)
	}
}
