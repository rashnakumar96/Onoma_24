// Handles DNS queries by forwarding them to one or more resolvers
// based heavily upon github.com/kenshinx/godns/handler.go

package handler

import (
	"bufio"
	"bytes"
	"errors"
	"fmt"
	"namehelp/cache"
	"namehelp/hosts"
	"namehelp/network"
	"namehelp/resolver"
	"namehelp/settings"
	"namehelp/utils"
	"net"
	"net/url"
	"os"
	"os/exec"
	"strconv"
	"strings"
	"sync"
	"time"

	"github.com/miekg/dns"
	log "github.com/sirupsen/logrus"
)

// PublicDNSServers for DNS over UDP
var PublicDNSServers = []string{
	"8.8.8.8",        // Google
	"4.2.2.5",        // Verizon (Level 3)
	"208.67.222.222", // OpenDNS
	"75.75.75.75",    //Comcast
}
var DNSServersToTest []string
var DoHServersToTest []string
var ResolverMapping map[string][]string
var Experiment bool
var DoHEnabled bool
var Proxy bool
var PrivacyEnabled bool
var Racing bool
var Decentralized bool
var PDNSServers []string

// var TestingDir string

// DNSQueryHandlerSettings specifies settings for query handlers
type DNSQueryHandlerSettings struct {
	isEnabledDirectResolution bool
	isEnabledCache            bool
	isEnabledHostsFile        bool
	isEnabledCounter          bool
	// whether to count the lookup for the purposes of tracking user's top sites
	experimentMode   bool
	isEnabledDoH     bool
	isEnabledProxy   bool
	isEnabledPrivacy bool
	isEnabledRacing  bool
}

// PingResult stores the result for ping command
type PingResult struct {
	Command string
	Target  string
	Args    []string
	Stdout  string
	Stderr  string
}

// DNSQueryHandler is the object for DNS query handler
type DNSQueryHandler struct {
	resolver      *resolver.Resolver
	cache         cache.Cache
	negativeCache cache.Cache
	hosts         hosts.Hosts
	settings      DNSQueryHandlerSettings
	mutex         sync.Mutex
	// topSites      *topsites.TopSites
	doID int // for logging purposes (increment this every time do is called)
}

// NewHandler returns a new initialized handler
func NewHandler(oldDNSServers map[string][]string) *DNSQueryHandler {
	var (
		clientConfig    *dns.ClientConfig
		cacheConfig     settings.CacheSettings
		handlerResolver *resolver.Resolver
		handlerCache    cache.Cache
		negativeCache   cache.Cache
	)

	dnsQueryHandlerSettings := DNSQueryHandlerSettings{
		isEnabledDirectResolution: true,
		isEnabledCache:            true,
		isEnabledHostsFile:        true,
		isEnabledCounter:          true,
	}

	resolvConfig := settings.NamehelpSettings.ResolvConfig

	serversList := PublicDNSServers

	// TODO add user's local DNS server (and their manually configured DNS too?)

	serversList = addOriginalDNSServers(serversList, oldDNSServers)
	localDNSServers := network.DhcpGetLocalDNSServers()
	serversList = utils.UnionStringLists(serversList, localDNSServers)

	clientConfig = &dns.ClientConfig{
		Servers:  serversList,
		Search:   []string{},
		Port:     "53",
		Ndots:    1,  // number of dots in name to trigger absolute lookup
		Timeout:  5,  // seconds before giving up on packet
		Attempts: -1, // lost packets before giving up on server, not used in the package dns

	}

	clientConfig.Timeout = resolvConfig.Timeout

	handlerResolver = &resolver.Resolver{clientConfig}

	cacheConfig = settings.NamehelpSettings.Cache
	switch cacheConfig.Backend {
	case "memory":
		handlerCache = &cache.MemoryCache{
			Backend:  make(map[string]cache.Mesg, cacheConfig.Maxcount),
			Expire:   time.Duration(cacheConfig.Expire) * time.Second,
			Maxcount: cacheConfig.Maxcount,
		}
		negativeCache = &cache.MemoryCache{
			Backend:  make(map[string]cache.Mesg),
			Expire:   time.Duration(cacheConfig.Expire) * time.Second / 2,
			Maxcount: cacheConfig.Maxcount,
		}
	default:
		//logger.Error("Invalid cache backend %s", cacheConfig.Backend)
		panic("Invalid cache backend")
	}

	var handlerHosts hosts.Hosts
	if settings.NamehelpSettings.Hosts.Enable {
		handlerHosts = hosts.NewHosts(settings.NamehelpSettings.Hosts)
	}

	dnsQueryHandlerMutex := sync.Mutex{}

	// alexaListPath := "data/alexa-top-30000-domains.txt"
	// alexaListBytes, err := Asset(alexaListPath)
	// if err != nil {
	// 	log.WithFields(log.Fields{
	// 		"Asset": alexaListPath, "Error": err.Error()}).Error("Failed to go-bindata")
	// 	alexaListBytes = []byte{}
	// }

	// topSites := topsites.NewTopSites(alexaListBytes)

	dnsQueryHandler := DNSQueryHandler{
		resolver:      handlerResolver,
		cache:         handlerCache,
		negativeCache: negativeCache,
		hosts:         handlerHosts,
		settings:      dnsQueryHandlerSettings,
		mutex:         dnsQueryHandlerMutex,
		// topSites:      topSites,
		doID: 0,
	}
	if len(resolver.Client.Resolvers) == 0 {
		resolver.Client.AddUpstream("Google", "8.8.8.8/resolve", 443)
		resolver.Client.AddUpstream("Cloudflare", "1.1.1.1/dns-query", 443)
		resolver.Client.AddUpstream("Quad9", "9.9.9.9:5053/dns-query", 443)
		for _, pDNS := range PDNSServers {
			resolver.Client.AddUpstream(pDNS, pDNS, 53)
		}

		log.WithFields(log.Fields{
			"client.Resolvers": resolver.Client.Resolvers}).Info("These are the clientResolvers")

		// // resolver.Client.AddUpstream("Comcast", "75.75.75.75", 53)
		// resolver.Client.AddUpstream("Verizon", "4.2.2.5", 53)
		// resolver.Client.AddUpstream("Verisign", "64.6.64.6", 53)
		// localDNSServers := network.DhcpGetLocalDNSServers()
		// localDNSServers=strings.Split(localDNSServers[0], ",")
		// localdnsServer:=localDNSServers[0]
		// resolver.Client.AddUpstream("LocalR",localdnsServer, 53)
		// resolver.Client.AddUpstream("opendns","208.67.222.222", 53)
	}

	return &dnsQueryHandler
}

