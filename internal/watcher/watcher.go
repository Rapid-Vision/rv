package watcher

import (
	"context"
	"path/filepath"
	"time"

	"github.com/fsnotify/fsnotify"
)

const DEBOUNCE_DELAY = 150 * time.Millisecond

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
	defer func() { _ = w.Close() }()

	if err = w.Add(dir); err != nil {
		return err
	}

	var debounce *time.Timer
	var debounceCh <-chan time.Time

	enqueue := func() {
		if debounce == nil {
			debounce = time.NewTimer(DEBOUNCE_DELAY)
			debounceCh = debounce.C
			return
		}
		if !debounce.Stop() {
			select {
			case <-debounce.C:
			default:
			}
		}
		debounce.Reset(DEBOUNCE_DELAY)
	}

	for {
		select {
		case <-ctx.Done():
			if debounce != nil {
				debounce.Stop()
			}
			return nil
		case ev := <-w.Events:
			if ev.Name == abs && (ev.Op&fsnotify.Write == fsnotify.Write || ev.Op&fsnotify.Create == fsnotify.Create || ev.Op&fsnotify.Rename == fsnotify.Rename) {
				enqueue()
			}
		case <-debounceCh:
			callback()
			debounce = nil
			debounceCh = nil
		case err = <-w.Errors:
			return err
		}
	}
}
