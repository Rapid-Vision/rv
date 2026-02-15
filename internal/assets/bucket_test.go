package assets

import (
	"context"
	"testing"

	"github.com/minio/minio-go/v7"
)

func TestEnsureS3Bucket_RequiresEndpoint(t *testing.T) {
	err := EnsureS3Bucket(context.Background(), S3BucketOptions{
		DestinationURL: "s3://rv-assets/base",
	})
	if err == nil {
		t.Fatal("expected endpoint validation error")
	}
	if err.Error() != "s3 endpoint is required" {
		t.Fatalf("unexpected error: %v", err)
	}
}

func TestEnsureS3Bucket_InvalidDestination(t *testing.T) {
	err := EnsureS3Bucket(context.Background(), S3BucketOptions{
		DestinationURL: "http://example.com/file",
		Endpoint:       "localhost:9000",
	})
	if err == nil {
		t.Fatal("expected destination URL validation error")
	}
	if err.Error() != "unsupported URL scheme \"http\"" {
		t.Fatalf("unexpected error: %v", err)
	}
}

func TestIsS3BucketExistsPermissionError(t *testing.T) {
	if !isS3BucketExistsPermissionError(minio.ErrorResponse{Code: "AccessDenied"}) {
		t.Fatal("expected AccessDenied to be treated as permission error")
	}
	if !isS3BucketExistsPermissionError(minio.ErrorResponse{StatusCode: 403}) {
		t.Fatal("expected status 403 to be treated as permission error")
	}
	if isS3BucketExistsPermissionError(minio.ErrorResponse{Code: "NoSuchBucket", StatusCode: 404}) {
		t.Fatal("did not expect NoSuchBucket to be treated as permission error")
	}
}