func addOriginalDNSServers(serversList []string, originalDNSServersMap map[string][]string) []string {
	for _, serversOnInterface := range originalDNSServersMap {
		// loop through interfaces
		for _, dnsServer := range serversOnInterface {
			// loop through list of servers for this interface
			_, alreadyInList := utils.ContainsString(serversList, dnsServer)
			if alreadyInList {
				continue
			}
			if dnsServer == "" || dnsServer == "empty" {
				continue
			}
			if utils.IsLocalhost(dnsServer) {
				continue
			}

			// add it to list
			serversList = append(serversList, dnsServer)

		}
	}

	return serversList
}

// EnableDirectResolution enables direct resolution
func (handler *DNSQueryHandler) EnableDirectResolution() {
	handler.settings.isEnabledDirectResolution = true
}

// DisableDirectResolution disables direct resolution
func (handler *DNSQueryHandler) DisableDirectResolution() {
	handler.settings.isEnabledDirectResolution = false
}

// EnableCache enables cache
func (handler *DNSQueryHandler) EnableCache() {
	handler.settings.isEnabledCache = true
}

// DisableCache disables cache
func (handler *DNSQueryHandler) DisableCache() {
	handler.settings.isEnabledCache = false
}

// EnableHostsFile enables hosts file
func (handler *DNSQueryHandler) EnableHostsFile() {
	handler.settings.isEnabledHostsFile = true
}

// DisableHostsFile disables hosts file
func (handler *DNSQueryHandler) DisableHostsFile() {
	handler.settings.isEnabledHostsFile = false
}

// EnableCounter enables counter
func (handler *DNSQueryHandler) EnableCounter() {
	handler.settings.isEnabledCounter = true
}

// DisableCounter disables counter
func (handler *DNSQueryHandler) DisableCounter() {
	handler.settings.isEnabledCounter = false
}

// SetIsEnabledDirectResolution sets preference for direct resolution
func (handler *DNSQueryHandler) SetIsEnabledDirectResolution(isEnabled bool) {
	handler.settings.isEnabledDirectResolution = isEnabled
}

// SetIsEnabledCache sets preference for cache
func (handler *DNSQueryHandler) SetIsEnabledCache(isEnabled bool) {
	handler.settings.isEnabledCache = isEnabled
}

// SetIsEnabledHostsFile sets preference for hosts file
func (handler *DNSQueryHandler) SetIsEnabledHostsFile(isEnabled bool) {
	handler.settings.isEnabledHostsFile = isEnabled
}

// SetIsEnabledCounter sets preference for counter
func (handler *DNSQueryHandler) SetIsEnabledCounter(isEnabled bool) {
	handler.settings.isEnabledCounter = isEnabled
}

// EnableExperiment enables direct resolution
func (handler *DNSQueryHandler) EnableExperiment() {
	handler.settings.experimentMode = true
}

// DisableExperiment disables direct resolution
func (handler *DNSQueryHandler) DisableExperiment() {
	handler.settings.experimentMode = false
}

// EnableDoH enables direct resolution
func (handler *DNSQueryHandler) EnableDoH() {
	handler.settings.isEnabledDoH = true
}

// DisableDoH disables direct resolution
func (handler *DNSQueryHandler) DisableDoH() {
	handler.settings.isEnabledDoH = false
}

// EnableProxy enables direct resolution
func (handler *DNSQueryHandler) EnableProxy() {
	handler.settings.isEnabledProxy = true
}

// DisableProxy disables direct resolution
func (handler *DNSQueryHandler) DisableProxy() {
	handler.settings.isEnabledProxy = false
}

// EnablePrivacy enables direct resolution
func (handler *DNSQueryHandler) EnablePrivacy() {
	handler.settings.isEnabledPrivacy = true
}

// DisablePrivacy disables direct resolution
func (handler *DNSQueryHandler) DisablePrivacy() {
	handler.settings.isEnabledPrivacy = false
}

// EnableRacing enables direct resolution
func (handler *DNSQueryHandler) EnableRacing() {
	handler.settings.isEnabledRacing = true
}

// DisableRacing disables direct resolution
func (handler *DNSQueryHandler) DisableRacing() {
	handler.settings.isEnabledRacing = false
}

