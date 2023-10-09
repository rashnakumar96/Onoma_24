package network

import (
	"fmt"
	"os/exec"
	"runtime"
	"strconv"
	"strings"

	"namehelp/utils"

	log "github.com/sirupsen/logrus"
)

// DhcpGetLocalDNSServers Uses DHCP to find the default local DNS servers
// and returns them as a list of strings.
// e.g. {"192.168.0.1", "209.140.70.162"}
func DhcpGetLocalDNSServers() (localDNSServers []string) {
	numberOfInterfaces := DhcpGetNumberOfInterfaces()
	log.WithFields(log.Fields{
		"number of interfaces": numberOfInterfaces}).Debug("Running DhcpGetLocalDNSServers")

	for i := 0; i < numberOfInterfaces; i++ {
		networkInterface := fmt.Sprintf("en%d", i)
		dnsServersForInterface := DhcpGetDNSServersForInterface(networkInterface)
		log.WithFields(log.Fields{
			"network interface": networkInterface,
			"DNS server":        dnsServersForInterface}).Debug("Network interface found interface servers and add to local DNS servers")
		localDNSServers = append(localDNSServers, dnsServersForInterface...)
	}

	log.WithFields(log.Fields{
		"local DNS servers": localDNSServers}).Debug("local DNS servers found")
	return localDNSServers
}

// DhcpGetNumberOfInterfaces gets the number of interfaces used by the machine
func DhcpGetNumberOfInterfaces() (numberOfInterfaces int) {
	log.Debug("Running DhcpGetNumberOfInterfaces")

	var err error
	combinedOutput := ""
	commandName := ""
	if runtime.GOOS == "darwin" {
		//For mac
		commandName = "ipconfig"
		arguments := []string{"ifcount"}

		tmp, err1 := utils.RunCommand(commandName, arguments...)
		err = err1
		combinedOutput = string(tmp)
		if err != nil {
			log.WithFields(log.Fields{
				"command": commandName,
				"error":   err.Error()}).Error("Unable to run.")
			return 0 // fail
		}
	} else if runtime.GOOS == "linux" {
		// For linux, enable now start
		commandName = "ls -A /sys/class/net | wc -l"
		tmp, err1 := exec.Command("bash", "-c", commandName).Output()
		err = err1
		combinedOutput = string(tmp[:len(tmp)])
		if err != nil {
			log.WithFields(log.Fields{
				"command": commandName,
				"error":   err.Error()}).Debug("Unable to run.")
			return 0 // fail
		}
		// For linux, enable now end
	} else if runtime.GOOS == "windows" {
		commandName = "wmic nic get NetConnectionID"
		tmp, err1 := exec.Command(`cmd`, `/C`, `wmic nic get NetConnectionID`).Output()
		err = err1
		combinedOutput = strconv.Itoa(len(strings.Split(string(tmp[:len(tmp)]), "\n")))
		if err != nil {
			log.WithFields(log.Fields{
				"command": commandName,
				"error":   err.Error()}).Error("Unable to run.")
			return 0 // fail
		}
	}

	linesOfOutput := strings.Split(combinedOutput, "\n")
	log.WithFields(log.Fields{
		"command":         commandName,
		"lines of output": linesOfOutput}).Debug("Run command finished. ")
	for _, outputLine := range linesOfOutput {
		numberOfInterfaces, err = strconv.Atoi(outputLine)
		if err != nil {
			log.WithFields(log.Fields{
				"output line": outputLine,
				"error":       err.Error()}).Error("Unable to convert output to int.")
			continue
		}
		// success
		return numberOfInterfaces
	}

	log.WithFields(log.Fields{
		"error": err.Error()}).Warn("Unable to get interface count.")
	return 0 // fail
}

// DhcpGetDNSServersForInterface runs ipconfig getpacket <networkInterface>
// and parses result to get list of DNS servers
func DhcpGetDNSServersForInterface(networkInterface string) (dnsServersForInterface []string) {

	log.Debug("Running DhcpGetDNSServersForInterface")

	var err error
	combinedOutput := ""
	if runtime.GOOS == "darwin" {
		//For mac
		commandName := "ipconfig"
		arguments := []string{"getpacket", networkInterface}
		tmp, err1 := utils.RunCommand(commandName, arguments...)
		combinedOutput = string(tmp)
		err = err1
		//For mac
	} else if runtime.GOOS == "linux" {
		//for linux, enable for Now
		commandName := "ls -A /sys/class/net | wc -l"
		tmp, err1 := exec.Command("bash", "-c", commandName).Output()
		combinedOutput = string(tmp[:len(tmp)])
		err = err1
		//for linux, enable for now end
	} else if runtime.GOOS == "windows" {
		commandName := "ipconfig /all"
		tmp, err1 := exec.Command("cmd", "/C", commandName).Output()
		combinedOutput = string(tmp[:len(tmp)])
		err = err1
	}

	if err != nil {
		log.WithFields(log.Fields{
			"error": err.Error()}).Debug("Unable to get info about local DNS servers.")
		return []string{}
	}

	linesOfOutput := strings.Split(combinedOutput, "\n")
	for _, outputLine := range linesOfOutput {
		if !strings.HasPrefix(outputLine, "domain_name_server") {
			continue
		}

		startIndex := strings.Index(outputLine, "{") + 1
		endIndex := strings.Index(outputLine, "}")

		if startIndex < 0 || endIndex < 0 {
			continue
		}

		dnsServersForInterface = []string{outputLine[startIndex:endIndex]}
		return dnsServersForInterface
	}

	return []string{}
}
