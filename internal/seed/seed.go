package seed

import (
	"fmt"
	"strconv"
	"strings"
)

type Mode string

const (
	RandomMode Mode = "rand"
	SeqMode    Mode = "seq"
	FixedMode  Mode = "fixed"
)

type Config struct {
	Mode  Mode
	Value int64
}

func Default() Config {
	return Config{Mode: RandomMode}
}

func Normalize(cfg Config) Config {
	if cfg.Mode == "" {
		return Default()
	}
	return cfg
}

func Parse(raw string) (Config, error) {
	value := strings.TrimSpace(raw)
	if value == "" {
		return Config{}, fmt.Errorf("--seed must be random, seq, or an integer")
	}

	if strings.HasPrefix(strings.ToLower(value), string(RandomMode)) {
		return Config{Mode: RandomMode}, nil
	}

	if strings.HasPrefix(strings.ToLower(value), string(SeqMode)) {
		return Config{Mode: SeqMode}, nil
	}

	seedValue, err := strconv.ParseInt(value, 10, 64)
	if err != nil {
		return Config{}, fmt.Errorf("--seed must be random, seq, or an integer")
	}

	return Config{
		Mode:  FixedMode,
		Value: seedValue,
	}, nil
}
