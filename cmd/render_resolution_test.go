package cmd

import "testing"

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
