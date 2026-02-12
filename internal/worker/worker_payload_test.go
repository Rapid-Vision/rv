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
	if got.TimeLimit != nil || got.MaxSamples != nil || got.MinSamples != nil || got.NoiseThresholdEnabled != nil || got.NoiseThreshold != nil {
		t.Fatal("expected optional render fields to be unset")
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

func TestParseWorkerPayload_WithOptionalRenderFields(t *testing.T) {
	raw := json.RawMessage(`{
		"script":"scene.py",
		"number": 5,
		"resolution": [1280, 720],
		"time_limit": 4.5,
		"max_samples": 512,
		"min_samples": 16,
		"noise_threshold_enabled": true,
		"noise_threshold": 0.03
	}`)

	got, err := parseWorkerPayload(&raw)
	if err != nil {
		t.Fatalf("parseWorkerPayload() error = %v", err)
	}
	if got.TimeLimit == nil || *got.TimeLimit != 4.5 {
		t.Fatalf("TimeLimit = %v", got.TimeLimit)
	}
	if got.MaxSamples == nil || *got.MaxSamples != 512 {
		t.Fatalf("MaxSamples = %v", got.MaxSamples)
	}
	if got.MinSamples == nil || *got.MinSamples != 16 {
		t.Fatalf("MinSamples = %v", got.MinSamples)
	}
	if got.NoiseThresholdEnabled == nil || !*got.NoiseThresholdEnabled {
		t.Fatalf("NoiseThresholdEnabled = %v", got.NoiseThresholdEnabled)
	}
	if got.NoiseThreshold == nil || *got.NoiseThreshold != 0.03 {
		t.Fatalf("NoiseThreshold = %v", got.NoiseThreshold)
	}
}

func TestParseWorkerPayload_InvalidOptionalRenderFields(t *testing.T) {
	tests := []struct {
		name string
		raw  string
	}{
		{
			name: "invalid time_limit",
			raw: `{
				"script":"scene.py",
				"resolution":[640,640],
				"time_limit":0
			}`,
		},
		{
			name: "invalid max_samples",
			raw: `{
				"script":"scene.py",
				"resolution":[640,640],
				"max_samples":0
			}`,
		},
		{
			name: "invalid min_samples",
			raw: `{
				"script":"scene.py",
				"resolution":[640,640],
				"min_samples":-1
			}`,
		},
		{
			name: "min greater than max",
			raw: `{
				"script":"scene.py",
				"resolution":[640,640],
				"max_samples":8,
				"min_samples":9
			}`,
		},
		{
			name: "noise threshold enabled without value",
			raw: `{
				"script":"scene.py",
				"resolution":[640,640],
				"noise_threshold_enabled":true
			}`,
		},
		{
			name: "noise threshold value without enabled",
			raw: `{
				"script":"scene.py",
				"resolution":[640,640],
				"noise_threshold":0.05
			}`,
		},
		{
			name: "noise threshold value with enabled false",
			raw: `{
				"script":"scene.py",
				"resolution":[640,640],
				"noise_threshold_enabled":false,
				"noise_threshold":0.05
			}`,
		},
		{
			name: "asset destination reserved script filename",
			raw: `{
				"script":"scene.py",
				"resolution":[640,640],
				"asset_mappings":[{"source":"s3://bucket/cube.blend","destination":"__scene.py"}]
			}`,
		},
		{
			name: "asset destination nested reserved script filename",
			raw: `{
				"script":"scene.py",
				"resolution":[640,640],
				"asset_mappings":[{"source":"s3://bucket/cube.blend","destination":"models/__scene.py"}]
			}`,
		},
	}

	for _, tc := range tests {
		t.Run(tc.name, func(t *testing.T) {
			msg := json.RawMessage(tc.raw)
			if _, err := parseWorkerPayload(&msg); err == nil {
				t.Fatal("expected parseWorkerPayload to fail")
			}
		})
	}
}
