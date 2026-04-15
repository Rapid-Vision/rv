package utils

import (
	"errors"
	"fmt"
	"net"
	"os"
	"os/exec"
	"path"
	"path/filepath"
	"runtime"
	"strconv"
	"strings"

	"github.com/Rapid-Vision/rv/rvlib"
	"github.com/google/uuid"
)

var blenderEnvBlockedKeys = map[string]struct{}{
	"PYTHONHOME":          {},
	"PYTHONPATH":          {},
	"PYTHONSTARTUP":       {},
	"PYTHONUSERBASE":      {},
	"VIRTUAL_ENV":         {},
	"__PYVENV_LAUNCHER__": {},
}

// get an available port
func GetPort() (int, error) {
	l, err := net.Listen("tcp", "127.0.0.1:0")
	if err != nil {
		return 0, err
	}
	defer func() { _ = l.Close() }()
	return l.(*net.TCPListener).Addr().(*net.TCPAddr).Port, nil
}

// try several locations to find a Blender executable.
func GetBlenderPath() (string, error) {
	// 1. BLENDER_PATH env var
	if p := os.Getenv("BLENDER_PATH"); p != "" {
		if _, err := os.Stat(p); err == nil {
			return p, nil
		}
	}

	// 2. LookPath
	if p, err := exec.LookPath("blender"); err == nil {
		return p, nil
	}

	// 3. Platform-specific fallbacks
	switch runtime.GOOS {
	case "darwin":
		p := "/Applications/Blender.app/Contents/MacOS/Blender"
		if _, err := os.Stat(p); err == nil {
			return p, nil
		}
	case "windows":
		p := `C:\Program Files\Blender Foundation\Blender\blender.exe`
		if _, err := os.Stat(p); err == nil {
			return p, nil
		}
	}

	return "", errors.New("blender executable not found")
}

// try several locations to find a rvlib
func GetLibPath() (string, error) {
	// 1. RVLIB_PATH env var
	if p := os.Getenv("RVLIB_PATH"); p != "" {
		return p, nil
	}

	// 2. Check if local rvlib directory exists
	localPath := "./rvlib/rvlib/"
	if _, err := os.Stat(localPath); err == nil {
		absPath, err := filepath.Abs(localPath)
		if err == nil {
			return absPath, nil
		}
	}

	// 3. Unpack embedded rvlib into .cache/rvlib

	cacheDir, err := os.UserCacheDir()
	if err != nil {
		return "", err
	}

	absPath, err := filepath.Abs(filepath.Join(cacheDir, "rvlib"))
	if err != nil {
		return "", err
	}

	err = rvlib.UnpackRVLib(absPath)
	if err != nil {
		return "", err
	}

	return absPath, nil
}

// generate a sequential output directory name based on the contents
// of the specified `output_dir`. If the directory doesn't exist, create it.
func GetSequentialOutputDir(output_dir string) (string, error) {
	if _, err := os.Stat(output_dir); os.IsNotExist(err) {
		err = os.MkdirAll(output_dir, os.ModePerm)
		if err != nil {
			return "", err
		}
	}

	files, err := os.ReadDir(output_dir)
	if err != nil {
		return "", err
	}

	var maxVal int64 = 0

	for _, file := range files {
		i, err := strconv.ParseInt(file.Name(), 10, 64)
		if err == nil && i > maxVal {
			maxVal = i
		}
	}

	return path.Join(output_dir, fmt.Sprint(maxVal+1)), nil
}

// wait for command to quit and notify through channel
func WaitCmd(c *exec.Cmd) <-chan error {
	ch := make(chan error, 1)
	go func() { ch <- c.Wait() }()
	return ch
}

// wait for command to quit and notify through channel
func WaitCmdBuff(buff []*exec.Cmd) <-chan error {
	n := len(buff)
	ch := make(chan error, n)
	for i := 0; i < n; i += 1 {
		cmd := buff[i]
		go func(c *exec.Cmd) { ch <- c.Wait() }(cmd)
	}
	return ch
}

