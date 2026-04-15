package cmd

import (
	"errors"
	"path/filepath"

	"github.com/Rapid-Vision/rv/internal/logs"
	"github.com/Rapid-Vision/rv/internal/preview"
	"github.com/Rapid-Vision/rv/internal/seed"
	"github.com/Rapid-Vision/rv/internal/utils"
	"github.com/spf13/cobra"
)

var (
	previewCwd        string
	previewGenDir     string
	previewGenRetain  string
	previewFiles      bool
	previewOut        string
	previewNoWindow   bool
	previewRes        string
	previewGPUBackend string
	previewTimeLimit  float64
	previewSeed       string
)

var previewCmd = &cobra.Command{
	Use:   "preview <script.py>",
	Short: "Run live preview",
	Long:  `Run live scene preview with hot reload. Optionally save preview images to disk and run without opening a Blender window.`,
	Args:  cobra.ExactArgs(1),
	Run:   runPreview,
}

func init() {
	rootCmd.AddCommand(previewCmd)
	previewCmd.Flags().StringVar(&previewCwd, "cwd", "", "Working directory for resolving relative paths (defaults to script directory)")
	previewCmd.Flags().StringVar(&previewGenDir, "gen-dir", "", "Generator base directory (defaults to <root_dir>/generated; relative paths resolve from root_dir)")
	previewCmd.Flags().StringVar(&previewGenRetain, "gen-retain", string(utils.GeneratorRetainLast), "Generator work-dir retention: all, last, none")
	previewCmd.Flags().BoolVar(&previewFiles, "preview-files", false, "Save a single preview sample to files on each script change")
	previewCmd.Flags().StringVar(&previewOut, "preview-out", "./preview_out", "Output directory for preview files")
	previewCmd.Flags().BoolVar(&previewNoWindow, "no-window", false, "Run preview without opening Blender window (requires --preview-files)")
	previewCmd.Flags().StringVar(&previewRes, "resolution", "640,640", "Output image resolution in WIDTH,HEIGHT format (for --preview-files)")
	previewCmd.Flags().StringVar(&previewGPUBackend, "gpu-backend", "auto", "Cycles render device backend: auto, optix, cuda, hip, oneapi, metal, cpu")
	previewCmd.Flags().Float64Var(&previewTimeLimit, "time-limit", 0, "Cycles rendering time limit in seconds (for --preview-files)")
	previewCmd.Flags().StringVar(&previewSeed, "seed", string(seed.RandomMode), "Scene seed mode: rand, seq, or a concrete integer")
}

func runPreview(cmd *cobra.Command, args []string) {
	if err := validatePreviewFlags(
		previewNoWindow,
		previewFiles,
		cmd.Flags().Changed("resolution"),
		cmd.Flags().Changed("time-limit"),
	); err != nil {
		logs.Err.Fatalln(err)
	}

	previewOutAbs, err := resolvePreviewOutputDir(previewFiles, previewOut)
	if err != nil {
		logs.Err.Fatalln("Failed to resolve --preview-out path:", err)
	}
	resolution, err := parseResolutionFlag(previewRes)
	if err != nil {
		logs.Err.Fatalln("Invalid --resolution:", err)
	}
	seedCfg, err := parseSeedFlag(previewSeed)
	if err != nil {
		logs.Err.Fatalln("Invalid --seed:", err)
	}
	genRetain, err := utils.ParseGeneratorRetention(previewGenRetain)
	if err != nil {
		logs.Err.Fatalln(err)
	}
	var timeLimit *float64
	if cmd.Flags().Changed("time-limit") {
		timeLimit = &previewTimeLimit
	}

	preview.Preview(preview.Options{
		ScriptPathArg: args[0],
		CwdArg:        previewCwd,
		GenDirArg:     previewGenDir,
		GenRetain:     genRetain,
		PreviewFiles:  previewFiles,
		PreviewOut:    previewOutAbs,
		NoWindow:      previewNoWindow,
		Resolution:    resolution,
		GPUBackend:    previewGPUBackend,
		TimeLimit:     timeLimit,
		Seed:          seedCfg,
	})
}

func validatePreviewFlags(noWindow bool, files bool, resolutionChanged bool, timeLimitChanged bool) error {
	if noWindow && !files {
		return errors.New("--no-window requires --preview-files")
	}
	if resolutionChanged && !files {
		return errors.New("--resolution requires --preview-files")
	}
	if timeLimitChanged && !files {
		return errors.New("--time-limit requires --preview-files")
	}
	return nil
}

func resolvePreviewOutputDir(files bool, out string) (string, error) {
	if !files {
		return "", nil
	}
	absPath, err := filepath.Abs(out)
	if err != nil {
		return "", err
	}
	return filepath.Clean(absPath), nil
}
