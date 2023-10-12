package utils

import (
	"encoding/json"
	"errors"
	"fmt"
	"github.com/bobesa/go-domain-util/domainutil"
	"io/ioutil"
	"math/rand"
	"net/http"
	"os"
	"os/exec"
	"path"
	"path/filepath"
	"strings"
	"time"

	"github.com/kardianos/osext"
	"github.com/miekg/dns"
	log "github.com/sirupsen/logrus"
	"github.com/zyalm/odoh-client-go/commands"
)

const (
	NotIPQuery = 0
	IP4Query   = 4
	IP6Query   = 6
	// LOCALHOST is the ip address for localhost
	LOCALHOST = "127.0.0.1"
	// PORT is the port for localhost
	PORT = 53 // DNS port
)

type IPInfoResponse struct {
	Ip       string `json:"ip"`
	Hostname string `json:"hostname"`
	Country  string `json:"country_iso"`
}

func UnionStringLists(list1 []string, list2 []string) []string {
	var baseList []string
	var searchList []string

	if len(list1) < len(list2) {
		baseList = list1
		searchList = list2
	} else {
		baseList = list2
		searchList = list1
	}

	for _, thisString := range baseList {
		_, found := ContainsString(searchList, thisString)
		if found {
			continue
		}
		searchList = append(searchList, thisString)
	}

	return searchList
}

func AddPortToEach(list []string, port string) (resultList []string) {
	for _, item := range list {
		if i := strings.IndexByte(item, '#'); i > 0 {
			item = item[:i] + ":" + item[i+1:]
		} else {
			item = item + ":" + port
		}
		resultList = append(resultList, item)
	}
	return resultList
}

// flushes system's local DNS on OSX 10.10.4+ (https://coolestguidesontheplanet.com/clear-the-local-dns-cache-in-osx/)
// TODO write other functions for other platforms
func FlushLocalDnsCache() {
	var output string
	var err error

	name := "dscacheutil"
	arguments := []string{"-flushcache"}
	output, err = RunCommand(name, arguments...)
	if err != nil {
		log.WithFields(log.Fields{
			"DNS cache": name,
			"output":    output,
			"error":     err.Error()}).Error("Error flushing DNS cache")
	}
	name = "killall"
	arguments = []string{"-HUP", "mDNSResponder"}
	output, err = RunCommand(name, arguments...)
	if err != nil {
		log.WithFields(log.Fields{
			"DNS cache": name,
			"output":    output,
			"error":     err.Error()}).Error("Error flushing DNS cache")
	}
}

func PathExists(path string) bool {
	_, err := os.Stat(path)
	if err == nil {
		return true
	}
	return false
}

func GetDirectoryOfExecutable() string {
	executable, err := osext.Executable()
	if err != nil {
		panic(err)
	}

	executableDirectory := path.Dir(executable)

	return executableDirectory
}

func RunCommand(name string, arguments ...string) (combinedOutputString string, err error) {
	log.WithFields(log.Fields{"command": name, "args": arguments}).Debug("Running command")
	command := exec.Command(name, arguments...)
	combinedOutput, err := command.CombinedOutput()
	combinedOutputString = string(combinedOutput)
	log.WithFields(log.Fields{
		"command":  name,
		"argument": arguments,
		"output":   combinedOutput}).Debug("Executing command")
	if err != nil {
		log.WithFields(log.Fields{
			"command":  name,
			"argument": arguments,
			"output":   combinedOutput,
			"error":    err.Error()}).Debug("Command failed")
		return combinedOutputString, err
	}

	return combinedOutputString, nil
}

func IsNamehelp(url string) bool {
	url = strings.ToLower(url)

	if url == "namehelp" || url == "direct resolution" {
		return true
	}

	if IsLocalhost(url) {
		return true
	}

	return false
}

func IsLocalhost(url string) bool {
	if url == "localhost" {
		return true
	}
	// TODO technically should this condition check anything between 127.0.0.1 and 127.255.255.255?
	if url == "127.0.0.1" {
		return true
	}
	if url == "::1" {
		return true
	}

	return false
}

