package config

import (
	"errors"
	"fmt"
	"os"
	"strings"
	"time"

	"github.com/Rapid-Vision/rv/internal/assets"
	"github.com/spf13/viper"
)

type WorkerConfig struct {
	WorkerName string `mapstructure:"worker_name"`
	TaskName   string `mapstructure:"task_name"`
	Renderer   struct {
		MaxProcs int `mapstructure:"max_procs"`
	} `mapstructure:"renderer"`
	RTasks struct {
		URL               string        `mapstructure:"url"`
		Token             string        `mapstructure:"token"`
		PollInterval      time.Duration `mapstructure:"poll_interval"`
		HeartbeatInterval time.Duration `mapstructure:"heartbeat_interval"`
	} `mapstructure:"rtasks"`
	Directories struct {
		Working       string `mapstructure:"working"`
		Output        string `mapstructure:"output"`
		CleanupPolicy string `mapstructure:"cleanup_policy"`
	} `mapstructure:"directories"`
	S3 struct {
		Endpoint     string `mapstructure:"endpoint"`
		OutputURL    string `mapstructure:"output_url"`
		Path         string `mapstructure:"path"`
		Region       string `mapstructure:"region"`
		Secure       bool   `mapstructure:"secure"`
		Cleanup      bool   `mapstructure:"cleanup"`
		AccessKeyID  string `mapstructure:"access_key"`
		SecretKey    string `mapstructure:"secret_key"`
		SessionToken string `mapstructure:"session_token"`
	} `mapstructure:"s3"`
}

func LoadWorkerConfig(configPath string) (WorkerConfig, error) {
	if strings.TrimSpace(configPath) == "" {
		return WorkerConfig{}, errors.New("config path is required")
	}

	v := viper.New()
	v.SetConfigFile(configPath)
	v.SetConfigType("yaml")

	v.SetDefault("worker.rtasks.token", os.Getenv("RTASKS_API_TOKEN"))
	v.SetDefault("worker.rtasks.poll_interval", "2s")
	v.SetDefault("worker.rtasks.heartbeat_interval", "10s")
	v.SetDefault("worker.renderer.max_procs", 1)
	v.SetDefault("worker.directories.output", "./out")
	v.SetDefault("worker.directories.cleanup_policy", "keep")
	v.SetDefault("worker.s3.endpoint", "s3.amazonaws.com")
	v.SetDefault("worker.s3.region", os.Getenv("AWS_REGION"))
	v.SetDefault("worker.s3.secure", true)
	v.SetDefault("worker.s3.cleanup", false)
	v.SetDefault("worker.s3.access_key", os.Getenv("S3_ACCESS_KEY"))
	v.SetDefault("worker.s3.secret_key", os.Getenv("S3_SECRET_KEY"))
	v.SetDefault("worker.s3.session_token", os.Getenv("S3_SESSION_TOKEN"))

	if err := v.ReadInConfig(); err != nil {
		return WorkerConfig{}, err
	}

	cfg := WorkerConfig{
		WorkerName: strings.TrimSpace(v.GetString("worker.worker_name")),
		TaskName:   strings.TrimSpace(v.GetString("worker.task_name")),
	}
	cfg.RTasks.URL = strings.TrimSpace(v.GetString("worker.rtasks.url"))
	cfg.RTasks.Token = strings.TrimSpace(v.GetString("worker.rtasks.token"))
	cfg.RTasks.PollInterval = v.GetDuration("worker.rtasks.poll_interval")
	cfg.RTasks.HeartbeatInterval = v.GetDuration("worker.rtasks.heartbeat_interval")
	cfg.Renderer.MaxProcs = v.GetInt("worker.renderer.max_procs")

	cfg.Directories.Working = strings.TrimSpace(v.GetString("worker.directories.working"))
	cfg.Directories.Output = strings.TrimSpace(v.GetString("worker.directories.output"))
	cfg.Directories.CleanupPolicy = strings.TrimSpace(v.GetString("worker.directories.cleanup_policy"))

	cfg.S3.Endpoint = strings.TrimSpace(v.GetString("worker.s3.endpoint"))
	cfg.S3.OutputURL = strings.TrimSpace(v.GetString("worker.s3.output_url"))
	cfg.S3.Path = strings.TrimSpace(v.GetString("worker.s3.path"))
	cfg.S3.Region = strings.TrimSpace(v.GetString("worker.s3.region"))
	cfg.S3.Secure = v.GetBool("worker.s3.secure")
	cfg.S3.Cleanup = v.GetBool("worker.s3.cleanup")
	cfg.S3.AccessKeyID = strings.TrimSpace(v.GetString("worker.s3.access_key"))
	cfg.S3.SecretKey = strings.TrimSpace(v.GetString("worker.s3.secret_key"))
	cfg.S3.SessionToken = strings.TrimSpace(v.GetString("worker.s3.session_token"))

	return cfg, nil
}

func ResolveWorkerS3BaseURL(outputURL string, s3Path string) (string, error) {
	outputURL = strings.TrimSpace(outputURL)
	s3Path = strings.TrimSpace(s3Path)

	if outputURL != "" && s3Path != "" {
		return "", errors.New("set only one of worker.s3.output_url or worker.s3.path")
	}
	if outputURL != "" {
		if _, err := assets.ParseS3URL(outputURL); err != nil {
			return "", fmt.Errorf("worker.s3.output_url is invalid: %w", err)
		}
		return outputURL, nil
	}
	if s3Path == "" {
		return "", nil
	}

	normalized := strings.Trim(strings.TrimSpace(s3Path), "/")
	if normalized == "" {
		return "", errors.New("worker.s3.path must include bucket name")
	}
	parts := strings.SplitN(normalized, "/", 2)
	bucket := strings.TrimSpace(parts[0])
	if bucket == "" {
		return "", errors.New("worker.s3.path must include bucket name")
	}

	url := fmt.Sprintf("s3://%s", bucket)
	if len(parts) == 2 {
		prefix := strings.TrimSpace(parts[1])
		if prefix != "" {
			url = fmt.Sprintf("s3://%s/%s", bucket, prefix)
		}
	}
	if _, err := assets.ParseS3URL(url); err != nil {
		return "", fmt.Errorf("worker.s3.path is invalid: %w", err)
	}
	return url, nil
}
