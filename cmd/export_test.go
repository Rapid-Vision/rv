package cmd

import "testing"

func TestExportOutputFlagIsRequired(t *testing.T) {
	err := exportCmd.Args(exportCmd, []string{"scene.py"})
	if err != nil {
		t.Fatalf("unexpected args error: %v", err)
	}

	outputFlag := exportCmd.Flags().Lookup("output")
	if outputFlag == nil {
		t.Fatal("expected output flag to exist")
	}
	if outputFlag.DefValue != "" {
		t.Fatalf("expected empty default output value, got %q", outputFlag.DefValue)
	}
}

func TestExportGenRetainDefault(t *testing.T) {
	genRetainFlag := exportCmd.Flags().Lookup("gen-retain")
	if genRetainFlag == nil {
		t.Fatal("expected gen-retain flag to exist")
	}
	if genRetainFlag.DefValue != "all" {
		t.Fatalf("expected default gen-retain=all, got %q", genRetainFlag.DefValue)
	}
}
