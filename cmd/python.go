package cmd

import (
	"github.com/Rapid-Vision/rv/internal/logs"
	rvpython "github.com/Rapid-Vision/rv/internal/python"
	"github.com/spf13/cobra"
)

var pythonCmd = &cobra.Command{
	Use:   "python",
	Short: "Manage Python editor integration",
}

var pythonInstallCmd = &cobra.Command{
	Use:   "install",
	Short: "Install the embedded rv Python package into the active virtual environment",
	Args:  cobra.NoArgs,
	Run:   runPythonInstall,
}

func init() {
	rootCmd.AddCommand(pythonCmd)
	pythonCmd.AddCommand(pythonInstallCmd)
}

func runPythonInstall(_ *cobra.Command, _ []string) {
	result, err := rvpython.Install(rvpython.InstallOptions{})
	if err != nil {
		logs.Err.Fatalln("Python install failed:", err)
	}

	logs.Info.Printf("Installed rv Python package to %s", result.InstalledPath)
}
