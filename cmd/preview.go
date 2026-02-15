package cmd

import (
	"errors"
	"path/filepath"

	"github.com/Rapid-Vision/rv/internal/logs"
	"github.com/Rapid-Vision/rv/internal/preview"
	"github.com/spf13/cobra"
)

var (
	previewCwd       string
	previewFiles     bool
	previewOut       string
	previewNoWindow  bool
	previewRes       string
	previewTimeLimit float64
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
	previewCmd.Flags().BoolVar(&previewFiles, "preview-files", false, "Save a single preview sample to files on each script change")
	previewCmd.Flags().StringVar(&previewOut, "preview-out", "./preview_out", "Output directory for preview files")
	previewCmd.Flags().BoolVar(&previewNoWindow, "no-window", false, "Run preview without opening Blender window (requires --preview-files)")
	previewCmd.Flags().StringVar(&previewRes, "resolution", "640,640", "Output image resolution in WIDTH,HEIGHT format (for --preview-files)")
	previewCmd.Flags().Float64Var(&previewTimeLimit, "time-limit", 0, "Cycles rendering time limit in seconds (for --preview-files)")
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
	var timeLimit *float64
	if cmd.Flags().Changed("time-limit") {
		timeLimit = &previewTimeLimit
	}

	preview.Preview(preview.Options{
		ScriptPathArg: args[0],
		CwdArg:        previewCwd,
		PreviewFiles:  previewFiles,
		PreviewOut:    previewOutAbs,
		NoWindow:      previewNoWindow,
		Resolution:    resolution,
		TimeLimit:     timeLimit,
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
