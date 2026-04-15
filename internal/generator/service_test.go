package generator

import (
	"context"
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"testing"
)

func TestExecuteGenerateRequestCommand(t *testing.T) {
	tmp := t.TempDir()
	generatorPath := filepath.Join(tmp, "gen.sh")
	workDir := filepath.Join(tmp, "generated", "run-1")
	outputPath := filepath.Join(workDir, "texture.txt")

script := `#!/bin/sh
req_file="$PWD/request.json"
cat > "$req_file"
python3 -c '
import json, os, sys
with open("request.json", "r", encoding="utf-8") as f:
    req = json.load(f)
path = os.path.join(req["work_dir"], "texture.txt")
with open(path, "w", encoding="utf-8") as f:
    f.write(req["params"]["kind"] + ":" + req["params"]["text"])
json.dump({"result": path}, sys.stdout)
'
`
	if err := os.WriteFile(generatorPath, []byte(script), 0o644); err != nil {
		t.Fatalf("write generator: %v", err)
	}

	seed := int64(42)
	got, err := executeGenerateRequest(context.Background(), generateRequest{
		Command:   "sh ./gen.sh",
		RootDir:   tmp,
		WorkDir:   workDir,
		Params:    json.RawMessage(`{"kind":"text_texture","text":"ABC"}`),
		Seed:      &seed,
		SeedMode:  "fixed",
	})
	if err != nil {
		t.Fatalf("executeGenerateRequest: %v", err)
	}
	var gotPath string
	if err := json.Unmarshal(got, &gotPath); err != nil {
		t.Fatalf("unmarshal result: %v", err)
	}
	if gotPath != outputPath {
		t.Fatalf("got path %q, want %q", gotPath, outputPath)
	}
}

func TestParseGeneratorOutputString(t *testing.T) {
	got, err := parseGeneratorOutput([]byte(`{"result":"asset.png"}`))
	if err != nil {
		t.Fatalf("parseGeneratorOutput: %v", err)
	}
	var value string
	if err := json.Unmarshal(got, &value); err != nil {
		t.Fatalf("unmarshal result: %v", err)
	}
	if value != "asset.png" {
		t.Fatalf("got %q, want %q", value, "asset.png")
	}
}

func TestParseGeneratorOutputArray(t *testing.T) {
	got, err := parseGeneratorOutput([]byte(`{"result":[1,"two",{"x":3}]}`))
	if err != nil {
		t.Fatalf("parseGeneratorOutput: %v", err)
	}
	var values []any
	if err := json.Unmarshal(got, &values); err != nil {
		t.Fatalf("unmarshal result: %v", err)
	}
	if len(values) != 3 {
		t.Fatalf("len = %d, want 3", len(values))
	}
}

func TestParseGeneratorOutputPreservesLargeIntegerBytes(t *testing.T) {
	got, err := parseGeneratorOutput([]byte(`{"result":{"n":9007199254740993}}`))
	if err != nil {
		t.Fatalf("parseGeneratorOutput: %v", err)
	}
	want := `{"n":9007199254740993}`
	if string(got) != want {
		t.Fatalf("got %s, want %s", string(got), want)
	}
}

func TestRequestRoundTrip(t *testing.T) {
	tmp := t.TempDir()
	generatorPath := filepath.Join(tmp, "gen.py")
	workDir := filepath.Join(tmp, "generated", "run-2")
	outputPath := filepath.Join(workDir, "result.txt")
	if err := os.WriteFile(generatorPath, []byte(`import json, os, sys
req = json.load(sys.stdin)
path = os.path.join(req["work_dir"], "result.txt")
with open(path, "w", encoding="utf-8") as f:
    json.dump(req, f)
json.dump({"result": path}, sys.stdout)
`), 0o644); err != nil {
		t.Fatalf("write generator: %v", err)
	}

	ctx, cancel := context.WithCancel(context.Background())
	svc, err := Start(ctx)
	if err != nil {
		t.Fatalf("Start: %v", err)
	}
	defer svc.Wait()
	defer cancel()

	seed := int64(7)
	resp, err := Request(
		fmt.Sprintf("http://127.0.0.1:%d/v1/generate", svc.Port()),
		generateRequest{
			Command:   "python3 ./gen.py",
			RootDir:   tmp,
			WorkDir:   workDir,
			Params:    json.RawMessage(`{"x":"y"}`),
			Seed:      &seed,
			SeedMode:  "fixed",
		},
	)
	if err != nil {
		t.Fatalf("Request: %v", err)
	}
	var resultPath string
	if err := json.Unmarshal(resp.Result, &resultPath); err != nil {
		t.Fatalf("unmarshal result: %v", err)
	}
	if resultPath != outputPath {
		t.Fatalf("result = %q, want %q", resultPath, outputPath)
	}
}