// CombineStringMaps combines two maps into one and returns the resulting map.
// The smaller map is copied into the larger map, which is then returned.
// CAUTION: If the two maps share keys, the values in the smaller map will overwrite
// the corresponding values in the larger map.
func CombineStringMaps(map1 map[string]string, map2 map[string]string) map[string]string {
	if len(map1) <= len(map2) {
		for key, value := range map1 {
			// check if key already exists in map
			_, ok := map2[key]
			if ok {
				log.WithFields(log.Fields{
					"key":       key,
					"value":     value,
					"old value": map2[key]}).Error("Writing map2[key]=value but map2 already contains key with old value.  Overwriting.")
			}

			map2[key] = value
		}
		return map2
	} else {
		for key, value := range map2 {
			// check if key already exists in map
			_, ok := map1[key]
			if ok {
				log.WithFields(log.Fields{
					"key":       key,
					"value":     value,
					"old value": map1[key]}).Error("Writing map1[key]=value but map1 already contains key with old value.  Overwriting.")
			}

			map1[key] = value
		}
		return map1
	}
}

func IsProcessRunning(processName string) bool {
	command := exec.Command("pgrep", processName)
	output, err := command.Output()
	if err != nil {
		log.WithFields(log.Fields{
			"process name": processName,
			"error":        err.Error()}).Error("Error pgrepping for process")
		return false
	}

	if len(output) > 0 {
		return true
	}

	return false
}

// check whether arrayOfStrings contains the searchString
// If found, returns the index of the search string and true
// Otherwise, returns -1 and false
func ContainsString(arrayOfStrings []string, searchString string) (index int, success bool) {
	if len(arrayOfStrings) > 100 {
		log.WithFields(log.Fields{
			"search string": searchString,
			"size":          len(arrayOfStrings)}).Warn("Using linear search for string on large array.  Consider using more efficient method.")
	}

	for index, thisString := range arrayOfStrings {
		if thisString == searchString {
			return index, true
		}
	}

	return -1, false
}

func BuildDnsQuery(name string, qType uint16, msgId uint16, rescursionDesired bool) (queryMessage *dns.Msg) {
	queryMessage = new(dns.Msg)

	if name[len(name)-1:] != "." {
		name = name + "."
	}

	queryMessage.MsgHdr = dns.MsgHdr{
		Id:                 msgId, // allows client to match responses with requests?
		Response:           false,
		Opcode:             dns.OpcodeQuery,
		Authoritative:      false, // not valid on a query
		Truncated:          false,
		RecursionDesired:   rescursionDesired,
		RecursionAvailable: false, // not valid on a query
		Zero:               false, // must be zero--not sure how the dns package handles this since it's a bool
		AuthenticatedData:  false, // not sure what this is
		CheckingDisabled:   false, // not sure what this is
		Rcode:              0,     // not valid on a query
	}

	queryMessage.Question = []dns.Question{
		{
			Name:   name,
			Qtype:  qType,
			Qclass: dns.ClassINET,
		},
	}

	return queryMessage
}

// Returns the first IP Address (if any) from the answer section
func GetIpAddressFromAnswerMessage(answerMessage *dns.Msg) (ipAddress string, err error) {
	if answerMessage == nil {
		return "", errors.New("answerMessage was nil.")
	}

	if answerMessage.MsgHdr.Rcode != dns.RcodeSuccess {
		err = errors.New(dns.RcodeToString[answerMessage.MsgHdr.Rcode])
		return "", err
	}

	for _, answerRR := range answerMessage.Answer {
		if answerRR.Header().Rrtype == dns.TypeA || answerRR.Header().Rrtype == dns.TypeAAAA {
			return dns.Field(answerRR, 1), nil
		}
	}

	err = errors.New("No IP Address in answer message.")
	return "", err
}

// UnFullyQualifyDomainName returns the ending dot
func UnFullyQualifyDomainName(s string) string {
	if dns.IsFqdn(s) {
		return s[:len(s)-1]
	}
	return s
}

func GetPublicIPInfo() (*IPInfoResponse, error) {
	var ipInfo *IPInfoResponse
	// read ip info from file, if no file exist, query and write to the file
	fileName := "ipInfo.json"
	filePath := filepath.Join(GetSrcDir(), "analysis", fileName)

	file, err := os.Open(filePath)
	if err != nil {
		log.Info("No Ip Info file exists yet")
		ipInfo, _ = QueryPublicIpInfo()
		return ipInfo, nil
	}
	defer file.Close()

	// Read the file content
	fileContent, err := ioutil.ReadAll(file)
	if err != nil {
		log.Debug("Error reading file:", err)
		return nil, nil
	}

	if err := json.Unmarshal(fileContent, &ipInfo); err != nil {
		return nil, err
	}

	return ipInfo, nil
}

