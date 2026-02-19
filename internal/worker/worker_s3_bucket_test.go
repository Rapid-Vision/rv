package worker

import (
	"context"
	"errors"
	"testing"

	"github.com/Rapid-Vision/rv/internal/assets"
	"github.com/Rapid-Vision/rv/internal/config"
)

func TestEnsureConfiguredS3Bucket_NoPath(t *testing.T) {
	cfg := &config.WorkerConfig{}
	called := false
	runner := NewRunner(Deps{
		EnsureBucketFn: func(context.Context, assets.S3BucketOptions) error {
			called = true
			return nil
		},
	})

	if err := runner.ensureConfiguredS3Bucket(context.Background(), cfg); err != nil {
		t.Fatalf("ensureConfiguredS3Bucket() error = %v", err)
	}
	if called {
		t.Fatal("EnsureBucketFn should not be called when path is empty")
	}
}

func TestEnsureConfiguredS3Bucket_CallsEnsure(t *testing.T) {
	cfg := &config.WorkerConfig{}
	cfg.S3.Path = "/rv-assets/base"
	cfg.S3.Endpoint = "localhost:9000"
	cfg.S3.Region = "us-east-1"
	cfg.S3.Secure = false
	cfg.S3.AccessKeyID = "minioadmin"
	cfg.S3.SecretKey = "minioadmin"

	var got assets.S3BucketOptions
	runner := NewRunner(Deps{
		EnsureBucketFn: func(_ context.Context, opts assets.S3BucketOptions) error {
			got = opts
			return nil
		},
	})

	if err := runner.ensureConfiguredS3Bucket(context.Background(), cfg); err != nil {
		t.Fatalf("ensureConfiguredS3Bucket() error = %v", err)
	}
	if got.DestinationURL != "s3://rv-assets/base" {
		t.Fatalf("DestinationURL = %q", got.DestinationURL)
	}
	if got.Endpoint != "localhost:9000" {
		t.Fatalf("Endpoint = %q", got.Endpoint)
	}
	if got.Region != "us-east-1" {
		t.Fatalf("Region = %q", got.Region)
	}
	if got.Secure {
		t.Fatal("Secure should be false")
	}
}

func TestEnsureConfiguredS3Bucket_PathOnlyConfig(t *testing.T) {
	cfg := &config.WorkerConfig{}
	cfg.S3.Path = "/rv-results/base"

	var got assets.S3BucketOptions
	runner := NewRunner(Deps{
		EnsureBucketFn: func(_ context.Context, opts assets.S3BucketOptions) error {
			got = opts
			return nil
		},
	})

	if err := runner.ensureConfiguredS3Bucket(context.Background(), cfg); err != nil {
		t.Fatalf("ensureConfiguredS3Bucket() error = %v", err)
	}
	if got.DestinationURL != "s3://rv-results/base" {
		t.Fatalf("DestinationURL = %q", got.DestinationURL)
	}
}

func TestEnsureConfiguredS3Bucket_Error(t *testing.T) {
	cfg := &config.WorkerConfig{}
	cfg.S3.Path = "/rv-assets/base"

	runner := NewRunner(Deps{
		EnsureBucketFn: func(_ context.Context, _ assets.S3BucketOptions) error {
			return errors.New("boom")
		},
	})

	err := runner.ensureConfiguredS3Bucket(context.Background(), cfg)
	if err == nil {
		t.Fatal("expected error")
	}
	if err.Error() != "ensure configured s3 bucket: boom" {
		t.Fatalf("unexpected error: %v", err)
	}
}

func TestEnsureConfiguredS3Bucket_InvalidPathResolveError(t *testing.T) {
	cfg := &config.WorkerConfig{}
	cfg.S3.Path = "/"

	runner := NewRunner(Deps{
		EnsureBucketFn: func(_ context.Context, _ assets.S3BucketOptions) error {
			t.Fatal("EnsureBucketFn should not be called when URL resolution fails")
			return nil
		},
	})

	err := runner.ensureConfiguredS3Bucket(context.Background(), cfg)
	if err == nil {
		t.Fatal("expected error")
	}
	if err.Error() != "resolve worker s3 base url: worker.s3.path must include bucket name" {
		t.Fatalf("unexpected error: %v", err)
	}
}
