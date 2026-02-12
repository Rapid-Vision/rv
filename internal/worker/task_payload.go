package worker

type WorkerTaskPayload struct {
	Script                string               `json:"script"`
	Number                int                  `json:"number"`
	Resolution            []int                `json:"resolution"`
	TimeLimit             *float64             `json:"time_limit"`
	MaxSamples            *int                 `json:"max_samples"`
	MinSamples            *int                 `json:"min_samples"`
	NoiseThresholdEnabled *bool                `json:"noise_threshold_enabled"`
	NoiseThreshold        *float64             `json:"noise_threshold"`
	AssetMappings         []WorkerAssetMapping `json:"asset_mappings"`
}

type WorkerAssetMapping struct {
	Source      string `json:"source"`
	Destination string `json:"destination"`
}
