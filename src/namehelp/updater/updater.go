package updater

import (
	"net/http"
	"os/exec"
	"syscall"

	"github.com/inconshreveable/go-update"
	"github.com/kardianos/osext"
	log "github.com/sirupsen/logrus"
)

func doUpdate(url string) error {
	resp, err := http.Get(url)
	if err != nil {
		return err
	}
	defer resp.Body.Close()
	err := update.Apply(resp.Body, update.Options{})
	if err != nil {
		log.Withfields(log.Fields{"error": err}).Error("Updater: Error updating binary")
		return err
	}

	filename, err := osext.Executable()
	if err != nil {
		log.Withfields(log.Fields{"error": err}).Error("Updater: Error getting executable path")
		return err
	}
	log.WithFields(log.Fields{"exe": filename}).Debug("Updater: Attempting restart.")
	args := []string{"--service", "restart"}
	c := exec.Command(filename, args...)

	// This following part may not be needed for Windows
	c.SysProcAttr = &syscall.SysProcAttr{}
	c.SysProcAttr.Setpgid = true

	err = c.Run()
	if err != nil {
		log.WithFields(log.Fields{"error": err}).
			Error("Updater: Problem restarting.")
		return err
	}
	return nil
}
