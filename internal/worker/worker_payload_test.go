package worker

import (
	"encoding/json"
	"testing"
)

func TestParseWorkerPayload_WithOutputS3URL(t *testing.T) {
	raw := json.RawMessage(`{
		"script":"scene.py",
		"number": 5,
		"resolution": [1280, 720]
	}`)

	got, err := parseWorkerPayload(&raw)
	if err != nil {
		t.Fatalf("parseWorkerPayload() error = %v", err)
	}
	if got.Resolution[0] != 1280 || got.Resolution[1] != 720 {
		t.Fatalf("Resolution = %v", got.Resolution)
	}
}

func TestParseWorkerPayload_InvalidResolution(t *testing.T) {
	raw := json.RawMessage(`{
		"script":"scene.py",
		"resolution": [1280]
	}`)

	if _, err := parseWorkerPayload(&raw); err == nil {
		t.Fatal("expected parseWorkerPayload to reject invalid resolution")
	}
}
