package assets

import (
	"context"
	"errors"
	"fmt"
	"net/http"
	"os"
	"strings"

	"github.com/minio/minio-go/v7"
	"github.com/minio/minio-go/v7/pkg/credentials"
)

type S3BucketOptions struct {
	DestinationURL  string
	Endpoint        string
	Region          string
	Secure          bool
	AccessKeyID     string
	SecretAccessKey string
	SessionToken    string
}

func EnsureS3Bucket(ctx context.Context, opts S3BucketOptions) error {
	endpoint := strings.TrimSpace(opts.Endpoint)
	if endpoint == "" {
		return errors.New("s3 endpoint is required")
	}

	loc, err := ParseS3URL(opts.DestinationURL)
	if err != nil {
		return err
	}

	region := strings.TrimSpace(opts.Region)
	if region == "" {
		region = strings.TrimSpace(os.Getenv("AWS_REGION"))
	}

	client, err := minio.New(endpoint, &minio.Options{
		Creds:  bucketCredentials(opts),
		Secure: opts.Secure || endpoint == "s3.amazonaws.com",
		Region: region,
	})
	if err != nil {
		return fmt.Errorf("init s3 client: %w", err)
	}

	exists, err := client.BucketExists(ctx, loc.Bucket)
	if err != nil {
		// Some least-privilege IAM policies allow object uploads but deny
		// bucket-level existence checks (HEAD/LIST bucket). In that case we
		// can't preflight bucket creation here, so continue and let uploads
		// validate access later.
		if isS3BucketExistsPermissionError(err) {
			return nil
		}
		return fmt.Errorf("check s3 bucket %q: %w", loc.Bucket, err)
	}
	if exists {
		return nil
	}

	if err := client.MakeBucket(ctx, loc.Bucket, minio.MakeBucketOptions{Region: region}); err != nil {
		// Handle creation races.
		existsAfterCreate, existsErr := client.BucketExists(ctx, loc.Bucket)
		if existsErr == nil && existsAfterCreate {
			return nil
		}
		return fmt.Errorf("create s3 bucket %q: %w", loc.Bucket, err)
	}

	return nil
}

func isS3BucketExistsPermissionError(err error) bool {
	resp := minio.ToErrorResponse(err)
	if resp.StatusCode == http.StatusForbidden {
		return true
	}
	return resp.Code == "AccessDenied"
}

func bucketCredentials(opts S3BucketOptions) *credentials.Credentials {
	if strings.TrimSpace(opts.AccessKeyID) != "" && strings.TrimSpace(opts.SecretAccessKey) != "" {
		return credentials.NewStaticV4(strings.TrimSpace(opts.AccessKeyID), strings.TrimSpace(opts.SecretAccessKey), strings.TrimSpace(opts.SessionToken))
	}
	if strings.TrimSpace(os.Getenv("AWS_ACCESS_KEY_ID")) != "" && strings.TrimSpace(os.Getenv("AWS_SECRET_ACCESS_KEY")) != "" {
		return credentials.NewEnvAWS()
	}
	return credentials.NewIAM("")
}
