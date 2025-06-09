package watcher

import (
	"context"
	"path/filepath"

	"github.com/fsnotify/fsnotify"
)

func WatchFile(ctx context.Context, path string, callback func()) error {
	abs, err := filepath.Abs(path)
	if err != nil {
		return err
	}
	dir := filepath.Dir(abs)
	w, err := fsnotify.NewWatcher()
	if err != nil {
		return err
	}
	defer w.Close()

	if err = w.Add(dir); err != nil {
		return err
	}

	for {
		select {
		case <-ctx.Done():
			return nil
		case ev := <-w.Events:
			if ev.Op&fsnotify.Write == fsnotify.Write && ev.Name == abs {
				callback()
			}
		case err = <-w.Errors:
			return err
		}
	}
}
