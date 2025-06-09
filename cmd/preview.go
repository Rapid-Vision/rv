package cmd

import (
	"log"
	"path/filepath"

	"github.com/Rapid-Vision/rv/cmd/internal/preview"
	"github.com/spf13/cobra"
)

var previewCmd = &cobra.Command{
	Use:   "preview <script.py>",
	Short: "Run live preview",
	Long:  `Open a separate blender window which updates preview on each script file change.`,
	Args:  cobra.ExactArgs(1),
	Run: func(cmd *cobra.Command, args []string) {
		scriptPath, err := filepath.Abs(args[0])
		if err != nil {
			log.Fatalf("Failed to get absolute path: %v", err)
		}

		preview.Preview(scriptPath)
	},
}

func init() {
	rootCmd.AddCommand(previewCmd)
}
