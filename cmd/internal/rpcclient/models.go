// THIS CODE IS GENERATED

package rpcclient

import "encoding/json"

type TaskModel struct {
	Id                 int              `json:"id"`
	TaskName           string           `json:"task_name"`
	Payload            *json.RawMessage `json:"payload"`
	Status             string           `json:"status"`
	WorkerId           *int             `json:"worker_id"`
	Result             *json.RawMessage `json:"result"`
	RetryCount         int              `json:"retry_count"`
	MaxAttempts        *int             `json:"max_attempts"`
	BackoffBaseSeconds *int             `json:"backoff_base_seconds"`
	MaxTimeout         *int             `json:"max_timeout"`
	TimeoutSetAt       *string          `json:"timeout_set_at"`
	Progress           *int             `json:"progress"`
	ProgressMessage    *string          `json:"progress_message"`
	ProgressPayload    *json.RawMessage `json:"progress_payload"`
	AvailableAt        *string          `json:"available_at"`
	CreatedAt          string           `json:"created_at"`
	UpdatedAt          string           `json:"updated_at"`
}
type TasksStatusModel struct {
	Total     int `json:"total"`
	Pending   int `json:"pending"`
	Deleted   int `json:"deleted"`
	Completed int `json:"completed"`
	Claimed   int `json:"claimed"`
	Failed    int `json:"failed"`
	Rejected  int `json:"rejected"`
}
type HealthStatusModel struct {
	Db string `json:"db"`
}
type StatusModel struct {
	Tasks  TasksStatusModel  `json:"tasks"`
	Health HealthStatusModel `json:"health"`
}
type WorkerModel struct {
	Id        int    `json:"id"`
	Name      string `json:"name"`
	TaskName  string `json:"task_name"`
	Status    string `json:"status"`
	CreatedAt string `json:"created_at"`
	LastSeen  string `json:"last_seen"`
}
type HistoryModel struct {
	Id         int    `json:"id"`
	EntityType string `json:"entity_type"`
	EntityId   int    `json:"entity_id"`
	EventType  string `json:"event_type"`
	Data       string `json:"data"`
	CreatedAt  string `json:"created_at"`
}
type TaskDispatchModel struct {
	Task          *TaskModel `json:"task"`
	DispatchToken *string    `json:"dispatch_token"`
}
