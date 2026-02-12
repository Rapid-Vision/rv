package assets

import (
	"context"
	"errors"
	"fmt"
	"net/url"
	"os"
	"path"
	"path/filepath"
	"strings"

	"github.com/minio/minio-go/v7"
	"github.com/minio/minio-go/v7/pkg/credentials"
)

type S3UploadOptions struct {
	LocalDir        string
	DestinationURL  string
	Endpoint        string
	Region          string
	Secure          bool
	AccessKeyID     string
	SecretAccessKey string
	SessionToken    string
}

type S3URL struct {
	Bucket string
	Prefix string
}

func (s S3URL) String() string {
	return fmt.Sprintf("s3://%s/%s", s.Bucket, s.Prefix)
}

func ParseS3URL(raw string) (S3URL, error) {
	parsed, err := url.Parse(strings.TrimSpace(raw))
	if err != nil {
		return S3URL{}, err
	}
	if parsed.Scheme != "s3" {
		return S3URL{}, fmt.Errorf("unsupported URL scheme %q", parsed.Scheme)
	}
	if parsed.Host == "" {
		return S3URL{}, errors.New("bucket is required")
	}

	prefix, err := normalizeS3Prefix(parsed.Path)
	if err != nil {
		return S3URL{}, err
	}

	return S3URL{
		Bucket: parsed.Host,
		Prefix: prefix,
	}, nil
}

func BuildWorkerTaskS3URL(baseURL string, taskID int, outputDir string) (string, error) {
	loc, err := ParseS3URL(baseURL)
	if err != nil {
		return "", err
	}
	if taskID <= 0 {
		return "", errors.New("task ID must be > 0")
	}

	outputBase := filepath.Base(filepath.Clean(outputDir))
	if outputBase == "" || outputBase == "." || outputBase == string(filepath.Separator) {
		return "", errors.New("output directory basename is invalid")
	}
	if outputBase == ".." {
		return "", errors.New("output directory basename must not be traversal")
	}

	taskPrefix := path.Join(loc.Prefix, fmt.Sprintf("task-%d", taskID), outputBase)
	return S3URL{
		Bucket: loc.Bucket,
		Prefix: taskPrefix,
	}.String(), nil
}

func UploadDirectoryToS3(ctx context.Context, opts S3UploadOptions) (string, error) {
	if strings.TrimSpace(opts.Endpoint) == "" {
		return "", errors.New("s3 endpoint is required")
	}

	loc, err := ParseS3URL(opts.DestinationURL)
	if err != nil {
		return "", err
	}

	root := filepath.Clean(opts.LocalDir)
	info, err := os.Stat(root)
	if err != nil {
		return "", err
	}
	if !info.IsDir() {
		return "", errors.New("local dir must be a directory")
	}

	client, err := minio.New(opts.Endpoint, &minio.Options{
		Creds:  newS3Credentials(opts),
		Secure: opts.Secure,
		Region: opts.Region,
	})
	if err != nil {
		return "", fmt.Errorf("init s3 client: %w", err)
	}

	err = filepath.WalkDir(root, func(filePath string, d os.DirEntry, walkErr error) error {
		if walkErr != nil {
			return walkErr
		}
		if d.IsDir() {
			return nil
		}

		relPath, err := filepath.Rel(root, filePath)
		if err != nil {
			return err
		}
		if relPath == "." || relPath == "" {
			return fmt.Errorf("invalid relative path for %q", filePath)
		}

		key := path.Join(loc.Prefix, filepath.ToSlash(relPath))
		if _, err := client.FPutObject(ctx, loc.Bucket, key, filePath, minio.PutObjectOptions{}); err != nil {
			return fmt.Errorf("put object %q: %w", key, err)
		}
		return nil
	})
	if err != nil {
		return "", err
	}

	return loc.String(), nil
}

func normalizeS3Prefix(rawPath string) (string, error) {
	trimmed := strings.TrimSpace(strings.TrimPrefix(rawPath, "/"))
	if trimmed == "" {
		return "", errors.New("s3 prefix is required")
	}

	cleaned := path.Clean(trimmed)
	if cleaned == "." || cleaned == "" {
		return "", errors.New("s3 prefix is required")
	}
	if cleaned == ".." || strings.HasPrefix(cleaned, "../") {
		return "", errors.New("s3 prefix must not escape root")
	}

	segments := strings.Split(cleaned, "/")
	for _, segment := range segments {
		if segment == "" || segment == "." || segment == ".." {
			return "", errors.New("s3 prefix contains invalid path segment")
		}
	}

	return cleaned, nil
}

func newS3Credentials(opts S3UploadOptions) *credentials.Credentials {
	if strings.TrimSpace(opts.AccessKeyID) != "" && strings.TrimSpace(opts.SecretAccessKey) != "" {
		return credentials.NewStaticV4(strings.TrimSpace(opts.AccessKeyID), strings.TrimSpace(opts.SecretAccessKey), strings.TrimSpace(opts.SessionToken))
	}
	if strings.TrimSpace(os.Getenv("AWS_ACCESS_KEY_ID")) != "" && strings.TrimSpace(os.Getenv("AWS_SECRET_ACCESS_KEY")) != "" {
		return credentials.NewEnvAWS()
	}
	return credentials.NewIAM("")
}
