package cmd

import (
	"log"
	"path/filepath"

	"github.com/Rapid-Vision/rv/cmd/internal/render"
	"github.com/spf13/cobra"
)

var renderCmd = &cobra.Command{
	Use:   "render <script.py>",
	Short: "Render final dataset",
	Long:  `Run generation script in several instances of blender and save resulting dataset.`,
	Args:  cobra.ExactArgs(1),
	Run: func(cmd *cobra.Command, args []string) {
		scriptPath, err := filepath.Abs(args[0])
		if err != nil {
			log.Fatalf("Failed to parse script path: %v", err)
		}

		imageNum, _ := cmd.Flags().GetInt("number")
		procs, _ := cmd.Flags().GetInt("procs")

		outputDir, _ := cmd.Flags().GetString("output")
		outputDirAbs, err := filepath.Abs(outputDir)
		if err != nil {
			log.Fatalf("Failed to parse output path: %v", err)
		}

		render.Render(scriptPath, imageNum, procs, outputDirAbs)
	},
}

func init() {
	rootCmd.AddCommand(renderCmd)

	renderCmd.Flags().IntP("number", "n", 1000, "Number of total images generated")
	renderCmd.Flags().IntP("procs", "p", 1, "Maximum number of spawned Blender processes")
	renderCmd.Flags().StringP("output", "o", "./out", "Output directory")
}
