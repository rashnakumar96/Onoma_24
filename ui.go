package main

import (
	"net/http"
	"os/exec"
	"path"
	"path/filepath"

	log "github.com/sirupsen/logrus"

	"github.com/asticode/go-astikit"
	"github.com/asticode/go-astilectron"
	"github.com/kardianos/osext"
)

// StartNamehelpUI starts the user interface for namehelp
func StartNamehelpUI() {
	// Make sure namehelp service is installed
	command := exec.Command("sudo", "./bin/namehelp", "--service", "install")
	output, err := command.Output()
	log.WithFields(log.Fields{"output": string(output)}).Info("Command Output")
	if err != nil {
		log.WithFields(log.Fields{
			"error": err}).Error("Namehelp has already been installed")
	}

	// Start the UI
	Start()
}

// Start starts the app and opens the app in a window
func Start() {
	exe, err := osext.Executable()
	if err != nil {
		panic(err)
	}
	execPath := path.Dir(exe)

	// Create astilectron
	App, err := astilectron.New(log.New(), astilectron.Options{
		AppName:            "DDoH-2",
		AppIconDarwinPath:  filepath.Join(execPath, "resources", "icon.icns"),
		AppIconDefaultPath: filepath.Join(execPath, "resources", "icon.png"),
	})
	if err != nil {
		log.WithFields(log.Fields{"error": err}).Fatal("Creating astilectron failed")
	}

	// Handle signals
	// App.HandleSignals()

	// Start
	err = App.Start()
	if err != nil {
		log.WithFields(log.Fields{"error": err}).Fatal("Starting astilectron failed")
	}

	indexPath := filepath.Join(execPath, "resources", "app", "static", "home.html")

	Window, err := App.NewWindow(indexPath, &astilectron.WindowOptions{
		Center: astikit.BoolPtr(true),
		Height: astikit.IntPtr(700),
		Width:  astikit.IntPtr(700),
	})
	if err != nil {
		log.WithFields(log.Fields{"error": err}).Fatal("New window failed")
	}
	// Create windows
	err = Window.Create()
	if err != nil {
		log.WithFields(log.Fields{"error": err}).Fatal("Create window failed")
	}

	Window.OnMessage(func(m *astilectron.EventMessage) interface{} {
		// Unmarshal
		var s string
		m.Unmarshal(&s)
		log.WithFields(log.Fields{"message": s}).Info("Message Received")

		switch s {
		case "start":
			handleStart()
			break
		case "stop":
			handleStop()
			break
		case "add":
			// TODO: handle hadd resolver
			break
		}
		return nil
	})

	// Blocking pattern
	App.Wait()
}

// Server server object
type Server struct {
	Started bool
}

// NamehelpServer keep track of the status of namehelp
var NamehelpServer = Server{Started: false}

func enableCors(w *http.ResponseWriter) {
	(*w).Header().Set("Access-Control-Allow-Origin", "*")
}

// Start namehelp setups
// Does not modify the already running background service
// Change the DNS settings to local host
func handleStart() {
	if NamehelpServer.Started {
		log.WithFields(log.Fields{
			"action": "Start",
			"method": "POST",
			"error":  "Already Started"}).Error("Handle button: error")
	} else {
		command := exec.Command("sudo", "./bin/namehelp", "--service", "start")
		// command := exec.Command("sudo", "./bin/namehelp")
		output, err := command.Output()
		log.WithFields(log.Fields{"output": string(output)}).Info("Command Output")
		if err != nil {
			log.Fatal(err)
		}
		log.WithFields(log.Fields{
			"action": "Start", "method": "POST"}).Info("Handle button: succeeded")

		NamehelpServer.Started = true
	}
	return
}

// Stop namehelp setups
// Does not modify the already running background service
// Change the DNS settings to default
func handleStop() {
	if !NamehelpServer.Started {
		log.WithFields(log.Fields{
			"action": "Stop",
			"method": "POST",
			"error":  "Already Stopped"}).Error("Handle button: error")
	} else {
		command := exec.Command("sudo", "./bin/namehelp", "--service", "stop")
		output, err := command.Output()
		log.WithFields(log.Fields{"output": string(output)}).Info("Command Output")
		if err != nil {
			log.Fatal(err)
		}
		log.WithFields(log.Fields{
			"action": "Stop", "method": "POST"}).Info("Handle button: succeeded")

		NamehelpServer.Started = false
	}
	return
}
