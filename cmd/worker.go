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
	"github.com/Rapid-Vision/rv/internal/config"
	"github.com/Rapid-Vision/rv/internal/logs"
	"github.com/Rapid-Vision/rv/internal/render"
	"github.com/Rapid-Vision/rv/internal/rpcclient"
	"github.com/Rapid-Vision/rv/internal/utils"
	"github.com/spf13/cobra"
)

var (
	workerConfigPath        string
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
	workerS3OutputURL       string
	workerS3Path            string
	workerS3Endpoint        string
	workerS3Region          string
	workerS3Secure          bool
	workerCleanupOutputS3   bool
	workerS3AccessKey       string
	workerS3SecretKey       string
	workerS3SessionToken    string
)

var workerCmd = &cobra.Command{
	Use:   "worker",
	Short: "Run an rv worker using rtasks",
	Long:  "Poll rtasks for render jobs and execute them using rv render.",
	Run:   runWorker,
}

func init() {
	rootCmd.AddCommand(workerCmd)

	workerCmd.Flags().BoolVar(&workerRunOnce, "once", false, "run a single task and exit")
	workerCmd.Flags().StringVar(&workerConfigPath, "config", "worker-conf.yaml", "Path to worker config file")
}

type workerTaskPayload struct {
	Script        string               `json:"script"`
	Number        int                  `json:"number"`
	Procs         int                  `json:"procs"`
	OutputS3URL   string               `json:"output_s3_url"`
	AssetMappings []workerAssetMapping `json:"asset_mappings"`
}

var uploadDirectoryToS3 = assets.UploadDirectoryToS3

type workerAssetMapping struct {
	Source      string `json:"source"`
	Destination string `json:"destination"`
}

