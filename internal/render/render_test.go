package render

import (
	"encoding/json"
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
		GPUBackend:            "optix",
		TimeLimit:             &timeLimit,
		MaxSamples:            &maxSamples,
		MinSamples:            &minSamples,
		NoiseThresholdEnabled: &noiseEnabled,
		NoiseThreshold:        &noiseThreshold,
	}

	got := buildBlenderRenderArgs(opts, "/tmp/lib", "/tmp/out/1", 3)

	wantPairs := [][]string{
		{"--gpu-backend", "optix"},
		{"--time-limit", "2.5"},
		{"--max-samples", "256"},
		{"--min-samples", "8"},
		{"--noise-threshold", "0.02"},
	}
	for _, pair := range wantPairs {
		idx := slices.Index(got, pair[0])
		if idx < 0 || idx+1 >= len(got) || got[idx+1] != pair[1] {
			t.Fatalf("missing %s %s in args: %v", pair[0], pair[1], got)
		}
	}
	if !slices.Contains(got, "--noise-threshold-enabled") {
		t.Fatalf("missing --noise-threshold-enabled in args: %v", got)
	}
}

func TestBuildBlenderRenderArgs_UnsetOptionalArgs(t *testing.T) {
	opts := RenderOptions{
		ScriptPath: "/tmp/scene.py",
		Cwd:        "/tmp",
		Resolution: [2]int{800, 600},
	}

	got := buildBlenderRenderArgs(opts, "/tmp/lib", "/tmp/out/1", 3)
	pythonExitIdx := slices.Index(got, "--python-exit-code")
	if pythonExitIdx < 0 || pythonExitIdx+1 >= len(got) || got[pythonExitIdx+1] != "1" {
		t.Fatalf("expected --python-exit-code 1 in args: %v", got)
	}

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

	gpuBackendIdx := slices.Index(got, "--gpu-backend")
	if gpuBackendIdx < 0 || gpuBackendIdx+1 >= len(got) || got[gpuBackendIdx+1] != "auto" {
		t.Fatalf("expected default auto --gpu-backend value in args: %v", got)
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

func TestValidateOptionalRenderOptions_InvalidGPUBackend(t *testing.T) {
	err := validateOptionalRenderOptions(RenderOptions{
		GPUBackend: "invalid",
	})

	if err == nil {
		t.Fatal("expected error for invalid gpu backend")
	}
	if err.Error() != "--gpu-backend must be one of auto, optix, cuda, hip, oneapi, metal, cpu" {
		t.Fatalf("unexpected error: %v", err)
	}
}

func TestWriteDatasetMetadata(t *testing.T) {
	outDir := t.TempDir()
	sampleA := filepath.Join(outDir, "sample-a")
	sampleB := filepath.Join(outDir, "sample-b")
	if err := os.MkdirAll(filepath.Join(sampleA, "nested"), 0o755); err != nil {
		t.Fatalf("mkdir sample-a: %v", err)
	}
	if err := os.MkdirAll(sampleB, 0o755); err != nil {
		t.Fatalf("mkdir sample-b: %v", err)
	}
	if err := os.WriteFile(filepath.Join(sampleA, "nested", "mask.png"), []byte("x"), 0o644); err != nil {
		t.Fatalf("write sample-a file: %v", err)
	}
	if err := os.WriteFile(filepath.Join(sampleA, "_meta.json"), []byte("{}"), 0o644); err != nil {
		t.Fatalf("write sample-a meta: %v", err)
	}
	if err := os.WriteFile(filepath.Join(sampleB, "rgb.png"), []byte("x"), 0o644); err != nil {
		t.Fatalf("write sample-b file: %v", err)
	}

	timeLimit := 1.5
	maxSamples := 128
	opts := RenderOptions{
		ScriptPath: "/tmp/scene.py",
		Cwd:        "/tmp",
		ImageNum:   2,
		Procs:      2,
		Resolution: [2]int{800, 600},
		GPUBackend: "cuda",
		TimeLimit:  &timeLimit,
		MaxSamples: &maxSamples,
	}

	if err := writeDatasetMetadata(outDir, opts); err != nil {
		t.Fatalf("writeDatasetMetadata() error = %v", err)
	}

	raw, err := os.ReadFile(filepath.Join(outDir, "_meta.json"))
	if err != nil {
		t.Fatalf("read dataset _meta.json: %v", err)
	}

	var got datasetMeta
	if err := json.Unmarshal(raw, &got); err != nil {
		t.Fatalf("unmarshal dataset _meta.json: %v", err)
	}

	if got.Resolution != [2]int{800, 600} {
		t.Fatalf("resolution = %v", got.Resolution)
	}
	if got.RenderParams.Number != 2 || got.RenderParams.Procs != 2 {
		t.Fatalf("render params number/procs = %d/%d", got.RenderParams.Number, got.RenderParams.Procs)
	}
	if got.RenderParams.GPUBackend != "cuda" {
		t.Fatalf("gpu_backend = %q", got.RenderParams.GPUBackend)
	}
	if got.RenderParams.TimeLimit == nil || *got.RenderParams.TimeLimit != 1.5 {
		t.Fatalf("time_limit = %v", got.RenderParams.TimeLimit)
	}
	if got.RenderParams.MaxSamples == nil || *got.RenderParams.MaxSamples != 128 {
		t.Fatalf("max_samples = %v", got.RenderParams.MaxSamples)
	}
}
