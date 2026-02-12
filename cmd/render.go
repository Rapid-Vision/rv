package cmd

import (
	"github.com/Rapid-Vision/rv/internal/logs"
	"github.com/Rapid-Vision/rv/internal/render"
	"github.com/Rapid-Vision/rv/internal/utils"
	"github.com/spf13/cobra"
)

var (
	renderImageNum  int
	renderProcs     int
	renderOutputDir string
	renderCwd       string
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
	renderCmd.Flags().StringVar(&renderCwd, "cwd", "", "Working directory for resolving relative paths (defaults to script directory)")
}

func runRender(_ *cobra.Command, args []string) {
	paths, err := utils.ResolveRenderPaths(args[0], renderOutputDir, renderCwd)
	if err != nil {
		logs.Err.Fatalln("Failed to resolve paths:", err)
	}

	if _, err := render.Render(render.RenderOptions{
		ScriptPath: paths.ScriptPath,
		Cwd:        paths.Cwd,
		ImageNum:   renderImageNum,
		Procs:      renderProcs,
		OutputDir:  paths.OutputDir,
	}); err != nil {
		logs.Err.Fatalln("Render failed:", err)
	}
}