// PerformDNSQuery performs a DNS Query using the following method:
// First check the hosts file (if enabled).  If the domain is not found, check the cache (if enabled).
// If still not found, do a lookup by forwarding the request to real DNS server(s).
// If the dnsServer argument is provided, we only query that specific server.  Otherwise we simultaneously query all
// the servers listed in DNSQueryHandler.Resolver.config.Servers and use the first response that comes back.
// Then, finally perform direct resolution (if enabled) on CNAME answers.
func (handler *DNSQueryHandler) PerformDNSQuery(Net string, dnsQueryMessage *dns.Msg, dnsServer net.IP,
	isEnabledDirectResolution bool, isEnabledHostsFile bool, isEnabledCache bool, isEnabledCounter bool) (answerMessage *dns.Msg, success bool) {

	var err error
	var dnsServersToQuery []string

	doID := handler.doID
	handler.doID++

	question := dnsQueryMessage.Question[0]

	if isEnabledCounter {
		// handler.topSites.Update(question.Name)
	}

	// TODO handle more than 1 question
	if len(dnsQueryMessage.Question) > 1 {
		log.WithFields(log.Fields{
			"id": doID, "total # of question": len(dnsQueryMessage.Question),
			"first question":  dnsQueryMessage.Question[0],
			"second question": dnsQueryMessage.Question[1]}).Info("DNS Query contains more than 1 question.")
	}

	if utils.IsNamehelp(dnsServer.String()) {
		dnsServersToQuery = handler.resolver.Config.Servers
	} else {
		dnsServersToQuery = []string{dnsServer.String()}
	}

	log.WithFields(log.Fields{
		"id": doID, "nameservers": dnsServersToQuery,
		"query": question.String()[1:]}).Debug("Doing lookup at nameservers")
	// clip the ';' from the start of the string

	var IPQuery int
	IPQuery = handler.whichIPVersion(question)

	// Query hosts file
	if settings.NamehelpSettings.Hosts.Enable && IPQuery > 0 && isEnabledHostsFile {
		if ips, ok := handler.hosts.Get(utils.UnFullyQualifyDomainName(question.Name), IPQuery); ok {
			answerMessage = new(dns.Msg)
			answerMessage.SetReply(dnsQueryMessage)

			switch IPQuery {
			case utils.IP4Query:
				rr_header := dns.RR_Header{
					Name:   question.Name,
					Rrtype: dns.TypeA,
					Class:  dns.ClassINET,
					Ttl:    settings.NamehelpSettings.Hosts.TTL,
				}
				for _, ip := range ips {
					a := &dns.A{Hdr: rr_header, A: ip}
					answerMessage.Answer = append(answerMessage.Answer, a)
				}
			case utils.IP6Query:
				rr_header := dns.RR_Header{
					Name:   question.Name,
					Rrtype: dns.TypeAAAA,
					Class:  dns.ClassINET,
					Ttl:    settings.NamehelpSettings.Hosts.TTL,
				}
				for _, ip := range ips {
					aaaa := &dns.AAAA{Hdr: rr_header, AAAA: ip}
					answerMessage.Answer = append(answerMessage.Answer, aaaa)
				}
			}

			log.WithFields(log.Fields{
				"id":       doID,
				"question": question.Name}).Debug("Questioned server found in hosts file")
			return answerMessage, true
		} else {
			log.WithFields(log.Fields{
				"id":       doID,
				"question": question.Name}).Debug("Questioned server not in hosts file")
		}
	}

	if isEnabledCache {
		// check cache
		cacheKey := cache.KeyGen(question)
		message, whichCache, isHit := handler.checkCache(question, cacheKey, IPQuery, doID)

		if isHit {

			// handle different types of hit, then return
			if whichCache == &handler.cache {
				// positive cache
				// we need this copy in case of concurrent modification of Id
				messageCopy := *message
				messageCopy.Id = dnsQueryMessage.Id
				log.WithFields(log.Fields{
					"question": question,
					"message":  *message}).Info("dns_query_handler cache isHit")
				return &messageCopy, true
			} else if whichCache == &handler.negativeCache {
				log.WithFields(log.Fields{
					"question": question}).Info("Hit in negative cache")
				// negative cache
				return nil, false
			} else {
				log.WithFields(log.Fields{
					"id":       doID,
					"question": question,
					"message":  *message,
					"cache":    *whichCache}).Info("Hit in unknown cache")
				return message, false
			}

			log.WithFields(log.Fields{
				"id": doID}).Fatal("Should never reach here: dns_query_handler cache isHit")
			return nil, false
		}
	}
	// not a cache hit so do Lookup
	if DoHEnabled && Experiment {
		dnsServersToQuery = DoHServersToTest
	} else if !DoHEnabled && Experiment {
		dnsServersToQuery = DNSServersToTest
	}
	log.WithFields(log.Fields{
		"question":                  question,
		"DoHEnabled":                DoHEnabled,
		"Experiment":                Experiment,
		"dnsServersToQuery":         dnsServersToQuery,
		"cacheEnabled":              isEnabledCache,
		"isEnabledDirectResolution": isEnabledDirectResolution}).Info("Doing Lookup At NameServers")
	answerMessage, err = handler.resolver.LookupAtNameservers(Net, dnsQueryMessage, dnsServersToQuery, doID, DoHEnabled, Experiment, Proxy, ResolverMapping, PrivacyEnabled, Racing, Decentralized)

	if err != nil {
		// handler.handleResolutionError(err, responseWriter, dnsQueryMessage, cacheKey, doID)

		// TODO need to handle the error better (see ^^)
		log.WithFields(log.Fields{
			"id":    doID,
			"error": err.Error()}).Error("Error occured: LookupAtNameservers")
		return nil, false
	}

	if isEnabledDirectResolution {

		// check for redirection to CDN
		isRedirect := true
		numberOfCDNRedirects := 0
		//for isRedirect {
		isRedirect, cName, authoritativeNameServer, _ := handler.GetCDNRedirect(answerMessage, doID)
		if isRedirect {
			numberOfCDNRedirects++
			var betterAnswerMessage *dns.Msg
			log.WithFields(log.Fields{
				"id":       doID,
				"question": question.String()[1:],
				"CName":    cName,
				"NS":       authoritativeNameServer}).Info("Query question redirects to CName with NS")

			log.WithFields(log.Fields{
				"id":       doID,
				"response": answerMessage.String()}).Info("Full response from nameserver lookup")

			if authoritativeNameServer != "" {
				// If we are conveniently provided the NS without having to ask
				log.WithFields(log.Fields{
					"Authoritative Name Server": authoritativeNameServer,
					"question":                  question.String()[1:],
				}).Info("CDN REDIRECT")
				cNameQuery := handler.buildCnameQuery(cName, dnsQueryMessage.Id, question.Qtype)
				authoritativeNameserverAndPort := authoritativeNameServer + ":53"
				betterAnswerMessage, err = handler.resolver.LookupAtNameserver(
					Net,
					cNameQuery,
					authoritativeNameserverAndPort,
					doID)
				log.WithFields(log.Fields{
					"Authoritative Name Server": authoritativeNameServer,
					"question":                  question.String()[1:],
					"betterAnswerMessage":       betterAnswerMessage,
				}).Info("Better answer message when conveniently provided the NS without having to ask")

			} else {
				// If we don't know the NS
				stime := time.Now()
				betterAnswerMessage, err = handler.doSimpleDirectResolutionOfCname(
					Net,
					answerMessage,
					cName,
					doID)
				elapsed := time.Since(stime)
				log.WithFields(log.Fields{
					"TimeofDRwithnoNS": elapsed,
					"question":         question.String()[1:]}).Info("Direct Resolution after contacting NS")
			}

			if err != nil {
				// if there is an error, we should be able to just provide the simple answer
				log.WithFields(log.Fields{
					"question": question.String()[1:],
					"error":    err.Error()}).Warn("Error asking authoritative nameserver. Using original DNS answer as response.")

				return answerMessage, true
			} else {
				// no error, so use "better" answer
				answerMessage = betterAnswerMessage

				// make sure the question and node names match the original query
				// (otherwise, browsers seem to notice the discrepancy and discard the response)
				answerMessage.Question[0] = question // make question match
				for index := range answerMessage.Answer {
					answerMessage.Answer[index].Header().Name = question.Name // make nodeName match
				}

				// log.WithFields(log.Fields{
				// 	"question": dnsQueryMessage.Question[0],
				// 	"answer":   answerMessage}).Info("betterAnswerMessage added to cache")

				return answerMessage, true
			}

		} // isRedirect
	} // allowDirectResolution

	return answerMessage, true
}

