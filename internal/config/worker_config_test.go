package config_test

import (
	"os"
	"path/filepath"
	"testing"
	"time"

	"github.com/Rapid-Vision/rv/internal/config"
)

func TestLoadWorkerConfig(t *testing.T) {
	tmp := t.TempDir()
	configPath := filepath.Join(tmp, "worker.yaml")
	content := []byte(`worker:
  worker_name: render-1
  task_name: render
  rtasks:
    url: http://localhost:5701
    token: secret_token
    poll_interval: 3s
    heartbeat_interval: 7s
  directories:
    working: ./tmp/
    output: ./out/
    cleanup_policy: cleanup
  s3:
    endpoint: localhost:6000
    path: /rv-results/datasets
    region: us-east-1
    secure: false
    cleanup: true
    access_key: minioadmin
    secret_key: minioadmin
`)
	if err := os.WriteFile(configPath, content, 0o644); err != nil {
		t.Fatalf("write config: %v", err)
	}

	cfg, err := config.LoadWorkerConfig(configPath)
	if err != nil {
		t.Fatalf("loadWorkerConfig() error = %v", err)
	}
	if cfg.WorkerName != "render-1" || cfg.TaskName != "render" {
		t.Fatalf("unexpected worker identity: %#v", cfg)
	}
	if cfg.RTasks.PollInterval != 3*time.Second {
		t.Fatalf("poll interval = %v", cfg.RTasks.PollInterval)
	}
	if cfg.RTasks.HeartbeatInterval != 7*time.Second {
		t.Fatalf("heartbeat interval = %v", cfg.RTasks.HeartbeatInterval)
	}
	if cfg.S3.Path != "/rv-results/datasets" || cfg.S3.Secure {
		t.Fatalf("unexpected s3 config: %#v", cfg.S3)
	}
	if cfg.S3.AccessKeyID != "minioadmin" || cfg.S3.SecretKey != "minioadmin" {
		t.Fatalf("unexpected s3 creds: %#v", cfg.S3)
	}
}

func TestLoadWorkerConfig_Defaults(t *testing.T) {
	tmp := t.TempDir()
	configPath := filepath.Join(tmp, "worker.yaml")
	content := []byte(`worker:
  worker_name: render-1
  task_name: render
  rtasks:
    url: http://localhost:5701
`)
	if err := os.WriteFile(configPath, content, 0o644); err != nil {
		t.Fatalf("write config: %v", err)
	}

	t.Setenv("RTASKS_API_TOKEN", "from-env")
	t.Setenv("AWS_REGION", "eu-central-1")

	cfg, err := config.LoadWorkerConfig(configPath)
	if err != nil {
		t.Fatalf("loadWorkerConfig() error = %v", err)
	}
	if cfg.RTasks.Token != "from-env" {
		t.Fatalf("token = %q", cfg.RTasks.Token)
	}
	if cfg.RTasks.PollInterval != 2*time.Second {
		t.Fatalf("poll interval = %v", cfg.RTasks.PollInterval)
	}
	if cfg.RTasks.HeartbeatInterval != 10*time.Second {
		t.Fatalf("heartbeat interval = %v", cfg.RTasks.HeartbeatInterval)
	}
	if cfg.Directories.Output != "./out" {
		t.Fatalf("output = %q", cfg.Directories.Output)
	}
	if cfg.Directories.CleanupPolicy != "keep" {
		t.Fatalf("cleanup policy = %q", cfg.Directories.CleanupPolicy)
	}
	if cfg.S3.Endpoint != "s3.amazonaws.com" {
		t.Fatalf("endpoint = %q", cfg.S3.Endpoint)
	}
	if cfg.S3.Region != "eu-central-1" {
		t.Fatalf("region = %q", cfg.S3.Region)
	}
	if !cfg.S3.Secure {
		t.Fatalf("secure should default to true")
	}
	if cfg.S3.Cleanup {
		t.Fatalf("cleanup should default to false")
	}
}
