package cmd

import "testing"

func TestIsManagedResourceSource(t *testing.T) {
	tests := []struct {
		name   string
		source string
		want   bool
	}{
		{name: "http", source: "http://example.com/scene.py", want: true},
		{name: "https", source: "https://example.com/scene.py", want: true},
		{name: "s3", source: "s3://bucket/path/scene.py", want: true},
		{name: "file", source: "file:///tmp/scene.py", want: true},
		{name: "local relative path", source: "scenes/scene.py", want: false},
		{name: "local absolute path", source: "/tmp/scene.py", want: false},
		{name: "empty", source: "", want: false},
	}

	for _, tc := range tests {
		t.Run(tc.name, func(t *testing.T) {
			got := isManagedResourceSource(tc.source)
			if got != tc.want {
				t.Fatalf("isManagedResourceSource(%q) = %v, want %v", tc.source, got, tc.want)
			}
		})
	}
}

func TestWorkerScriptDestination(t *testing.T) {
	tests := []struct {
		name   string
		source string
		want   string
	}{
		{
			name:   "s3 filename",
			source: "s3://bucket/path/scene.py",
			want:   "scripts/scene.py",
		},
		{
			name:   "http filename",
			source: "https://example.com/files/scene_main.py",
			want:   "scripts/scene_main.py",
		},
		{
			name:   "fallback filename",
			source: "file://",
			want:   "scripts/script.py",
		},
	}

	for _, tc := range tests {
		t.Run(tc.name, func(t *testing.T) {
			got := workerScriptDestination(tc.source)
			if got != tc.want {
				t.Fatalf("workerScriptDestination(%q) = %q, want %q", tc.source, got, tc.want)
			}
		})
	}
}

func TestWorkerAssetDestination(t *testing.T) {
	tests := []struct {
		name        string
		destination string
		want        string
	}{
		{
			name:        "simple file",
			destination: "a.png",
			want:        "assets/a.png",
		},
		{
			name:        "nested path",
			destination: "textures/a.png",
			want:        "assets/textures/a.png",
		},
	}

	for _, tc := range tests {
		t.Run(tc.name, func(t *testing.T) {
			got := workerAssetDestination(tc.destination)
			if got != tc.want {
				t.Fatalf("workerAssetDestination(%q) = %q, want %q", tc.destination, got, tc.want)
			}
		})
	}
}