func (handler *DNSQueryHandler) doSimpleDirectResolutionOfCname(
	Net string,
	answerMessage *dns.Msg,
	cName string,
	doID int) (directResolutionResult *dns.Msg, err error) {

	// Step 1: Get authoritative name server
	requestAuthoritativeServer := new(dns.Msg)
	requestAuthoritativeServer.MsgHdr = dns.MsgHdr{
		Id:                 answerMessage.Id, // NOTE maintain same ID so requestor can match replies to queries
		Response:           false,
		Opcode:             dns.OpcodeQuery,
		Authoritative:      false, // not valid on a query
		Truncated:          false,
		RecursionDesired:   true,  // although we're asking the authority so it shouldn't have to recurse
		RecursionAvailable: false, // not valid on a query
		Zero:               false, // must be zero--not sure how the dns package handles this since it's a bool
		AuthenticatedData:  false, // not sure what this is
		CheckingDisabled:   false, // not sure what this is
		Rcode:              0,     // not valid on a query
	}

	// add question RR to message
	authoritativeQuestion := dns.Question{
		Name:   cName,
		Qtype:  dns.TypeNS,
		Qclass: dns.ClassINET,
	}

	cacheAnswer := new(dns.Msg)
	responseAuthoritativeServer := new(dns.Msg)

	requestAuthoritativeServer.Question = []dns.Question{authoritativeQuestion}

	cacheKey := cache.KeyGen(requestAuthoritativeServer.Question[0])
	log.WithFields(log.Fields{
		"question": requestAuthoritativeServer.Question[0],
		"cacheKey": cacheKey}).Info("Verifying CACHE KEY")
	message, whichCache, isHit := handler.checkCache(requestAuthoritativeServer.Question[0], cacheKey, handler.whichIPVersion(requestAuthoritativeServer.Question[0]), doID)

	cacheHit := false
	if isHit {

		// handle different types of hit, then return
		if whichCache == &handler.cache {
			// positive cache
			// we need this copy in case of concurrent modification of Id
			messageCopy := *message
			messageCopy.Id = requestAuthoritativeServer.Id
			cacheAnswer = &messageCopy
			cacheAnswer = message
			cacheHit = true
			log.WithFields(log.Fields{
				"id":           doID,
				"question":     requestAuthoritativeServer.Question[0],
				"cache Answer": *cacheAnswer}).Info("Found NS in positive cache")

		} else if whichCache == &handler.negativeCache {
			// negative cache
			cacheAnswer = nil
			log.WithFields(log.Fields{
				"id":       doID,
				"question": requestAuthoritativeServer.Question[0]}).Info("NS In negative cache")
			cacheHit = false
		} else {
			log.WithFields(log.Fields{
				"id":       doID,
				"question": requestAuthoritativeServer.Question[0],
				"cache":    *whichCache}).Info("NS Hit in unknown cache")
			cacheAnswer = message
			cacheHit = true

		}
	}
	if cacheHit == false {

		stime := time.Now()
		_responseAuthoritativeServer, err := handler.resolver.Lookup(Net, requestAuthoritativeServer, doID, Proxy, ResolverMapping, PrivacyEnabled, Racing, Decentralized)
		responseAuthoritativeServer = _responseAuthoritativeServer
		elapsed := time.Since(stime)
		log.WithFields(log.Fields{
			"FindAuthoritativeTime": elapsed,
			"question":              requestAuthoritativeServer.Question[0].String(),
			"response":              responseAuthoritativeServer.String()}).Info("CACHING NS")

		if err != nil {
			log.WithFields(log.Fields{
				"id":    doID,
				"error": err.Error()}).Error("Error occured: resolver lookup at NS")
			return nil, err
		}
		//Cache the authoritativeNameServer
		handler.cacheAnswer(requestAuthoritativeServer.Question[0], responseAuthoritativeServer, handler.whichIPVersion(requestAuthoritativeServer.Question[0]), doID)
	} else {
		log.WithFields(log.Fields{
			"question":     requestAuthoritativeServer.Question,
			"cache Answer": *cacheAnswer}).Info("Found Ns in cache,bypassed lookup")
		responseAuthoritativeServer = cacheAnswer
	}

	log.WithFields(log.Fields{
		"id":       doID,
		"question": requestAuthoritativeServer.Question[0].String(),
		"response": responseAuthoritativeServer.Ns}).Info("Question with full response to NS query")

	authoritativeNameserver := ""
	authoritativeNameserverAndPort := ""

	/* TODO currently, if there is more than 1 authoritative nameserver, the last one wins,
	 * which is arbitrary.  We at least want to somehow report that there is more than one.
	 */
	for index, authorityResourceRecord := range responseAuthoritativeServer.Ns {
		log.WithFields(log.Fields{
			"id":                       doID,
			"nameserver index":         index,
			"query":                    authorityResourceRecord.Header().Name,
			"authoritative nameserver": dns.Field(authorityResourceRecord, 1),
			"type":                     authorityResourceRecord.Header().Rrtype,
			"ttl":                      authorityResourceRecord.Header().Ttl,
			"rdlength":                 authorityResourceRecord.Header().Rdlength,
		}).Info("Authoritative name server answer in Authority Section")

		authoritativeNameserver = dns.Field(authorityResourceRecord, 1)
	}

	if authoritativeNameserver == "" {
		// No authority in Authority section.
		// Authorities might be in Answer section (e.g. cdn.amazon.com, dk9ps7goqoeef.cloudfront.net)

		// TODO currently, if there is more than 1, the first one wins, which is (maybe?) arbitrary

		for index, answerResourceRecord := range responseAuthoritativeServer.Answer {
			if answerResourceRecord.Header().Rrtype == dns.TypeNS {
				log.WithFields(log.Fields{
					"id":               doID,
					"nameserver index": index,
					"query":            answerResourceRecord.Header().Name,
					"response":         dns.Field(answerResourceRecord, 1)}).Info("Authoritative name server answer in Answer Section")

				authoritativeNameserver = dns.Field(answerResourceRecord, 1)
				break
			}
		}
	}

	if authoritativeNameserver == "" {
		log.WithFields(log.Fields{
			"id": doID}).Error("Unable to get authoritative nameserver.")
		return nil, errors.New("Failed to get authoritative nameserver")
	}

	authoritativeNameserverAndPort = authoritativeNameserver[:len(authoritativeNameserver)-1] + ":53"

	// Step 2: Get address for CName by querying the authoritative name server

	// build a request to send the authoritative name server
	requestAFromAuthoritativeServer := handler.buildCnameQuery(
		cName,
		requestAuthoritativeServer.Id,
		answerMessage.Question[0].Qtype)

	// perform lookup at the authoritative name server

	// TODO check cache first--might not need to do lookup...or check before we even begin direct resolution!
	log.WithFields(log.Fields{
		"Searched for Authoritative Name Server": authoritativeNameserverAndPort,
		"question":                               requestAuthoritativeServer.Question[0].String(),
	}).Info("Lookup at the authoritative name server")
	cacheKey = cache.KeyGen(requestAFromAuthoritativeServer.Question[0])
	log.WithFields(log.Fields{
		"question": requestAFromAuthoritativeServer.Question[0],
		"cacheKey": cacheKey}).Info("Verifying CACHE KEY of DR")
	message, whichCache, isHit = handler.checkCache(requestAFromAuthoritativeServer.Question[0], cacheKey, handler.whichIPVersion(requestAFromAuthoritativeServer.Question[0]), doID)
	cacheHit = false
	cacheAnswer = new(dns.Msg)
	if isHit {
		// handle different types of hit, then return
		if whichCache == &handler.cache {
			// positive cache
			// we need this copy in case of concurrent modification of Id
			messageCopy := *message
			messageCopy.Id = requestAFromAuthoritativeServer.Id
			cacheAnswer = &messageCopy
			cacheHit = true
			log.WithFields(log.Fields{
				"question":     requestAFromAuthoritativeServer.Question[0],
				"cache Answer": *cacheAnswer}).Info("Found betterAnswerMessage in positive cache")

		} else if whichCache == &handler.negativeCache {
			// negative cache
			cacheAnswer = nil
			log.WithFields(log.Fields{
				"id":       doID,
				"question": requestAFromAuthoritativeServer.Question[0]}).Info("betterAnswerMessage in negative cache")
			cacheHit = false
		} else {
			log.WithFields(log.Fields{
				"id":       doID,
				"question": requestAFromAuthoritativeServer.Question[0],
				"cache":    *whichCache}).Warn("betterAnswerMessage Hit in unknown cache")
			cacheAnswer = message
			cacheHit = true

		}

	}
	if cacheHit == false {
		directResolutionResult, err = handler.resolver.LookupAtNameserver(
			Net,
			requestAFromAuthoritativeServer,
			authoritativeNameserverAndPort,
			doID)
		if err != nil {
			log.WithFields(log.Fields{
				"id":    doID,
				"error": err.Error()}).Warn("Direct resolution failed")
			return nil, err
		}
		handler.cacheAnswer(requestAFromAuthoritativeServer.Question[0], directResolutionResult, handler.whichIPVersion(requestAFromAuthoritativeServer.Question[0]), doID)
	} else {
		log.WithFields(log.Fields{
			"question":     requestAFromAuthoritativeServer.Question[0],
			"cache Answer": *cacheAnswer}).Info("Found directResolutionResult in cache,bypassed lookup")
		directResolutionResult = cacheAnswer
	}

	return directResolutionResult, nil
}