func runWorker(_ *cobra.Command, args []string) {
	cfg, err := config.LoadWorkerConfig(workerConfigPath)
	if err != nil {
		logs.Err.Fatalln("Failed to load worker config:", err)
	}

	workerURL = cfg.RTasks.URL
	workerToken = cfg.RTasks.Token
	workerName = cfg.WorkerName
	workerTaskName = cfg.TaskName
	workerPollInterval = cfg.RTasks.PollInterval
	workerHeartbeatInterval = cfg.RTasks.HeartbeatInterval
	workerCwd = cfg.Directories.Working
	workerOutputDir = cfg.Directories.Output
	workerCleanupPolicy = cfg.Directories.CleanupPolicy
	workerS3OutputURL = cfg.S3.OutputURL
	workerS3Path = cfg.S3.Path
	workerS3Endpoint = cfg.S3.Endpoint
	workerS3Region = cfg.S3.Region
	workerS3Secure = cfg.S3.Secure
	workerCleanupOutputS3 = cfg.S3.Cleanup
	workerS3AccessKey = cfg.S3.AccessKeyID
	workerS3SecretKey = cfg.S3.SecretKey
	workerS3SessionToken = cfg.S3.SessionToken

	if workerURL == "" {
		logs.Err.Fatalln("worker.rtasks.url is required")
	}
	if workerName == "" {
		logs.Err.Fatalln("worker.worker_name is required")
	}
	if workerTaskName == "" {
		logs.Err.Fatalln("worker.task_name is required")
	}
	if workerPollInterval <= 0 {
		logs.Err.Fatalln("worker.rtasks.poll_interval must be > 0")
	}
	switch workerCleanupPolicy {
	case "keep", "cleanup":
	default:
		logs.Err.Fatalln("worker.directories.cleanup_policy must be either \"keep\" or \"cleanup\"")
	}
	var errS3URL error
	workerS3OutputURL, errS3URL = config.ResolveWorkerS3BaseURL(workerS3OutputURL, workerS3Path)
	if errS3URL != nil {
		logs.Err.Fatalln("Invalid worker.s3 destination:", errS3URL)
	}
	if workerS3OutputURL != "" && strings.TrimSpace(workerS3Endpoint) == "" {
		logs.Err.Fatalln("worker.s3.endpoint is required when worker.s3.output_url is set")
	}
	if (strings.TrimSpace(workerS3AccessKey) == "") != (strings.TrimSpace(workerS3SecretKey) == "") {
		logs.Err.Fatalln("worker.s3.access_key and worker.s3.secret_key must be set together")
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
	renderResult, err := render.Render(render.RenderOptions{
		ScriptPath: scriptPath,
		Cwd:        runtimeCwd,
		ImageNum:   payload.Number,
		Procs:      payload.Procs,
		OutputDir:  outputDirAbs,
	})
	if err != nil {
		cleanupErr := runCleanup()
		result := map[string]any{"error": err.Error()}
		if cleanupErr != nil {
			result["cleanup_warning"] = cleanupErr.Error()
		}
		submitTaskResult(ctx, client, workerId, task.Id, dispatchToken, "failed", result)
		return err
	}

	resultOutput := map[string]any{
		"local_dir": renderResult.OutputDir,
	}

	targetS3URL := strings.TrimSpace(workerS3OutputURL)
	if strings.TrimSpace(payload.OutputS3URL) != "" {
		targetS3URL = strings.TrimSpace(payload.OutputS3URL)
	}
	if targetS3URL != "" {
		submitTaskProgress(ctx, client, workerId, task.Id, dispatchToken, 70, "uploading dataset", nil)
		uploadedS3URL, taskS3URL, uploadErr := uploadRenderedOutput(ctx, task.Id, targetS3URL, renderResult.OutputDir)
		if uploadErr != nil {
			cleanupErr := runCleanup()
			result := map[string]any{
				"error": "dataset upload failed",
				"output": map[string]any{
					"local_dir": renderResult.OutputDir,
					"s3_target": taskS3URL,
				},
				"details": map[string]any{
					"message": uploadErr.Error(),
				},
			}
			if cleanupErr != nil {
				result["cleanup_warning"] = cleanupErr.Error()
			}
			submitTaskResult(ctx, client, workerId, task.Id, dispatchToken, "failed", result)
			return uploadErr
		}
		resultOutput["s3_uri"] = uploadedS3URL

		if workerCleanupOutputS3 {
			if err := os.RemoveAll(renderResult.OutputDir); err != nil {
				resultOutput["cleanup_output_warning"] = err.Error()
			}
		}
	}

	cleanupErr := runCleanup()
	result := map[string]any{
		"ok":     true,
		"output": resultOutput,
	}
	if cleanupErr != nil {
		result["cleanup_warning"] = cleanupErr.Error()
	}
	submitTaskProgress(ctx, client, workerId, task.Id, dispatchToken, 90, "finalizing result", nil)
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
	if strings.TrimSpace(payload.OutputS3URL) != "" {
		if _, err := assets.ParseS3URL(payload.OutputS3URL); err != nil {
			return nil, fmt.Errorf("payload.output_s3_url is invalid: %w", err)
		}
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

func uploadRenderedOutput(ctx context.Context, taskID int, targetS3URL string, localOutputDir string) (string, string, error) {
	taskS3URL, err := assets.BuildWorkerTaskS3URL(targetS3URL, taskID, localOutputDir)
	if err != nil {
		return "", targetS3URL, err
	}

	uploadedS3URL, err := uploadDirectoryToS3(ctx, assets.S3UploadOptions{
		LocalDir:        localOutputDir,
		DestinationURL:  taskS3URL,
		Endpoint:        workerS3Endpoint,
		Region:          workerS3Region,
		Secure:          workerS3Secure,
		AccessKeyID:     workerS3AccessKey,
		SecretAccessKey: workerS3SecretKey,
		SessionToken:    workerS3SessionToken,
	})
	if err != nil {
		return "", taskS3URL, err
	}

	return uploadedS3URL, taskS3URL, nil
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
