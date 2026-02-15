package cmd

import (
	"context"
	"errors"
	"strings"

	"github.com/Rapid-Vision/rv/internal/config"
	"github.com/Rapid-Vision/rv/internal/logs"
	"github.com/Rapid-Vision/rv/internal/worker"
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

func runWorker(_ *cobra.Command, _ []string) {
	cfg, err := config.LoadWorkerConfig(workerConfigPath)
	if err != nil {
		logs.Err.Fatalln("Failed to load worker config:", err)
	}

	if err := validateWorkerConfig(&cfg); err != nil {
		logs.Err.Fatalln("Invalid worker config:", err)
	}

	if err := worker.Run(context.Background(), &cfg, workerRunOnce); err != nil {
		logs.Err.Fatalln("Worker failed:", err)
	}
}

func validateWorkerConfig(cfg *config.WorkerConfig) error {
	if cfg == nil {
		return errors.New("worker config is required")
	}

	if cfg.RTasks.URL == "" {
		return errors.New("worker.rtasks.url is required")
	}
	if cfg.WorkerName == "" {
		return errors.New("worker.worker_name is required")
	}
	if cfg.TaskName == "" {
		return errors.New("worker.task_name is required")
	}
	if cfg.RTasks.PollInterval <= 0 {
		return errors.New("worker.rtasks.poll_interval must be > 0")
	}
	if cfg.Renderer.MaxProcs <= 0 {
		return errors.New("worker.renderer.max_procs must be > 0")
	}
	switch cfg.Directories.CleanupPolicy {
	case "keep", "cleanup":
	default:
		return errors.New("worker.directories.cleanup_policy must be either \"keep\" or \"cleanup\"")
	}
	resolvedS3URL, errS3URL := config.ResolveWorkerS3BaseURL(cfg.S3.OutputURL, cfg.S3.Path)
	if errS3URL != nil {
		return errS3URL
	}
	cfg.S3.OutputURL = resolvedS3URL
	if cfg.S3.OutputURL != "" && strings.TrimSpace(cfg.S3.Endpoint) == "" {
		return errors.New("worker.s3.endpoint is required when worker.s3.output_url is set")
	}
	if (strings.TrimSpace(cfg.S3.AccessKeyID) == "") != (strings.TrimSpace(cfg.S3.SecretKey) == "") {
		return errors.New("worker.s3.access_key and worker.s3.secret_key must be set together")
	}
	return nil
}