func (handler *DNSQueryHandler) do(Net string, responseWriter dns.ResponseWriter, dnsQueryMessage *dns.Msg) {

	doID := handler.doID
	handler.doID++

	question := dnsQueryMessage.Question[0]

	answerMessage, success := handler.PerformDNSQuery(Net, dnsQueryMessage, net.ParseIP(utils.LOCALHOST),
		handler.settings.isEnabledDirectResolution, handler.settings.isEnabledHostsFile, handler.settings.isEnabledCache,
		handler.settings.isEnabledCounter)

	ipVersion := handler.whichIPVersion(question)

	if success {
		log.WithFields(log.Fields{
			"id":       doID,
			"question": question.String()[1:],
			"answer":   answerMessage.String()}).Info("DNS query succeeded")
		responseWriter.WriteMsg(answerMessage)
		log.WithFields(log.Fields{
			"id":       doID,
			"question": question.String()[1:]}).Debug("Finished writing answer")

		handler.cacheAnswer(question, answerMessage, ipVersion, doID)
	} else {
		// cacheKey := cache.KeyGen(question)
		err := errors.New("Failed to perform DNSQuery")
		log.WithFields(log.Fields{
			"question": question.String()[1:],
			"err":   err}).Info("DNS query succeeded")
		// handler.handleResolutionError(err, responseWriter, dnsQueryMessage, cacheKey, doID)
		dns.HandleFailed(responseWriter, dnsQueryMessage)
	}

	log.WithFields(log.Fields{
		"id":       doID,
		"question": question.String()[1:]}).Debug("Function finished: do")
}

func (handler *DNSQueryHandler) cacheAnswer(question dns.Question, answerMessage *dns.Msg, ipVersion int, doID int) {
	// cache results

	// 	if ipVersion > 0 && len(answerMessage.Answer) > 0 {
	if len(answerMessage.Answer) > 0 {

		// 	    log.WithFields(log.Fields{
		//             			"id":       doID,
		//             			"question": question.String()[1:],
		//             			"cache answer": answerMessage.Answer}).Info("CACHING ANSWER")

		cacheKey := cache.KeyGen(question)
		err := handler.cache.Set(cacheKey, answerMessage)
		if err != nil {
			log.WithFields(log.Fields{
				"id":       doID,
				"question": question.String()[1:],
				"error":    err.Error()}).Info("Caching answer error")
		}
		log.WithFields(log.Fields{
			"id":           doID,
			"question":     question.String()[1:],
			"cache answer": answerMessage.Answer,
			"cacheKey":     cacheKey}).Info("Finished caching answer")
	}
}

// handleResolutionError responds to the requesting client with a failure code
// and stores the failure in the negative cache
func (handler *DNSQueryHandler) handleResolutionError(err error, responseWriter dns.ResponseWriter,

	requestMessage *dns.Msg, cacheKey string, doID int) {
	log.WithFields(log.Fields{
		"id":             doID,
		"requestMessage": requestMessage.Question[0].String(),
		"error":          err}).Info("Resolve query error")
	// dns.HandleFailed(responseWriter, requestMessage)

	// cache the failure in the negative cache
	err = handler.negativeCache.Set(cacheKey, nil)
	if err != nil {
		log.WithFields(log.Fields{
			"id":       doID,
			"question": requestMessage.Question[0].String(),
			"error":    err}).Error("Set negative cache failed")
	}
}

