package main

import (
	log "github.com/sirupsen/logrus"
)

// init is called before main when starting a program.
// intializes loggers
func init() {
	log.SetFormatter(&log.TextFormatter{ForceColors: true})
	// Only log the Info level or above.
	log.SetLevel(log.InfoLevel)
}

func main() {
	log.Info("DDoH-2 Started")
	StartNamehelpUI()
}
