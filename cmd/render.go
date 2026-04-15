package cmd

import (
	"fmt"
	"strconv"
	"strings"

	"github.com/Rapid-Vision/rv/internal/logs"
	"github.com/Rapid-Vision/rv/internal/render"
	"github.com/Rapid-Vision/rv/internal/seed"
	"github.com/Rapid-Vision/rv/internal/utils"
	"github.com/spf13/cobra"
)

var (
	renderImageNum              int
	renderProcs                 int
	renderResolution            string
	renderOutputDir             string
	renderCwd                   string
	renderGenDir                string
	renderGPUBackend            string
	renderTimeLimit             float64
	renderMaxSamples            int
	renderMinSamples            int
	renderNoiseThresholdEnabled bool
	renderNoiseThreshold        float64
	renderSeed                  string
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
	renderCmd.Flags().StringVar(&renderResolution, "resolution", "640,640", "Output image resolution in WIDTH,HEIGHT format")
	renderCmd.Flags().StringVar(&renderGPUBackend, "gpu-backend", "auto", "Cycles render device backend: auto, optix, cuda, hip, oneapi, metal, cpu")
	renderCmd.Flags().Float64Var(&renderTimeLimit, "time-limit", 0, "Cycles rendering time limit in seconds")
	renderCmd.Flags().IntVar(&renderMaxSamples, "max-samples", 0, "Cycles maximum render samples")
	renderCmd.Flags().IntVar(&renderMinSamples, "min-samples", 0, "Cycles minimum adaptive render samples")
	renderCmd.Flags().BoolVar(&renderNoiseThresholdEnabled, "noise-threshold-enabled", false, "Enable Cycles adaptive noise threshold")
	renderCmd.Flags().Float64Var(&renderNoiseThreshold, "noise-threshold", 0, "Cycles adaptive noise threshold value")
	renderCmd.Flags().StringVarP(&renderOutputDir, "output", "o", "./out", "Output directory")
	renderCmd.Flags().StringVar(&renderCwd, "cwd", "", "Working directory for resolving relative paths (defaults to script directory)")
	renderCmd.Flags().StringVar(&renderGenDir, "gen-dir", "", "Generator base directory (defaults to <root_dir>/generated; relative paths resolve from root_dir)")
	renderCmd.Flags().StringVar(&renderSeed, "seed", string(seed.RandomMode), "Scene seed mode: rand, seq, or a concrete integer")
}

func runRender(cmd *cobra.Command, args []string) {
	paths, err := utils.ResolveRenderPaths(args[0], renderOutputDir, renderCwd)
	if err != nil {
		logs.Err.Fatalln("Failed to resolve paths:", err)
	}

	resolution, err := parseResolutionFlag(renderResolution)
	if err != nil {
		logs.Err.Fatalln("Invalid --resolution:", err)
	}
	seedCfg, err := parseSeedFlag(renderSeed)
	if err != nil {
		logs.Err.Fatalln("Invalid --seed:", err)
	}

	opts := render.RenderOptions{
		ScriptPath: paths.ScriptPath,
		Cwd:        paths.Cwd,
		ImageNum:   renderImageNum,
		Procs:      renderProcs,
		Resolution: resolution,
		OutputDir:  paths.OutputDir,
		GPUBackend: renderGPUBackend,
		Seed:       seedCfg,
	}
	generatorPaths, err := utils.ResolveGeneratorPaths(paths.Cwd, renderGenDir)
	if err != nil {
		logs.Err.Fatalln("Failed to resolve generator paths:", err)
	}
	opts.GenBaseDir = generatorPaths.GenBaseDir
	applyOptionalRenderFlags(cmd, &opts)

	if _, err := render.Render(opts); err != nil {
		logs.Err.Fatalln("Render failed:", err)
	}
}

func applyOptionalRenderFlags(cmd *cobra.Command, opts *render.RenderOptions) {
	if cmd.Flags().Changed("time-limit") {
		opts.TimeLimit = &renderTimeLimit
	}
	if cmd.Flags().Changed("max-samples") {
		opts.MaxSamples = &renderMaxSamples
	}
	if cmd.Flags().Changed("min-samples") {
		opts.MinSamples = &renderMinSamples
	}
	if cmd.Flags().Changed("noise-threshold-enabled") {
		opts.NoiseThresholdEnabled = &renderNoiseThresholdEnabled
	}
	if cmd.Flags().Changed("noise-threshold") {
		opts.NoiseThreshold = &renderNoiseThreshold
	}
}

func parseResolutionFlag(raw string) ([2]int, error) {
	parts := strings.Split(strings.TrimSpace(raw), ",")
	if len(parts) != 2 {
		return [2]int{}, fmt.Errorf("expected WIDTH,HEIGHT")
	}

	width, err := strconv.Atoi(strings.TrimSpace(parts[0]))
	if err != nil {
		return [2]int{}, fmt.Errorf("invalid width: %w", err)
	}
	height, err := strconv.Atoi(strings.TrimSpace(parts[1]))
	if err != nil {
		return [2]int{}, fmt.Errorf("invalid height: %w", err)
	}
	if width <= 0 || height <= 0 {
		return [2]int{}, fmt.Errorf("width and height must be > 0")
	}

	return [2]int{width, height}, nil
}
