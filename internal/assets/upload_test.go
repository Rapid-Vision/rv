package assets

import "testing"

func TestParseS3URL(t *testing.T) {
	t.Run("valid", func(t *testing.T) {
		got, err := ParseS3URL("s3://my-bucket/path/to/output")
		if err != nil {
			t.Fatalf("ParseS3URL() error = %v", err)
		}
		if got.Bucket != "my-bucket" {
			t.Fatalf("bucket = %q, want %q", got.Bucket, "my-bucket")
		}
		if got.Prefix != "path/to/output" {
			t.Fatalf("prefix = %q, want %q", got.Prefix, "path/to/output")
		}
	})

	t.Run("invalid scheme", func(t *testing.T) {
		if _, err := ParseS3URL("https://my-bucket/path"); err == nil {
			t.Fatal("expected scheme error")
		}
	})

	t.Run("missing prefix", func(t *testing.T) {
		if _, err := ParseS3URL("s3://my-bucket"); err == nil {
			t.Fatal("expected missing prefix error")
		}
	})

	t.Run("reject traversal", func(t *testing.T) {
		if _, err := ParseS3URL("s3://my-bucket/a/../../b"); err == nil {
			t.Fatal("expected traversal validation error")
		}
	})
}

func TestBuildWorkerTaskS3URL(t *testing.T) {
	got, err := BuildWorkerTaskS3URL("s3://bucket/datasets/base", 17, "/tmp/out/12")
	if err != nil {
		t.Fatalf("BuildWorkerTaskS3URL() error = %v", err)
	}

	want := "s3://bucket/datasets/base/task-17/12"
	if got != want {
		t.Fatalf("BuildWorkerTaskS3URL() = %q, want %q", got, want)
	}
}
