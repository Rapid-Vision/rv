package export

import (
	"os"
	"os/exec"
	"path/filepath"
	"slices"
	"testing"
)

func TestBuildBlenderExportArgs(t *testing.T) {
	got := buildBlenderExportArgs(
		Options{
			ScriptPath:    "/tmp/scene.py",
			Cwd:           "/tmp/work",
			OutputPath:    "/tmp/out/scene.blend",
			FreezePhysics: true,
			PackResources: true,
		},
		"/tmp/lib",
	)

	for _, arg := range []string{"--background", "--python-exit-code", "--python"} {
		if !slices.Contains(got, arg) {
			t.Fatalf("expected %s in args: %v", arg, got)
		}
	}

	wantPairs := [][]string{
		{"--script", "/tmp/scene.py"},
		{"--libpath", "/tmp/lib"},
		{"--output", "/tmp/out/scene.blend"},
		{"--cwd", "/tmp/work"},
		{"--freeze-physics", "true"},
		{"--pack-resources", "true"},
	}
	for _, pair := range wantPairs {
		idx := slices.Index(got, pair[0])
		if idx < 0 || idx+1 >= len(got) || got[idx+1] != pair[1] {
			t.Fatalf("missing %s %s in args: %v", pair[0], pair[1], got)
		}
	}
}

func TestExport_RequiresBlendOutput(t *testing.T) {
	err := Export(Options{
		ScriptPath: "/tmp/scene.py",
		Cwd:        "/tmp",
		OutputPath: "/tmp/out/scene.txt",
	})
	if err == nil {
		t.Fatal("expected error for non-.blend output")
	}
	if err.Error() != "--output must end with .blend" {
		t.Fatalf("unexpected error: %v", err)
	}
}

func TestExport_CreatesParentDirAndRunsBlender(t *testing.T) {
	blenderPath, err := exec.LookPath("true")
	if err != nil {
		t.Skip("true command is not available")
	}

	tmp := t.TempDir()
	libPath := filepath.Join(tmp, "rvlib")
	if err := os.MkdirAll(libPath, 0o755); err != nil {
		t.Fatalf("mkdir lib path: %v", err)
	}

	t.Setenv("BLENDER_PATH", blenderPath)
	t.Setenv("RVLIB_PATH", libPath)

	outputPath := filepath.Join(tmp, "nested", "scene.blend")
	if err := Export(Options{
		ScriptPath: filepath.Join(tmp, "scene.py"),
		Cwd:        tmp,
		OutputPath: outputPath,
	}); err != nil {
		t.Fatalf("Export() error = %v", err)
	}

	if _, err := os.Stat(filepath.Dir(outputPath)); err != nil {
		t.Fatalf("expected parent directory to exist: %v", err)
	}
}
