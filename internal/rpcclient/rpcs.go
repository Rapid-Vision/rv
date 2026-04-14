// THIS CODE IS GENERATED

package rpcclient

import (
	"context"
	"encoding/json"
)

type StatusParams struct {
}
type StatusResult struct {
	Status StatusModel `json:"status"`
}

func (c *RPCClient) Status(ctx context.Context) (StatusModel, error) {
	var zero StatusModel
	var res StatusResult
	var payload any = nil
	if err := c.doRequest(ctx, "/rpc/status", payload, &res); err != nil {
		return zero, err
	}
	return res.Status, nil
}

type HealthParams struct {
}
type HealthResult struct {
	HealthStatus HealthStatusModel `json:"health_status"`
}

func (c *RPCClient) Health(ctx context.Context) (HealthStatusModel, error) {
	var zero HealthStatusModel
	var res HealthResult
	var payload any = nil
	if err := c.doRequest(ctx, "/rpc/health", payload, &res); err != nil {
		return zero, err
	}
	return res.HealthStatus, nil
}

type ListTasksParams struct {
	Statuses *[]string `json:"statuses"`
	Limit    *int      `json:"limit"`
	Offset   *int      `json:"offset"`
}
type ListTasksResult struct {
	Result []TaskModel `json:"result"`
}

func (c *RPCClient) ListTasks(ctx context.Context, params ListTasksParams) ([]TaskModel, error) {
	var zero []TaskModel
	var res ListTasksResult
	var payload any = params
	if err := c.doRequest(ctx, "/rpc/list_tasks", payload, &res); err != nil {
		return zero, err
	}
	return res.Result, nil
}

type ShowTaskParams struct {
	TaskId   *int    `json:"task_id"`
	TaskUuid *string `json:"task_uuid"`
}
type ShowTaskResult struct {
	Task TaskModel `json:"task"`
}

func (c *RPCClient) ShowTask(ctx context.Context, params ShowTaskParams) (TaskModel, error) {
	var zero TaskModel
	var res ShowTaskResult
	var payload any = params
	if err := c.doRequest(ctx, "/rpc/show_task", payload, &res); err != nil {
		return zero, err
	}
	return res.Task, nil
}

type ShowTaskHistoryParams struct {
	TaskId   *int    `json:"task_id"`
	TaskUuid *string `json:"task_uuid"`
	Limit    *int    `json:"limit"`
	Offset   *int    `json:"offset"`
}
type ShowTaskHistoryResult struct {
	Result []HistoryModel `json:"result"`
}

func (c *RPCClient) ShowTaskHistory(ctx context.Context, params ShowTaskHistoryParams) ([]HistoryModel, error) {
	var zero []HistoryModel
	var res ShowTaskHistoryResult
	var payload any = params
	if err := c.doRequest(ctx, "/rpc/show_task_history", payload, &res); err != nil {
		return zero, err
	}
	return res.Result, nil
}

type SubmitTaskParams struct {
	TaskName           string          `json:"task_name"`
	Payload            json.RawMessage `json:"payload"`
	MaxAttempts        *int            `json:"max_attempts"`
	BackoffBaseSeconds *int            `json:"backoff_base_seconds"`
}
type SubmitTaskResult struct {
	Task TaskModel `json:"task"`
}

func (c *RPCClient) SubmitTask(ctx context.Context, params SubmitTaskParams) (TaskModel, error) {
	var zero TaskModel
	var res SubmitTaskResult
	var payload any = params
	if err := c.doRequest(ctx, "/rpc/submit_task", payload, &res); err != nil {
		return zero, err
	}
	return res.Task, nil
}

type DeleteTaskParams struct {
	TaskId   *int    `json:"task_id"`
	TaskUuid *string `json:"task_uuid"`
}

func (c *RPCClient) DeleteTask(ctx context.Context, params DeleteTaskParams) error {
	var payload any = params
	if err := c.doRequest(ctx, "/rpc/delete_task", payload, nil); err != nil {
		return err
	}
	return nil
}

type UnclaimTaskParams struct {
	TaskId   *int    `json:"task_id"`
	TaskUuid *string `json:"task_uuid"`
}

func (c *RPCClient) UnclaimTask(ctx context.Context, params UnclaimTaskParams) error {
	var payload any = params
	if err := c.doRequest(ctx, "/rpc/unclaim_task", payload, nil); err != nil {
		return err
	}
	return nil
}

type DeclareWorkerParams struct {
	Name     string `json:"name"`
	TaskName string `json:"task_name"`
}
type DeclareWorkerResult struct {
	Worker WorkerModel `json:"worker"`
}

func (c *RPCClient) DeclareWorker(ctx context.Context, params DeclareWorkerParams) (WorkerModel, error) {
	var zero WorkerModel
	var res DeclareWorkerResult
	var payload any = params
	if err := c.doRequest(ctx, "/rpc/declare_worker", payload, &res); err != nil {
		return zero, err
	}
	return res.Worker, nil
}

