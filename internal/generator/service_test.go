package generator

import (
	"context"
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
		Params:    map[string]any{"kind": "text_texture", "text": "ABC"},
		Seed:      &seed,
		SeedMode:  "fixed",
	})
	if err != nil {
		t.Fatalf("executeGenerateRequest: %v", err)
	}
	if got != outputPath {
		t.Fatalf("got path %q, want %q", got, outputPath)
	}
}

func TestParseGeneratorOutputString(t *testing.T) {
	got, err := parseGeneratorOutput([]byte(`{"result":"asset.png"}`))
	if err != nil {
		t.Fatalf("parseGeneratorOutput: %v", err)
	}
	value, ok := got.(string)
	if !ok {
		t.Fatalf("got type %T, want string", got)
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
	values, ok := got.([]any)
	if !ok {
		t.Fatalf("got type %T, want []any", got)
	}
	if len(values) != 3 {
		t.Fatalf("len = %d, want 3", len(values))
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
			Params:    map[string]any{"x": "y"},
			Seed:      &seed,
			SeedMode:  "fixed",
		},
	)
	if err != nil {
		t.Fatalf("Request: %v", err)
	}
	resultPath, ok := resp.Result.(string)
	if !ok {
		t.Fatalf("result type = %T, want string", resp.Result)
	}
	if resultPath != outputPath {
		t.Fatalf("result = %q, want %q", resultPath, outputPath)
	}
}
