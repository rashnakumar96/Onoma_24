//go:generate go get -u github.com/alexthemonk/DoH_Proxy/
//go:generate go get -u github.com/kardianos/osext/
//go:generate go get -u github.com/kardianos/service/
//go:generate go get -u github.com/miekg/dns/
//go:generate go get -u github.com/sirupsen/logrus/
//go:generate go get -u go.mongodb.org/mongo-driver/mongo
//go:generate go get -u gopkg.in/natefinch/lumberjack.v2

package main

import (
	"flag"
	"fmt"
	"io"
	"io/ioutil"
	"math/rand"
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
	"encoding/json"
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
	program.initializeDNSServers()

	// start DNS servers for UDP and TCP requests
	program.initializeReporter()
	program.initializeDNSServers()

	go program.startDNSServer(program.udpServer)
	go program.startDNSServer(program.tcpServer)
	// this go func does the testing as soon as SubRosa is started
	// TODO: change this to per-trigger base
	handler.DoHEnabled = true
	go program.doMeasurement()
	return nil
}

func (program *Program) doMeasurement() error {
	//handler.Proxy is true when testing DoHProxy
	//handler.Racing is true when testing racing in SubRosa
	//handler.PrivacyEnabled is true when testing SubRosa and DoHProxy with privacy enabled, and all same 2lds go to the same resolver
	//EnableDirectResolution allows SubRosa to do DR, we disable with other approaches

	//for testing individual resolvers it's true, for testing DoHProxy and SubRosa it's false
	handler.Experiment = true
	//for testing DoH resolvers
	handler.DoHEnabled = true

	dict1 := make(map[string]map[string]map[string]interface{})
	// dict2:=make(map[string]map[string]interface{})

	//resolver mapping dict for privacy setting
	handler.ResolverMapping = make(map[string][]string)

	var err error
	iterations := 3
	dir, err := os.Getwd()
	testingDir := "measurements"

	//stores all measurements
	outPath := filepath.Join(dir, testingDir)
	if _, err := os.Stat(outPath); os.IsNotExist(err) {
		os.Mkdir(outPath, 0755)
	}
	if err != nil {
		log.Info("Error getting current working directory")
	}

	//stores DNSLatency results
	// outPath= filepath.Join(dir, testingDir+"/dnsLatencies")
	// if _, err := os.Stat(outPath); os.IsNotExist(err) {
	// 	os.Mkdir(outPath, 0755)
	// }
	// if err!=nil{
	// 	log.Info("Error getting current working directory")
	// }

	dnsLatencyFile := filepath.Join(dir, testingDir, "AlexaUniqueResources.txt")

	handler.Proxy = false
	program.dnsQueryHandler.DisableDirectResolution()
	handler.PrivacyEnabled = false
	handler.Racing = false

	utils.FlushLocalDnsCache()
	handler.DoHServersToTest = []string{"Google"}
	dict1, err = program.dnsQueryHandler.MeasureDnsLatencies(0, dnsLatencyFile, 0, handler.DoHEnabled, handler.Experiment, iterations, dict1, "GoogleDoH")
	file, _ := json.MarshalIndent(dict1, "", " ")
	_ = ioutil.WriteFile(filepath.Join(dir, testingDir, "dnsLatencies.json"), file, 0644)

	//this for loop ensures that DoHServersToTest is GoogleDoH till we collect all measurements with this resolver
	//and file dir+testingDir+"/lighthouseTTBGoogleDoH.json" is made in the directory
	utils.FlushLocalDnsCache()
	for {
		if _, err := os.Stat(filepath.Join(dir, testingDir, "lighthouseTTBGoogleDoH.json")); os.IsNotExist(err) {
			continue
		} else {
			log.Info("FileFound")
			break
		}
	}
	log.Info("Done Testing Google DoH")

	utils.FlushLocalDnsCache()
	handler.DoHServersToTest = []string{"Cloudflare"}
	dict1, err = program.dnsQueryHandler.MeasureDnsLatencies(0, dnsLatencyFile, 0, handler.DoHEnabled, handler.Experiment, iterations, dict1, "CloudflareDoH")
	file, _ = json.MarshalIndent(dict1, "", " ")
	_ = ioutil.WriteFile(filepath.Join(dir, testingDir, "dnsLatencies.json"), file, 0644)

	//this for loop ensures that DoHServersToTest is CloudflareDoH till we collect all measurements with this resolver
	//and file dir+testingDir+"/lighthouseTTBCloudflareDoH.json" is made in the directory
	utils.FlushLocalDnsCache()
	for {
		if _, err := os.Stat(filepath.Join(dir, testingDir, "lighthouseTTBCloudflareDoH.json")); os.IsNotExist(err) {
			continue
		} else {
			break
		}
	}
	log.Info("Done Testing Cloudflare DoH")

	utils.FlushLocalDnsCache()
	handler.DoHServersToTest = []string{"Quad9"}
	dict1, err = program.dnsQueryHandler.MeasureDnsLatencies(0, dnsLatencyFile, 0, handler.DoHEnabled, handler.Experiment, iterations, dict1, "Quad9DoH")
	file, _ = json.MarshalIndent(dict1, "", " ")
	_ = ioutil.WriteFile(filepath.Join(dir, testingDir, "dnsLatencies.json"), file, 0644)

	//this for loop ensures that DoHServersToTest is Quad9DoH till we collect all measurements with this resolver
	//and file dir+testingDir+"/lighthouseTTBQuad9DoH.json" is made in the directory
	utils.FlushLocalDnsCache()
	for {
		if _, err := os.Stat(filepath.Join(dir, testingDir, "lighthouseTTBQuad9DoH.json")); os.IsNotExist(err) {
			continue
		} else {
			break
		}
	}
	log.Info("Done Testing Quad9 DoH")

	// utils.FlushLocalDnsCache()
	// handler.DoHEnabled=false
	// handler.DNSServersToTest=[]string{"8.8.8.8"}
	// time.Sleep(60*2)
	// dict1, err = program.dnsQueryHandler.MeasureDnsLatencies(0,dnsLatencyFile,0,handler.DoHEnabled,handler.Experiment,iterations,dict1,"GoogleDNS")
	// if err != nil {
	// 	log.Info("Error measuring DNS latencies for [%s].  Error: [%s]", "alexaSites", err.Error())
	// }
	// program.dnsQueryHandler.RunWebPerformanceTest(dir+"/AlexaUniqueResources.txt",handler.DoHEnabled,handler.Experiment,iterations,outPath,"GoogleDNS")
	// program.dnsQueryHandler.PingServers(handler.DoHEnabled,handler.Experiment,iterations,dict2)

	// utils.FlushLocalDnsCache()
	// handler.DNSServersToTest=[]string{"1.1.1.1"}
	// time.Sleep(60*2)
	// dict1, err = program.dnsQueryHandler.MeasureDnsLatencies(0,dnsLatencyFile,0,handler.DoHEnabled,handler.Experiment,iterations,dict1,"CloudflareDNS")
	// if err != nil {
	// 	log.Info("Error measuring DNS latencies for [%s].  Error: [%s]", "alexaSites", err.Error())
	// }
	// program.dnsQueryHandler.RunWebPerformanceTest(dir+"/AlexaUniqueResources.txt",handler.DoHEnabled,handler.Experiment,iterations,outPath,"CloudflareDNS")
	// program.dnsQueryHandler.PingServers(handler.DoHEnabled,handler.Experiment,iterations,dict2)

	// utils.FlushLocalDnsCache()
	// handler.DNSServersToTest=[]string{"9.9.9.9"}
	// time.Sleep(60*2)
	// dict1, err = program.dnsQueryHandler.MeasureDnsLatencies(0,dnsLatencyFile,0,handler.DoHEnabled,handler.Experiment,iterations,dict1,"Quad9DNS")
	// if err != nil {
	// 	log.Info("Error measuring DNS latencies for [%s].  Error: [%s]", "alexaSites", err.Error())
	// }
	// program.dnsQueryHandler.RunWebPerformanceTest(dir+"/AlexaUniqueResources.txt",handler.DoHEnabled,handler.Experiment,iterations,outPath,"Quad9DNS")
	// program.dnsQueryHandler.PingServers(handler.DoHEnabled,handler.Experiment,iterations,dict2)

	handler.DoHEnabled = true
	handler.Experiment = false

	//testing DoHProxy with Privacy Enabled
	handler.PrivacyEnabled = true
	handler.Proxy = true
	utils.FlushLocalDnsCache()
	handler.DoHServersToTest = []string{"127.0.0.1"}
	dict1, err = program.dnsQueryHandler.MeasureDnsLatencies(0, dnsLatencyFile, 0, handler.DoHEnabled, handler.Experiment, iterations, dict1, "DoHProxy")
	file, _ = json.MarshalIndent(dict1, "", " ")
	_ = ioutil.WriteFile(filepath.Join(dir, testingDir, "dnsLatencies.json"), file, 0644)

	//these for loops ensure that DoHServersToTest is DoHProxy with Privacy enabled (but new resolver mapping dict btw each run)
	// till we collect all measurements with this resolver
	//and file dir+testingDir+"/lighthouseTTBDoHProxy.json" is made in the directory
	utils.FlushLocalDnsCache()
	for {
		if _, err := os.Stat(filepath.Join(dir, testingDir, "lighthouseTTBDoHProxy0.json")); os.IsNotExist(err) {
			continue
		} else {
			break
		}
	}

	handler.ResolverMapping = make(map[string][]string)
	for {
		if _, err := os.Stat(filepath.Join(dir, testingDir, "lighthouseTTBDoHProxy1.json")); os.IsNotExist(err) {
			continue
		} else {
			break
		}
	}
	handler.ResolverMapping = make(map[string][]string)
	for {
		if _, err := os.Stat(filepath.Join(dir, testingDir, "lighthouseTTBDoHProxy.json")); os.IsNotExist(err) {
			continue
		} else {
			break
		}
	}
	log.Info("Done Testing DoHProxy")

	//testing DoHProxy with No Privacy Enabled(DoHProxyNP)
	handler.PrivacyEnabled = false
	handler.Racing = false
	utils.FlushLocalDnsCache()
	handler.DoHServersToTest = []string{"127.0.0.1"}
	dict1, err = program.dnsQueryHandler.MeasureDnsLatencies(0, dnsLatencyFile, 0, handler.DoHEnabled, handler.Experiment, iterations, dict1, "DoHProxyNP")
	file, _ = json.MarshalIndent(dict1, "", " ")
	_ = ioutil.WriteFile(filepath.Join(dir, testingDir, "dnsLatencies.json"), file, 0644)

	//this for loop ensures that DoHServersToTest is DoHProxy with No Privacy Enabled, till we collect all measurements with this resolver
	//and file dir+testingDir+"/lighthouseTTBDoHProxyNP.json" is made in the directory
	utils.FlushLocalDnsCache()
	for {
		if _, err := os.Stat(filepath.Join(dir, testingDir, "lighthouseTTBDoHProxyNP.json")); os.IsNotExist(err) {
			continue
		} else {
			break
		}
	}
	log.Info("Done Testing DoHProxyNP")

	//testing SubRosa with Privacy Enabled and Racing
	handler.PrivacyEnabled = true
	handler.Racing = true
	utils.FlushLocalDnsCache()
	program.dnsQueryHandler.EnableDirectResolution()
	handler.Proxy = false
	handler.DoHServersToTest = []string{"127.0.0.1"}
	dict1, err = program.dnsQueryHandler.MeasureDnsLatencies(0, dnsLatencyFile, 0, handler.DoHEnabled, handler.Experiment, iterations, dict1, "SubRosa")
	file, _ = json.MarshalIndent(dict1, "", " ")
	_ = ioutil.WriteFile(filepath.Join(dir, testingDir, "dnsLatencies.json"), file, 0644)

	//these for loops ensure that DoHServersToTest is SubRosa with Privacy enabled & Racing (but new resolver mapping dict btw each run)
	// till we collect all measurements with this resolver
	//and file dir+testingDir+"/lighthouseTTBSubRosa.json" is made in the directory
	utils.FlushLocalDnsCache()
	for {
		if _, err := os.Stat(filepath.Join(dir, testingDir, "lighthouseTTBSubRosa0.json")); os.IsNotExist(err) {
			continue
		} else {
			break
		}
	}
	handler.ResolverMapping = make(map[string][]string)
	for {
		if _, err := os.Stat(filepath.Join(dir, testingDir, "lighthouseTTBSubRosa1.json")); os.IsNotExist(err) {
			continue
		} else {
			break
		}
	}
	handler.ResolverMapping = make(map[string][]string)
	for {
		if _, err := os.Stat(filepath.Join(dir, testingDir, "lighthouseTTBSubRosa.json")); os.IsNotExist(err) {
			continue
		} else {
			break
		}
	}
	log.Info("Done Testing SubRosa")

	//testing SubRosa with No Privacy Enabled,but Racing enabled(SubRosaNP)
	utils.FlushLocalDnsCache()
	handler.PrivacyEnabled = false
	handler.Racing = true
	program.dnsQueryHandler.EnableDirectResolution()
	handler.Proxy = false
	handler.DoHServersToTest = []string{"127.0.0.1"}
	dict1, err = program.dnsQueryHandler.MeasureDnsLatencies(0, dnsLatencyFile, 0, handler.DoHEnabled, handler.Experiment, iterations, dict1, "SubRosaNP")
	file, _ = json.MarshalIndent(dict1, "", " ")
	_ = ioutil.WriteFile(filepath.Join(dir, testingDir, "dnsLatencies.json"), file, 0644)

	//this for loop ensures that DoHServersToTest is SubRosa with No Privacy Enabled,but Racing enabled till we collect all measurements with this resolver
	//and file dir+testingDir+"/lighthouseTTBSubRosaNP.json" is made in the directory
	utils.FlushLocalDnsCache()
	for {
		if _, err := os.Stat(filepath.Join(dir, testingDir, "lighthouseTTBSubRosaNP.json")); os.IsNotExist(err) {
			continue
		} else {
			break
		}
	}
	log.Info("Done Testing SubRosaNP")

	//testing SubRosa with No Privacy Enabled and No Racing Enabled(SubRosaNPR)
	utils.FlushLocalDnsCache()
	handler.PrivacyEnabled = false
	handler.Racing = false
	program.dnsQueryHandler.EnableDirectResolution()
	handler.Proxy = false
	handler.DoHServersToTest = []string{"127.0.0.1"}
	dict1, err = program.dnsQueryHandler.MeasureDnsLatencies(0, dnsLatencyFile, 0, handler.DoHEnabled, handler.Experiment, iterations, dict1, "SubRosaNPR")
	file, _ = json.MarshalIndent(dict1, "", " ")
	_ = ioutil.WriteFile(filepath.Join(dir, testingDir, "dnsLatencies.json"), file, 0644)

	//this for loop ensures that DoHServersToTest is SubRosa with No Privacy Enabled,No Racing enabled till we collect all measurements with this resolver
	//and file dir+testingDir+"/lighthouseTTBSubRosaNPR.json" is made in the directory
	utils.FlushLocalDnsCache()
	for {
		if _, err := os.Stat(filepath.Join(dir, testingDir, "lighthouseTTBSubRosaNPR.json")); os.IsNotExist(err) {
			continue
		} else {
			break
		}
	}
	log.Info("Done Testing SubRosaNPR")

	// handler.DoHEnabled=false
	// handler.Experiment=true
	// utils.FlushLocalDnsCache()
	// handler.DNSServersToTest=[]string{"89.249.65.99"}
	// dict1, err = program.dnsQueryHandler.MeasureDnsLatencies(0,dnsLatencyFile,0,handler.DoHEnabled,handler.Experiment,iterations,dict1,"LocalResolver")
	// file,_:=json.MarshalIndent(dict1, "", " ")
	// _ = ioutil.WriteFile(dir+testingDir+"/dnsLatenciesL.json", file, 0644)

	// localDNSServers := network.DhcpGetLocalDNSServers()
	// localDNSServers=strings.Split(localDNSServers[0], ",")
	// // for _, localdnsServer := range localDNSServers {
	// localdnsServer:=localDNSServers[0]
	// log.WithFields(log.Fields{
	// "dnsServer": localdnsServer}).Info("Testing localDNSServer")
	// handler.DNSServersToTest=[]string{localdnsServer}
	// time.Sleep(60*2)
	// // dict1, err = program.dnsQueryHandler.MeasureDnsLatencies(0,dir+"/alexaSites.txt",0,handler.DoHEnabled,handler.Experiment,iterations,"LocalR")
	// if err != nil {
	// 	log.Info("Error measuring DNS latencies for [%s].  Error: [%s]", "alexaSites", err.Error())
	// }
	// program.dnsQueryHandler.RunWebPerformanceTest(dir+"/AlexaUniqueResources.txt",handler.DoHEnabled,handler.Experiment,iterations,outPath,"LocalR")
	// program.dnsQueryHandler.PingServers(handler.DoHEnabled,handler.Experiment,iterations,dict2)
	// }

	//finished testing, restore setting to run SubRosa
	// handler.DoHEnabled=true
	// handler.Experiment=false
	// program.dnsQueryHandler.EnableDirectResolution()

	// approachList:=[]string{"GoogleDoH","Quad9DoH","CloudflareDoH","SubRosa","DoHProxy"}
	// var dict3=make(map[string]map[string]map[string]interface{})

	// for _, approach := range approachList{
	// 	path:=outPath+"/"+approach+"/data"
	// 	files, err := ioutil.ReadDir(path)
	// 	if err != nil {
	// 	    log.Fatal(err)
	// 	}
	// 	dict3[approach]=make(map[string]map[string]interface{})
	// 	for _, f := range files {
	// 	    if (!strings.Contains(f.Name(), "browsertime.summary-total") && !strings.Contains(f.Name(), "browsertime.browser") && strings.Contains(f.Name(), ".json")){
	// 	    	fmt.Println(f.Name())
	// 	    	jsonFile:=path+"/"+f.Name()
	// 			plan, _ := ioutil.ReadFile(jsonFile)
	// 			var data map[string]interface{}
	// 			err = json.Unmarshal(plan, &data)
	// 	    	site:=strings.Split(strings.Split(f.Name(),"browsertime.summary-")[1],".json")[0]
	// 			dict3[approach][site]=make(map[string]interface{})
	// 			var err error
	// 			var found int

	// 	    	if (data["rumSpeedIndex"]!=err){
	// 				dict3[approach][site]["speedIndex"]=data["rumSpeedIndex"]
	// 	    	}else{
	// 	    		dict3[approach][site]["speedIndex"]=-1
	// 	    	}

	// 	    	found=0
	// 	    	for key, value := range data["pageTimings"].(map[string]interface{}) {
	// 				if key=="pageLoadTime"{
	// 					dict3[approach][site]["pageLoadTime"]=value
	// 					found=1
	// 				}
	// 			}
	// 			if found==0{
	// 				dict3[approach][site]["pageLoadTime"]=-1
	// 			}

	// 	    	found=0
	// 			for key, value := range data["navigationTiming"].(map[string]interface{}) {
	// 				if key=="domInteractive"{
	// 					dict3[approach][site]["domInteractive"]=value
	// 					found=1
	// 				}
	// 			}
	// 			if found==0{
	// 				dict3[approach][site]["domInteractive"]=-1

	// 			}

	// 	    	if (data["firstPaint"]!=err){
	// 				dict3[approach][site]["firstPaint"]=data["firstPaint"]
	// 	    	}else{
	// 	    		dict3[approach][site]["firstPaint"]=-1
	// 	    	}

	// 	    	found=0
	// 	    	for key, value := range data["timings"].(map[string]interface{}) {
	// 				if key=="largestContentfulPaint"{
	// 					dict3[approach][site]["largestContentfulPaint"]=value
	// 					found=1
	// 				}
	// 			}
	// 			if found==0{
	// 				dict3[approach][site]["largestContentfulPaint"]=-1
	// 			}
	// 	    }
	// 	}
	// }
	// push dict1, dict2 and dict3 to server
	// program.reporter.PushToMongoDB("SubRosa-Test", "dnsLatencies", dict1)
	// program.reporter.PushToMongoDB("SubRosa-Test", "PingServers.json", dict2)
	// program.reporter.PushToMongoDB("SubRosa-Test", "Sitespeed-Matrics", dict3)

	// file3,_:=json.MarshalIndent(dict3, "", " ")
	// _ = ioutil.WriteFile("sitespeedMetrics.json", file3, 0644)

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
	// -------------------------------------------------------------------------
	// Admin State    State          Type             Interface Name
	// -------------------------------------------------------------------------
	// Enabled        Disconnected   Dedicated        Ethernet 2
	// Enabled        Connected      Dedicated        Wi-Fi 2
	// To only care connected and remain only “Wi-Fi 2” in this case

	// Detect connected network interfaces for windows
	if runtime.GOOS == "windows" {
		var tmpOutput []byte
		networkInterfaces := strings.Split(string(output), "\n")
		// index 0 and 2 are blank new lines, index 1 are table headers, all actual interface starts at index 3
		for _, networkInterface := range networkInterfaces {
			strippedString := strings.ToLower(strings.Replace(networkInterface, "-", "", -1))

			// only for windows to check disconnected interface
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
			command := exec.Command("cmd", "/C", fmt.Sprintf(" netsh interface ipv6 add dnsservers %q address=127.0.0.1 index=1", networkInterface.String()))
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

	log.Info("Main exiting...")
}
