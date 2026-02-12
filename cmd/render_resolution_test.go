package cmd

import (
	"testing"

	"github.com/Rapid-Vision/rv/internal/render"
	"github.com/spf13/cobra"
)

func TestParseResolutionFlag(t *testing.T) {
	tests := []struct {
		name    string
		input   string
		want    [2]int
		wantErr bool
	}{
		{name: "valid", input: "640,640", want: [2]int{640, 640}},
		{name: "valid with spaces", input: "1280, 720", want: [2]int{1280, 720}},
		{name: "missing value", input: "640", wantErr: true},
		{name: "invalid width", input: "abc,720", wantErr: true},
		{name: "invalid height", input: "640,abc", wantErr: true},
		{name: "zero width", input: "0,720", wantErr: true},
		{name: "negative height", input: "640,-1", wantErr: true},
	}

	for _, tc := range tests {
		t.Run(tc.name, func(t *testing.T) {
			got, err := parseResolutionFlag(tc.input)
			if (err != nil) != tc.wantErr {
				t.Fatalf("err = %v, wantErr = %v", err, tc.wantErr)
			}
			if !tc.wantErr && got != tc.want {
				t.Fatalf("got = %v, want = %v", got, tc.want)
			}
		})
	}
}

func TestApplyOptionalRenderFlags(t *testing.T) {
	resetRenderOptionalFlagGlobals()

	cmd := newRenderOptionalFlagCommand()
	opts := render.RenderOptions{}

	applyOptionalRenderFlags(cmd, &opts)

	if opts.TimeLimit != nil || opts.MaxSamples != nil || opts.MinSamples != nil || opts.NoiseThresholdEnabled != nil || opts.NoiseThreshold != nil {
		t.Fatal("expected optional render settings to stay unset when flags are unchanged")
	}
}

func TestApplyOptionalRenderFlags_Changed(t *testing.T) {
	resetRenderOptionalFlagGlobals()
	cmd := newRenderOptionalFlagCommand()

	if err := cmd.Flags().Set("time-limit", "2.5"); err != nil {
		t.Fatalf("set --time-limit: %v", err)
	}
	if err := cmd.Flags().Set("max-samples", "128"); err != nil {
		t.Fatalf("set --max-samples: %v", err)
	}
	if err := cmd.Flags().Set("min-samples", "16"); err != nil {
		t.Fatalf("set --min-samples: %v", err)
	}
	if err := cmd.Flags().Set("noise-threshold-enabled", "true"); err != nil {
		t.Fatalf("set --noise-threshold-enabled: %v", err)
	}
	if err := cmd.Flags().Set("noise-threshold", "0.03"); err != nil {
		t.Fatalf("set --noise-threshold: %v", err)
	}

	opts := render.RenderOptions{}
	applyOptionalRenderFlags(cmd, &opts)

	if opts.TimeLimit == nil || *opts.TimeLimit != 2.5 {
		t.Fatalf("TimeLimit = %v", opts.TimeLimit)
	}
	if opts.MaxSamples == nil || *opts.MaxSamples != 128 {
		t.Fatalf("MaxSamples = %v", opts.MaxSamples)
	}
	if opts.MinSamples == nil || *opts.MinSamples != 16 {
		t.Fatalf("MinSamples = %v", opts.MinSamples)
	}
	if opts.NoiseThresholdEnabled == nil || !*opts.NoiseThresholdEnabled {
		t.Fatalf("NoiseThresholdEnabled = %v", opts.NoiseThresholdEnabled)
	}
	if opts.NoiseThreshold == nil || *opts.NoiseThreshold != 0.03 {
		t.Fatalf("NoiseThreshold = %v", opts.NoiseThreshold)
	}
}

func newRenderOptionalFlagCommand() *cobra.Command {
	cmd := &cobra.Command{}
	cmd.Flags().Float64Var(&renderTimeLimit, "time-limit", 0, "")
	cmd.Flags().IntVar(&renderMaxSamples, "max-samples", 0, "")
	cmd.Flags().IntVar(&renderMinSamples, "min-samples", 0, "")
	cmd.Flags().BoolVar(&renderNoiseThresholdEnabled, "noise-threshold-enabled", false, "")
	cmd.Flags().Float64Var(&renderNoiseThreshold, "noise-threshold", 0, "")
	return cmd
}

func resetRenderOptionalFlagGlobals() {
	renderTimeLimit = 0
	renderMaxSamples = 0
	renderMinSamples = 0
	renderNoiseThresholdEnabled = false
	renderNoiseThreshold = 0
}
