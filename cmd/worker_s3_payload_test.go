package cmd

import (
	"encoding/json"
	"testing"
)

func TestParseWorkerPayload_WithOutputS3URL(t *testing.T) {
	raw := json.RawMessage(`{
		"script":"scene.py",
		"number": 5,
		"procs": 2,
		"output_s3_url":"s3://bucket/datasets/base"
	}`)

	got, err := parseWorkerPayload(&raw)
	if err != nil {
		t.Fatalf("parseWorkerPayload() error = %v", err)
	}
	if got.OutputS3URL != "s3://bucket/datasets/base" {
		t.Fatalf("OutputS3URL = %q", got.OutputS3URL)
	}
}

func TestParseWorkerPayload_InvalidOutputS3URL(t *testing.T) {
	raw := json.RawMessage(`{
		"script":"scene.py",
		"output_s3_url":"https://bucket/datasets/base"
	}`)

	if _, err := parseWorkerPayload(&raw); err == nil {
		t.Fatal("expected parseWorkerPayload to reject invalid output_s3_url")
	}
}
