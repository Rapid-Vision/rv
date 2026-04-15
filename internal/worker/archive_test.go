package worker

import (
	"archive/zip"
	"os"
	"path/filepath"
	"slices"
	"testing"
)

func TestCreateDatasetArchive(t *testing.T) {
	datasetDir := t.TempDir()
	if err := os.MkdirAll(filepath.Join(datasetDir, "sample-1"), 0o755); err != nil {
		t.Fatalf("mkdir sample-1: %v", err)
	}
	if err := os.MkdirAll(filepath.Join(datasetDir, "sample-2", "nested"), 0o755); err != nil {
		t.Fatalf("mkdir sample-2 nested: %v", err)
	}
	if err := os.WriteFile(filepath.Join(datasetDir, "_meta.json"), []byte("{}"), 0o644); err != nil {
		t.Fatalf("write _meta.json: %v", err)
	}
	if err := os.WriteFile(filepath.Join(datasetDir, "sample-1", "rgb.png"), []byte("rgb"), 0o644); err != nil {
		t.Fatalf("write sample-1 rgb.png: %v", err)
	}
	if err := os.WriteFile(filepath.Join(datasetDir, "sample-2", "nested", "mask.png"), []byte("mask"), 0o644); err != nil {
		t.Fatalf("write sample-2 nested mask.png: %v", err)
	}

	archivePath, err := createDatasetArchive(datasetDir)
	if err != nil {
		t.Fatalf("createDatasetArchive() error = %v", err)
	}
	if got, want := filepath.Base(archivePath), datasetArchiveName; got != want {
		t.Fatalf("archive name = %q, want %q", got, want)
	}

	rc, err := zip.OpenReader(archivePath)
	if err != nil {
		t.Fatalf("open archive: %v", err)
	}
	defer func() { _ = rc.Close() }()

	names := make([]string, 0, len(rc.File))
	for _, f := range rc.File {
		names = append(names, f.Name)
	}
	slices.Sort(names)

	want := []string{
		"dataset/_meta.json",
		"dataset/sample-1/rgb.png",
		"dataset/sample-2/nested/mask.png",
	}
	if len(names) != len(want) {
		t.Fatalf("archive entries = %v, want %v", names, want)
	}
	for i := range want {
		if names[i] != want[i] {
			t.Fatalf("archive entry[%d] = %q, want %q", i, names[i], want[i])
		}
	}
}

func TestCreateDatasetArchive_RequiresDir(t *testing.T) {
	tmp := t.TempDir()
	filePath := filepath.Join(tmp, "not-a-dir.txt")
	if err := os.WriteFile(filePath, []byte("x"), 0o644); err != nil {
		t.Fatalf("write test file: %v", err)
	}

	if _, err := createDatasetArchive(filePath); err == nil {
		t.Fatal("expected createDatasetArchive to reject file path")
	}
}
