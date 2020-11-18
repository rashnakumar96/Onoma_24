//go:generate go get -u github.com/alexthemonk/DoH_Proxy/
//go:generate go get -u github.com/kardianos/osext/
//go:generate go get -u github.com/kardianos/service/
//go:generate go get -u github.com/miekg/dns/
//go:generate go get -u github.com/sirupsen/logrus/
//go:generate go get -u go.mongodb.org/mongo-driver/mongo
//go:generate go get -u gopkg.in/natefinch/lumberjack.v2

package main

import (
	"encoding/json"
	"flag"
	"fmt"
	"io"
	"io/ioutil"
	"math/rand"
	"net/http"
	"os"
	"os/exec"
	"os/signal"
	"path"
	"path/filepath"
	"reflect"
	"runtime"
	"strconv"
	"strings"
	"syscall"
	"time"

	// "namehelp/network"

	"namehelp/reporter"

	"namehelp/handler"
	"namehelp/utils"

	"github.com/kardianos/osext"
	"github.com/kardianos/service"
	"github.com/miekg/dns"
	log "github.com/sirupsen/logrus"
	"gopkg.in/natefinch/lumberjack.v2"
)

var backupHosts = []string{}

var signalChannel chan os.Signal

// Config contains the configuration specifications
type Config struct {
	Name        string
	DisplayName string
	Version     string
	APIURL      string
	BinURL      string
	DiffURL     string
	UpdateDir   string
	Description string
}

// Program of Namehelp
type Program struct {
	oldDNSServers   map[string][]string
	dnsQueryHandler *handler.DNSQueryHandler
	tcpServer       *dns.Server
	udpServer       *dns.Server
	// smartDNSSelector *SmartDNSSelector
	shutdownChan chan bool
	reporter     *reporter.Reporter
}

var appConfig = Config{
	Name:        "namehelp",
	DisplayName: "namehelp",
	Version:     "2.0.2",
	APIURL:      "https://aquarium.aqualab.cs.northwestern.edu/",
	BinURL:      "https://aquarium.aqualab.cs.northwestern.edu/",
	DiffURL:     "https://aquarium.aqualab.cs.northwestern.edu/",
	UpdateDir:   "update/",
	Description: "Namehelp is a background service that improves web performance" +
		" and reliability through better DNS resolution. " +
		"Developed by AquaLab at Northwestern University.",
}

// NewProgram initialize a new namehelp program
func NewProgram() *Program {
	var newProgram *Program = &Program{}
	newProgram.shutdownChan = make(chan bool)
	return newProgram
}

var namehelpProgram = NewProgram()

