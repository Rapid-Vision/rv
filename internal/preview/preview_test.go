package preview

import (
	"path/filepath"
	"testing"
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
		PreviewFiles: true,
		PreviewOut:   "/tmp/preview_out",
		NoWindow:     true,
		Resolution:   [2]int{1280, 720},
		GPUBackend:   "optix",
		TimeLimit:    floatPtr(2.5),
	}
	args := buildBlenderPreviewArgs(opts, "/work/scene.py", "/work", libPath, 12345)

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
	assertContains(t, args, "--cwd")
	assertContains(t, args, "/work")
	assertContains(t, args, "--preview-files")
	assertContains(t, args, "--no-window")
	assertContains(t, args, "--preview-out")
	assertContains(t, args, "/tmp/preview_out")
	assertContains(t, args, "--resolution")
	assertContains(t, args, "1280,720")
	assertContains(t, args, "--gpu-backend")
	assertContains(t, args, "optix")
	assertContains(t, args, "--time-limit")
	assertContains(t, args, "2.5")
}

func TestBuildBlenderPreviewArgs_NoWindowModeDisabled(t *testing.T) {
	args := buildBlenderPreviewArgs(
		Options{PreviewFiles: false, NoWindow: false, Resolution: [2]int{640, 640}},
		"/work/scene.py",
		"/work",
		"/lib/rvlib",
		5757,
	)
	assertNotContains(t, args, "--background")
	assertNotContains(t, args, "--preview-out")
	assertNotContains(t, args, "--preview-files")
	assertNotContains(t, args, "--no-window")
	assertContains(t, args, "--gpu-backend")
	assertContains(t, args, "auto")
}

func floatPtr(v float64) *float64 {
	return &v
}

func assertContains(t *testing.T, values []string, needle string) {
	t.Helper()
	for _, value := range values {
		if value == needle {
			return
		}
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
