package cmd

import "github.com/Rapid-Vision/rv/internal/seed"

func parseSeedFlag(raw string) (seed.Config, error) {
	return seed.Parse(raw)
}