// doDirectResolutionOfCname performs direct resolution as follows.
// Step 1: Send a DNS query of type NS in order to get the authoritative name server for the given CName
// Step 2: Send a DNS query of type A to the authoritative name server to get the address for the given CName
func (handler *DNSQueryHandler) doDirectResolutionOfCname(Net string, answerMessage *dns.Msg, cName string,
	responseWriter dns.ResponseWriter, cacheKey string, doID int) (directResolutionResult *dns.Msg, err error) {

	// Step 1: Get authoritative name server
	requestAuthoritativeServer := new(dns.Msg)
	requestAuthoritativeServer.MsgHdr = dns.MsgHdr{
		Id:                 answerMessage.Id, // NOTE maintain same ID so requestor can match replies to queries
		Response:           false,
		Opcode:             dns.OpcodeQuery,
		Authoritative:      false, // not valid on a query
		Truncated:          false,
		RecursionDesired:   true,
		RecursionAvailable: false, // not valid on a query
		Zero:               false, // must be zero--not sure how the dns package handles this since it's a bool
		AuthenticatedData:  false, // not sure what this is
		CheckingDisabled:   false, // not sure what this is
		Rcode:              0,     // not valid on a query
	}

	authoritativeQuestion := dns.Question{
		Name:   cName,
		Qtype:  dns.TypeNS,
		Qclass: dns.ClassINET,
	}
	requestAuthoritativeServer.Question = []dns.Question{authoritativeQuestion}

	responseAuthoritativeServer, err := handler.resolver.Lookup(Net, requestAuthoritativeServer, doID, Proxy, ResolverMapping, PrivacyEnabled, Racing, Decentralized)
	if err != nil {
		log.WithFields(log.Fields{
			"id":    doID,
			"error": err.Error()}).Error("Error occured: resolver lookup")
		//log.Println(err.Error())
	}
	log.WithFields(log.Fields{
		"id":       doID,
		"question": requestAuthoritativeServer.Question[0].String(),
		"response": responseAuthoritativeServer.String()}).Info("Full response to NS query")
	//log.Printf("[%d] For question [%s], full response to NS query:\n[%s]", doID, requestAuthoritativeServer.Question[0].String(), responseAuthoritativeServer.String())

	authoritativeNameserver := ""
	authoritativeNameserverAndPort := ""

	// TODO currently, if there is more than 1 authoritative nameserver, the last one wins,
	// TODO which is arbitrary.  We at least want to somehow report that there is more than one.

	for index, authorityResourceRecord := range responseAuthoritativeServer.Ns {
		log.WithFields(log.Fields{
			"id":                       doID,
			"index":                    index,
			"query":                    authorityResourceRecord.Header().Name,
			"authoritative nameserver": dns.Field(authorityResourceRecord, 1),
			"type":                     authorityResourceRecord.Header().Rrtype,
			"ttl":                      authorityResourceRecord.Header().Ttl,
			"rdlength":                 authorityResourceRecord.Header().Rdlength}).Info("Authoritative nameserver answer")

		authoritativeNameserver = dns.Field(authorityResourceRecord, 1)
		authoritativeNameserverAndPort = authoritativeNameserver[:len(authoritativeNameserver)-1] + ":53"
	}

	// Authorities might be in Answer section (e.g. cdn.amazon.com, dk9ps7goqoeef.cloudfront.net)

	// TODO currently, if there is more than 1, the first one wins, which is (maybe?) arbitrary

	if authoritativeNameserver == "" {
		for index, answerResourceRecord := range responseAuthoritativeServer.Answer {
			if answerResourceRecord.Header().Rrtype == dns.TypeNS {
				log.WithFields(log.Fields{
					"id":     doID,
					"index":  index,
					"query":  answerResourceRecord.Header().Name,
					"answer": dns.Field(answerResourceRecord, 1)}).Info("Authoritative name server answer")
				authoritativeNameserver = dns.Field(answerResourceRecord, 1)
				authoritativeNameserverAndPort = authoritativeNameserver[:len(authoritativeNameserver)-1] + ":53"
				break
			}
		}
	}

	// Step 2: Get address for CName by querying the authoritative name server

	// build a request to send the authoritative name server
	requestAFromAuthoritativeServer := handler.buildCnameQuery(cName, requestAuthoritativeServer.Id, answerMessage.Question[0].Qtype)

	// perform lookup at the authoritative name server

	// TODO check cache first--might not need to do lookup

	directResolutionResult, err = handler.resolver.LookupAtNameserver(Net, requestAFromAuthoritativeServer, authoritativeNameserverAndPort, doID)
	if err != nil {
		log.WithFields(log.Fields{
			"id":    doID,
			"error": err.Error()}).Error("Direct resolution failed")
	}

	return directResolutionResult, err
}

func (handler *DNSQueryHandler) buildCnameQuery(cName string, id uint16, qType uint16) (cNameQuery *dns.Msg) {
	cNameQuery = new(dns.Msg)
	cNameQuery.MsgHdr = dns.MsgHdr{
		Id:                 id,
		Response:           false,
		Opcode:             dns.OpcodeQuery,
		Authoritative:      false, // not valid on a query
		Truncated:          false,
		RecursionDesired:   false, // no recursion needed because directly asking the authority
		RecursionAvailable: false, // not valid on a query
		Zero:               false, // must be zero--not sure how the dns package handles this since it's a bool
		AuthenticatedData:  false, // not sure what this is
		CheckingDisabled:   false, // not sure what this is
		Rcode:              0,     // not valid on a query
	}
	questionForAuthoritativeServer := dns.Question{
		Name:   cName,
		Qtype:  qType,
		Qclass: dns.ClassINET,
	}
	cNameQuery.Question = []dns.Question{questionForAuthoritativeServer}

	return cNameQuery
}

func (handler *DNSQueryHandler) checkCache(question dns.Question, cacheKey string, IPQuery int, doID int) (message *dns.Msg, whichCache *cache.Cache, isCacheHit bool) {
	// 	if IPQuery > 0 {
	message, err := handler.cache.Get(cacheKey)

	if err != nil {
		// not in positive cache
		message, err = handler.negativeCache.Get(cacheKey) // check negative cache
		if err != nil {
			// not in negative cache
			log.WithFields(log.Fields{
				"id":       doID,
				"key":      cacheKey,
				"question": question.Name}).Error("Question didn't hit cache", doID, question.Name)
			return message, nil, false
		} else {
			// hit in negative cache
			log.WithFields(log.Fields{
				"id":       doID,
				"question": question.Name}).Info("Question hit negative cache")
			return message, &handler.negativeCache, true
		}
	} else {
		// cache hit (positive cache)
		log.WithFields(log.Fields{
			"id":       doID,
			"question": question.Name}).Info("Question hit cache")
		return message, &handler.cache, true
	}
	// 	}
	return nil, nil, false
}

