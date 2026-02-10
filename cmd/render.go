package cmd

import (
	"path/filepath"

	"github.com/Rapid-Vision/rv/internal/logs"
	"github.com/Rapid-Vision/rv/internal/render"
	"github.com/spf13/cobra"
)

var (
	renderImageNum  int
	renderProcs     int
	renderOutputDir string
)

var renderCmd = &cobra.Command{
	Use:   "render <script.py>",
	Short: "Render final dataset",
	Long:  `Run generation script in several instances of blender and save resulting dataset.`,
	Args:  cobra.ExactArgs(1),
	Run:   runRender,
}

func init() {
	rootCmd.AddCommand(renderCmd)

	renderCmd.Flags().IntVarP(&renderImageNum, "number", "n", 1, "Number of total images generated")
	renderCmd.Flags().IntVarP(&renderProcs, "procs", "p", 1, "Maximum number of spawned Blender processes")
	renderCmd.Flags().StringVarP(&renderOutputDir, "output", "o", "./out", "Output directory")
}

func runRender(_ *cobra.Command, args []string) {
	scriptPath := args[0]
	outputDirAbs, err := filepath.Abs(renderOutputDir)
	if err != nil {
		logs.Err.Fatalln("Failed to parse output path:", err)
	}

	if err := render.Render(scriptPath, renderImageNum, renderProcs, outputDirAbs); err != nil {
		logs.Err.Fatalln("Render failed:", err)
	}
}
