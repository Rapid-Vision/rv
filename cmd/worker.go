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
	"github.com/google/uuid"
	"github.com/spf13/cobra"
)

var (
	workerConfigPath string
	workerRunOnce    bool
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
	Resolution    []int                `json:"resolution"`
	AssetMappings []workerAssetMapping `json:"asset_mappings"`
}

var uploadDirectoryToS3 = assets.UploadDirectoryToS3
var newWorkerTaskUUID = func() string { return uuid.NewString() }

type workerAssetMapping struct {
	Source      string `json:"source"`
	Destination string `json:"destination"`
}

func runWorker(_ *cobra.Command, args []string) {
	cfg, err := config.LoadWorkerConfig(workerConfigPath)
	if err != nil {
		logs.Err.Fatalln("Failed to load worker config:", err)
	}

	if cfg.RTasks.URL == "" {
		logs.Err.Fatalln("worker.rtasks.url is required")
	}
	if cfg.WorkerName == "" {
		logs.Err.Fatalln("worker.worker_name is required")
	}
	if cfg.TaskName == "" {
		logs.Err.Fatalln("worker.task_name is required")
	}
	if cfg.RTasks.PollInterval <= 0 {
		logs.Err.Fatalln("worker.rtasks.poll_interval must be > 0")
	}
	if cfg.Renderer.MaxProcs <= 0 {
		logs.Err.Fatalln("worker.renderer.max_procs must be > 0")
	}
	switch cfg.Directories.CleanupPolicy {
	case "keep", "cleanup":
	default:
		logs.Err.Fatalln("worker.directories.cleanup_policy must be either \"keep\" or \"cleanup\"")
	}
	resolvedS3URL, errS3URL := config.ResolveWorkerS3BaseURL(cfg.S3.OutputURL, cfg.S3.Path)
	if errS3URL != nil {
		logs.Err.Fatalln("Invalid worker.s3 destination:", errS3URL)
	}
	cfg.S3.OutputURL = resolvedS3URL
	if cfg.S3.OutputURL != "" && strings.TrimSpace(cfg.S3.Endpoint) == "" {
		logs.Err.Fatalln("worker.s3.endpoint is required when worker.s3.output_url is set")
	}
	if (strings.TrimSpace(cfg.S3.AccessKeyID) == "") != (strings.TrimSpace(cfg.S3.SecretKey) == "") {
		logs.Err.Fatalln("worker.s3.access_key and worker.s3.secret_key must be set together")
	}

	client := rpcclient.NewRPCClient(cfg.RTasks.URL)
	if cfg.RTasks.Token != "" {
		client = client.WithBearerToken(cfg.RTasks.Token)
	}

	ctx := context.Background()
	worker, err := client.DeclareWorker(ctx, rpcclient.DeclareWorkerParams{
		Name:     cfg.WorkerName,
		TaskName: cfg.TaskName,
	})
	if err != nil {
		logs.Err.Fatalln("Failed to declare worker:", err)
	}
	logs.Info.Printf("Worker declared (id=%d, name=%s, task=%s)\n", worker.Id, worker.Name, worker.TaskName)

	stopCh := make(chan os.Signal, 1)
	signal.Notify(stopCh, os.Interrupt, syscall.SIGTERM)

	done := make(chan struct{})
	if cfg.RTasks.HeartbeatInterval > 0 {
		go func() {
			ticker := time.NewTicker(cfg.RTasks.HeartbeatInterval)
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
			time.Sleep(cfg.RTasks.PollInterval)
			continue
		}
		if dispatch.Task == nil {
			time.Sleep(cfg.RTasks.PollInterval)
			continue
		}
		if dispatch.DispatchToken == nil {
			logs.Warn.Println("Dispatch token missing; skipping task")
			time.Sleep(cfg.RTasks.PollInterval)
			continue
		}

		task := dispatch.Task
		err = handleWorkerTask(ctx, client, worker.Id, *dispatch.DispatchToken, task, &cfg)
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

func handleWorkerTask(ctx context.Context, client *rpcclient.RPCClient, workerId int, dispatchToken string, task *rpcclient.TaskModel, cfg *config.WorkerConfig) error {
	payload, err := parseWorkerPayload(task.Payload)
	if err != nil {
		submitTaskResult(ctx, client, workerId, task.Id, dispatchToken, "failed", map[string]any{"error": err.Error()})
		return err
	}

	resolveWorkerCwd := func() (string, error) {
		if cfg.Directories.Working != "" {
			return filepath.Abs(cfg.Directories.Working)
		}
		return os.Getwd()
	}

	var scriptPath string
	var runtimeCwd string
	var taskWorkDir string
	var taskUUID string
	var staged []assets.StagedFile
	managedSource := isManagedResourceSource(payload.Script)

	addTaskWorkspaceMeta := func(result map[string]any) {
		if strings.TrimSpace(taskWorkDir) == "" {
			return
		}
		result["task_work_dir"] = taskWorkDir
		if strings.TrimSpace(taskUUID) != "" {
			result["task_uuid"] = taskUUID
		}
	}

	runCleanup := func() error {
		if cfg.Directories.CleanupPolicy != "cleanup" {
			return nil
		}
		if len(staged) == 0 && strings.TrimSpace(taskWorkDir) == "" {
			return nil
		}
		submitTaskProgress(ctx, client, workerId, task.Id, dispatchToken, 95, "cleanup", nil)
		cleanupErr := cleanupWorkerTaskResources(cfg.Directories.CleanupPolicy, staged, taskWorkDir)
		if cleanupErr != nil {
			logs.Warn.Printf("Task %d cleanup failed: %v\n", task.Id, cleanupErr)
		}
		return cleanupErr
	}

	submitTaskProgress(ctx, client, workerId, task.Id, dispatchToken, 5, "resolving paths", nil)
	outputDirAbs, err := filepath.Abs(cfg.Directories.Output)
	if err != nil {
		result := map[string]any{
			"error": "failed to resolve output path",
			"details": map[string]any{
				"message": err.Error(),
			},
		}
		addTaskWorkspaceMeta(result)
		submitTaskResult(ctx, client, workerId, task.Id, dispatchToken, "failed", result)
		return err
	}

	if managedSource {
		baseCwd, resolveErr := resolveWorkerCwd()
		if resolveErr != nil {
			result := map[string]any{
				"error": "failed to resolve cwd",
				"details": map[string]any{
					"message": resolveErr.Error(),
				},
			}
			addTaskWorkspaceMeta(result)
			submitTaskResult(ctx, client, workerId, task.Id, dispatchToken, "failed", result)
			return resolveErr
		}

		runtimeCwd, taskUUID, err = resolveManagedTaskRuntimeCwd(baseCwd)
		if err != nil {
			result := map[string]any{
				"error": "failed to build task workspace",
				"details": map[string]any{
					"message": err.Error(),
				},
			}
			addTaskWorkspaceMeta(result)
			submitTaskResult(ctx, client, workerId, task.Id, dispatchToken, "failed", result)
			return err
		}
		taskWorkDir = runtimeCwd

		if err := os.MkdirAll(runtimeCwd, 0o755); err != nil {
			result := map[string]any{
				"error": "failed to create cwd",
				"details": map[string]any{
					"cwd":     runtimeCwd,
					"message": err.Error(),
				},
			}
			addTaskWorkspaceMeta(result)
			submitTaskResult(ctx, client, workerId, task.Id, dispatchToken, "failed", result)
			return err
		}
		logs.Info.Printf("Task %d workspace: task_uuid=%s task_work_dir=%s\n", task.Id, taskUUID, taskWorkDir)

		submitTaskProgress(ctx, client, workerId, task.Id, dispatchToken, 12, "staging script", nil)
		scriptMappings := []assets.Mapping{{
			Source:      payload.Script,
			Destination: workerScriptDestination(payload.Script),
		}}
		stagedScript, stageErr := assets.StageMappings(ctx, runtimeCwd, scriptMappings)
		staged = append(staged, stagedScript...)
		if stageErr != nil {
			result := map[string]any{
				"error": "script staging failed",
				"details": map[string]any{
					"message": stageErr.Error(),
				},
			}
			cleanupErr := runCleanup()
			addTaskWorkspaceMeta(result)
			var mappingErr *assets.MappingError
			if errors.As(stageErr, &mappingErr) {
				result["details"] = map[string]any{
					"source":      mappingErr.Source,
					"destination": mappingErr.Destination,
					"message":     mappingErr.Err.Error(),
				}
			}
			if cleanupErr != nil {
				result["cleanup_warning"] = cleanupErr.Error()
			}
			submitTaskResult(ctx, client, workerId, task.Id, dispatchToken, "failed", result)
			return stageErr
		}
		if len(stagedScript) == 0 {
			err := errors.New("script staging produced no files")
			result := map[string]any{
				"error": err.Error(),
			}
			cleanupErr := runCleanup()
			addTaskWorkspaceMeta(result)
			if cleanupErr != nil {
				result["cleanup_warning"] = cleanupErr.Error()
			}
			submitTaskResult(ctx, client, workerId, task.Id, dispatchToken, "failed", result)
			return err
		}
		scriptPath = stagedScript[0].Path
	} else {
		runtimePaths, pathErr := utils.ResolveRuntimePaths(payload.Script, cfg.Directories.Working)
		if pathErr != nil {
			result := map[string]any{
				"error": "failed to resolve paths",
				"details": map[string]any{
					"message": pathErr.Error(),
				},
			}
			addTaskWorkspaceMeta(result)
			submitTaskResult(ctx, client, workerId, task.Id, dispatchToken, "failed", result)
			return pathErr
		}
		scriptPath = runtimePaths.ScriptPath
		runtimeCwd = runtimePaths.Cwd
	}

	if err := os.MkdirAll(runtimeCwd, 0o755); err != nil {
		result := map[string]any{
			"error": "failed to create cwd",
			"details": map[string]any{
				"cwd":     runtimeCwd,
				"message": err.Error(),
			},
		}
		addTaskWorkspaceMeta(result)
		submitTaskResult(ctx, client, workerId, task.Id, dispatchToken, "failed", result)
		return err
	}

	logs.Info.Printf("Running task %d: script=%s number=%d resolution=%v output=%s cwd=%s\n", task.Id, scriptPath, payload.Number, payload.Resolution, outputDirAbs, runtimeCwd)

	if len(payload.AssetMappings) > 0 {
		submitTaskProgress(ctx, client, workerId, task.Id, dispatchToken, 20, "staging assets", nil)
		mappings := make([]assets.Mapping, 0, len(payload.AssetMappings))
		for _, mapping := range payload.AssetMappings {
			destination := mapping.Destination
			if managedSource {
				destination = workerAssetDestination(mapping.Destination)
			}
			mappings = append(mappings, assets.Mapping{
				Source:      mapping.Source,
				Destination: destination,
			})
		}

		stagedAssets, stageErr := assets.StageMappings(ctx, runtimeCwd, mappings)
		staged = append(staged, stagedAssets...)
		if stageErr != nil {
			result := map[string]any{
				"error": "asset staging failed",
				"details": map[string]any{
					"message": stageErr.Error(),
				},
			}
			cleanupErr := runCleanup()
			addTaskWorkspaceMeta(result)
			var mappingErr *assets.MappingError
			if errors.As(stageErr, &mappingErr) {
				result["details"] = map[string]any{
					"source":      mappingErr.Source,
					"destination": mappingErr.Destination,
					"message":     mappingErr.Err.Error(),
				}
			}
			if cleanupErr != nil {
				result["cleanup_warning"] = cleanupErr.Error()
			}
			submitTaskResult(ctx, client, workerId, task.Id, dispatchToken, "failed", result)
			return stageErr
		}
	}

	submitTaskProgress(ctx, client, workerId, task.Id, dispatchToken, 40, "rendering", nil)
	renderResult, err := render.Render(render.RenderOptions{
		ScriptPath: scriptPath,
		Cwd:        runtimeCwd,
		ImageNum:   payload.Number,
		Procs:      cfg.Renderer.MaxProcs,
		Resolution: [2]int{payload.Resolution[0], payload.Resolution[1]},
		OutputDir:  outputDirAbs,
	})
	if err != nil {
		cleanupErr := runCleanup()
		result := map[string]any{"error": err.Error()}
		addTaskWorkspaceMeta(result)
		if cleanupErr != nil {
			result["cleanup_warning"] = cleanupErr.Error()
		}
		submitTaskResult(ctx, client, workerId, task.Id, dispatchToken, "failed", result)
		return err
	}

	resultOutput := map[string]any{
		"local_dir": renderResult.OutputDir,
	}
	if strings.TrimSpace(taskWorkDir) != "" {
		resultOutput["task_work_dir"] = taskWorkDir
	}
	if strings.TrimSpace(taskUUID) != "" {
		resultOutput["task_uuid"] = taskUUID
	}

	targetS3URL := strings.TrimSpace(cfg.S3.OutputURL)
	if targetS3URL != "" {
		submitTaskProgress(ctx, client, workerId, task.Id, dispatchToken, 70, "uploading dataset", nil)
		uploadedS3URL, taskS3URL, uploadErr := uploadRenderedOutput(ctx, cfg, task.Id, targetS3URL, renderResult.OutputDir)
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
			addTaskWorkspaceMeta(result)
			if cleanupErr != nil {
				result["cleanup_warning"] = cleanupErr.Error()
			}
			submitTaskResult(ctx, client, workerId, task.Id, dispatchToken, "failed", result)
			return uploadErr
		}
		resultOutput["s3_uri"] = uploadedS3URL

		if cfg.S3.Cleanup {
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
	addTaskWorkspaceMeta(result)
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
	if len(payload.Resolution) != 2 {
		return nil, errors.New("payload.resolution must be [width, height]")
	}
	if payload.Resolution[0] <= 0 || payload.Resolution[1] <= 0 {
		return nil, errors.New("payload.resolution width and height must be > 0")
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

func uploadRenderedOutput(ctx context.Context, cfg *config.WorkerConfig, taskID int, targetS3URL string, localOutputDir string) (string, string, error) {
	taskS3URL, err := assets.BuildWorkerTaskS3URL(targetS3URL, taskID, localOutputDir)
	if err != nil {
		return "", targetS3URL, err
	}

	uploadedS3URL, err := uploadDirectoryToS3(ctx, assets.S3UploadOptions{
		LocalDir:        localOutputDir,
		DestinationURL:  taskS3URL,
		Endpoint:        cfg.S3.Endpoint,
		Region:          cfg.S3.Region,
		Secure:          cfg.S3.Secure,
		AccessKeyID:     cfg.S3.AccessKeyID,
		SecretAccessKey: cfg.S3.SecretKey,
		SessionToken:    cfg.S3.SessionToken,
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
	return filepath.Join("scripts", base)
}

func buildTaskWorkDir(baseCwd string, taskUUID string) string {
	return filepath.Join(baseCwd, taskUUID)
}

func workerAssetDestination(destination string) string {
	return filepath.Join("assets", destination)
}

func resolveManagedTaskRuntimeCwd(baseCwd string) (string, string, error) {
	baseCwd = strings.TrimSpace(baseCwd)
	if baseCwd == "" {
		return "", "", errors.New("base cwd is required")
	}

	taskUUID := strings.TrimSpace(newWorkerTaskUUID())
	if taskUUID == "" {
		return "", "", errors.New("task UUID is empty")
	}

	return buildTaskWorkDir(baseCwd, taskUUID), taskUUID, nil
}

func cleanupWorkerTaskResources(cleanupPolicy string, staged []assets.StagedFile, taskWorkDir string) error {
	if cleanupPolicy != "cleanup" {
		return nil
	}

	var errs []string
	if len(staged) > 0 {
		if err := assets.CleanupStagedFiles(staged); err != nil {
			errs = append(errs, err.Error())
		}
	}
	if strings.TrimSpace(taskWorkDir) != "" {
		if err := os.RemoveAll(taskWorkDir); err != nil {
			errs = append(errs, fmt.Sprintf("remove task work dir %q: %v", taskWorkDir, err))
		}
	}

	if len(errs) > 0 {
		return errors.New(strings.Join(errs, "; "))
	}
	return nil
}