// GetCDNRedirect checks for CNAME response from DNS message and extract the information
func (handler *DNSQueryHandler) GetCDNRedirect(message *dns.Msg, doID int) (isCDNRedirect bool, cName string, authoritativeNameServer string, naiveIPAddress string) {
	isCDNRedirect = false
	originalNodeName := ""
	nodeName := ""
	cName = ""
	authoritativeNameServer = ""
	naiveIPAddress = ""

	// Loop through Answer section resource records
	// Anytime the response is TypeCNAME, we assume it is a redirect to a CDN
	index := 0
	for _, answer := range message.Answer {
		if answer.Header().Rrtype == dns.TypeCNAME {
			isCDNRedirect = true
			cName = dns.Field(answer, 1)
			nodeName = answer.Header().Name
			originalNodeName = nodeName
			log.WithFields(log.Fields{
				"id":            doID,
				"original name": originalNodeName,
				"cName":         cName}).Info("cName redirection")
			break
		}
		index++
	}

	// Loop through remaining resource records looking for more info
	index++ // move to next resource record
	for ; index < len(message.Answer); index++ {
		thisAnswer := message.Answer[index]
		if thisAnswer.Header().Name == cName {
			if thisAnswer.Header().Rrtype == dns.TypeCNAME {
				cName = dns.Field(thisAnswer, 1)
				nodeName = thisAnswer.Header().Name
				log.WithFields(log.Fields{
					"id":        doID,
					"node name": nodeName,
					"cName":     cName}).Info("Second redirection")
			}
			if thisAnswer.Header().Rrtype == dns.TypeA || thisAnswer.Header().Rrtype == dns.TypeAAAA {
				nodeName = thisAnswer.Header().Name
				naiveIPAddress = dns.Field(thisAnswer, 1)
				log.WithFields(log.Fields{
					"id":        doID,
					"node name": nodeName,
					"naive IP":  naiveIPAddress}).Info("naive mapping to IP")
			}
		}
	}

	for _, authorityRecord := range message.Ns {
		if authorityRecord.Header().Rrtype == dns.TypeSOA {
			authoritativeNameServer = dns.Field(authorityRecord, 1)
			nodeName = authorityRecord.Header().Name
			log.WithFields(log.Fields{
				"id":                        doID,
				"node name":                 nodeName,
				"authoritative name server": authoritativeNameServer}).Info("Authoritative name server for node")
			break
		}
	}

	return isCDNRedirect, cName, authoritativeNameServer, naiveIPAddress
}

func (handler *DNSQueryHandler) whichIPVersion(question dns.Question) int {
	if question.Qclass != dns.ClassINET {
		return utils.NotIPQuery
	}

	switch question.Qtype {
	case dns.TypeA:
		return utils.IP4Query
	case dns.TypeAAAA:
		return utils.IP6Query
	default:
		return utils.NotIPQuery
	}
}

// DoTCP performs TCP query
func (handler *DNSQueryHandler) DoTCP(responseWriter dns.ResponseWriter, req *dns.Msg) {
	handler.do("tcp", responseWriter, req)
}

// DoUDP performs UDP query
func (handler *DNSQueryHandler) DoUDP(responseWriter dns.ResponseWriter, req *dns.Msg) {
	handler.do("udp", responseWriter, req)
}

// measure the DNS resolution time of each alexa site and measure min ping latency to the replica server
func (handler *DNSQueryHandler) MeasureDnsLatencies(indexW int, websiteFile string, smartDnsSelectorId int, dohEnabled bool, experiment bool, iterations int, dict map[string]map[string]map[string]interface{}, resolver string) (dictionary map[string]map[string]map[string]interface{}, err error) {
	// dict:= make(map[string]map[string]map[string]interface{})
	var serversToTest []string
	if dohEnabled {
		serversToTest = DoHServersToTest
	} else {
		serversToTest = DNSServersToTest
	}

	file, err := os.Open(websiteFile)
	if err != nil {
		log.Fatal(err)
	}
	defer file.Close()

	scanner := bufio.NewScanner(file)

	// TODO parallelize this for loop with goroutine (and channel?)
	dict[resolver] = make(map[string]map[string]interface{})

	// count:=0
	var websites []string
	for scanner.Scan() {
		// if count==20{
		// 	break
		// }
		// count+=1
		website := scanner.Text()
		u, err := url.Parse(website)
		if err != nil {
			log.Fatal("Error Parsing website", err)
		}
		if err := scanner.Err(); err != nil {
			log.Fatal("Error while scanning for website", err)
		}
		found := 0
		for _, ele := range websites {
			if ele == u.Hostname() {
				found = 1
			}
		}
		if found == 0 {
			websites = append(websites, u.Hostname())
		}
	}
	log.WithFields(log.Fields{
		"len of websites": len(websites),
		"websites":        websites,
		"resolver":        resolver,
		"serversToTest":   serversToTest}).Info("Testing DNS resolution time of this approach")

	// dir, err := os.Getwd()
	// testingDir:="/temp/AR/Decentralized"
	// f, err := os.Create(dir+testingDir+"/websiteDomains.txt")
	//    if err != nil {
	//        fmt.Println(err)
	//        return
	//    }
	// sep := "\n"
	//    for _, line := range websites {
	//        if _, err = f.WriteString(line + sep); err != nil {
	//            panic(err)
	//        }
	//    }

	for _, website := range websites {
		dnsQueryMessage := utils.BuildDnsQuery(website, dns.TypeA, 0, true)
		// var dnsServersToQuery []string
		var elapsedTime time.Duration
		var answerMessage *dns.Msg
		// var dnsResolutionTimes []time.Duration
		var dnsResolutionTimes []string

		log.WithFields(log.Fields{
			"smart selector id":      smartDnsSelectorId,
			"website":                website,
			"experiment":             experiment,
			"dohEnabled":             dohEnabled,
			"Proxy":                  Proxy,
			"PrivacyEnabled":         PrivacyEnabled,
			"Racing":                 Racing,
			"EnableDirectResolution": handler.settings.isEnabledDirectResolution,
			"EnableHostsFile":        handler.settings.isEnabledHostsFile,
			"isEnabledCache":         handler.settings.isEnabledCache,
			"isEnabledCounter":       handler.settings.isEnabledCounter,
			"DNS server":             resolver}).Info("Measuring DNS Latency for website")

		for x := 0; x < iterations; x++ {
			utils.FlushLocalDnsCache()
			Net := "udp"

			var success bool
			startTime := time.Now()
			answerMessage, success = handler.PerformDNSQuery(Net, dnsQueryMessage, net.ParseIP(utils.LOCALHOST), handler.settings.isEnabledDirectResolution, handler.settings.isEnabledHostsFile, handler.settings.isEnabledCache, handler.settings.isEnabledCounter)
			elapsedTime = time.Since(startTime)

			if !success {
				log.WithFields(log.Fields{
					"DNS server": resolver,
					"query":      dnsQueryMessage.Question[0].String()}).Error("No valid answer received from DNS server for question")
				//can continue iterating in case of DoHproxy or SubRosa becasue random resolvers selected each time
				if experiment {
					break
				}
				continue
			}

			log.WithFields(log.Fields{
				"DNS Latency":    strconv.FormatInt(elapsedTime.Nanoseconds()/1e6, 10),
				"website":        website,
				"experiment":     experiment,
				"dohEnabled":     dohEnabled,
				"Proxy":          Proxy,
				"PrivacyEnabled": PrivacyEnabled,
				"Racing":         Racing,
				"DNS server":     resolver}).Info("DNS Latency for website")
			dnsResolutionTimes = append(dnsResolutionTimes, strconv.FormatInt(elapsedTime.Nanoseconds()/1e6, 10)+" ms")

		}
		if len(dnsResolutionTimes) == 0 {
			log.WithFields(log.Fields{
				"DNS server": resolver,
				"query":      dnsQueryMessage.Question[0].String()}).Info("DNS resolution times empty")
			continue
		}

		dict[resolver][website] = make(map[string]interface{})
		dict[resolver][website]["DNS Resolution Time"] = dnsResolutionTimes

		log.WithFields(log.Fields{
			"DNS Latency":    dnsResolutionTimes,
			"website":        website,
			"experiment":     experiment,
			"dohEnabled":     dohEnabled,
			"Proxy":          Proxy,
			"PrivacyEnabled": PrivacyEnabled,
			"Racing":         Racing,
			"DNS server":     resolver}).Info("Minimum DNS Resolution time for website")

		ipAddress, err := utils.GetIpAddressFromAnswerMessage(answerMessage)
		if err != nil {
			log.WithFields(log.Fields{
				"smart selector id": smartDnsSelectorId,
				"error":             err.Error(),
				"answer":            answerMessage.String()}).Error("Error: Answer does not contain valid IP Address.")
			dictionary = dict
			continue
		} else {
			log.WithFields(log.Fields{
				"website":   website,
				"ipAddress": ipAddress}).Info("Answer does contain valid IP Address.")
		}
		dict[resolver][website]["ReplicaIP"] = ipAddress

		var cmd string
		var args []string
		var result *PingResult
		var stdout bytes.Buffer

		if cmd, err = exec.LookPath("ping.exe"); err == nil {
			args = []string{"-n", strconv.Itoa(iterations), ipAddress}
		} else if cmd, err = exec.LookPath("ping"); err == nil {
			args = []string{"-c", strconv.Itoa(iterations), ipAddress}
		}
		if cmd != "" {
			// If a traceroute command was found, run it.
			var stderr bytes.Buffer
			c := exec.Command(cmd, args...)
			c.Stdout = &stdout
			c.Stderr = &stderr
			err = c.Run()
			if err != nil {
				result = nil
			} else {
				result = &PingResult{cmd, ipAddress, args, stdout.String(), stderr.String()}
			}
		} else {
			// Otherwise we can't do anything
			result = nil
		}

		if result != nil {
			pingTimes := strings.Split(stdout.String(), "min/avg/max/stddev =")[1]
			// minPingTime:=strings.Split(pingTimes,"/")[0]
			// dict[resolver][website]["Replica Ping"]=minPingTime
			dict[resolver][website]["Replica Ping"] = pingTimes
		}
	}

	dictionary = dict
	return dictionary, err
}

