package cmd

import (
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"net/url"
	"os"
	"os/signal"
	"path/filepath"
	"strings"
	"syscall"
	"time"

	"github.com/Rapid-Vision/rv/internal/assets"
	"github.com/Rapid-Vision/rv/internal/logs"
	"github.com/Rapid-Vision/rv/internal/render"
	"github.com/Rapid-Vision/rv/internal/rpcclient"
	"github.com/Rapid-Vision/rv/internal/utils"
	"github.com/spf13/cobra"
)

var (
	workerURL               string
	workerToken             string
	workerName              string
	workerTaskName          string
	workerPollInterval      time.Duration
	workerHeartbeatInterval time.Duration
	workerRunOnce           bool
	workerCwd               string
	workerOutputDir         string
	workerCleanupPolicy     string
)

var workerCmd = &cobra.Command{
	Use:   "worker",
	Short: "Run an rv worker using rtasks",
	Long:  "Poll rtasks for render jobs and execute them using rv render.",
	Run:   runWorker,
}

func init() {
	rootCmd.AddCommand(workerCmd)

	workerCmd.Flags().StringVar(&workerURL, "url", "", "rtasks server URL")
	workerCmd.Flags().StringVar(&workerToken, "token", os.Getenv("RTASKS_API_TOKEN"), "rtasks API token")
	workerCmd.Flags().StringVar(&workerName, "worker-name", "", "worker name")
	workerCmd.Flags().StringVar(&workerTaskName, "task-name", "", "task name")
	workerCmd.Flags().DurationVar(&workerPollInterval, "poll-interval", 2*time.Second, "poll interval when idle")
	workerCmd.Flags().DurationVar(&workerHeartbeatInterval, "heartbeat-interval", 10*time.Second, "heartbeat interval (0 disables)")
	workerCmd.Flags().BoolVar(&workerRunOnce, "once", false, "run a single task and exit")
	workerCmd.Flags().StringVar(&workerCwd, "cwd", "", "Working directory for resolving relative script paths (defaults to script directory)")
	workerCmd.Flags().StringVarP(&workerOutputDir, "output", "o", "./out", "Output directory for rendered files (resolved from process working directory)")
	workerCmd.Flags().StringVar(&workerCleanupPolicy, "cleanup-policy", "keep", "Asset cleanup policy: keep or cleanup")
}

type workerTaskPayload struct {
	Script        string               `json:"script"`
	Number        int                  `json:"number"`
	Procs         int                  `json:"procs"`
	AssetMappings []workerAssetMapping `json:"asset_mappings"`
}

type workerAssetMapping struct {
	Source      string `json:"source"`
	Destination string `json:"destination"`
}