// init is called before main when starting a program.
// intializes loggers
func init() {
	// Configures the log settings in this function.
	//
	// Optional example: Log as JSON instead of the default ASCII formatter.
	// log.SetFormatter(&log.JSONFormatter{})

	// You can also use lumberjack to set up rollling logs.
	// Can either output logs to stdout or lumberjack. Pick one, comment out the other.
	exe, err := osext.Executable()
	if err != nil {
		panic(err)
	}
	exeDir := path.Dir(exe)
	ljack := &lumberjack.Logger{
		Filename:   filepath.Join(exeDir, appConfig.Name+".log"),
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

// Start is the Service.Interface method invoked when run with "--service start"
func (program *Program) Start(s service.Service) error {

	log.WithFields(log.Fields{"app": appConfig.Name}).
		Debug("program.Start(service) invoked.")

	// Start() should return immediately. Kick off async execution.
	go program.run()
	return nil
}

// Stop is the Service.Interface method invoked when run with "--service stop"
func (program *Program) Stop(s service.Service) error {

	// Stop should not block. Return with a few seconds.
	log.Debug("program.Stop(service) invoked")
	go func() {
		for signalChannel == nil {
			// Make sure that shutdown channel has been initilized.
		}
		log.Info("Sending SIGINT on signalChannel")
		signalChannel <- syscall.SIGINT
	}()

	return nil
}

// run is the main process running
func (program *Program) run() {
	log.Debug("program.run() invoked.")
	rand.Seed(time.Now().UTC().UnixNano())
	log.Info("Starting app.")

	err := program.launchNamehelpDNSServer()
	if err != nil {
		message := fmt.Sprintf(
			"Failed to launch namehelp.  Error: [%s]\nShutting down.",
			err.Error())
		log.Error(message)
		// TODO shut self down gracefully (including Aquarium)
	}

	// Switch DNS server to 127.0.0.1 (use namehelp as DNS server)
	// save the old configuration for restoration at stopping
	program.oldDNSServers = program.saveCurrentDNSConfiguration()
	networkInterfaces := reflect.ValueOf(program.oldDNSServers).MapKeys()
	// get slice of keys
	program.setDNSServer(utils.LOCALHOST, backupHosts, networkInterfaces)

	// program.smartDNSSelector = NewSmartDNSSelector()
	// going off to the new locally started DNS server for namehelp
	// go program.smartDNSSelector.routine_Do()

	// TODO run aquarium measurements

	// Capture and handle Ctrl-C signal
	signalChannel = make(chan os.Signal)
	signal.Notify(signalChannel, syscall.SIGINT, syscall.SIGTERM)

	log.Info("Waiting for signal from signalChannel (blocking)")

	thisSignal := <-signalChannel

	log.WithFields(log.Fields{
		"signal": thisSignal.String()}).Info("Signal received")

	// restore original DNS settings
	program.restoreOldDNSServers(program.oldDNSServers)
	// save user's top sites to file
	// program.dnsQueryHandler.topSites.SaveUserSites()

	log.Info("Shutdown complete. Exiting.")
	program.shutdownChan <- true
}

func (program *Program) initializeReporter() {
	program.reporter = reporter.NewReporter(appConfig.Version)
}

func (program *Program) initializeDNSServers() {
	// dns library requires a handler function for the ServeMux
	program.dnsQueryHandler = handler.NewHandler(program.oldDNSServers)

	tcpRequestMultiplexer := dns.NewServeMux()
	tcpRequestMultiplexer.HandleFunc(".", program.dnsQueryHandler.DoTCP)

	udpRequestMultiplexer := dns.NewServeMux()
	udpRequestMultiplexer.HandleFunc(".", program.dnsQueryHandler.DoUDP)

	rTimeout := 5 * time.Second
	wTimeout := 5 * time.Second
	dnsServerAddress := utils.LOCALHOST + ":" + strconv.Itoa(utils.PORT)

	program.tcpServer = &dns.Server{
		Addr:         dnsServerAddress,
		Net:          "tcp",
		Handler:      tcpRequestMultiplexer,
		ReadTimeout:  rTimeout,
		WriteTimeout: wTimeout}

	program.udpServer = &dns.Server{
		Addr:         dnsServerAddress,
		Net:          "udp",
		Handler:      udpRequestMultiplexer,
		UDPSize:      65535,
		ReadTimeout:  rTimeout,
		WriteTimeout: wTimeout}
}

func (program *Program) launchNamehelpDNSServer() error {
	url := "http://ipinfo.io/json"
	resp, err := http.Get(url)
	if err != nil {
		log.Fatal(err)
	}
	defer resp.Body.Close()
	body, readErr := ioutil.ReadAll(resp.Body)
	if readErr != nil {
		log.Fatal(readErr)
	}
	json_map := make(map[string]interface{})

	jsonErr := json.Unmarshal(body, &json_map)
	if jsonErr != nil {
		log.Fatal(jsonErr)
	}

	country, ok := json_map["country"].(string)
	if ok {
		log.WithFields(log.Fields{
			"country": json_map["country"]}).Info("Country code")
	} else {
		url := "https://extreme-ip-lookup.com/json"
		resp, err := http.Get(url)
		if err != nil {
			log.Fatal(err)
		}
		defer resp.Body.Close()
		body, readErr := ioutil.ReadAll(resp.Body)
		if readErr != nil {
			log.Fatal(readErr)
		}
		json_map := make(map[string]interface{})

		jsonErr := json.Unmarshal(body, &json_map)
		if jsonErr != nil {
			log.Fatal(jsonErr)
		}

		country, ok = json_map["countryCode"].(string)
		if ok {
			log.WithFields(log.Fields{
				"country": json_map["countryCode"]}).Info("Country code")
		} else {
			log.Fatal("Failed to get country code")
		}
	}

	testingDir := filepath.Join("analysis", "measurements", country)
	dir, err := os.Getwd()
	//testingDir has the countrycode we want to test with e.g.
	// testingDir:="/analysis/measurements/IN"

	//////////
	jsonFile, err := os.Open(filepath.Join(dir, testingDir, "publicDNSServers.json"))
	if err != nil {
		log.Info("error opening file: " + filepath.Join(dir, testingDir, "publicDNSServers.json"))
	}
	defer jsonFile.Close()
	byteValue, _ := ioutil.ReadAll(jsonFile)
	var publicDNSServers []string
	json.Unmarshal([]byte(byteValue), &publicDNSServers)
	log.WithFields(log.Fields{
		"publicDNSServers": publicDNSServers}).Info("These are the public DNS servers")
	handler.PDNSServers = publicDNSServers

	program.initializeDNSServers()

	// start DNS servers for UDP and TCP requests
	program.initializeReporter()
	program.initializeDNSServers()

	go program.startDNSServer(program.udpServer)
	go program.startDNSServer(program.tcpServer)
	// this go func does the testing as soon as SubRosa is started
	// TODO: change this to per-trigger base
	go program.doMeasurement(testingDir)
	return nil
}

func (program *Program) runTests(resolverName string, ip string, dir string, testingDir string) {
	utils.FlushLocalDnsCache()
	if !handler.Experiment {
		handler.DoHServersToTest = []string{"127.0.0.1"}
	}
	if handler.DoHEnabled && handler.Experiment {
		handler.DoHServersToTest = []string{resolverName}
	} else if !handler.DoHEnabled && handler.Experiment {
		handler.DNSServersToTest = []string{ip}
	}

	//this for loop ensures that ServersToTest is resolverName till we collect all measurements with this resolverName
	//and file dir+testingDir+"/lighthouseTTBresolverName.json" is made in the directory
	utils.FlushLocalDnsCache()
	log.WithFields(log.Fields{
		"dir": dir}).Info("confirming Directory")

	for {
		if _, err := os.Stat(filepath.Join(dir, "lighthouseTTB", resolverName, "_.json")); os.IsNotExist(err) {
			continue
		} else {
			log.Info("FileFound")
			break
		}
	}
	log.Info("Done Testing " + resolverName)

}

func (program *Program) MeasureDnsLatencies(resolverName string, ip string, dir string, dict1 map[string]map[string]map[string]interface{}, dnsLatencyFile string, iterations int, testingDir string) {
	utils.FlushLocalDnsCache()
	var err error
	if !handler.Experiment {
		handler.DoHServersToTest = []string{"127.0.0.1"}
	}
	if handler.DoHEnabled && handler.Experiment {
		handler.DoHServersToTest = []string{resolverName}
	} else if !handler.DoHEnabled && handler.Experiment {
		handler.DNSServersToTest = []string{ip}
	}
	dict1, err = program.dnsQueryHandler.MeasureDnsLatencies(0, dnsLatencyFile, 0, handler.DoHEnabled, handler.Experiment, iterations, dict1, resolverName)
	file, _ := json.MarshalIndent(dict1, "", " ")
	_ = ioutil.WriteFile(filepath.Join(dir, "/dnsLatencies.json"), file, 0644)
	if err != nil {
		log.WithFields(log.Fields{
			"error": err}).Info("DNS Latency Command produced error")
	}
	log.WithFields(log.Fields{
		"dnsLatencyFile: ": filepath.Join(dir, "/dnsLatencies.json")}).Info("Looking for this file")
}

func (program *Program) DnsLatenciesSettings(dir string, testingDir string, publicDNSServers []string) {
	dict1 := make(map[string]map[string]map[string]interface{})
	iterations := 3
	dnsLatencyFile := filepath.Join(dir, testingDir, "AlexaUniqueResources.txt")

	handler.Experiment = true
	handler.Proxy = false
	program.dnsQueryHandler.DisableDirectResolution()
	handler.PrivacyEnabled = false
	handler.Racing = false
	handler.Decentralized = false
	handler.DoHEnabled = true
	program.MeasureDnsLatencies("Google", "", dir+testingDir, dict1, dnsLatencyFile, iterations, testingDir)
	program.MeasureDnsLatencies("Cloudflare", "", dir+testingDir, dict1, dnsLatencyFile, iterations, testingDir)
	program.MeasureDnsLatencies("Quad9", "", dir+testingDir, dict1, dnsLatencyFile, iterations, testingDir)
	handler.DoHEnabled = false
	for i := 0; i < len(publicDNSServers); i++ {
		program.MeasureDnsLatencies(publicDNSServers[i], publicDNSServers[i], dir+testingDir, dict1, dnsLatencyFile, iterations, testingDir)
	}
	handler.PDNSServers = publicDNSServers

	handler.DoHEnabled = true
	handler.Experiment = false
	handler.Decentralized = true
	program.dnsQueryHandler.DisableDirectResolution()
	handler.Proxy = true

	handler.PrivacyEnabled = false
	handler.Racing = false
	utils.FlushLocalDnsCache()
	handler.DoHServersToTest = []string{"127.0.0.1"}
	program.MeasureDnsLatencies("DoHProxyNP", "", dir+testingDir, dict1, dnsLatencyFile, iterations, testingDir)
	utils.FlushLocalDnsCache()
	handler.PrivacyEnabled = false
	handler.Racing = true
	program.dnsQueryHandler.EnableDirectResolution()
	handler.Proxy = false
	handler.DoHServersToTest = []string{"127.0.0.1"}
	program.MeasureDnsLatencies("SubRosaNP", "", dir+testingDir, dict1, dnsLatencyFile, iterations, testingDir)

	utils.FlushLocalDnsCache()
	handler.PrivacyEnabled = false
	handler.Racing = false
	program.dnsQueryHandler.EnableDirectResolution()
	handler.Proxy = false
	handler.DoHServersToTest = []string{"127.0.0.1"}
	program.MeasureDnsLatencies("SubRosaNPR", "", dir+testingDir, dict1, dnsLatencyFile, iterations, testingDir)

	program.reporter.PushToMongoDB("SubRosa-Test", "dnsLatencies"+testingDir[len(testingDir)-2:], dict1)

}

func (program *Program) doMeasurement(testingDir string) error {

	dir, err := os.Getwd()
	d1 := []byte("start Measurements\n")
	err = ioutil.WriteFile(dir+"/dat", d1, 0644)
	if err != nil {
		log.WithFields(log.Fields{
			"error": err}).Info("couldn't start measurements")
		panic(err)
	}

	publicDNSServers := handler.PDNSServers
	//handler.Proxy is true when testing DoHProxy
	//handler.Racing is true when testing racing in SubRosa
	//handler.PrivacyEnabled is true when testing SubRosa and DoHProxy with privacy enabled, and all same 2lds go to the same resolver
	//EnableDirectResolution allows SubRosa to do DR, we disable with other approaches

	// //for testing individual resolvers it's true, for testing DoHProxy and SubRosa it's false
	handler.Experiment = true
	// //for testing DoH resolvers

	// //resolver mapping dict for privacy setting
	handler.ResolverMapping = make(map[string][]string)

	// //stores all measurements
	outPath := filepath.Join(dir, testingDir)
	if _, err := os.Stat(outPath); os.IsNotExist(err) {
		os.Mkdir(outPath, 0755)
	}
	if err != nil {
		log.Info("Error getting current working directory")
	}

	handler.Proxy = false
	program.dnsQueryHandler.DisableDirectResolution()
	handler.PrivacyEnabled = false
	handler.Racing = false
	handler.Decentralized = false
	handler.DoHEnabled = true

	program.runTests("Google", "", dir+testingDir, testingDir)
	program.runTests("Cloudflare", "", dir+testingDir, testingDir)
	program.runTests("Quad9", "", dir+testingDir, testingDir)

	handler.DoHEnabled = false

	///testing publicDns servers
	//publicDNSServers.json file should have ips of public DNS servers of a country to test
	for i := 0; i < len(publicDNSServers); i++ {
		program.runTests(publicDNSServers[i], publicDNSServers[i], dir+testingDir, testingDir)
	}
	handler.PDNSServers = publicDNSServers
	// Done testing them
	//////////////////

	handler.DoHEnabled = true
	handler.Experiment = false
	handler.Decentralized = true
	program.dnsQueryHandler.DisableDirectResolution()
	handler.Proxy = true

	// //testing DoHProxy with Privacy Enabled
	// handler.PrivacyEnabled=true
	// handler.Proxy=true
	// utils.FlushLocalDnsCache()
	// handler.DoHServersToTest=[]string{"127.0.0.1"}
	// dict1, err = program.dnsQueryHandler.MeasureDnsLatencies(0,dnsLatencyFile,0,handler.DoHEnabled,handler.Experiment,iterations,dict1,"DoHProxy")
	// file,_=json.MarshalIndent(dict1, "", " ")
	// _ = ioutil.WriteFile(dir+testingDir+"/dnsLatencies.json", file, 0644)

	// //these for loops ensure that DoHServersToTest is DoHProxy with Privacy enabled (but new resolver mapping dict btw each run)
	// // till we collect all measurements with this resolver
	// //and file dir+testingDir+"/lighthouseTTBDoHProxy.json" is made in the directory
	// utils.FlushLocalDnsCache()
	// for{
	// 	if _, err := os.Stat(dir+testingDir+"/lighthouseTTBDoHProxy0.json"); os.IsNotExist(err) {
	// 		continue
	// 	}else{
	// 		break
	// 	}
	// }

	// handler.ResolverMapping=make(map[string][]string)
	// for{
	// 	if _, err := os.Stat(dir+testingDir+"/lighthouseTTBDoHProxy1.json"); os.IsNotExist(err) {
	// 		continue
	// 	}else{
	// 		break
	// 	}
	// }
	// handler.ResolverMapping=make(map[string][]string)
	// for{
	// 	if _, err := os.Stat(dir+testingDir+"/lighthouseTTBDoHProxy.json"); os.IsNotExist(err) {
	// 		continue
	// 	}else{
	// 		break
	// 	}
	// }
	// log.Info("Done Testing DoHProxy")

	//testing DoHProxy with No Privacy Enabled(DoHProxyNP)
	handler.PrivacyEnabled = false
	handler.Racing = false
	utils.FlushLocalDnsCache()
	handler.DoHServersToTest = []string{"127.0.0.1"}
	program.runTests("DoHProxyNP", "", dir+testingDir, testingDir)

	//testing SubRosa with Privacy Enabled and Racing
	// handler.PrivacyEnabled=true
	// handler.Racing=true
	// utils.FlushLocalDnsCache()
	// program.dnsQueryHandler.EnableDirectResolution()
	// handler.Proxy=false
	// handler.DoHServersToTest=[]string{"127.0.0.1"}
	// dict1, err = program.dnsQueryHandler.MeasureDnsLatencies(0,dnsLatencyFile,0,handler.DoHEnabled,handler.Experiment,iterations,dict1,"SubRosa")
	// file,_=json.MarshalIndent(dict1, "", " ")
	// _ = ioutil.WriteFile(dir+testingDir+"/dnsLatencies.json", file, 0644)

	// //these for loops ensure that DoHServersToTest is SubRosa with Privacy enabled & Racing (but new resolver mapping dict btw each run)
	// // till we collect all measurements with this resolver
	// //and file dir+testingDir+"/lighthouseTTBSubRosa.json" is made in the directory
	// utils.FlushLocalDnsCache()
	// for{
	// 	if _, err := os.Stat(dir+testingDir+"/lighthouseTTBSubRosa0.json"); os.IsNotExist(err) {
	// 		continue
	// 	}else{
	// 		break
	// 	}
	// }
	// handler.ResolverMapping=make(map[string][]string)
	// for{
	// 	if _, err := os.Stat(dir+testingDir+"/lighthouseTTBSubRosa1.json"); os.IsNotExist(err) {
	// 		continue
	// 	}else{
	// 		break
	// 	}
	// }
	// handler.ResolverMapping=make(map[string][]string)
	// for{
	// 	if _, err := os.Stat(dir+testingDir+"/lighthouseTTBSubRosa.json"); os.IsNotExist(err) {
	// 		continue
	// 	}else{
	// 		break
	// 	}
	// }
	// log.Info("Done Testing SubRosa")

	//testing SubRosa with No Privacy Enabled,but Racing enabled(SubRosaNP)
	utils.FlushLocalDnsCache()
	handler.PrivacyEnabled = false
	handler.Racing = true
	program.dnsQueryHandler.EnableDirectResolution()
	handler.Proxy = false
	handler.DoHServersToTest = []string{"127.0.0.1"}
	program.runTests("SubRosaNP", "", dir+testingDir, testingDir)

	//testing SubRosa with No Privacy Enabled and No Racing Enabled(SubRosaNPR)
	utils.FlushLocalDnsCache()
	handler.PrivacyEnabled = false
	handler.Racing = false
	program.dnsQueryHandler.EnableDirectResolution()
	handler.Proxy = false
	handler.DoHServersToTest = []string{"127.0.0.1"}
	program.runTests("SubRosaNPR", "", dir+testingDir, testingDir)

	//Measuring Pings to Resolvers
	dict2 := make(map[string]interface{})
	dohresolvers := []string{"8.8.8.8", "9.9.9.9", "1.1.1.1"}
	iterations := 3
	resolverList := append(publicDNSServers, dohresolvers...)
	dict2 = program.dnsQueryHandler.PingServers(handler.DoHEnabled, handler.Experiment, iterations, dict2, resolverList)
	file, _ := json.MarshalIndent(dict2, "", " ")
	_ = ioutil.WriteFile(filepath.Join(dir, testingDir, "pingServers.json"), file, 0644)
	program.reporter.PushToMongoDB("SubRosa-Test", "PingServers.json_"+testingDir[len(testingDir)-2:], dict2)

	// Measuring DNSLatencies and Pings to Replicas
	program.DnsLatenciesSettings(dir, testingDir, publicDNSServers)

	// push resourcesttbbyCDNLighthouse.json to server
	jsonFile, err := os.Open(filepath.Join(dir, testingDir, "resourcesttbbyCDNLighthouse.json"))
	if err != nil {
		log.Info("error opening file: " + filepath.Join(dir, testingDir, "resourcesttbbyCDNLighthouse.json"))
	}
	defer jsonFile.Close()
	byteValue, _ := ioutil.ReadAll(jsonFile)
	json_map := make(map[string]map[string]map[string]interface{})
	json.Unmarshal([]byte(byteValue), &json_map)
	program.reporter.PushToMongoDB("SubRosa-Test", "resourcesttbbyCDNLighthouse_"+testingDir[len(testingDir)-2:], json_map)

	return err
}

// Saves the current system configuration for future restoration
// Returns a map of {networkinterface: <list of old dns servers>}
func (program *Program) saveCurrentDNSConfiguration() (oldDNSServers map[string][]string) {
	log.Info("Saving original DNS configuration.")
	oldDNSServers = make(map[string][]string)

	command := exec.Command("")

	// Command to get network interfaces
	if runtime.GOOS == "darwin" {
		// for MacOS
		command = exec.Command("networksetup", "-listallnetworkservices")
	} else if runtime.GOOS == "linux" {
		// for Linux
		command = exec.Command("iwconfig")
	} else if runtime.GOOS == "windows" {
		// for Windows
		// command = exec.Command(`cmd`, `/C`, "wmic nic get NetConnectionID")
		command = exec.Command(`cmd`, `/C`, "netsh interface show interface")
	}

	output, err := command.Output()
	if err != nil {
		log.WithFields(log.Fields{
			"path":     command.Path,
			"argument": command.Args,
			"error":    err.Error()}).Error("Command produced error.  Returning.")
		return oldDNSServers
	}

	// only for windows
	// since the output of windows is special, we have to convert
	// Admin State    State          Type             Interface Name
	// -------------------------------------------------------------------------
	// Enabled        Disconnected   Dedicated        Ethernet 2
	// Enabled        Connected      Dedicated        Wi-Fi 2
	// To only care connected and remain only “Wi-Fi 2” in this case

	// Detect connected network interfaces for windows
	if runtime.GOOS == "windows" {
		var tmpOutput []byte
		networkInterfaces := strings.Split(string(output), "\n")
		for _, networkInterface := range networkInterfaces {
			strippedString := strings.ToLower(strings.Replace(networkInterface, "-", "", -1))

			//only for windows to check disconnected interface
			if strings.Contains(strippedString, "connected") {
				if strings.Contains(strippedString, "disconnected") {
					continue
				}
				tmp := strings.Split(networkInterface, "    ")
				tmp[5] = strings.Split(tmp[5], "\r")[0]
				tmpInter := []byte(tmp[5])
				tmpOutput = append(tmpOutput, tmpInter...)
				tmpOutput = append(tmpOutput, []byte("\n")...)
			} else {
				continue
			}
		}
		output = tmpOutput
	}

	networkInterfaces := strings.Split(strings.TrimSpace(string(output)), "\n")
	log.WithFields(log.Fields{
		"interface": networkInterfaces}).Info("Network interfaces found")

	// Only focus on wifi and ethernet
	interfaceKeywords := []string{"", ""}
	interfacesToChange := make([]string, len(networkInterfaces))
	if runtime.GOOS == "darwin" {
		// For mac
		interfaceKeywords[0] = "wifi"
		interfaceKeywords[1] = "ethernet"
	} else if runtime.GOOS == "linux" {
		// For linux, enable for now
		// keywords need to be adapted
		interfaceKeywords[0] = "wlp2s0"
		interfaceKeywords[1] = "enp2s0"
		// For linux, enable for now
	} else if runtime.GOOS == "windows" {
		// For windows
		interfaceKeywords[0] = "ethernet"
		interfaceKeywords[1] = "wifi" // Wi-Fi or wi-fi or wifi
		// interfaceKeywords[1] = "wifi 2"// Wi-Fi or wi-fi or wifi
		// interfaceKeywords[2] = "Ethernet"
		// interfaceKeywords[3] = "Wi-Fi"
	}

	// Traverse each interface to get DNS setting for each of them
	counter := 0
	for _, networkInterface := range networkInterfaces {
		log.WithFields(log.Fields{
			"interface": networkInterface,
		}).Debug("traversing interfaces")

		for _, keyword := range interfaceKeywords {
			strippedString := strings.ToLower(strings.Replace(networkInterface, "-", "", -1))

			if strings.Contains(strippedString, keyword) {
				interfacesToChange[counter] = networkInterface
				counter++
			}
		}
	}

	log.WithFields(log.Fields{
		"interface": interfacesToChange}).Debug("These network interfaces will have DNS settings changed")

	for _, networkInterface := range interfacesToChange {
		if networkInterface == "" {
			continue
		}
		command := exec.Command("")
		output := ""
		if runtime.GOOS == "darwin" {
			// For mac, disable for now
			command = exec.Command("networksetup", "-getdnsservers", networkInterface)
			tmp, err := command.Output()
			output = string(tmp)
			if err != nil {
				log.Fatal(err)
			}
		} else if runtime.GOOS == "linux" {
			// For linux, enable for Now
			output = "127.0.0.1"
		} else if runtime.GOOS == "windows" {
			// For windows enable for now
			output = "127.0.0.1"
		}

		var oldServers []string
		if strings.Contains(strings.ToLower(string(output)), "there aren't any dns servers") {
			log.WithFields(log.Fields{
				"interface": networkInterface,
			}).Debug("No DNS servers configured")
			oldServers = []string{"empty"}
		} else {
			oldServers = strings.Split(string(output), "\n")
		}

		oldDNSServers[networkInterface] = make([]string, len(oldServers))
		i := 0
		for _, oldServer := range oldServers {
			oldServer = strings.Replace(oldServer, " ", "", -1)
			if oldServer == "127.0.0.1" || oldServer == "LOCALHOST" || oldServer == "" {
				// don't add localhost to list of oldServers
				log.WithFields(log.Fields{
					"old server": oldServer}).Debug("Skipping oldServer")
				continue
			}
			log.WithFields(log.Fields{
				"old server": oldServer,
				"interface":  networkInterface}).Debug("Saving DNS server for interface.")
			oldDNSServers[networkInterface][i] = oldServer
			i++
		}

		// slice off empty strings
		oldDNSServers[networkInterface] = oldDNSServers[networkInterface][:i]

		// if all else fails, at least save "empty"
		if len(oldDNSServers[networkInterface]) == 0 {
			log.WithFields(log.Fields{
				"interface": networkInterface}).Info("No DNS servers to save.  Saving {'empty'}")
			oldDNSServers[networkInterface] = []string{"empty"}
		}
	}

	log.WithFields(log.Fields{
		"old DNS server": oldDNSServers}).Info("old DNS server saved")
	fmt.Printf("oldDNSServers: %v Length [%d]\n", oldDNSServers, len(oldDNSServers))

	return oldDNSServers
}

// Set DNS servers for wifi and ethernet interfaces
func (program *Program) setDNSServer(primaryDNS string, backupDNSList []string, networkInterfaces []reflect.Value) {
	for _, networkInterface := range networkInterfaces {
		log.WithFields(log.Fields{
			"interface":   networkInterface,
			"primary DNS": primaryDNS,
			"backup DNS":  backupDNSList}).Info("changing DNS server for interface to primary and backup")

		// "..." flattens the list to use each element as separate argument
		if runtime.GOOS == "darwin" {
			//for mac
			argumentList := append([]string{"-setdnsservers", networkInterface.String(), primaryDNS}, backupDNSList...)
			command := exec.Command("networksetup", argumentList...)

			output, err := command.Output()
			if err != nil {
				log.Fatal(err)
			}

			log.Println(output)

		} else if runtime.GOOS == "linux" {
			b, err := ioutil.ReadFile("/etc/resolv.conf") // just pass the file name
			if err != nil {
				fmt.Print(err)
			}
			str := string(b)

			var newData = "nameserver 127.0.0.1\n#\n" + str

			d1 := []byte(newData)
			err1 := ioutil.WriteFile("/etc/resolv.conf", d1, 0644)
			if err1 != nil {
				fmt.Println(err)
			}
		} else if runtime.GOOS == "windows" {
			command := exec.Command("cmd", "/C", fmt.Sprintf(" netsh interface ipv4 add dnsservers %q address=127.0.0.1 index=1", networkInterface.String()))
			output, err := command.Output()
			if err != nil {
				log.Fatal(err)
				return
			}
			log.Println(output)
		}
	}
}

// Restore the DNS settings to previously saved DNS resolvers
func (program *Program) restoreOldDNSServers(oldDNSServers map[string][]string) (err error) {
	err = nil

	if runtime.GOOS == "darwin" {
		for networkInterface, dnsServerList := range oldDNSServers {
			fmt.Printf("dnsServerList [%v] length [%d]\n", dnsServerList, len(dnsServerList))
			argumentList := append([]string{"-setdnsservers", networkInterface}, dnsServerList...)

			fmt.Printf("Running networksetup %v\n", argumentList)
			output, thisError := utils.RunCommand("networksetup", argumentList...)
			if thisError != nil {
				fmt.Printf("output [%s] error [%s]\n", output, thisError.Error())
				err = thisError
			}
		}
	} else if runtime.GOOS == "linux" {
		b, err := ioutil.ReadFile("/etc/resolv.conf") // just pass the file name
		if err != nil {
			fmt.Print(err)
		}
		str := string(b) // convert content to a 'string'

		var newData = ""

		var start = false
		for _, i := range str {
			if start {
				newData += string(i)
			} else if i == '\n' {
				start = true
			}
		}

		d1 := []byte(newData)
		err1 := ioutil.WriteFile("/etc/resolv.conf", d1, 0644)
		if err1 != nil {
			fmt.Println(err)
		}
	} else if runtime.GOOS == "windows" {
		for networkInterface := range oldDNSServers {
			fmt.Println("enter windows restoreDNS")
			command := exec.Command("cmd", "/C", fmt.Sprintf(" netsh interface ipv4 set dnsservers %q dhcp", networkInterface))
			output, err1 := command.Output()
			if err1 != nil {
				log.Fatal(err)
				return err1
			}
			log.Println(output)
		}
	}

	log.Info("DNS setting restored.")
	return err
}

// start the DNS proxy
func (program *Program) startDNSServer(dnsServer *dns.Server) {
	err := dnsServer.ListenAndServe()
	if err != nil {
		log.WithFields(log.Fields{
			"DNS server selected": dnsServer.Net,
			"server address":      dnsServer.Addr,
			"error":               err}).Fatal("Failed to start listener on server")
	}
}

// CleanNamehelp clean up the program
func CleanNamehelp() {
	configFilename := getAbsolutePath("config.json")
	os.Remove(configFilename)
}

// Takes relative path to executable
// Returns the absolute path of the executable
func getAbsolutePath(pathRelativeToExecutable string) string {
	executable, err := osext.Executable()
	if err != nil {
		panic(err)
	}

	path := filepath.Join(path.Dir(executable), pathRelativeToExecutable)
	return path
}

var config service.Config = service.Config{
	Name:        appConfig.Name,
	DisplayName: appConfig.DisplayName,
	Description: appConfig.Description,
}

// normally the program should be started with service flag
func main() {
	// NOTE: before executing main(), namehelpProgram is created at the top of this file.

	// do command-line flag parsing
	serviceFlag := flag.String("service", "", "Control the system service")
	cleanFlag := flag.Bool("cleanup", false, "Clean namehelp config files")
	flag.Parse()

	log.Info("Instantiating service")
	namehelpService, err := service.New(namehelpProgram, &config)
	if err != nil {
		log.WithFields(log.Fields{
			"error": err}).Fatal("Failed to instantiate service")
	}
	log.Info("Namehelp service instantiated")

	// if service flag specified
	// execute the specific operation
	if len(*serviceFlag) != 0 {
		log.WithFields(log.Fields{
			"flag": *serviceFlag}).Info("Calling service.Control with flag")
		err := service.Control(namehelpService, *serviceFlag)
		log.Info("Returned from service.Control()")

		if err != nil {
			log.WithFields(log.Fields{
				"action": service.ControlAction,
				"error":  err.Error()}).Error("Valid actions with Error")
			log.Fatal(err)
		}
		log.Debug("Calling return")
		return
	}
	if *cleanFlag {
		CleanNamehelp()
		return
	}

	// running without service flag
	// try install the program first
	*serviceFlag = "install"
	err = service.Control(namehelpService, *serviceFlag)
	if err != nil {
		log.WithFields(log.Fields{
			"error": err}).Error("Namehelp has already been installed")
	}

	// directly executing the program
	err = namehelpService.Run()
	if err != nil {
		log.WithFields(log.Fields{
			"error": err}).Error("Problem running service")
	}

	// wait for signal from run until shut down completed
	<-namehelpProgram.shutdownChan
	dir, err := os.Getwd()
	e := os.Remove(dir + "/dat")
	if e != nil {
		log.Fatal(e)
	}

	log.Info("Main exiting...")
}
