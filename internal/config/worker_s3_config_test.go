package config_test

import (
	"testing"

	"github.com/Rapid-Vision/rv/internal/config"
)

func TestResolveWorkerS3BaseURL(t *testing.T) {
	tests := []struct {
		name      string
		outputURL string
		path      string
		want      string
		wantErr   bool
	}{
		{
			name:      "from output url",
			outputURL: "s3://bucket/base",
			want:      "s3://bucket/base",
		},
		{
			name: "from path",
			path: "/bucket/base",
			want: "s3://bucket/base",
		},
		{
			name: "path without leading slash",
			path: "bucket/base",
			want: "s3://bucket/base",
		},
		{
			name:      "both set",
			outputURL: "s3://bucket/base",
			path:      "/bucket/base",
			wantErr:   true,
		},
		{
			name:    "invalid path",
			path:    "/",
			wantErr: true,
		},
		{
			name: "bucket root path",
			path: "/bucket/",
			want: "s3://bucket",
		},
	}

	for _, tc := range tests {
		t.Run(tc.name, func(t *testing.T) {
			got, err := config.ResolveWorkerS3BaseURL(tc.outputURL, tc.path)
			if (err != nil) != tc.wantErr {
				t.Fatalf("err = %v, wantErr = %v", err, tc.wantErr)
			}
			if !tc.wantErr && got != tc.want {
				t.Fatalf("got = %q, want = %q", got, tc.want)
			}
		})
	}
}
