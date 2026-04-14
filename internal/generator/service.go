package generator

import (
	"bytes"
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"net"
	"net/http"
	"os"
	"os/exec"
	"path/filepath"
	"runtime"
	"strings"
	"sync"
	"time"
)

const requestTimeout = 60 * time.Second

type Service struct {
	listener net.Listener
	server   *http.Server
	wg       sync.WaitGroup
}

type generateRequest struct {
	Command   string         `json:"command"`
	Cwd       string         `json:"cwd"`
	Operation string         `json:"operation"`
	Params    map[string]any `json:"params"`
	Seed      *int64         `json:"seed,omitempty"`
	SeedMode  string         `json:"seed_mode,omitempty"`
}

type generateResponse struct {
	Path string `json:"path"`
}

type generatorStdioRequest struct {
	Operation string         `json:"operation"`
	Params    map[string]any `json:"params"`
	Seed      *int64         `json:"seed,omitempty"`
	SeedMode  string         `json:"seed_mode,omitempty"`
	Cwd       string         `json:"cwd"`
}

func Start(ctx context.Context) (*Service, error) {
	listener, err := net.Listen("tcp", "127.0.0.1:0")
	if err != nil {
		return nil, err
	}

	svc := &Service{
		listener: listener,
	}

	mux := http.NewServeMux()
	mux.HandleFunc("/v1/generate", svc.handleGenerate)

	svc.server = &http.Server{
		Handler: mux,
	}

	svc.wg.Add(1)
	go func() {
		defer svc.wg.Done()
		_ = svc.server.Serve(listener)
	}()

	go func() {
		<-ctx.Done()
		shutdownCtx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
		defer cancel()
		_ = svc.server.Shutdown(shutdownCtx)
	}()

	return svc, nil
}

func (s *Service) Port() int {
	return s.listener.Addr().(*net.TCPAddr).Port
}

func (s *Service) Wait() {
	s.wg.Wait()
}

func (s *Service) handleGenerate(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		http.Error(w, "method not allowed", http.StatusMethodNotAllowed)
		return
	}

	defer func() { _ = r.Body.Close() }()
	var req generateRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		http.Error(w, fmt.Sprintf("decode request: %v", err), http.StatusBadRequest)
		return
	}

	path, err := executeGenerateRequest(r.Context(), req)
	if err != nil {
		http.Error(w, err.Error(), http.StatusBadRequest)
		return
	}

	w.Header().Set("Content-Type", "application/json")
	if err := json.NewEncoder(w).Encode(generateResponse{Path: path}); err != nil {
		http.Error(w, fmt.Sprintf("encode response: %v", err), http.StatusInternalServerError)
		return
	}
}

func executeGenerateRequest(parent context.Context, req generateRequest) (string, error) {
	if strings.TrimSpace(req.Operation) == "" {
		return "", errors.New("operation is required")
	}
	if strings.TrimSpace(req.Command) == "" {
		return "", errors.New("command is required")
	}
	if strings.TrimSpace(req.Cwd) == "" {
		return "", errors.New("cwd is required")
	}

	cwdAbs, err := filepath.Abs(req.Cwd)
	if err != nil {
		return "", fmt.Errorf("resolve cwd: %w", err)
	}
	payload := generatorStdioRequest{
		Operation: req.Operation,
		Params:    req.Params,
		Seed:      req.Seed,
		SeedMode:  req.SeedMode,
		Cwd:       cwdAbs,
	}
	stdin, err := json.Marshal(payload)
	if err != nil {
		return "", fmt.Errorf("marshal request: %w", err)
	}

	ctx, cancel := context.WithTimeout(parent, requestTimeout)
	defer cancel()

	shell, shellArgs := commandShell()
	cmd := exec.CommandContext(ctx, shell, append(shellArgs, req.Command)...)
	cmd.Dir = cwdAbs
	cmd.Stdin = bytes.NewReader(stdin)

	var stdout bytes.Buffer
	var stderr bytes.Buffer
	cmd.Stdout = &stdout
	cmd.Stderr = &stderr

	if err := cmd.Run(); err != nil {
		errText := strings.TrimSpace(stderr.String())
		if errText == "" {
			errText = strings.TrimSpace(stdout.String())
		}
		if errText != "" {
			return "", fmt.Errorf("generator failed: %s", errText)
		}
		return "", fmt.Errorf("generator failed: %w", err)
	}

	path, err := parseGeneratorOutput(stdout.Bytes(), cwdAbs)
	if err != nil {
		errText := strings.TrimSpace(stderr.String())
		if errText != "" {
			return "", fmt.Errorf("%w: %s", err, errText)
		}
		return "", err
	}
	return path, nil
}

func commandShell() (string, []string) {
	switch runtime.GOOS {
	case "windows":
		if shell := os.Getenv("COMSPEC"); shell != "" {
			return shell, []string{"/C"}
		}
		return "cmd", []string{"/C"}
	default:
		return "/bin/sh", []string{"-lc"}
	}
}

func parseGeneratorOutput(raw []byte, cwd string) (string, error) {
	raw = bytes.TrimSpace(raw)
	if len(raw) == 0 {
		return "", errors.New("generator returned empty stdout")
	}

	var path string
	if raw[0] == '"' {
		if err := json.Unmarshal(raw, &path); err != nil {
			return "", fmt.Errorf("decode generator path: %w", err)
		}
	} else {
		var response generateResponse
		if err := json.Unmarshal(raw, &response); err != nil {
			return "", fmt.Errorf("decode generator response: %w", err)
		}
		path = response.Path
	}

	if strings.TrimSpace(path) == "" {
		return "", errors.New("generator response must include path")
	}
	if !filepath.IsAbs(path) {
		path = filepath.Join(cwd, path)
	}
	path = filepath.Clean(path)
	if _, err := os.Stat(path); err != nil {
		if errors.Is(err, os.ErrNotExist) {
			return "", fmt.Errorf("generated path does not exist: %s", path)
		}
		return "", fmt.Errorf("stat generated path: %w", err)
	}
	return path, nil
}

func Request(url string, payload any) (generateResponse, error) {
	body, err := json.Marshal(payload)
	if err != nil {
		return generateResponse{}, err
	}
	resp, err := http.Post(url, "application/json", bytes.NewReader(body))
	if err != nil {
		return generateResponse{}, err
	}
	defer func() { _ = resp.Body.Close() }()

	if resp.StatusCode != http.StatusOK {
		raw, _ := io.ReadAll(io.LimitReader(resp.Body, 4096))
		return generateResponse{}, fmt.Errorf("generator server returned status %d: %s", resp.StatusCode, strings.TrimSpace(string(raw)))
	}

	var out generateResponse
	if err := json.NewDecoder(resp.Body).Decode(&out); err != nil {
		return generateResponse{}, err
	}
	return out, nil
}
