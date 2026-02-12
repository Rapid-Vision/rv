package render

import (
	"os"
	"os/exec"
	"path/filepath"
	"slices"
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
		Resolution: [2]int{640, 640},
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

func TestBuildBlenderRenderArgs_OptionalArgs(t *testing.T) {
	timeLimit := 2.5
	maxSamples := 256
	minSamples := 8
	noiseEnabled := true
	noiseThreshold := 0.02

	opts := RenderOptions{
		ScriptPath:            "/tmp/scene.py",
		Cwd:                   "/tmp",
		Resolution:            [2]int{800, 600},
		TimeLimit:             &timeLimit,
		MaxSamples:            &maxSamples,
		MinSamples:            &minSamples,
		NoiseThresholdEnabled: &noiseEnabled,
		NoiseThreshold:        &noiseThreshold,
	}

	got := buildBlenderRenderArgs(opts, "/tmp/lib", "/tmp/out/1", 3)

	wantPairs := [][]string{
		{"--time-limit", "2.5"},
		{"--max-samples", "256"},
		{"--min-samples", "8"},
		{"--noise-threshold-enabled", "true"},
		{"--noise-threshold", "0.02"},
	}
	for _, pair := range wantPairs {
		idx := slices.Index(got, pair[0])
		if idx < 0 || idx+1 >= len(got) || got[idx+1] != pair[1] {
			t.Fatalf("missing %s %s in args: %v", pair[0], pair[1], got)
		}
	}
}

func TestBuildBlenderRenderArgs_UnsetOptionalArgs(t *testing.T) {
	opts := RenderOptions{
		ScriptPath: "/tmp/scene.py",
		Cwd:        "/tmp",
		Resolution: [2]int{800, 600},
	}

	got := buildBlenderRenderArgs(opts, "/tmp/lib", "/tmp/out/1", 3)
	for _, forbidden := range []string{
		"--time-limit",
		"--max-samples",
		"--min-samples",
		"--noise-threshold-enabled",
		"--noise-threshold",
	} {
		if slices.Contains(got, forbidden) {
			t.Fatalf("did not expect %s in args: %v", forbidden, got)
		}
	}
}

func TestValidateOptionalRenderOptions(t *testing.T) {
	maxSamples := 10
	minSamples := 11
	noiseThreshold := 0.1
	noiseEnabled := false

	err := validateOptionalRenderOptions(RenderOptions{
		MaxSamples:            &maxSamples,
		MinSamples:            &minSamples,
		NoiseThresholdEnabled: &noiseEnabled,
		NoiseThreshold:        &noiseThreshold,
	})

	if err == nil {
		t.Fatal("expected error for invalid optional render options")
	}
	if err.Error() != "--min-samples must be <= --max-samples" {
		t.Fatalf("unexpected error: %v", err)
	}
}
