/*
Copyright © 2025-2026 Mikhail Pankin mishapankin@gmail.com, RAPID VISION LLC
*/
package main

import (
	"log"

	"github.com/Rapid-Vision/rv/cmd"
	"github.com/joho/godotenv"
)

func init() {
	_ = godotenv.Load()
	log.SetFlags(0)
}

func main() {
	cmd.Execute()
}