func QueryPublicIpInfo() (*IPInfoResponse, error) {
	url := "https://ipconfig.io/json"
	resp, err := http.Get(url)
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		return nil, fmt.Errorf("HTTP request failed with status code: %d", resp.StatusCode)
	}

	body, err := ioutil.ReadAll(resp.Body)
	if err != nil {
		return nil, err
	}

	var ipInfo *IPInfoResponse
	if err := json.Unmarshal(body, &ipInfo); err != nil {
		return nil, err
	}

	fileName := "ipInfo.json"
	filePath := filepath.Join(GetSrcDir(), "analysis", fileName)

	// Write the JSON-encoded data to a file
	err = ioutil.WriteFile(filePath, body, 0644)
	if err != nil {
		log.Info("Error writing JSON to file:", err)
		return nil, nil
	}

	return ipInfo, nil
}

func GetSrcDir() string {
	exe, err := osext.Executable()
	if err != nil {
		panic(err)
	}
	exeDir := path.Dir(exe)
	return path.Dir(path.Dir(exeDir))
}

type JSONData struct {
	Data []string `json:"data"`
}

func ReadFromResolverConfig(ipAddr string, country string) map[string][]string {
	fileName := "config.json"
	filePath := filepath.Join(GetSrcDir(), "analysis", "measurements", country, fileName)

	file, err := os.Open(filePath)
	if err != nil {
		log.Info("No best resolver config exists yet")
		return nil
	}
	defer file.Close()

	// Read the file content
	fileContent, err := ioutil.ReadAll(file)
	if err != nil {
		log.Debug("Error reading file:", err)
		return nil
	}

	var config map[string]map[string][]string

	if err := json.Unmarshal(fileContent, &config); err != nil {
		log.Debug("Error unmarshaling JSON:", err)
		return nil
	}

	resolvers, ok := config[ipAddr]
	if !ok {
		log.Debug("resolvers config for this ip doesn't exist")
		return nil
	}

	return resolvers
}

func HasOverlap(slice1, slice2 []string) bool {
	elementsMap := make(map[string]bool)

	for _, element := range slice1 {
		elementsMap[element] = true
	}

	for _, element := range slice2 {
		if elementsMap[element] {
			return true
		}
	}

	return false
}

func RandomChoice(slice []string) string {
	// Seed the random number generator with the current time
	rand.Seed(time.Now().UnixNano())

	// Check if the slice is empty
	if len(slice) == 0 {
		return ""
	}

	// Generate a random index within the range of the slice
	randomIndex := rand.Intn(len(slice))

	// Return the randomly chosen element
	return slice[randomIndex]
}

func GetObliviousDnsRequest() {
	domain := "shop.goodgames.com.au"
	dnsTypeString := "AAAA"
	targetName := "odoh.cloudflare-dns.com"

	domain = dns.Fqdn(domain)

	msg, err := commands.ObliviousDnsRequest(domain, dnsTypeString, targetName, "", "", "")
	if err != nil {
		log.Error("commands.ObliviousDnsRequest failed.", domain, dnsTypeString, targetName)
		return
	}
	log.Info("msg is: ", msg.Answer)
}

func GetUniqueWebsites() []string {
	fileName := "unique_websites.json"
	filePath := filepath.Join(GetSrcDir(), "data", fileName)

	file, err := os.Open(filePath)
	if err != nil {
		log.Info("User hasn't defined unique websites yet.")
		return []string{}
	}
	defer file.Close()

	// Read the file content
	fileContent, err := ioutil.ReadAll(file)
	if err != nil {
		log.Debug("Error reading file:", err)
		return []string{}
	}

	var uniqueWebsites []string
	if err := json.Unmarshal(fileContent, &uniqueWebsites); err != nil {
		log.Debug("Error unmarshaling JSON:", err)
		return []string{}
	}
	return uniqueWebsites
}

func CheckUniqueWebsites(website string) bool {
	uniqueWebsites := GetUniqueWebsites()
	for _, site := range uniqueWebsites {
		if domainutil.DomainPrefix(website) == domainutil.DomainPrefix(site) {
			log.Info("unique domain name is: ", site)
			return true
		}
	}
	return false
}
