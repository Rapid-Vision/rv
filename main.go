/*
Copyright © 2025 NAME HERE <EMAIL ADDRESS>
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