func runWorker(_ *cobra.Command, args []string) {
	if workerURL == "" {
		logs.Err.Fatalln("--url is required")
	}
	if workerName == "" {
		logs.Err.Fatalln("--worker-name is required")
	}
	if workerTaskName == "" {
		logs.Err.Fatalln("--task-name is required")
	}
	if workerPollInterval <= 0 {
		logs.Err.Fatalln("--poll-interval must be > 0")
	}
	switch workerCleanupPolicy {
	case "keep", "cleanup":
	default:
		logs.Err.Fatalln("--cleanup-policy must be either \"keep\" or \"cleanup\"")
	}

	client := rpcclient.NewRPCClient(workerURL)
	if workerToken != "" {
		client = client.WithBearerToken(workerToken)
	}

	ctx := context.Background()
	worker, err := client.DeclareWorker(ctx, rpcclient.DeclareWorkerParams{
		Name:     workerName,
		TaskName: workerTaskName,
	})
	if err != nil {
		logs.Err.Fatalln("Failed to declare worker:", err)
	}
	logs.Info.Printf("Worker declared (id=%d, name=%s, task=%s)\n", worker.Id, worker.Name, worker.TaskName)

	stopCh := make(chan os.Signal, 1)
	signal.Notify(stopCh, os.Interrupt, syscall.SIGTERM)

	done := make(chan struct{})
	if workerHeartbeatInterval > 0 {
		go func() {
			ticker := time.NewTicker(workerHeartbeatInterval)
			defer ticker.Stop()
			for {
				select {
				case <-ticker.C:
					_, _ = client.UpdateWorkerStatus(ctx, rpcclient.UpdateWorkerStatusParams{WorkerId: worker.Id})
				case <-done:
					return
				}
			}
		}()
	}

	for {
		select {
		case <-stopCh:
			close(done)
			_ = client.StopWorker(ctx, rpcclient.StopWorkerParams{WorkerId: worker.Id})
			logs.Info.Println("Worker stopped.")
			return
		default:
		}

		dispatch, err := client.RequestTask(ctx, rpcclient.RequestTaskParams{WorkerId: worker.Id})
		if err != nil {
			logs.Warn.Println("Request task failed:", err)
			time.Sleep(workerPollInterval)
			continue
		}
		if dispatch.Task == nil {
			time.Sleep(workerPollInterval)
			continue
		}
		if dispatch.DispatchToken == nil {
			logs.Warn.Println("Dispatch token missing; skipping task")
			time.Sleep(workerPollInterval)
			continue
		}

		task := dispatch.Task
		err = handleWorkerTask(ctx, client, worker.Id, *dispatch.DispatchToken, task)
		if err != nil {
			logs.Warn.Println("Task failed:", err)
		}

		if workerRunOnce {
			close(done)
			_ = client.StopWorker(ctx, rpcclient.StopWorkerParams{WorkerId: worker.Id})
			logs.Info.Println("Worker stopped (once mode).")
			return
		}
	}
}

