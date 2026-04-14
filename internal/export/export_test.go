package export

import (
	"path/filepath"
	"testing"

	"github.com/Rapid-Vision/rv/internal/seed"
)

func TestBuildBlenderExportArgs(t *testing.T) {
	opts := Options{
		ScriptPath:    "/work/scene.py",
		Cwd:           "/work",
		OutputPath:    "/tmp/out/scene.blend",
		FreezePhysics: true,
		PackResources: true,
		Seed:          seed.Config{Mode: seed.FixedMode, Value: 23},
		GeneratorPort: 8444,
	}

	args := buildBlenderExportArgs(opts, "/lib/rvlib")

	assertContains(t, args, filepath.Join("/lib/rvlib", "template.blend"))
	assertContains(t, args, "--python")
	assertContains(t, args, filepath.Join("/lib/rvlib", "export.py"))
	assertContains(t, args, "--script")
	assertContains(t, args, "/work/scene.py")
	assertContains(t, args, "--cwd")
	assertContains(t, args, "/work")
	assertContains(t, args, "--output")
	assertContains(t, args, "/tmp/out/scene.blend")
	assertContains(t, args, "--seed-mode")
	assertContains(t, args, "fixed")
	assertContains(t, args, "--seed-value")
	assertContains(t, args, "23")
	assertContains(t, args, "--generator-port")
	assertContains(t, args, "8444")
	assertContains(t, args, "--freeze-physics")
	assertContains(t, args, "--pack-resources")
}

func assertContains(t *testing.T, values []string, needle string) {
	t.Helper()
	for _, value := range values {
		if value == needle {
			return
		}
	}
	t.Fatalf("expected %q in %v", needle, values)
}
