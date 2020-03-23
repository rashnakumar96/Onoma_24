package main

import (
	"net/http"
	"path/filepath"
	"reflect"

	"utils"

	log "github.com/sirupsen/logrus"

	"github.com/asticode/go-astikit"
	"github.com/asticode/go-astilectron"
)

// Start starts the app and opens the app in a window
func Start() {

	// Create astilectron
	App, err := astilectron.New(log.New(), astilectron.Options{
		AppName:            "DDoH-2",
		AppIconDarwinPath:  "resources/icon.icns",
		AppIconDefaultPath: "resources/icon.png",
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

	indexPath := filepath.Join("resources", "app", "static", "home.html")

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

// StartNamehelpUI starts the user interface for namehelp
func StartNamehelpUI() {
	go Start()
	return
}

// Server server object
type Server struct {
	Started bool
}

// NamehelpServer keep track of the status of namehelp
var NamehelpServer = Server{Started: true}

func enableCors(w *http.ResponseWriter) {
	(*w).Header().Set("Access-Control-Allow-Origin", "*")
}

// Start namehelp setups
// Does not modify the already running background service
// Change the DNS settings to local host
func handleStart() {
	if NamehelpServer.Started {
		// fmt.Fprintf(responseWriter, "Already started")
		log.WithFields(log.Fields{
			"action": "Start",
			"method": "POST",
			"error":  "Already Started"}).Error("Handle button: error")
	} else {
		// fmt.Fprintf(responseWriter, "Starting")
		namehelpProgram.oldDNSServers = namehelpProgram.saveCurrentDNSConfiguration()
		networkInterfaces := reflect.ValueOf(namehelpProgram.oldDNSServers).MapKeys()
		// get slice of keys
		namehelpProgram.setDNSServer(utils.LOCALHOST, backupHosts, networkInterfaces)
		log.WithFields(log.Fields{
			"action": "Start", "method": "POST"}).Debug("Handle button: succeeded")

		NamehelpServer.Started = true
	}
	return
}

// Stop namehelp setups
// Does not modify the already running background service
// Change the DNS settings to default
func handleStop() {
	if !NamehelpServer.Started {
		// fmt.Fprintf(responseWriter, "Already stopped")
		log.WithFields(log.Fields{
			"action": "Stop",
			"method": "POST",
			"error":  "Already Stopped"}).Error("Handle button: error")
	} else {
		// fmt.Fprintf(responseWriter, "Stopping")
		namehelpProgram.restoreOldDNSServers(namehelpProgram.oldDNSServers) // restore original DNS settings
		// namehelpProgram.dnsQueryHandler.topSites.SaveUserSites()            // save user's top sites to file
		log.WithFields(log.Fields{
			"action": "Stop", "method": "POST"}).Debug("Handle button: succeeded")

		NamehelpServer.Started = false
	}
	return
}