func handleWorkerTask(ctx context.Context, client *rpcclient.RPCClient, workerId int, dispatchToken string, task *rpcclient.TaskModel) error {
	payload, err := parseWorkerPayload(task.Payload)
	if err != nil {
		submitTaskResult(ctx, client, workerId, task.Id, dispatchToken, "failed", map[string]any{"error": err.Error()})
		return err
	}

	resolveWorkerCwd := func() (string, error) {
		if workerCwd != "" {
			return filepath.Abs(workerCwd)
		}
		return os.Getwd()
	}

	var scriptPath string
	var runtimeCwd string
	var staged []assets.StagedFile

	submitTaskProgress(ctx, client, workerId, task.Id, dispatchToken, 5, "resolving paths", nil)
	outputDirAbs, err := filepath.Abs(workerOutputDir)
	if err != nil {
		submitTaskResult(ctx, client, workerId, task.Id, dispatchToken, "failed", map[string]any{
			"error": "failed to resolve output path",
			"details": map[string]any{
				"message": err.Error(),
			},
		})
		return err
	}

	if isManagedResourceSource(payload.Script) {
		runtimeCwd, err = resolveWorkerCwd()
		if err != nil {
			submitTaskResult(ctx, client, workerId, task.Id, dispatchToken, "failed", map[string]any{
				"error": "failed to resolve cwd",
				"details": map[string]any{
					"message": err.Error(),
				},
			})
			return err
		}

		if err := os.MkdirAll(runtimeCwd, 0o755); err != nil {
			submitTaskResult(ctx, client, workerId, task.Id, dispatchToken, "failed", map[string]any{
				"error": "failed to create cwd",
				"details": map[string]any{
					"cwd":     runtimeCwd,
					"message": err.Error(),
				},
			})
			return err
		}

		submitTaskProgress(ctx, client, workerId, task.Id, dispatchToken, 12, "staging script", nil)
		scriptMappings := []assets.Mapping{{
			Source:      payload.Script,
			Destination: workerScriptDestination(payload.Script),
		}}
		stagedScript, stageErr := assets.StageMappings(ctx, runtimeCwd, scriptMappings)
		if stageErr != nil {
			result := map[string]any{
				"error": "script staging failed",
				"details": map[string]any{
					"message": stageErr.Error(),
				},
			}
			if workerCleanupPolicy == "cleanup" && len(stagedScript) > 0 {
				if cleanupErr := assets.CleanupStagedFiles(stagedScript); cleanupErr != nil {
					result["cleanup_warning"] = cleanupErr.Error()
				}
			}
			var mappingErr *assets.MappingError
			if errors.As(stageErr, &mappingErr) {
				result["details"] = map[string]any{
					"source":      mappingErr.Source,
					"destination": mappingErr.Destination,
					"message":     mappingErr.Err.Error(),
				}
			}
			submitTaskResult(ctx, client, workerId, task.Id, dispatchToken, "failed", result)
			return stageErr
		}

		staged = append(staged, stagedScript...)
		scriptPath = stagedScript[0].Path
	} else {
		runtimePaths, pathErr := utils.ResolveRuntimePaths(payload.Script, workerCwd)
		if pathErr != nil {
			submitTaskResult(ctx, client, workerId, task.Id, dispatchToken, "failed", map[string]any{
				"error": "failed to resolve paths",
				"details": map[string]any{
					"message": pathErr.Error(),
				},
			})
			return pathErr
		}
		scriptPath = runtimePaths.ScriptPath
		runtimeCwd = runtimePaths.Cwd
	}

	if err := os.MkdirAll(runtimeCwd, 0o755); err != nil {
		submitTaskResult(ctx, client, workerId, task.Id, dispatchToken, "failed", map[string]any{
			"error": "failed to create cwd",
			"details": map[string]any{
				"cwd":     runtimeCwd,
				"message": err.Error(),
			},
		})
		return err
	}

	logs.Info.Printf("Running task %d: script=%s number=%d procs=%d output=%s cwd=%s\n", task.Id, scriptPath, payload.Number, payload.Procs, outputDirAbs, runtimeCwd)

	if len(payload.AssetMappings) > 0 {
		submitTaskProgress(ctx, client, workerId, task.Id, dispatchToken, 20, "staging assets", nil)
		mappings := make([]assets.Mapping, 0, len(payload.AssetMappings))
		for _, mapping := range payload.AssetMappings {
			mappings = append(mappings, assets.Mapping{
				Source:      mapping.Source,
				Destination: mapping.Destination,
			})
		}

		stagedAssets, stageErr := assets.StageMappings(ctx, runtimeCwd, mappings)
		if stageErr != nil {
			result := map[string]any{
				"error": "asset staging failed",
				"details": map[string]any{
					"message": stageErr.Error(),
				},
			}
			if workerCleanupPolicy == "cleanup" && len(stagedAssets) > 0 {
				toCleanup := append(append([]assets.StagedFile{}, staged...), stagedAssets...)
				cleanupErr := assets.CleanupStagedFiles(toCleanup)
				if cleanupErr != nil {
					logs.Warn.Printf("Task %d cleanup failed after staging error: %v\n", task.Id, cleanupErr)
					result["cleanup_warning"] = cleanupErr.Error()
				}
			}
			var mappingErr *assets.MappingError
			if errors.As(stageErr, &mappingErr) {
				result["details"] = map[string]any{
					"source":      mappingErr.Source,
					"destination": mappingErr.Destination,
					"message":     mappingErr.Err.Error(),
				}
			}
			submitTaskResult(ctx, client, workerId, task.Id, dispatchToken, "failed", result)
			return stageErr
		}
		staged = append(staged, stagedAssets...)
	}

	runCleanup := func() error {
		if workerCleanupPolicy != "cleanup" || len(staged) == 0 {
			return nil
		}
		submitTaskProgress(ctx, client, workerId, task.Id, dispatchToken, 95, "cleanup", nil)
		cleanupErr := assets.CleanupStagedFiles(staged)
		if cleanupErr != nil {
			logs.Warn.Printf("Task %d cleanup failed: %v\n", task.Id, cleanupErr)
		}
		return cleanupErr
	}

	submitTaskProgress(ctx, client, workerId, task.Id, dispatchToken, 40, "rendering", nil)
	if err := render.Render(render.RenderOptions{
		ScriptPath: scriptPath,
		Cwd:        runtimeCwd,
		ImageNum:   payload.Number,
		Procs:      payload.Procs,
		OutputDir:  outputDirAbs,
	}); err != nil {
		cleanupErr := runCleanup()
		result := map[string]any{"error": err.Error()}
		if cleanupErr != nil {
			result["cleanup_warning"] = cleanupErr.Error()
		}
		submitTaskResult(ctx, client, workerId, task.Id, dispatchToken, "failed", result)
		return err
	}

	cleanupErr := runCleanup()
	result := map[string]any{"ok": true}
	if cleanupErr != nil {
		result["cleanup_warning"] = cleanupErr.Error()
	}
	submitTaskProgress(ctx, client, workerId, task.Id, dispatchToken, 100, "completed", nil)
	submitTaskResult(ctx, client, workerId, task.Id, dispatchToken, "success", result)
	return nil
}

