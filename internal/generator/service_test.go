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
    f.write(req["operation"] + ":" + req["params"]["text"])
json.dump({"path": path}, sys.stdout)
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
		Operation: "text_texture",
		Params:    map[string]any{"text": "ABC"},
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

func TestParseGeneratorOutputRelativePath(t *testing.T) {
	tmp := t.TempDir()
	target := filepath.Join(tmp, "asset.png")
	if err := os.WriteFile(target, []byte("ok"), 0o644); err != nil {
		t.Fatalf("write target: %v", err)
	}

	got, err := parseGeneratorOutput([]byte(`{"path":"asset.png"}`), tmp)
	if err != nil {
		t.Fatalf("parseGeneratorOutput: %v", err)
	}
	if got != target {
		t.Fatalf("got %q, want %q", got, target)
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
json.dump({"path": path}, sys.stdout)
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
			Operation: "sample",
			Params:    map[string]any{"x": "y"},
			Seed:      &seed,
			SeedMode:  "fixed",
		},
	)
	if err != nil {
		t.Fatalf("Request: %v", err)
	}
	if resp.Path != outputPath {
		t.Fatalf("path = %q, want %q", resp.Path, outputPath)
	}
}
