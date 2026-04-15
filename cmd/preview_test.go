package cmd

import (
	"os"
	"path/filepath"
	"testing"
)

func TestValidatePreviewFlags(t *testing.T) {
	tests := []struct {
		name        string
		noWindow    bool
		files       bool
		resChanged  bool
		timeChanged bool
		wantError   bool
	}{
		{
			name:        "window mode without files",
			noWindow:    false,
			files:       false,
			resChanged:  false,
			timeChanged: false,
			wantError:   false,
		},
		{
			name:        "headless with files",
			noWindow:    true,
			files:       true,
			resChanged:  false,
			timeChanged: false,
			wantError:   false,
		},
		{
			name:        "headless without files",
			noWindow:    true,
			files:       false,
			resChanged:  false,
			timeChanged: false,
			wantError:   true,
		},
		{
			name:        "resolution requires preview files",
			noWindow:    false,
			files:       false,
			resChanged:  true,
			timeChanged: false,
			wantError:   true,
		},
		{
			name:        "time limit requires preview files",
			noWindow:    false,
			files:       false,
			resChanged:  false,
			timeChanged: true,
			wantError:   true,
		},
	}

	for _, tc := range tests {
		t.Run(tc.name, func(t *testing.T) {
			err := validatePreviewFlags(tc.noWindow, tc.files, tc.resChanged, tc.timeChanged)
			if (err != nil) != tc.wantError {
				t.Fatalf("err = %v, wantError = %v", err, tc.wantError)
			}
		})
	}
}

func TestResolvePreviewOutputDir_DefaultRelativeToProcessCwd(t *testing.T) {
	oldWd, err := os.Getwd()
	if err != nil {
		t.Fatalf("getwd: %v", err)
	}
	defer func() { _ = os.Chdir(oldWd) }()

	tmp := t.TempDir()
	if err := os.Chdir(tmp); err != nil {
		t.Fatalf("chdir: %v", err)
	}

	got, err := resolvePreviewOutputDir(true, "./preview_out")
	if err != nil {
		t.Fatalf("resolvePreviewOutputDir: %v", err)
	}

	want, err := filepath.Abs("./preview_out")
	if err != nil {
		t.Fatalf("resolve expected path: %v", err)
	}
	if filepath.Clean(got) != filepath.Clean(want) {
		t.Fatalf("got = %q, want = %q", got, want)
	}
}

func TestPreviewGenRetainDefault(t *testing.T) {
	genRetainFlag := previewCmd.Flags().Lookup("gen-retain")
	if genRetainFlag == nil {
		t.Fatal("expected gen-retain flag to exist")
	}
	if genRetainFlag.DefValue != "last" {
		t.Fatalf("expected default gen-retain=last, got %q", genRetainFlag.DefValue)
	}
}