//run webperformance test on each alexa site
func (handler *DNSQueryHandler) RunWebPerformanceTest(urlFile string, dohEnabled bool, experiment bool, iterations int, resultPath string, dnsServer string) {
	// cmd := exec.Command("CHROME_PATH=/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge","lighthouse","http://google.com", "--quiet", "--only-categories=performance", "--output=json", "--output-path=./report.json")
	// cmd := exec.Command("node","/Users/rashnakumar/Documents/subRosaLighthouse.js")
	//brew install yarn
	// yarn global add sitespeed.io to install site speed
	f, err := os.Open(urlFile)
	if err != nil {
		log.Fatal(err)
	}
	defer f.Close()

	scanner := bufio.NewScanner(f)
	for scanner.Scan() {
		fmt.Println(scanner.Text())
		url := scanner.Text()
		// cmd := exec.Command("docker", "run", "sitespeedio/sitespeed.io:14.2.3",url,"--headless","-n", strconv.Itoa(iterations),"--logToFile","--plugins.add", "analysisstorer","--plugins.remove", "coach,html,harstorer,assets,thirdparty,pagexray,budget,tracestorer,text,domains", "--outputFolder", resultPath+"/"+dnsServer, "--browsertime.retries", "0", "--browsertime.retryWaitTime", "10000")
		cmd := exec.Command("sitespeed.io", url, "--headless", "-n", strconv.Itoa(iterations), "--logToFile", "--plugins.add", "analysisstorer", "--plugins.remove", "coach,html,harstorer,assets,thirdparty,pagexray,budget,tracestorer,text,domains", "--outputFolder", resultPath+"/"+dnsServer, "--browsertime.retries", "0", "--browsertime.retryWaitTime", "10000")
		if err := cmd.Run(); err != nil {
			log.WithFields(log.Fields{
				"error":   err.Error(),
				"website": url}).Info("Error: running sitespeed.io")
		}
	}
}

//measure the min ping latency to each DNS/DoH server
// func(handler *DNSQueryHandler)PingServers(dohEnabled bool,experiment bool,iterations int,dict map[string]map[string]interface{},resolverList []string){
func (handler *DNSQueryHandler) PingServers(dohEnabled bool, experiment bool, iterations int, dict map[string]interface{}, resolverList []string) (dictionary map[string]interface{}) {

	var cmd string
	var args []string
	var result *PingResult
	utils.FlushLocalDnsCache()

	for _, dnsServer := range resolverList {

		var err error
		var stdout bytes.Buffer

		ipAddress := dnsServer

		if cmd, err = exec.LookPath("ping.exe"); err == nil {
			args = []string{"-n", strconv.Itoa(iterations), ipAddress}
		} else if cmd, err = exec.LookPath("ping"); err == nil {
			args = []string{"-c", strconv.Itoa(iterations), ipAddress}
		}
		if cmd != "" {
			// If a traceroute command was found, run it.
			var stderr bytes.Buffer
			c := exec.Command(cmd, args...)
			c.Stdout = &stdout
			c.Stderr = &stderr
			err = c.Run()
			if err != nil {
				result = nil
			} else {
				result = &PingResult{cmd, ipAddress, args, stdout.String(), stderr.String()}

			}
		} else {
			// Otherwise we can't do anything
			result = nil
		}
		log.WithFields(log.Fields{
			"dnsServer":   dnsServer,
			"ipAddress":   ipAddress,
			"ping Result": result}).Info("Ping Response of DNS Server")
		if result != nil {
			pingTimes := strings.Split(stdout.String(), "min/avg/max/stddev =")[1]
			dict[dnsServer] = pingTimes

		}
	}
	dictionary = dict
	return dictionary

}
