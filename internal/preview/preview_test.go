package preview

import (
	"os"
	"path/filepath"
	"slices"
	"testing"

	"github.com/Rapid-Vision/rv/internal/seed"
)

func TestValidateOptions(t *testing.T) {
	tests := []struct {
		name    string
		opts    Options
		wantErr bool
	}{
		{
			name: "default window mode",
			opts: Options{
				Resolution: [2]int{640, 640},
			},
		},
		{
			name: "headless requires preview files",
			opts: Options{
				NoWindow:   true,
				Resolution: [2]int{640, 640},
			},
			wantErr: true,
		},
		{
			name: "preview files requires output",
			opts: Options{
				PreviewFiles: true,
				Resolution:   [2]int{640, 640},
			},
			wantErr: true,
		},
		{
			name: "valid files headless",
			opts: Options{
				PreviewFiles: true,
				PreviewOut:   "/tmp/preview_out",
				NoWindow:     true,
				Resolution:   [2]int{640, 640},
			},
		},
		{
			name: "invalid time limit",
			opts: Options{
				PreviewFiles: true,
				PreviewOut:   "/tmp/preview_out",
				Resolution:   [2]int{640, 640},
				TimeLimit:    floatPtr(0),
			},
			wantErr: true,
		},
		{
			name: "invalid gpu backend",
			opts: Options{
				Resolution: [2]int{640, 640},
				GPUBackend: "invalid",
			},
			wantErr: true,
		},
	}

	for _, tc := range tests {
		t.Run(tc.name, func(t *testing.T) {
			err := validateOptions(tc.opts)
			if (err != nil) != tc.wantErr {
				t.Fatalf("err = %v, wantErr = %v", err, tc.wantErr)
			}
		})
	}
}

func TestBuildBlenderPreviewArgs(t *testing.T) {
	libPath := "/lib/rvlib"
	opts := Options{
		PreviewFiles:  true,
		PreviewOut:    "/tmp/preview_out",
		NoWindow:      true,
		Resolution:    [2]int{1280, 720},
		GPUBackend:    "optix",
		TimeLimit:     floatPtr(2.5),
		Seed:          seed.Config{Mode: seed.FixedMode, Value: 17},
		GeneratorPort: 9911,
		GenRetain:     "last",
	}
	args := buildBlenderPreviewArgs(opts, "/work/scene.py", "/work", "/work/generated", libPath, 12345)

	wantPreviewPy := filepath.Join(libPath, "preview.py")
	wantTemplate := filepath.Join(libPath, "template.blend")

	assertContains(t, args, wantTemplate)
	assertContains(t, args, "--factory-startup")
	assertContains(t, args, "--background")
	assertContains(t, args, "--python")
	assertContains(t, args, wantPreviewPy)
	assertContains(t, args, "--port")
	assertContains(t, args, "12345")
	assertContains(t, args, "--script")
	assertContains(t, args, "/work/scene.py")
	assertContains(t, args, "--root-dir")
	assertContains(t, args, "/work")
	assertContains(t, args, "--gen-base-dir")
	assertContains(t, args, "/work/generated")
	assertContains(t, args, "--gen-retain")
	assertContains(t, args, "last")
	assertContains(t, args, "--preview-files")
	assertContains(t, args, "--no-window")
	assertContains(t, args, "--preview-out")
	assertContains(t, args, "/tmp/preview_out")
	assertContains(t, args, "--resolution")
	assertContains(t, args, "1280,720")
	assertContains(t, args, "--gpu-backend")
	assertContains(t, args, "optix")
	assertContains(t, args, "--seed-mode")
	assertContains(t, args, "fixed")
	assertContains(t, args, "--generator-port")
	assertContains(t, args, "9911")
	assertContains(t, args, "--seed-value")
	assertContains(t, args, "17")
	assertContains(t, args, "--time-limit")
	assertContains(t, args, "2.5")
}

func TestBuildBlenderPreviewArgs_NoWindowModeDisabled(t *testing.T) {
	args := buildBlenderPreviewArgs(
		Options{PreviewFiles: false, NoWindow: false, Resolution: [2]int{640, 640}, Seed: seed.Config{Mode: seed.RandomMode}, GenRetain: "last"},
		"/work/scene.py",
		"/work",
		"/work/generated",
		"/lib/rvlib",
		5757,
	)
	assertNotContains(t, args, "--background")
	assertNotContains(t, args, "--preview-out")
	assertNotContains(t, args, "--preview-files")
	assertNotContains(t, args, "--no-window")
	assertContains(t, args, "--gpu-backend")
	assertContains(t, args, "auto")
	assertContains(t, args, "--seed-mode")
	assertContains(t, args, "rand")
	assertNotContains(t, args, "--seed-value")
}

func TestStdinSupportsCommands(t *testing.T) {
	if stdinSupportsCommands(nil) {
		t.Fatal("expected nil stdin to be unsupported")
	}

	file, err := os.CreateTemp(t.TempDir(), "stdin-*")
	if err != nil {
		t.Fatalf("create temp file: %v", err)
	}
	defer func() { _ = file.Close() }()

	if stdinSupportsCommands(file) {
		t.Fatal("expected regular file stdin to be unsupported")
	}
}

func floatPtr(v float64) *float64 {
	return &v
}

func assertContains(t *testing.T, values []string, needle string) {
	t.Helper()
	if slices.Contains(values, needle) {
		return
	}
	t.Fatalf("expected %q in %v", needle, values)
}

func assertNotContains(t *testing.T, values []string, needle string) {
	t.Helper()
	for _, value := range values {
		if value == needle {
			t.Fatalf("did not expect %q in %v", needle, values)
		}
	}
}
