package render

import (
	"testing"

	"github.com/Rapid-Vision/rv/internal/seed"
)

func TestBuildBlenderRenderArgs_SeedFlags(t *testing.T) {
	opts := RenderOptions{
		ScriptPath:    "/work/scene.py",
		Cwd:           "/work",
		WorkDir:       "/work/generated/run-1",
		ImageNum:      4,
		Procs:         2,
		Resolution:    [2]int{640, 480},
		OutputDir:     "/tmp/out",
		GPUBackend:    "cuda",
		Seed:          seed.Config{Mode: seed.FixedMode, Value: 123},
		GeneratorPort: 9090,
	}

	args := buildBlenderRenderArgs(opts, "/lib/rvlib", "/tmp/out/1", 2, 5)

	assertContains(t, args, "--seed-mode")
	assertContains(t, args, "fixed")
	assertContains(t, args, "--seed-value")
	assertContains(t, args, "123")
	assertContains(t, args, "--seed-base")
	assertContains(t, args, "5")
	assertContains(t, args, "--generator-port")
	assertContains(t, args, "9090")
	assertContains(t, args, "--root-dir")
	assertContains(t, args, "--work-dir")
	assertContains(t, args, "/work/generated/run-1")
}

func TestRenderSeedBase(t *testing.T) {
	got := []int{
		renderSeedBase(10, 3, 0),
		renderSeedBase(10, 3, 1),
		renderSeedBase(10, 3, 2),
	}
	want := []int{0, 4, 7}
	for i := range want {
		if got[i] != want[i] {
			t.Fatalf("got = %v, want = %v", got, want)
		}
	}
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
