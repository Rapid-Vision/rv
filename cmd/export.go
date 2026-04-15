package cmd

import (
	"github.com/Rapid-Vision/rv/internal/export"
	"github.com/Rapid-Vision/rv/internal/logs"
	"github.com/Rapid-Vision/rv/internal/seed"
	"github.com/Rapid-Vision/rv/internal/utils"
	"github.com/spf13/cobra"
)

var (
	exportOutputPath    string
	exportCwd           string
	exportGenDir        string
	exportGenRetain     string
	exportFreezePhysics bool
	exportPackResources bool
	exportSeed          string
)

var exportCmd = &cobra.Command{
	Use:   "export <script.py>",
	Short: "Export a realized scene to a .blend file",
	Long:  `Run the scene script once in headless Blender and save the resulting scene as a .blend file.`,
	Args:  cobra.ExactArgs(1),
	Run:   runExport,
}

func init() {
	rootCmd.AddCommand(exportCmd)

	exportCmd.Flags().StringVarP(&exportOutputPath, "output", "o", "", "Output .blend file path")
	exportCmd.Flags().StringVar(&exportCwd, "cwd", "", "Working directory for resolving relative paths (defaults to script directory)")
	exportCmd.Flags().StringVar(&exportGenDir, "gen-dir", "", "Generator base directory (defaults to <root_dir>/generated; relative paths resolve from root_dir)")
	exportCmd.Flags().StringVar(&exportGenRetain, "gen-retain", string(utils.GeneratorRetainAll), "Generator work-dir retention: all, last, none")
	exportCmd.Flags().BoolVar(&exportFreezePhysics, "freeze-physics", false, "Simulate rigid-body physics to the end state and remove rigid-body simulation before saving")
	exportCmd.Flags().BoolVar(&exportPackResources, "pack-resources", false, "Pack external resources into the saved .blend file")
	exportCmd.Flags().StringVar(&exportSeed, "seed", string(seed.RandomMode), "Scene seed mode: rand, seq, or a concrete integer")
	_ = exportCmd.MarkFlagRequired("output")
}

func runExport(_ *cobra.Command, args []string) {
	paths, err := utils.ResolveExportPaths(args[0], exportOutputPath, exportCwd)
	if err != nil {
		logs.Err.Fatalln("Failed to resolve paths:", err)
	}
	seedCfg, err := parseSeedFlag(exportSeed)
	if err != nil {
		logs.Err.Fatalln("Invalid --seed:", err)
	}
	generatorPaths, err := utils.ResolveGeneratorPaths(paths.Cwd, exportGenDir)
	if err != nil {
		logs.Err.Fatalln("Failed to resolve generator paths:", err)
	}
	genRetain, err := utils.ParseGeneratorRetention(exportGenRetain)
	if err != nil {
		logs.Err.Fatalln(err)
	}

	if err := export.Export(export.Options{
		ScriptPath:    paths.ScriptPath,
		Cwd:           paths.Cwd,
		GenBaseDir:    generatorPaths.GenBaseDir,
		GenRetain:     genRetain,
		OutputPath:    paths.OutputPath,
		FreezePhysics: exportFreezePhysics,
		PackResources: exportPackResources,
		Seed:          seedCfg,
	}); err != nil {
		logs.Err.Fatalln("Export failed:", err)
	}
}