func BlenderCommandEnv() []string {
	env := os.Environ()
	virtualEnv := filepath.Clean(os.Getenv("VIRTUAL_ENV"))
	venvBinDir := ""
	if virtualEnv != "" && virtualEnv != "." {
		venvBinDir = filepath.Join(virtualEnv, "bin")
		if runtime.GOOS == "windows" {
			venvBinDir = filepath.Join(virtualEnv, "Scripts")
		}
	}

	sanitized := make([]string, 0, len(env))
	for _, entry := range env {
		key, value, found := strings.Cut(entry, "=")
		if !found {
			continue
		}
		if _, blocked := blenderEnvBlockedKeys[key]; blocked {
			continue
		}
		if key == "PATH" && venvBinDir != "" {
			value = removePathEntry(value, venvBinDir)
		}
		sanitized = append(sanitized, key+"="+value)
	}

	return sanitized
}

func removePathEntry(rawPath string, target string) string {
	if rawPath == "" || target == "" {
		return rawPath
	}

	target = filepath.Clean(target)
	parts := filepath.SplitList(rawPath)
	filtered := make([]string, 0, len(parts))
	for _, part := range parts {
		if filepath.Clean(part) == target {
			continue
		}
		filtered = append(filtered, part)
	}
	return strings.Join(filtered, string(os.PathListSeparator))
}

func SplitTaskBetweenProcs(n int, p int, i int) int {
	if n <= 0 || i < 0 || i >= p {
		return 0
	}

	res := n / p
	if i < n%p {
		res += 1
	}

	return res
}

type RuntimePaths struct {
	ScriptPath string
	Cwd        string
}

type RenderPaths struct {
	ScriptPath string
	Cwd        string
	OutputDir  string
}

type ExportPaths struct {
	ScriptPath string
	Cwd        string
	OutputPath string
}

type GeneratorPaths struct {
	RootDir    string
	GenBaseDir string
}

type GeneratorRetention string

const (
	GeneratorRetainAll     GeneratorRetention = "all"
	GeneratorRetainLast    GeneratorRetention = "last"
	GeneratorRetainNone    GeneratorRetention = "none"
	generatorWorkDirPrefix                    = "_rv_"
)

func ParseGeneratorRetention(raw string) (GeneratorRetention, error) {
	value := GeneratorRetention(strings.ToLower(strings.TrimSpace(raw)))
	switch value {
	case GeneratorRetainAll, GeneratorRetainLast, GeneratorRetainNone:
		return value, nil
	default:
		return "", fmt.Errorf("invalid --gen-retain value %q: must be one of all, last, none", raw)
	}
}

func AllocateGeneratorWorkDir(genBaseDir string) (string, error) {
	if strings.TrimSpace(genBaseDir) == "" {
		return "", errors.New("generator base directory is required")
	}

	workDir := filepath.Join(filepath.Clean(genBaseDir), generatorWorkDirPrefix+uuid.NewString())
	if err := os.MkdirAll(workDir, 0o755); err != nil {
		return "", fmt.Errorf("create generator work directory: %w", err)
	}
	return filepath.Clean(workDir), nil
}

func CleanupGeneratorWorkDirs(genBaseDir string, retain GeneratorRetention, keepWorkDir string) error {
	genBaseDir = strings.TrimSpace(genBaseDir)
	if genBaseDir == "" {
		return errors.New("generator base directory is required")
	}
	if retain == "" {
		return errors.New("generator retention is required")
	}

	entries, err := os.ReadDir(genBaseDir)
	if err != nil {
		if errors.Is(err, os.ErrNotExist) {
			return nil
		}
		return fmt.Errorf("read generator base directory: %w", err)
	}

	keepWorkDir = filepath.Clean(strings.TrimSpace(keepWorkDir))
	var errs []string
	for _, entry := range entries {
		if !entry.IsDir() {
			continue
		}
		if !strings.HasPrefix(entry.Name(), generatorWorkDirPrefix) {
			continue
		}

		target := filepath.Join(genBaseDir, entry.Name())
		shouldKeep := false
		switch retain {
		case GeneratorRetainAll:
			shouldKeep = true
		case GeneratorRetainLast:
			shouldKeep = keepWorkDir != "" && filepath.Clean(target) == keepWorkDir
		case GeneratorRetainNone:
			shouldKeep = false
		default:
			return fmt.Errorf("unsupported generator retention: %s", retain)
		}
		if shouldKeep {
			continue
		}
		if err := os.RemoveAll(target); err != nil {
			errs = append(errs, fmt.Sprintf("remove %q: %v", target, err))
		}
	}

	if len(errs) > 0 {
		return errors.New(strings.Join(errs, "; "))
	}
	return nil
}

