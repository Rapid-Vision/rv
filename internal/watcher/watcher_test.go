package watcher

import (
	"context"
	"os"
	"path/filepath"
	"sync/atomic"
	"testing"
	"time"
)

func TestWatchFileDebouncesRapidWrites(t *testing.T) {
	t.Parallel()

	dir := t.TempDir()
	target := filepath.Join(dir, "scene.py")
	if err := os.WriteFile(target, []byte("start"), 0o644); err != nil {
		t.Fatalf("failed to create target file: %v", err)
	}

	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()

	var calls int32
	done := make(chan error, 1)
	fired := make(chan struct{}, 1)

	go func() {
		done <- WatchFile(ctx, target, func() {
			atomic.AddInt32(&calls, 1)
			select {
			case fired <- struct{}{}:
			default:
			}
		})
	}()

	// Give fsnotify watcher a moment to start.
	time.Sleep(40 * time.Millisecond)

	for i := 0; i < 3; i++ {
		if err := os.WriteFile(target, []byte(time.Now().String()), 0o644); err != nil {
			t.Fatalf("failed to write target file: %v", err)
		}
		time.Sleep(30 * time.Millisecond)
	}

	select {
	case <-fired:
	case <-time.After(2 * time.Second):
		t.Fatal("expected callback to fire")
	}

	time.Sleep(DEBOUNCE_DELAY + 80*time.Millisecond)
	if got := atomic.LoadInt32(&calls); got != 1 {
		t.Fatalf("expected exactly 1 callback, got %d", got)
	}

	cancel()
	select {
	case err := <-done:
		if err != nil {
			t.Fatalf("watcher returned error: %v", err)
		}
	case <-time.After(2 * time.Second):
		t.Fatal("watcher did not stop after cancel")
	}
}

func TestWatchFileIgnoresOtherFiles(t *testing.T) {
	t.Parallel()

	dir := t.TempDir()
	target := filepath.Join(dir, "scene.py")
	other := filepath.Join(dir, "other.py")
	if err := os.WriteFile(target, []byte("start"), 0o644); err != nil {
		t.Fatalf("failed to create target file: %v", err)
	}
	if err := os.WriteFile(other, []byte("start"), 0o644); err != nil {
		t.Fatalf("failed to create other file: %v", err)
	}

	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()

	var calls int32
	done := make(chan error, 1)
	fired := make(chan struct{}, 1)

	go func() {
		done <- WatchFile(ctx, target, func() {
			atomic.AddInt32(&calls, 1)
			select {
			case fired <- struct{}{}:
			default:
			}
		})
	}()

	time.Sleep(40 * time.Millisecond)

	if err := os.WriteFile(other, []byte("changed"), 0o644); err != nil {
		t.Fatalf("failed to write other file: %v", err)
	}
	time.Sleep(DEBOUNCE_DELAY + 120*time.Millisecond)
	if got := atomic.LoadInt32(&calls); got != 0 {
		t.Fatalf("expected no callback for unrelated file, got %d", got)
	}

	if err := os.WriteFile(target, []byte("changed"), 0o644); err != nil {
		t.Fatalf("failed to write target file: %v", err)
	}
	select {
	case <-fired:
	case <-time.After(2 * time.Second):
		t.Fatal("expected callback after target file write")
	}

	cancel()
	select {
	case err := <-done:
		if err != nil {
			t.Fatalf("watcher returned error: %v", err)
		}
	case <-time.After(2 * time.Second):
		t.Fatal("watcher did not stop after cancel")
	}
}
