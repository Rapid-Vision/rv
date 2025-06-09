package cmd

import (
	"github.com/Rapid-Vision/rv/cmd/internal/preview"
	"github.com/spf13/cobra"
)

var previewCmd = &cobra.Command{
	Use:   "preview <script.py>",
	Short: "Run live preview",
	Long:  `Open a separate blender window which updates preview on each script file change.`,
	Args:  cobra.ExactArgs(1),
	Run: func(cmd *cobra.Command, args []string) {
		preview.Preview(args[0])
	},
}

func init() {
	rootCmd.AddCommand(previewCmd)
}
