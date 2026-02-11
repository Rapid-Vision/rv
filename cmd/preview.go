package cmd

import (
	"github.com/Rapid-Vision/rv/internal/preview"
	"github.com/spf13/cobra"
)

var previewCwd string

var previewCmd = &cobra.Command{
	Use:   "preview <script.py>",
	Short: "Run live preview",
	Long:  `Open a separate blender window which updates preview on each script file change.`,
	Args:  cobra.ExactArgs(1),
	Run:   runPreview,
}

func init() {
	rootCmd.AddCommand(previewCmd)
	previewCmd.Flags().StringVar(&previewCwd, "cwd", "", "Working directory for resolving relative paths (defaults to script directory)")
}

func runPreview(cmd *cobra.Command, args []string) {
	preview.Preview(args[0], previewCwd)
}
