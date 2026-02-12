package worker

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
)

type UUIDFn func() string
type UploadDirFn func(context.Context, assets.S3UploadOptions) (string, error)
type EnsureS3BucketFn func(context.Context, assets.S3BucketOptions) error

type Deps struct {
	UUIDFn         UUIDFn
	UploadDirFn    UploadDirFn
	EnsureBucketFn EnsureS3BucketFn
}

type Runner struct {
	deps Deps
}

func defaultUUIDFn() UUIDFn {
	return uuid.NewString
}

func defaultUploadDirFn() UploadDirFn {
	return assets.UploadDirectoryToS3
}

func defaultEnsureBucketFn() EnsureS3BucketFn {
	return assets.EnsureS3Bucket
}

func NewRunner(deps Deps) *Runner {
	if deps.UUIDFn == nil {
		deps.UUIDFn = defaultUUIDFn()
	}
	if deps.UploadDirFn == nil {
		deps.UploadDirFn = defaultUploadDirFn()
	}
	if deps.EnsureBucketFn == nil {
		deps.EnsureBucketFn = defaultEnsureBucketFn()
	}
	return &Runner{deps: deps}
}

func Run(ctx context.Context, cfg *config.WorkerConfig, runOnce bool) error {
	return NewRunner(Deps{}).Run(ctx, cfg, runOnce)
}

func (r *Runner) Run(ctx context.Context, cfg *config.WorkerConfig, runOnce bool) error {
	if cfg == nil {
		return errors.New("worker config is required")
	}
	if ctx == nil {
		ctx = context.Background()
	}
	if err := r.ensureConfiguredS3Bucket(ctx, cfg); err != nil {
		return err
	}

	client := rpcclient.NewRPCClient(cfg.RTasks.URL)
	if cfg.RTasks.Token != "" {
		client = client.WithBearerToken(cfg.RTasks.Token)
	}

	declaredWorker, err := client.DeclareWorker(ctx, rpcclient.DeclareWorkerParams{
		Name:     cfg.WorkerName,
		TaskName: cfg.TaskName,
	})
	if err != nil {
		return fmt.Errorf("declare worker: %w", err)
	}
	logs.Info.Printf("Worker declared (id=%d, name=%s, task=%s)\n", declaredWorker.Id, declaredWorker.Name, declaredWorker.TaskName)

	stopCh := make(chan os.Signal, 1)
	signal.Notify(stopCh, os.Interrupt, syscall.SIGTERM)
	defer signal.Stop(stopCh)

	done := make(chan struct{})
	doneClosed := false
	closeDone := func() {
		if doneClosed {
			return
		}
		close(done)
		doneClosed = true
	}

	if cfg.RTasks.HeartbeatInterval > 0 {
		go func() {
			ticker := time.NewTicker(cfg.RTasks.HeartbeatInterval)
			defer ticker.Stop()
			for {
				select {
				case <-ticker.C:
					_, _ = client.UpdateWorkerStatus(ctx, rpcclient.UpdateWorkerStatusParams{WorkerId: declaredWorker.Id})
				case <-done:
					return
				}
			}
		}()
	}

	stopAndReturn := func(message string) error {
		closeDone()
		if err := client.StopWorker(ctx, rpcclient.StopWorkerParams{WorkerId: declaredWorker.Id}); err != nil {
			return fmt.Errorf("stop worker: %w", err)
		}
		logs.Info.Println(message)
		return nil
	}

	for {
		select {
		case <-stopCh:
			return stopAndReturn("Worker stopped.")
		default:
		}

		dispatch, err := client.RequestTask(ctx, rpcclient.RequestTaskParams{WorkerId: declaredWorker.Id})
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
		err = r.HandleWorkerTask(ctx, client, declaredWorker.Id, *dispatch.DispatchToken, task, cfg)
		if err != nil {
			logs.Warn.Println("Task failed:", err)
		}

		if runOnce {
			return stopAndReturn("Worker stopped (once mode).")
		}
	}
}

