package worker

import (
	"archive/zip"
	"fmt"
	"io"
	"os"
	"path/filepath"
	"strings"
)

const datasetArchiveName = "_dataset.zip"

func createDatasetArchive(datasetDir string) (string, error) {
	datasetDir = strings.TrimSpace(datasetDir)
	if datasetDir == "" {
		return "", fmt.Errorf("dataset directory is required")
	}

	info, err := os.Stat(datasetDir)
	if err != nil {
		return "", fmt.Errorf("stat dataset directory: %w", err)
	}
	if !info.IsDir() {
		return "", fmt.Errorf("dataset path is not a directory: %s", datasetDir)
	}

	archivePath := filepath.Join(datasetDir, datasetArchiveName)
	out, err := os.Create(archivePath)
	if err != nil {
		return "", fmt.Errorf("create archive file: %w", err)
	}
	defer func() {
		_ = out.Close()
	}()

	zw := zip.NewWriter(out)

	err = filepath.WalkDir(datasetDir, func(path string, d os.DirEntry, walkErr error) error {
		if walkErr != nil {
			return walkErr
		}
		if d.IsDir() {
			return nil
		}

		// Prevent archive self-inclusion.
		if filepath.Clean(path) == filepath.Clean(archivePath) {
			return nil
		}

		rel, err := filepath.Rel(datasetDir, path)
		if err != nil {
			return err
		}
		zipPath := filepath.ToSlash(filepath.Join("dataset", rel))

		src, err := os.Open(path)
		if err != nil {
			return err
		}

		w, err := zw.Create(zipPath)
		if err != nil {
			_ = src.Close()
			return err
		}
		if _, err := io.Copy(w, src); err != nil {
			_ = src.Close()
			return err
		}
		if err := src.Close(); err != nil {
			return err
		}
		return nil
	})
	if err != nil {
		_ = zw.Close()
		return "", fmt.Errorf("build dataset archive: %w", err)
	}

	if err := zw.Close(); err != nil {
		return "", fmt.Errorf("close dataset archive: %w", err)
	}
	if err := out.Close(); err != nil {
		return "", fmt.Errorf("close archive file: %w", err)
	}

	return archivePath, nil
}