type ListWorkersParams struct {
	Limit  *int `json:"limit"`
	Offset *int `json:"offset"`
}
type ListWorkersResult struct {
	Result []WorkerModel `json:"result"`
}

func (c *RPCClient) ListWorkers(ctx context.Context, params ListWorkersParams) ([]WorkerModel, error) {
	var zero []WorkerModel
	var res ListWorkersResult
	var payload any = params
	if err := c.doRequest(ctx, "/rpc/list_workers", payload, &res); err != nil {
		return zero, err
	}
	return res.Result, nil
}

type RequestTaskParams struct {
	WorkerId   *int    `json:"worker_id"`
	WorkerUuid *string `json:"worker_uuid"`
}
type RequestTaskResult struct {
	TaskDispatch TaskDispatchModel `json:"task_dispatch"`
}

func (c *RPCClient) RequestTask(ctx context.Context, params RequestTaskParams) (TaskDispatchModel, error) {
	var zero TaskDispatchModel
	var res RequestTaskResult
	var payload any = params
	if err := c.doRequest(ctx, "/rpc/request_task", payload, &res); err != nil {
		return zero, err
	}
	return res.TaskDispatch, nil
}

type SubmitResultParams struct {
	DispatchToken string          `json:"dispatch_token"`
	Status        string          `json:"status"`
	Result        json.RawMessage `json:"result"`
	WorkerId      *int            `json:"worker_id"`
	WorkerUuid    *string         `json:"worker_uuid"`
	TaskId        *int            `json:"task_id"`
	TaskUuid      *string         `json:"task_uuid"`
}
type SubmitResultResult struct {
	Task TaskModel `json:"task"`
}

func (c *RPCClient) SubmitResult(ctx context.Context, params SubmitResultParams) (TaskModel, error) {
	var zero TaskModel
	var res SubmitResultResult
	var payload any = params
	if err := c.doRequest(ctx, "/rpc/submit_result", payload, &res); err != nil {
		return zero, err
	}
	return res.Task, nil
}

type UpdateTaskTimeoutParams struct {
	DispatchToken string  `json:"dispatch_token"`
	MaxTimeout    int     `json:"max_timeout"`
	WorkerId      *int    `json:"worker_id"`
	WorkerUuid    *string `json:"worker_uuid"`
	TaskId        *int    `json:"task_id"`
	TaskUuid      *string `json:"task_uuid"`
}
type UpdateTaskTimeoutResult struct {
	Task TaskModel `json:"task"`
}

func (c *RPCClient) UpdateTaskTimeout(ctx context.Context, params UpdateTaskTimeoutParams) (TaskModel, error) {
	var zero TaskModel
	var res UpdateTaskTimeoutResult
	var payload any = params
	if err := c.doRequest(ctx, "/rpc/update_task_timeout", payload, &res); err != nil {
		return zero, err
	}
	return res.Task, nil
}

type UpdateTaskProgressParams struct {
	DispatchToken   string           `json:"dispatch_token"`
	Progress        int              `json:"progress"`
	ProgressMessage *string          `json:"progress_message"`
	ProgressPayload *json.RawMessage `json:"progress_payload"`
	WorkerId        *int             `json:"worker_id"`
	WorkerUuid      *string          `json:"worker_uuid"`
	TaskId          *int             `json:"task_id"`
	TaskUuid        *string          `json:"task_uuid"`
}
type UpdateTaskProgressResult struct {
	Task TaskModel `json:"task"`
}

func (c *RPCClient) UpdateTaskProgress(ctx context.Context, params UpdateTaskProgressParams) (TaskModel, error) {
	var zero TaskModel
	var res UpdateTaskProgressResult
	var payload any = params
	if err := c.doRequest(ctx, "/rpc/update_task_progress", payload, &res); err != nil {
		return zero, err
	}
	return res.Task, nil
}

type UpdateWorkerStatusParams struct {
	WorkerId   *int    `json:"worker_id"`
	WorkerUuid *string `json:"worker_uuid"`
	Status     *string `json:"status"`
}
type UpdateWorkerStatusResult struct {
	Worker WorkerModel `json:"worker"`
}

func (c *RPCClient) UpdateWorkerStatus(ctx context.Context, params UpdateWorkerStatusParams) (WorkerModel, error) {
	var zero WorkerModel
	var res UpdateWorkerStatusResult
	var payload any = params
	if err := c.doRequest(ctx, "/rpc/update_worker_status", payload, &res); err != nil {
		return zero, err
	}
	return res.Worker, nil
}

type StopWorkerParams struct {
	WorkerId   *int    `json:"worker_id"`
	WorkerUuid *string `json:"worker_uuid"`
}

func (c *RPCClient) StopWorker(ctx context.Context, params StopWorkerParams) error {
	var payload any = params
	if err := c.doRequest(ctx, "/rpc/stop_worker", payload, nil); err != nil {
		return err
	}
	return nil
}