func (r *Runner) HandleWorkerTask(ctx context.Context, client *rpcclient.RPCClient, workerId int, dispatchToken string, task *rpcclient.TaskModel, cfg *config.WorkerConfig) error {
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

		runtimeCwd, taskUUID, err = r.resolveManagedTaskRuntimeCwd(baseCwd)
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
		stageOpts := stageOptionsFromConfig(cfg)
		stagedScript, stageErr := assets.StageMappingsWithOptions(ctx, runtimeCwd, scriptMappings, stageOpts)
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

	logs.Info.Printf(
		"Running task %d: script=%s number=%d resolution=%v time_limit=%v max_samples=%v min_samples=%v noise_threshold_enabled=%v noise_threshold=%v output=%s cwd=%s\n",
		task.Id,
		scriptPath,
		payload.Number,
		payload.Resolution,
		payload.TimeLimit,
		payload.MaxSamples,
		payload.MinSamples,
		payload.NoiseThresholdEnabled,
		payload.NoiseThreshold,
		outputDirAbs,
		runtimeCwd,
	)

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

		stageOpts := stageOptionsFromConfig(cfg)
		stagedAssets, stageErr := assets.StageMappingsWithOptions(ctx, runtimeCwd, mappings, stageOpts)
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
		ScriptPath:            scriptPath,
		Cwd:                   runtimeCwd,
		ImageNum:              payload.Number,
		Procs:                 cfg.Renderer.MaxProcs,
		Resolution:            [2]int{payload.Resolution[0], payload.Resolution[1]},
		OutputDir:             outputDirAbs,
		TimeLimit:             payload.TimeLimit,
		MaxSamples:            payload.MaxSamples,
		MinSamples:            payload.MinSamples,
		NoiseThresholdEnabled: payload.NoiseThresholdEnabled,
		NoiseThreshold:        payload.NoiseThreshold,
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
		uploadedS3URL, taskS3URL, uploadErr := r.uploadRenderedOutput(ctx, cfg, task.Id, targetS3URL, renderResult.OutputDir)
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

func parseWorkerPayload(raw *json.RawMessage) (*WorkerTaskPayload, error) {
	if raw == nil || len(*raw) == 0 {
		return nil, errors.New("task payload is empty")
	}

	var payload WorkerTaskPayload
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
	if payload.TimeLimit != nil && *payload.TimeLimit <= 0 {
		return nil, errors.New("payload.time_limit must be > 0")
	}
	if payload.MaxSamples != nil && *payload.MaxSamples <= 0 {
		return nil, errors.New("payload.max_samples must be > 0")
	}
	if payload.MinSamples != nil && *payload.MinSamples < 0 {
		return nil, errors.New("payload.min_samples must be >= 0")
	}
	if payload.MinSamples != nil && payload.MaxSamples != nil && *payload.MinSamples > *payload.MaxSamples {
		return nil, errors.New("payload.min_samples must be <= payload.max_samples")
	}
	if payload.NoiseThresholdEnabled != nil && *payload.NoiseThresholdEnabled {
		if payload.NoiseThreshold == nil {
			return nil, errors.New("payload.noise_threshold is required when payload.noise_threshold_enabled=true")
		}
		if *payload.NoiseThreshold <= 0 {
			return nil, errors.New("payload.noise_threshold must be > 0 when payload.noise_threshold_enabled=true")
		}
	}
	if payload.NoiseThreshold != nil {
		if payload.NoiseThresholdEnabled == nil || !*payload.NoiseThresholdEnabled {
			return nil, errors.New("payload.noise_threshold requires payload.noise_threshold_enabled=true")
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

func (r *Runner) uploadRenderedOutput(ctx context.Context, cfg *config.WorkerConfig, taskID int, targetS3URL string, localOutputDir string) (string, string, error) {
	taskS3URL, err := assets.BuildWorkerTaskS3URL(targetS3URL, taskID, localOutputDir)
	if err != nil {
		return "", targetS3URL, err
	}

	uploadedS3URL, err := r.deps.UploadDirFn(ctx, assets.S3UploadOptions{
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

func (r *Runner) ensureConfiguredS3Bucket(ctx context.Context, cfg *config.WorkerConfig) error {
	targetS3URL := strings.TrimSpace(cfg.S3.OutputURL)
	if targetS3URL == "" {
		return nil
	}
	if err := r.deps.EnsureBucketFn(ctx, assets.S3BucketOptions{
		DestinationURL:  targetS3URL,
		Endpoint:        cfg.S3.Endpoint,
		Region:          cfg.S3.Region,
		Secure:          cfg.S3.Secure,
		AccessKeyID:     cfg.S3.AccessKeyID,
		SecretAccessKey: cfg.S3.SecretKey,
		SessionToken:    cfg.S3.SessionToken,
	}); err != nil {
		return fmt.Errorf("ensure configured s3 bucket: %w", err)
	}
	return nil
}

func stageOptionsFromConfig(cfg *config.WorkerConfig) assets.StageOptions {
	return assets.StageOptions{
		S3: assets.StageS3Options{
			Endpoint:        cfg.S3.Endpoint,
			Region:          cfg.S3.Region,
			Secure:          cfg.S3.Secure,
			AccessKeyID:     cfg.S3.AccessKeyID,
			SecretAccessKey: cfg.S3.SecretKey,
			SessionToken:    cfg.S3.SessionToken,
		},
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
	return filepath.Join("scripts", base)
}

func buildTaskWorkDir(baseCwd string, taskUUID string) string {
	return filepath.Join(baseCwd, taskUUID)
}

func workerAssetDestination(destination string) string {
	return filepath.Join("assets", destination)
}

func (r *Runner) resolveManagedTaskRuntimeCwd(baseCwd string) (string, string, error) {
	baseCwd = strings.TrimSpace(baseCwd)
	if baseCwd == "" {
		return "", "", errors.New("base cwd is required")
	}

	taskUUID := strings.TrimSpace(r.deps.UUIDFn())
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
