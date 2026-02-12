package worker

import (
	"os"
	"path/filepath"
	"testing"

	"github.com/Rapid-Vision/rv/internal/assets"
)

func TestBuildTaskWorkDir(t *testing.T) {
	got := buildTaskWorkDir("/tmp/worker", "abc-123")
	want := filepath.Join("/tmp/worker", "abc-123")
	if got != want {
		t.Fatalf("buildTaskWorkDir() = %q, want %q", got, want)
	}
}

func TestResolveManagedTaskRuntimeCwd(t *testing.T) {
	runner := NewRunner(Deps{
		UUIDFn: func() string { return "task-uuid-1" },
	})

	cwd, taskUUID, err := runner.resolveManagedTaskRuntimeCwd("/tmp/worker")
	if err != nil {
		t.Fatalf("resolveManagedTaskRuntimeCwd() error = %v", err)
	}
	if taskUUID != "task-uuid-1" {
		t.Fatalf("taskUUID = %q", taskUUID)
	}
	want := filepath.Join("/tmp/worker", "task-uuid-1")
	if cwd != want {
		t.Fatalf("cwd = %q, want %q", cwd, want)
	}
}

func TestNewRunner_DefaultDeps(t *testing.T) {
	runner := NewRunner(Deps{})
	if runner.deps.UUIDFn == nil {
		t.Fatal("UUIDFn should be initialized")
	}
	if runner.deps.UploadDirFn == nil {
		t.Fatal("UploadDirFn should be initialized")
	}
}

func TestIsManagedResourceSource_LocalScriptUnchanged(t *testing.T) {
	if isManagedResourceSource("scenes/scene.py") {
		t.Fatal("expected local script path to remain non-managed")
	}
}

func TestCleanupWorkerTaskResources(t *testing.T) {
	t.Run("cleanup policy removes staged and task dir", func(t *testing.T) {
		tmp := t.TempDir()
		stagedPath := filepath.Join(tmp, "stage.txt")
		if err := os.WriteFile(stagedPath, []byte("x"), 0o644); err != nil {
			t.Fatalf("write staged file: %v", err)
		}
		taskDir := filepath.Join(tmp, "task-dir")
		if err := os.MkdirAll(taskDir, 0o755); err != nil {
			t.Fatalf("mkdir task dir: %v", err)
		}

		err := cleanupWorkerTaskResources("cleanup", []assets.StagedFile{{Path: stagedPath}}, taskDir)
		if err != nil {
			t.Fatalf("cleanupWorkerTaskResources() error = %v", err)
		}
		if _, err := os.Stat(stagedPath); !os.IsNotExist(err) {
			t.Fatalf("staged file should be removed, stat err=%v", err)
		}
		if _, err := os.Stat(taskDir); !os.IsNotExist(err) {
			t.Fatalf("task dir should be removed, stat err=%v", err)
		}
	})

	t.Run("keep policy leaves resources", func(t *testing.T) {
		tmp := t.TempDir()
		stagedPath := filepath.Join(tmp, "stage.txt")
		if err := os.WriteFile(stagedPath, []byte("x"), 0o644); err != nil {
			t.Fatalf("write staged file: %v", err)
		}
		taskDir := filepath.Join(tmp, "task-dir")
		if err := os.MkdirAll(taskDir, 0o755); err != nil {
			t.Fatalf("mkdir task dir: %v", err)
		}

		err := cleanupWorkerTaskResources("keep", []assets.StagedFile{{Path: stagedPath}}, taskDir)
		if err != nil {
			t.Fatalf("cleanupWorkerTaskResources() error = %v", err)
		}
		if _, err := os.Stat(stagedPath); err != nil {
			t.Fatalf("staged file should remain, stat err=%v", err)
		}
		if _, err := os.Stat(taskDir); err != nil {
			t.Fatalf("task dir should remain, stat err=%v", err)
		}
	})
}
