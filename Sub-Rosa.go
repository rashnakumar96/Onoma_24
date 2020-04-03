package main

import (
	"io"
	"os"
	"path"
	"path/filepath"

	"github.com/kardianos/osext"
	log "github.com/sirupsen/logrus"
	"gopkg.in/natefinch/lumberjack.v2"
)

// init is called before main when starting a program.
// intializes loggers
func init() {
	exe, err := osext.Executable()
	if err != nil {
		panic(err)
	}
	exeDir := path.Dir(exe)
	ljack := &lumberjack.Logger{
		Filename:   filepath.Join(exeDir, "Sub-Rosa.log"),
		MaxSize:    1, // In megabytes.
		MaxBackups: 3,
		MaxAge:     3, // In days (0 means keep forever?)
	}
	mw := io.MultiWriter(os.Stdout, ljack)
	log.SetOutput(mw)
	log.SetFormatter(&log.TextFormatter{ForceColors: true})
	// Only log the Info level or above.
	log.SetLevel(log.InfoLevel)
}

func main() {
	log.Info("Sub-Rosa Started")
	StartUI()
}
