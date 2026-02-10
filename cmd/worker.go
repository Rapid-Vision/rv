package cmd

import (
	"context"
	"encoding/json"
	"errors"
	"os"
	"os/signal"
	"syscall"
	"time"

	"github.com/Rapid-Vision/rv/cmd/internal/logs"
	"github.com/Rapid-Vision/rv/cmd/internal/render"
	"github.com/Rapid-Vision/rv/cmd/internal/rpcclient"
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
}

type workerTaskPayload struct {
	Script string `json:"script"`
	Number int    `json:"number"`
	Procs  int    `json:"procs"`
	Output string `json:"output"`
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

	logs.Info.Printf("Running task %d: script=%s number=%d procs=%d output=%s\n", task.Id, payload.Script, payload.Number, payload.Procs, payload.Output)

	if err := render.Render(payload.Script, payload.Number, payload.Procs, payload.Output); err != nil {
		submitTaskResult(ctx, client, workerId, task.Id, dispatchToken, "failed", map[string]any{"error": err.Error()})
		return err
	}

	submitTaskResult(ctx, client, workerId, task.Id, dispatchToken, "success", map[string]any{"ok": true})
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
	if payload.Output == "" {
		payload.Output = "./out"
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
