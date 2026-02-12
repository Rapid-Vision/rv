package worker

import (
	"context"
	"errors"
	"testing"

	"github.com/Rapid-Vision/rv/internal/assets"
	"github.com/Rapid-Vision/rv/internal/config"
)

func TestUploadRenderedOutput_Success(t *testing.T) {
	origUploader := uploadDirectoryToS3
	t.Cleanup(func() {
		uploadDirectoryToS3 = origUploader
	})

	cfg := &config.WorkerConfig{}
	cfg.S3.Endpoint = "s3.amazonaws.com"
	cfg.S3.Region = "us-east-1"
	cfg.S3.Secure = true

	var got assets.S3UploadOptions
	uploadDirectoryToS3 = func(_ context.Context, opts assets.S3UploadOptions) (string, error) {
		got = opts
		return opts.DestinationURL, nil
	}

	uploaded, target, err := uploadRenderedOutput(context.Background(), cfg, 19, "s3://bucket/base", "/tmp/out/5")
	if err != nil {
		t.Fatalf("uploadRenderedOutput() error = %v", err)
	}

	wantTarget := "s3://bucket/base/task-19/5"
	if target != wantTarget {
		t.Fatalf("target = %q, want %q", target, wantTarget)
	}
	if uploaded != wantTarget {
		t.Fatalf("uploaded = %q, want %q", uploaded, wantTarget)
	}
	if got.DestinationURL != wantTarget {
		t.Fatalf("uploader destination = %q, want %q", got.DestinationURL, wantTarget)
	}
}

func TestUploadRenderedOutput_UploadError(t *testing.T) {
	origUploader := uploadDirectoryToS3
	t.Cleanup(func() {
		uploadDirectoryToS3 = origUploader
	})

	uploadDirectoryToS3 = func(_ context.Context, _ assets.S3UploadOptions) (string, error) {
		return "", errors.New("boom")
	}

	cfg := &config.WorkerConfig{}
	uploaded, target, err := uploadRenderedOutput(context.Background(), cfg, 3, "s3://bucket/base", "/tmp/out/8")
	if err == nil {
		t.Fatal("expected uploadRenderedOutput to return an error")
	}
	if uploaded != "" {
		t.Fatalf("uploaded = %q, want empty", uploaded)
	}
	if target != "s3://bucket/base/task-3/8" {
		t.Fatalf("target = %q", target)
	}
}
