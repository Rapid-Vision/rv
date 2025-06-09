package rvlib

import (
	"embed"
	"io/fs"
	"os"
	"path/filepath"
)

//go:embed rvlib/*
var embeddedRVLib embed.FS

func UnpackRVLib(targetDir string) error {
	if err := os.MkdirAll(targetDir, 0755); err != nil {
		panic(err)
	}

	err := fs.WalkDir(embeddedRVLib, "rvlib", func(path string, d fs.DirEntry, err error) error {
		if err != nil {
			return err
		}
		if d.IsDir() {
			return nil
		}

		data, err := embeddedRVLib.ReadFile(path)
		if err != nil {
			return err
		}

		relPath, _ := filepath.Rel("rvlib", path)
		outPath := filepath.Join(targetDir, relPath)
		if err := os.MkdirAll(filepath.Dir(outPath), 0755); err != nil {
			return err
		}
		return os.WriteFile(outPath, data, 0644)
	})
	return err
}
