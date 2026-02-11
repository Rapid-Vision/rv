package assets

import (
	"context"
	"errors"
	"fmt"
	"io"
	"net/http"
	"net/url"
	"os"
	"path/filepath"
	"runtime"
	"strings"

	"github.com/Rapid-Vision/rv/internal/utils"
	"github.com/minio/minio-go/v7"
	"github.com/minio/minio-go/v7/pkg/credentials"
)

type Mapping struct {
	Source      string
	Destination string
}

type StagedFile struct {
	Source      string
	Destination string
	Path        string
}

type MappingError struct {
	Source      string
	Destination string
	Err         error
}

func (e *MappingError) Error() string {
	return fmt.Sprintf("stage mapping source=%q destination=%q: %v", e.Source, e.Destination, e.Err)
}

func (e *MappingError) Unwrap() error {
	return e.Err
}

func StageMappings(ctx context.Context, cwd string, mappings []Mapping) ([]StagedFile, error) {
	if cwd == "" {
		return nil, errors.New("cwd is required")
	}
	cwdAbs, err := filepath.Abs(cwd)
	if err != nil {
		return nil, err
	}
	if err := os.MkdirAll(cwdAbs, 0o755); err != nil {
		return nil, err
	}

	destinations := make(map[string]struct{}, len(mappings))
	res := make([]StagedFile, 0, len(mappings))
	for _, mapping := range mappings {
		relDest, err := utils.ValidateRelativePath(mapping.Destination)
		if err != nil {
			return res, &MappingError{
				Source:      mapping.Source,
				Destination: mapping.Destination,
				Err:         err,
			}
		}
		if _, exists := destinations[relDest]; exists {
			return res, &MappingError{
				Source:      mapping.Source,
				Destination: mapping.Destination,
				Err:         errors.New("duplicate destination"),
			}
		}
		destinations[relDest] = struct{}{}

		dstPath := filepath.Join(cwdAbs, relDest)
		if _, err := os.Stat(dstPath); err == nil {
			return res, &MappingError{
				Source:      mapping.Source,
				Destination: mapping.Destination,
				Err:         errors.New("destination already exists"),
			}
		} else if !errors.Is(err, os.ErrNotExist) {
			return res, &MappingError{
				Source:      mapping.Source,
				Destination: mapping.Destination,
				Err:         err,
			}
		}
		if err := os.MkdirAll(filepath.Dir(dstPath), 0o755); err != nil {
			return res, &MappingError{
				Source:      mapping.Source,
				Destination: mapping.Destination,
				Err:         err,
			}
		}

		// Pre-register the destination so caller cleanup can remove partial
		// files if the copy fails partway through.
		res = append(res, StagedFile{
			Source:      mapping.Source,
			Destination: relDest,
			Path:        dstPath,
		})

		if err := copySourceToPath(ctx, cwdAbs, mapping.Source, dstPath); err != nil {
			return res, &MappingError{
				Source:      mapping.Source,
				Destination: mapping.Destination,
				Err:         err,
			}
		}
	}

	return res, nil
}

func CleanupStagedFiles(staged []StagedFile) error {
	var errs []string
	for _, file := range staged {
		if err := os.Remove(file.Path); err != nil && !errors.Is(err, os.ErrNotExist) {
			errs = append(errs, fmt.Sprintf("%s: %v", file.Path, err))
		}
	}
	if len(errs) > 0 {
		return errors.New(strings.Join(errs, "; "))
	}
	return nil
}

func copySourceToPath(ctx context.Context, cwd string, source string, dstPath string) error {
	source = strings.TrimSpace(source)
	if source == "" {
		return errors.New("source is required")
	}
	if isWindowsAbsPath(source) {
		return copyLocalFile(source, dstPath)
	}

	parsed, err := url.Parse(source)
	if err != nil {
		return err
	}

	switch parsed.Scheme {
	case "http", "https":
		return downloadHTTP(ctx, source, dstPath)
	case "s3":
		return downloadS3(ctx, parsed, dstPath)
	case "file":
		return copyLocalFile(parsed.Path, dstPath)
	case "":
		src := source
		if !filepath.IsAbs(src) {
			src = filepath.Join(cwd, src)
		}
		return copyLocalFile(src, dstPath)
	default:
		return fmt.Errorf("unsupported source scheme: %q", parsed.Scheme)
	}
}

func isWindowsAbsPath(path string) bool {
	if len(path) < 3 {
		return false
	}
	drive := path[0]
	if !((drive >= 'a' && drive <= 'z') || (drive >= 'A' && drive <= 'Z')) {
		return false
	}
	if path[1] != ':' {
		return false
	}
	if path[2] != '\\' && path[2] != '/' {
		return false
	}
	return runtime.GOOS == "windows" || strings.Contains(path, "\\")
}

func downloadHTTP(ctx context.Context, source string, dstPath string) error {
	req, err := http.NewRequestWithContext(ctx, http.MethodGet, source, nil)
	if err != nil {
		return err
	}
	resp, err := http.DefaultClient.Do(req)
	if err != nil {
		return err
	}
	defer resp.Body.Close()
	if resp.StatusCode != http.StatusOK {
		return fmt.Errorf("download failed with status: %s", resp.Status)
	}

	dstFile, err := os.Create(dstPath)
	if err != nil {
		return err
	}
	defer dstFile.Close()

	_, err = io.Copy(dstFile, resp.Body)
	return err
}

func downloadS3(ctx context.Context, parsed *url.URL, dstPath string) error {
	bucket := parsed.Host
	key := strings.TrimPrefix(parsed.Path, "/")
	if bucket == "" || key == "" {
		return fmt.Errorf("invalid s3 source: %q", parsed.String())
	}

	client, err := minio.New("s3.amazonaws.com", &minio.Options{
		Creds:  credentials.NewEnvAWS(),
		Secure: true,
		Region: os.Getenv("AWS_REGION"),
	})
	if err != nil {
		return fmt.Errorf("init s3 client: %w", err)
	}

	obj, err := client.GetObject(ctx, bucket, key, minio.GetObjectOptions{})
	if err != nil {
		return fmt.Errorf("s3 get object failed: %w", err)
	}
	defer obj.Close()

	dstFile, err := os.Create(dstPath)
	if err != nil {
		return err
	}
	defer dstFile.Close()

	_, err = io.Copy(dstFile, obj)
	return err
}

func copyLocalFile(source string, dstPath string) error {
	srcFile, err := os.Open(source)
	if err != nil {
		return err
	}
	defer srcFile.Close()

	dstFile, err := os.Create(dstPath)
	if err != nil {
		return err
	}
	defer dstFile.Close()

	_, err = io.Copy(dstFile, srcFile)
	return err
}
