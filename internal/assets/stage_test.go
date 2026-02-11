package assets

import (
	"context"
	"net/http"
	"net/http/httptest"
	"os"
	"path/filepath"
	"testing"
)

func TestStageMappings_LocalSource(t *testing.T) {
	tmp := t.TempDir()
	source := filepath.Join(tmp, "source.txt")
	if err := os.WriteFile(source, []byte("hello"), 0o644); err != nil {
		t.Fatalf("write source: %v", err)
	}

	staged, err := StageMappings(context.Background(), filepath.Join(tmp, "cwd"), []Mapping{
		{Source: source, Destination: "assets/source.txt"},
	})
	if err != nil {
		t.Fatalf("stage mappings: %v", err)
	}
	if len(staged) != 1 {
		t.Fatalf("unexpected staged length: %d", len(staged))
	}

	dst := filepath.Join(tmp, "cwd", "assets", "source.txt")
	content, err := os.ReadFile(dst)
	if err != nil {
		t.Fatalf("read staged file: %v", err)
	}
	if string(content) != "hello" {
		t.Fatalf("unexpected staged content: %q", string(content))
	}
}

func TestStageMappings_HTTPSource(t *testing.T) {
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		_, _ = w.Write([]byte("from-http"))
	}))
	defer server.Close()

	tmp := t.TempDir()
	_, err := StageMappings(context.Background(), tmp, []Mapping{
		{Source: server.URL + "/file.txt", Destination: "data/file.txt"},
	})
	if err != nil {
		t.Fatalf("stage mappings: %v", err)
	}

	content, err := os.ReadFile(filepath.Join(tmp, "data", "file.txt"))
	if err != nil {
		t.Fatalf("read staged file: %v", err)
	}
	if string(content) != "from-http" {
		t.Fatalf("unexpected content: %q", string(content))
	}
}

func TestStageMappings_RejectsTraversalAndDuplicate(t *testing.T) {
	tmp := t.TempDir()
	source := filepath.Join(tmp, "source.txt")
	if err := os.WriteFile(source, []byte("x"), 0o644); err != nil {
		t.Fatalf("write source: %v", err)
	}

	if _, err := StageMappings(context.Background(), tmp, []Mapping{
		{Source: source, Destination: "../escape.txt"},
	}); err == nil {
		t.Fatal("expected traversal validation error")
	}

	if _, err := StageMappings(context.Background(), tmp, []Mapping{
		{Source: source, Destination: "a/file.txt"},
		{Source: source, Destination: "a/file.txt"},
	}); err == nil {
		t.Fatal("expected duplicate destination error")
	}
}

func TestStageMappings_ReturnsPartialStagedFilesOnError(t *testing.T) {
	tmp := t.TempDir()
	source := filepath.Join(tmp, "source.txt")
	if err := os.WriteFile(source, []byte("ok"), 0o644); err != nil {
		t.Fatalf("write source: %v", err)
	}

	staged, err := StageMappings(context.Background(), tmp, []Mapping{
		{Source: source, Destination: "a/first.txt"},
		{Source: filepath.Join(tmp, "missing.txt"), Destination: "a/second.txt"},
	})
	if err == nil {
		t.Fatal("expected staging error")
	}
	if len(staged) != 2 {
		t.Fatalf("expected two tracked destinations before failure, got=%d", len(staged))
	}
	if staged[0].Destination != filepath.Clean("a/first.txt") {
		t.Fatalf("unexpected staged destination: %q", staged[0].Destination)
	}
	if staged[1].Destination != filepath.Clean("a/second.txt") {
		t.Fatalf("unexpected staged destination: %q", staged[1].Destination)
	}
}

func TestStageMappings_RejectsExistingDestination(t *testing.T) {
	tmp := t.TempDir()
	source := filepath.Join(tmp, "source.txt")
	if err := os.WriteFile(source, []byte("new"), 0o644); err != nil {
		t.Fatalf("write source: %v", err)
	}

	existingPath := filepath.Join(tmp, "assets", "exists.txt")
	if err := os.MkdirAll(filepath.Dir(existingPath), 0o755); err != nil {
		t.Fatalf("mkdir existing dir: %v", err)
	}
	if err := os.WriteFile(existingPath, []byte("old"), 0o644); err != nil {
		t.Fatalf("write existing file: %v", err)
	}

	if _, err := StageMappings(context.Background(), tmp, []Mapping{
		{Source: source, Destination: "assets/exists.txt"},
	}); err == nil {
		t.Fatal("expected destination already exists error")
	}

	content, err := os.ReadFile(existingPath)
	if err != nil {
		t.Fatalf("read existing file: %v", err)
	}
	if string(content) != "old" {
		t.Fatalf("existing file should remain unchanged, got=%q", string(content))
	}
}

func TestIsWindowsAbsPath(t *testing.T) {
	if !isWindowsAbsPath(`C:\assets\foo.png`) {
		t.Fatal("expected drive-letter path to be detected as windows absolute path")
	}
	if isWindowsAbsPath("assets/foo.png") {
		t.Fatal("expected relative path to not be detected as windows absolute path")
	}
}

func TestCleanupStagedFiles(t *testing.T) {
	tmp := t.TempDir()
	path := filepath.Join(tmp, "file.txt")
	if err := os.WriteFile(path, []byte("x"), 0o644); err != nil {
		t.Fatalf("write file: %v", err)
	}

	if err := CleanupStagedFiles([]StagedFile{{Path: path}}); err != nil {
		t.Fatalf("cleanup staged files: %v", err)
	}
	if _, err := os.Stat(path); !os.IsNotExist(err) {
		t.Fatalf("expected file to be removed, stat err=%v", err)
	}
}