func ResolveRuntimePaths(scriptPathArg string, cwdArg string) (RuntimePaths, error) {
	if scriptPathArg == "" {
		return RuntimePaths{}, errors.New("script path is required")
	}

	var cwdAbs string
	var scriptAbs string

	if cwdArg != "" {
		var err error
		cwdAbs, err = filepath.Abs(cwdArg)
		if err != nil {
			return RuntimePaths{}, fmt.Errorf("resolve cwd: %w", err)
		}
		if filepath.IsAbs(scriptPathArg) {
			scriptAbs = filepath.Clean(scriptPathArg)
		} else {
			scriptAbs = filepath.Join(cwdAbs, scriptPathArg)
		}
	} else {
		var err error
		scriptAbs, err = filepath.Abs(scriptPathArg)
		if err != nil {
			return RuntimePaths{}, fmt.Errorf("resolve script: %w", err)
		}
		cwdAbs = filepath.Dir(scriptAbs)
	}

	return RuntimePaths{
		ScriptPath: filepath.Clean(scriptAbs),
		Cwd:        filepath.Clean(cwdAbs),
	}, nil
}

func ResolveGeneratorPaths(rootDir string, genDirArg string) (GeneratorPaths, error) {
	if rootDir == "" {
		return GeneratorPaths{}, errors.New("root directory is required")
	}

	rootAbs, err := filepath.Abs(rootDir)
	if err != nil {
		return GeneratorPaths{}, fmt.Errorf("resolve root directory: %w", err)
	}

	genDirArg = strings.TrimSpace(genDirArg)
	genBaseDir := ""
	if genDirArg == "" {
		genBaseDir = filepath.Join(rootAbs, "generated")
	} else if filepath.IsAbs(genDirArg) {
		genBaseDir = filepath.Clean(genDirArg)
	} else {
		genBaseDir = filepath.Join(rootAbs, genDirArg)
	}
	genBaseDir = filepath.Clean(genBaseDir)

	return GeneratorPaths{
		RootDir:    filepath.Clean(rootAbs),
		GenBaseDir: genBaseDir,
	}, nil
}

func ResolveRenderPaths(scriptPathArg string, outputArg string, cwdArg string) (RenderPaths, error) {
	runtimePaths, err := ResolveRuntimePaths(scriptPathArg, cwdArg)
	if err != nil {
		return RenderPaths{}, err
	}

	if outputArg == "" {
		return RenderPaths{}, errors.New("output path is required")
	}

	outputAbs, err := filepath.Abs(outputArg)
	if err != nil {
		return RenderPaths{}, fmt.Errorf("resolve output: %w", err)
	}

	return RenderPaths{
		ScriptPath: runtimePaths.ScriptPath,
		Cwd:        runtimePaths.Cwd,
		OutputDir:  filepath.Clean(outputAbs),
	}, nil
}

func ResolveExportPaths(scriptPathArg string, outputArg string, cwdArg string) (ExportPaths, error) {
	runtimePaths, err := ResolveRuntimePaths(scriptPathArg, cwdArg)
	if err != nil {
		return ExportPaths{}, err
	}

	if outputArg == "" {
		return ExportPaths{}, errors.New("output path is required")
	}

	outputAbs, err := filepath.Abs(outputArg)
	if err != nil {
		return ExportPaths{}, fmt.Errorf("resolve output: %w", err)
	}

	return ExportPaths{
		ScriptPath: runtimePaths.ScriptPath,
		Cwd:        runtimePaths.Cwd,
		OutputPath: filepath.Clean(outputAbs),
	}, nil
}

func ValidateRelativePath(pathArg string) (string, error) {
	if pathArg == "" {
		return "", errors.New("path is required")
	}
	if filepath.IsAbs(pathArg) {
		return "", errors.New("path must be relative")
	}

	cleanPath := filepath.Clean(pathArg)
	if cleanPath == "." {
		return "", errors.New("path must not be current directory")
	}

	if cleanPath == ".." {
		return "", errors.New("path must not escape cwd")
	}
	if rel, err := filepath.Rel(".", cleanPath); err == nil {
		if rel == ".." || strings.HasPrefix(rel, ".."+string(filepath.Separator)) {
			return "", errors.New("path must not escape cwd")
		}
	}

	return cleanPath, nil
}

func GetAbsCwdPath() (string, error) {
	cwd, err := os.Getwd()
	if err != nil {
		return "", err
	}

	cwdAbs, err := filepath.Abs(cwd)
	if err != nil {
		return "", err
	}

	return cwdAbs, nil
}
