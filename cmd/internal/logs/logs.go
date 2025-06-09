package logs

import (
	"log"

	"github.com/fatih/color"
)

var (
	Info = log.New(color.Output, color.HiBlueString("[INFO] "), log.Lmsgprefix)
	Warn = log.New(color.Output, color.HiYellowString("[WARN] "), log.Lmsgprefix)
	Err  = log.New(color.Output, color.HiRedString("[ERROR] "), log.Lmsgprefix)
)
