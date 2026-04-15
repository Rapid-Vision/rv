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
	Command  string          `json:"command"`
	RootDir  string          `json:"root_dir"`
	WorkDir  string          `json:"work_dir"`
	Params   json.RawMessage `json:"params"`
	Seed     *int64          `json:"seed,omitempty"`
	SeedMode string          `json:"seed_mode,omitempty"`
}

type generateResponse struct {
	Result json.RawMessage `json:"result"`
}

type generatorStdioRequest struct {
	Params   json.RawMessage `json:"params"`
	Seed     *int64          `json:"seed,omitempty"`
	SeedMode string          `json:"seed_mode,omitempty"`
	RootDir  string          `json:"root_dir"`
	WorkDir  string          `json:"work_dir"`
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

	result, err := executeGenerateRequest(r.Context(), req)
	if err != nil {
		http.Error(w, err.Error(), http.StatusBadRequest)
		return
	}

	w.Header().Set("Content-Type", "application/json")
	if err := json.NewEncoder(w).Encode(generateResponse{Result: result}); err != nil {
		http.Error(w, fmt.Sprintf("encode response: %v", err), http.StatusInternalServerError)
		return
	}
}

func executeGenerateRequest(parent context.Context, req generateRequest) (json.RawMessage, error) {
	if strings.TrimSpace(req.Command) == "" {
		return nil, errors.New("command is required")
	}
	if strings.TrimSpace(req.RootDir) == "" {
		return nil, errors.New("root_dir is required")
	}
	if strings.TrimSpace(req.WorkDir) == "" {
		return nil, errors.New("work_dir is required")
	}

	rootDirAbs, err := filepath.Abs(req.RootDir)
	if err != nil {
		return nil, fmt.Errorf("resolve root_dir: %w", err)
	}
	workDirAbs, err := filepath.Abs(req.WorkDir)
	if err != nil {
		return nil, fmt.Errorf("resolve work_dir: %w", err)
	}
	if err := os.MkdirAll(workDirAbs, 0o755); err != nil {
		return nil, fmt.Errorf("create work_dir: %w", err)
	}
	params := req.Params
	if len(bytes.TrimSpace(params)) == 0 {
		params = json.RawMessage(`{}`)
	}

	payload := generatorStdioRequest{
		Params:   params,
		Seed:     req.Seed,
		SeedMode: req.SeedMode,
		RootDir:  rootDirAbs,
		WorkDir:  workDirAbs,
	}
	stdin, err := json.Marshal(payload)
	if err != nil {
		return nil, fmt.Errorf("marshal request: %w", err)
	}

	ctx, cancel := context.WithTimeout(parent, requestTimeout)
	defer cancel()

	shell, shellArgs := commandShell()
	cmd := exec.CommandContext(ctx, shell, append(shellArgs, req.Command)...)
	cmd.Dir = rootDirAbs
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
			return nil, fmt.Errorf("generator failed: %s", errText)
		}
		return nil, fmt.Errorf("generator failed: %w", err)
	}

	result, err := parseGeneratorOutput(stdout.Bytes())
	if err != nil {
		errText := strings.TrimSpace(stderr.String())
		if errText != "" {
			return nil, fmt.Errorf("%w: %s", err, errText)
		}
		return nil, err
	}
	return result, nil
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

func parseGeneratorOutput(raw []byte) (json.RawMessage, error) {
	raw = bytes.TrimSpace(raw)
	if len(raw) == 0 {
		return nil, errors.New("generator returned empty stdout")
	}

	var response generateResponse
	if err := json.Unmarshal(raw, &response); err != nil {
		return nil, fmt.Errorf("decode generator response: %w", err)
	}
	if len(bytes.TrimSpace(response.Result)) == 0 {
		return nil, errors.New("generator response must include result")
	}
	return response.Result, nil
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