func parseWorkerPayload(raw *json.RawMessage) (*workerTaskPayload, error) {
	if raw == nil || len(*raw) == 0 {
		return nil, errors.New("task payload is empty")
	}

	var payload workerTaskPayload
	if err := json.Unmarshal(*raw, &payload); err != nil {
		return nil, err
	}

	if payload.Script == "" {
		return nil, errors.New("payload.script is required")
	}
	if payload.Number <= 0 {
		payload.Number = 1
	}
	if payload.Procs <= 0 {
		payload.Procs = 1
	}
	for i, mapping := range payload.AssetMappings {
		if mapping.Source == "" {
			return nil, fmt.Errorf("payload.asset_mappings[%d].source is required", i)
		}
		if mapping.Destination == "" {
			return nil, fmt.Errorf("payload.asset_mappings[%d].destination is required", i)
		}
	}

	return &payload, nil
}

func submitTaskResult(ctx context.Context, client *rpcclient.RPCClient, workerId int, taskId int, dispatchToken string, status string, result map[string]any) {
	raw, err := json.Marshal(result)
	if err != nil {
		logs.Warn.Println("Failed to encode result:", err)
		return
	}
	_, err = client.SubmitResult(ctx, rpcclient.SubmitResultParams{
		WorkerId:      workerId,
		TaskId:        taskId,
		DispatchToken: dispatchToken,
		Status:        status,
		Result:        raw,
	})
	if err != nil {
		logs.Warn.Println("Failed to submit result:", err)
	}
}

func submitTaskProgress(ctx context.Context, client *rpcclient.RPCClient, workerId int, taskId int, dispatchToken string, progress int, message string, payload map[string]any) {
	var rawPayload *json.RawMessage
	if payload != nil {
		raw, err := json.Marshal(payload)
		if err != nil {
			logs.Warn.Println("Failed to encode progress payload:", err)
			return
		}
		msg := json.RawMessage(raw)
		rawPayload = &msg
	}
	var progressMessage *string
	if message != "" {
		progressMessage = &message
	}
	_, err := client.UpdateTaskProgress(ctx, rpcclient.UpdateTaskProgressParams{
		WorkerId:        workerId,
		TaskId:          taskId,
		DispatchToken:   dispatchToken,
		Progress:        progress,
		ProgressMessage: progressMessage,
		ProgressPayload: rawPayload,
	})
	if err != nil {
		logs.Warn.Printf("Failed to submit task progress (task=%d): %v\n", taskId, err)
	}
}

func isManagedResourceSource(source string) bool {
	source = strings.TrimSpace(source)
	if source == "" {
		return false
	}
	parsed, err := url.Parse(source)
	if err != nil {
		return false
	}
	switch parsed.Scheme {
	case "http", "https", "s3", "file":
		return true
	default:
		return false
	}
}

func workerScriptDestination(source string) string {
	base := "script.py"
	if parsed, err := url.Parse(source); err == nil {
		if parsed.Path != "" {
			candidate := filepath.Base(parsed.Path)
			if candidate != "" && candidate != "." && candidate != "/" {
				base = candidate
			}
		}
	}
	return filepath.Join(".rv-staged", "scripts", base)
}
