package cmd

import (
	"testing"

	"github.com/Rapid-Vision/rv/internal/seed"
)

func TestParseSeedFlag(t *testing.T) {
	tests := []struct {
		name    string
		input   string
		want    seed.Config
		wantErr bool
	}{
		{name: "rand", input: "rand", want: seed.Config{Mode: seed.RandomMode}},
		{name: "random alias", input: "random", want: seed.Config{Mode: seed.RandomMode}},
		{name: "seq", input: "seq", want: seed.Config{Mode: seed.SeqMode}},
		{name: "fixed", input: "42", want: seed.Config{Mode: seed.FixedMode, Value: 42}},
		{name: "negative fixed", input: "-9", want: seed.Config{Mode: seed.FixedMode, Value: -9}},
		{name: "invalid", input: "abc", wantErr: true},
	}

	for _, tc := range tests {
		t.Run(tc.name, func(t *testing.T) {
			got, err := parseSeedFlag(tc.input)
			if (err != nil) != tc.wantErr {
				t.Fatalf("err = %v, wantErr = %v", err, tc.wantErr)
			}
			if !tc.wantErr && got != tc.want {
				t.Fatalf("got = %#v, want = %#v", got, tc.want)
			}
		})
	}
}
