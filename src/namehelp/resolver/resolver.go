// based heavily upon github.com/kenshinx/godns/resolver.go

package resolver

import (
	// 	"bytes"
	"errors"
	"fmt"
	"math/rand"
	// 	"os/exec"
	"strings"
	"sync"
	"time"
	// "strconv"

	// "namehelp/proxy"
	"namehelp/settings"
	"namehelp/utils"

	proxy "github.com/alexthemonk/DoH_Proxy"
	bloom "github.com/bits-and-blooms/bloom"
	domainutil "github.com/bobesa/go-domain-util/domainutil"
	"github.com/miekg/dns"
	log "github.com/sirupsen/logrus"
)

// Client for resolver proxy that translate DNS to DoH
var Client proxy.Client
var mutex = &sync.Mutex{}

// ResolvError error type
type ResolvError struct {
	qname, net  string
	nameservers []string
}

func (e ResolvError) Error() string {
	errmsg := fmt.Sprintf("%s resolv failed on %s (%s)",
		e.qname, strings.Join(e.nameservers, "; "), e.net)
	return errmsg
}

// Resolver for dns
type Resolver struct {
	Config *dns.ClientConfig
}

func waitTimeout(waitGroup *sync.WaitGroup, timeoutDuration time.Duration) bool {
	channel := make(chan interface{})

	go func() {
		defer close(channel)
		waitGroup.Wait()
		channel <- "waitGroup done waiting"
	}()

	select {
	case <-channel:
		return false // completed normally (waitGroup done waiting)
	case <-time.After(timeoutDuration):
		return true // timed out
	}
}

// routine_DoLookup performs dns lookup using go routine
func routine_DoLookup(nameserver string, dnsClient *dns.Client, waitGroup *sync.WaitGroup,
	requestMessage *dns.Msg, net string, resultChannel chan *dns.Msg, doID int, insertion bool) {

	qname := requestMessage.Question[0].Name
	qType := requestMessage.Question[0].Qtype

	responseMessage, rtt, err := dnsClient.Exchange(requestMessage, nameserver)
	if insertion == true {
		log.WithFields(log.Fields{
			"id":          doID,
			"query":       qname,
			"name server": nameserver}).Debug("Resolver: This is the inserted query, no response needed")
		return
	}
	defer waitGroup.Done() // when this goroutine finishes, notify the waitGroup
	if err != nil {
		log.WithFields(log.Fields{
			"id":          doID,
			"query":       qname,
			"error":       err.Error(),
			"name server": nameserver}).Debug("Resolver: DNS Client Exchange Socket error")
		return
	}

	// If SERVFAIL happens, should return immediately and try another upstream resolver.
	// However, other Error codes like NXDOMAIN are a clear response stating
	// that it has been verified no such domain exists and asking other resolvers
	// would make no sense. See more about #20
	if responseMessage != nil && responseMessage.Rcode != dns.RcodeSuccess {
		// failure
		log.WithFields(log.Fields{
			"id":          doID,
			"query":       qname,
			"name server": nameserver}).Debug("Resolver: Failed to get a valid answer for query from nameserver")
		if responseMessage.Rcode == dns.RcodeServerFailure {
			// SERVFAIL: don't provide response because other DNS servers may have better luck
			log.WithFields(log.Fields{"Rcode": responseMessage.Rcode}).Debug("Resolver: ServFail")
			return
		} else {
			log.WithFields(log.Fields{"Rcode": responseMessage.Rcode}).Debug("Resolver: NXDOMAIN ERROR")
		}
	} else {
		// success
		log.WithFields(log.Fields{
			"id":          doID,
			"domain name": utils.UnFullyQualifyDomainName(qname),
			"query type":  dns.TypeToString[qType],
			"name server": nameserver,
			"net":         net,
			"tll":         rtt}).Debug("Resolver: resolve successfully")
	}

	// use select statement with default to try the send without blocking
	select {
	// try to send response on channel
	case resultChannel <- responseMessage:
		log.WithFields(log.Fields{
			"id":          doID,
			"name server": nameserver}).Debug("Resolver: name server won the resolver race.")
	default:
		// if another goroutine already sent on channel and the message is not yet read
		// we simply return in order to invoke the deferred waitGroup.Done() call
		log.WithFields(log.Fields{
			"id":          doID,
			"name server": nameserver}).Debug("Resolver: name server DID NOT won the resolver race.")
		return
	}
}

// For initial DoH resolution
func routine_DoLookup_DoH(nameserver string, dnsClient *dns.Client, waitGroup *sync.WaitGroup, requestMessage *dns.Msg,
	net string, resultChannel chan *dns.Msg, doID int, insertion bool) {

	qname := requestMessage.Question[0].Name
	qType := requestMessage.Question[0].Qtype
	log.WithFields(log.Fields{"nameserver": nameserver}).Debug("Resolver: DoH look up at Namehelp")

	//Match the resolverName with the resolver
	var resolver proxy.Server
	for _, ns := range Client.Resolvers {
		if ns.Name == nameserver {
			resolver = ns
			break
		}
	}
	log.WithFields(log.Fields{"nameserver": resolver}).Debug("Resolver: DoH look up at Namehelp")

	responseMessage, err := Client.Resolve(requestMessage, resolver)
	if insertion == true {
		log.WithFields(log.Fields{
			"id":          doID,
			"query":       qname,
			"name server": nameserver}).Debug("ResolverDoH: This is the inserted query, no response needed")
		return
	}
	defer waitGroup.Done() // when this goroutine finishes, notify the waitGroup

	if err != nil {
		log.WithFields(log.Fields{
			"id":          doID,
			"query":       qname,
			"error":       err.Error(),
			"name server": nameserver}).Error("Resolver: DoH Client Resolve Socket error")
		return
	}

	log.WithFields(log.Fields{
		"name server": nameserver,
	}).Debug("Resolver: Response from DoH")

	// If SERVFAIL happens, should return immediately and try another upstream resolver.
	// However, other Error codes like NXDOMAIN are a clear response stating
	// that it has been verified no such domain exists and asking other resolvers
	// would make no sense. See more about #20
	if responseMessage != nil && responseMessage.Rcode != dns.RcodeSuccess {
		// failure
		log.WithFields(log.Fields{
			"id":          doID,
			"query":       qname,
			"name server": nameserver}).Debug("Resolver: Failed to get a valid answer for query from nameserver")
		if responseMessage.Rcode == dns.RcodeServerFailure {
			// SERVFAIL: don't provide response because other DNS servers may have better luck
			log.WithFields(log.Fields{"Rcode": responseMessage.Rcode}).Error("Resolver: ServFail")
			return
		} else {
			log.WithFields(log.Fields{"Rcode": responseMessage.Rcode}).Error("Resolver: NXDOMAIN ERROR")
			// NXDOMAIN and other failures: confirmed failure so provide the response (jump to end of function)
		}
	} else {
		// success
		log.WithFields(log.Fields{
			"id":          doID,
			"domain name": utils.UnFullyQualifyDomainName(qname),
			"query type":  dns.TypeToString[qType],
			"name server": nameserver,
			"net":         net}).Debug("Resolver: resolve successfully")
	}

	// use select statement with default to try the send without blocking
	select {
	// try to send response on channel
	case resultChannel <- responseMessage:
		log.WithFields(log.Fields{
			"id":          doID,
			"name server": nameserver}).Debug("Resolver: name server won the resolver race.")
	default:
		// if another goroutine already sent on channel and the message is not yet read
		// we simply return in order to invoke the deferred waitGroup.Done() call
		log.WithFields(log.Fields{
			"id":          doID,
			"name server": nameserver}).Debug("Resolver: name server DID NOT win the resolver race.")
		return
	}
}

// LookupAtNameserver performs the given dns query at the given nameserver
func (resolver *Resolver) LookupAtNameserver(net string, requestMessage *dns.Msg, nameserver string,
	doID int) (resultMessage *dns.Msg, err error) {
	if utils.IsNamehelp(nameserver) {
		log.WithFields(log.Fields{
			"id":          doID,
			"query":       requestMessage.Question[0],
			"name server": nameserver}).Error("Resolver: Trying to send query to self")
		return &dns.Msg{}, errors.New("Cannot send query to self")
	}

	log.WithFields(log.Fields{
		"id":           doID,
		"query":        requestMessage.Question[0].String(),
		"name server":  nameserver,
		"net":          net,
		"full request": requestMessage.String()}).Debug("Resolver: Performing lookup at nameserver for DR")

	dnsClient := &dns.Client{
		Net:          net,
		ReadTimeout:  resolver.Timeout(),
		WriteTimeout: resolver.Timeout(),
	}

	qname := requestMessage.Question[0].Name

	resultChannel := make(chan *dns.Msg, 1)
	var waitGroup sync.WaitGroup

	ticker := time.NewTicker(time.Duration(settings.NamehelpSettings.ResolvConfig.Interval) * time.Millisecond)
	defer ticker.Stop()

	// add to waitGroup and launch goroutine to do lookup
	waitGroup.Add(1)
	insertion := false
	go routine_DoLookup(nameserver, dnsClient, &waitGroup, requestMessage, net, resultChannel, doID, insertion)

	// but exit early, if we have an answer
	select {
	case resultMessage := <-resultChannel:
		log.WithFields(log.Fields{
			"id":          doID,
			"name server": nameserver,
			"message":     resultMessage.String()}).Debug("Resolver: Response from nameserver")
		return resultMessage, nil
	case <-ticker.C:
		break
	}

	// wait for the nameserver to finish or timeout
	timeoutDuration := time.Duration(300 * time.Millisecond)
	isTimeout := waitTimeout(&waitGroup, timeoutDuration)
	if isTimeout {
		log.WithFields(log.Fields{
			"id":          doID,
			"query":       qname,
			"name server": nameserver,
			"time out":    timeoutDuration.Nanoseconds() / 1e6}).Warn("Resolver: DNS lookup at nameserver timed out.")
	}

	select {
	case resultMessage := <-resultChannel:
		// success
		log.WithFields(log.Fields{
			"id":          doID,
			"name server": nameserver,
			"message":     resultMessage.String()}).Debug("Resolver: Response from nameserver for DR successfull")
		return resultMessage, nil
	default:
		log.WithFields(log.Fields{
			"id":          doID,
			"name server": nameserver}).Debug("Resolver: Response from nameserver for DR is: [nil] (SERVFAIL?)")
		return nil, ResolvError{qname, net, []string{nameserver}}
	}
}

// Shard generates a random set of nameservers for the client to use
// Returns a random subset of all DoH resolvers
func (resolver *Resolver) Shard() []proxy.Server {
	rand.Seed(time.Now().UnixNano())

	// Sharding: to randomize the list of resolvers each time
	rand.Seed(time.Now().UnixNano())
	rand.Shuffle(len(Client.Resolvers), func(i, j int) { Client.Resolvers[i], Client.Resolvers[j] = Client.Resolvers[j], Client.Resolvers[i] })

	// Make sure at least one resolver is included
	// Also try to make at least one resolver not selected
	log.WithFields(log.Fields{
		"resolversLength": len(Client.Resolvers),
		"resolvers":       Client.Resolvers}).Debug("Resolver: These are the shuffled resolvers")
	return Client.Resolvers

}

// LookupAtNameservers asks each nameserver in top-to-bottom fashion
// Starts a new request on every interval tick
// Will return as early as possible (have an answer)
// It returns an error if no request has succeeded.
func (resolver *Resolver) LookupAtNameservers(net string, requestMessage *dns.Msg, nameservers []string,
	doID int, dohEnabled bool, experiment bool, _proxy bool, ResolverMapping map[string][]string,
	PrivacyEnabled bool, Racing bool, Decentralized bool, BestResolvers []string, DNSDistribution map[string][]int64, DNSTime int, Top50Websites []string, Filter bloom.BloomFilter) (resultMessage *dns.Msg, err error) {
	var insertionFactor int
	insertion := false
	if experiment && !dohEnabled {
		nameservers = utils.AddPortToEach(nameservers, resolver.Config.Port)
	}

	dnsClient := &dns.Client{
		Net:          net,
		ReadTimeout:  resolver.Timeout(),
		WriteTimeout: resolver.Timeout(),
	}

	resultChannel := make(chan *dns.Msg, 1)
	var waitGroup sync.WaitGroup

	// Reaper for channel
	defer func(wg *sync.WaitGroup, c chan *dns.Msg) {
		go func(wg *sync.WaitGroup, c chan *dns.Msg) {
			wg.Wait()
			close(c)
		}(wg, c)
	}(&waitGroup, resultChannel)

	ticker := time.NewTicker(time.Duration(settings.NamehelpSettings.ResolvConfig.Interval) * time.Millisecond)
	defer ticker.Stop()
	// Start lookup on each nameserver top-down, in every second
	// If resolver provided use that, otherwise shard
	var resolvers []string

	_question := requestMessage.Question[0]
	question := strings.Split(_question.String()[1:], ".\tIN\t")[0]

	var domain string
	// The experiment flag is turned on when testing individual resolvers and is off when testing DoHProxy and SubRosa
	if experiment {
		resolvers = nameservers
	} else if !experiment && PrivacyEnabled {
		// This condition is true when Privacy flag is turned on for DoHProxy and SubRosa, and all same 2lds go to the same resolver
		insertionFactor = 3 // The number of requests inserted per request not found in top sites
		val := strings.Split(question, "\\")
		if len(val) == 1 {
			domain = question
			log.WithFields(log.Fields{
				"website": domain}).Debug("Resolver: Using original website name")
		} else {
			domain = val[0]
			log.WithFields(log.Fields{
				"website": domain}).Debug("Resolver: This is the domain of the website")
		}

		secondld := domainutil.DomainPrefix(domain)
		if secondld != "" {
			log.WithFields(log.Fields{
				"go2ld":                   secondld,
				"question_requestMessage": requestMessage,
				"question_name":           _question.Name,
				"website":                 domain}).Debug("Resolver: Found second level domain")
			domain = secondld
		} else {
			log.WithFields(log.Fields{
				"go2ld":   secondld,
				"website": domain}).Error("Resolver: Error finding second level domain")
		}
		if Filter.Test([]byte(domain)) {
			insertion = false
		} else {
			insertion = true
		}
		log.WithFields(log.Fields{
			"go2ld":     secondld,
			"insertion": insertion}).Error("Resolver: This is the value of insertion")

		mutex.Lock()
		val, ok := ResolverMapping[domain]
		mutex.Unlock()

		if ok {
			if !_proxy && len(val) == 1 {
				// if the resolvermapping has only one resolver and we are testing Onoma,
				// then add another resolver to the dictionary
				resolvers = val
				dohResolvers := resolver.Shard()
				for _, resolver := range dohResolvers {
					if resolver.Name != val[0] {
						resolvers = append(resolvers, resolver.Name)
						break
					}
				}
				mutex.Lock()
				ResolverMapping[domain] = resolvers
				mutex.Unlock()
			} else {
				resolvers = val
			}
			log.WithFields(log.Fields{
				"resolvers": resolvers,
				"website":   domain}).Debug("Resolver: These resolvers assigned to the domain")
		} else {
			// if domain not found in resolvermapping and if testing DoHProxy, shard and select a random resolver
			if _proxy {
				dohResolvers := resolver.Shard()
				for _, resolver := range dohResolvers {
					resolvers = append(resolvers, resolver.Name)
					break
				}
				mutex.Lock()
				ResolverMapping[domain] = resolvers
				mutex.Unlock()
			} else {
				// if domain not found in the resolvermapping and if testing SubRosa, shard and select two random resolvers for racing
				// and the remaining 4 from the bestresolvers stored

				dohResolvers := resolver.Shard()
				for _, resolver := range dohResolvers {
					found := 0
					for _, r := range BestResolvers {
						if r == resolver.Name {
							found = 1
							break
						}
					}
					if found == 1 {
						continue
					}
					if len(resolvers) >= 2 {
						break
					}

					resolvers = append(resolvers, resolver.Name)
				}
				mutex.Lock()
				ResolverMapping[domain] = resolvers
				mutex.Unlock()
			}
		}
		for _, r := range BestResolvers {
			resolvers = append(resolvers, r)
		}

	} else {
		// if experiment is false and privacy is also not enabled and
		// if we are testing with DoHProxy or with racing disabled in SubRosa, pick one random resolver each time
		if _proxy || !Racing {
			dohResolvers := resolver.Shard()
			for _, resolver := range dohResolvers {
				resolvers = append(resolvers, resolver.Name)
				break
			}

		} else {
			// otherwise race between resolvers
			originDohResolvers := resolver.Shard()
			dohResolvers := originDohResolvers
			dohResolvers = dohResolvers[:1]

			ipInfo, err := utils.GetPublicIPInfo()
			if err != nil {
				log.Error("Error getting local IP info:", err)
				ipInfo = &utils.IPInfoResponse{Country: "US", Ip: "8.8.8.8"}
			}

			config := utils.ReadFromResolverConfig(ipInfo.Ip, ipInfo.Country)
			if config != nil {
				highSpread := config["high_spread"]
				bestResolvers := config["best_resolvers"]
				if utils.HasOverlap([]string{dohResolvers[0].Name}, highSpread) {
					// if the best resolver config exists, then only race when shard resolver is in high spread resolver list
					// choose one from the best resolvers to race
					chosenBestRsolver := utils.RandomChoice(bestResolvers)
					for _, dohRes := range originDohResolvers {
						if dohRes.Name == chosenBestRsolver {
							dohResolvers = append(dohResolvers, dohRes)
							break
						}
					}
				} // else, no need to race
			}

			for _, resolver := range dohResolvers {
				resolvers = append(resolvers, resolver.Name)
				m := int64(DNSTime)
				mutex.Lock()
				DNSDistribution[resolver.Name] = append(DNSDistribution[resolver.Name], m)
				mutex.Unlock()

			}
		}
	}
	log.WithFields(log.Fields{
		"proxy":          _proxy,
		"PrivacyEnabled": PrivacyEnabled,
		"Racing":         Racing,
		"Decentralized":  Decentralized,
		"resolvers":      resolvers}).Debug("Resolver: These are the resolvers assigned checkP")

	for _, nameserver := range resolvers {
		// add to waitGroup and launch goroutine to do lookup
		waitGroup.Add(1)

		if Decentralized {
			var _resolver proxy.Server
			for _, ns := range Client.Resolvers {
				if ns.Name == nameserver {
					_resolver = ns
					break
				}
			}
			if _resolver.Port == 443 {
				dohEnabled = true
				nameserver = _resolver.Name
			} else {
				dohEnabled = false
				_nameservers := utils.AddPortToEach([]string{_resolver.Upstream}, resolver.Config.Port)
				nameserver = _nameservers[0]
			}
		}
		if strings.Contains(nameserver, "127.0.0.1") {
			continue // don't send query to yourself (infinite recursion sort of)
		}

		// add to waitGroup and launch goroutine to do lookup
		// if doh enabled use that otherwise use dnslookup
		if dohEnabled {
			go routine_DoLookup_DoH(nameserver, dnsClient, &waitGroup, requestMessage, net, resultChannel, doID, false)
			insertion = true
			if insertion {
				for i := 0; i < insertionFactor; i++ {
					randomIndex := rand.Intn(len(Top50Websites))
					insertedDomain := Top50Websites[randomIndex]
					m := new(dns.Msg)
					m.SetQuestion(dns.Fqdn(insertedDomain), dns.TypeA)
					log.WithFields(log.Fields{
						"originalQuestion": requestMessage.Question[0].Name,
						"insertedQuestion": m.Question[0].Name,
						"insertedDomain":   insertedDomain}).Debug("ResolverDoH: This is the Inserted Question")
					go routine_DoLookup_DoH(nameserver, dnsClient, &waitGroup, m, net, resultChannel, doID, true)
				}
			}

		} else {
			go routine_DoLookup(nameserver, dnsClient, &waitGroup, requestMessage, net, resultChannel, doID, false)
			insertion = true
			if insertion {
				for i := 0; i < insertionFactor; i++ {

					randomIndex := rand.Intn(len(Top50Websites))
					insertedDomain := Top50Websites[randomIndex]
					m := new(dns.Msg)
					m.SetQuestion(dns.Fqdn(insertedDomain), dns.TypeA)
					log.WithFields(log.Fields{
						"originalQuestion": requestMessage.Question[0].Name,
						"insertedQuestion": m.Question[0].Name,
						"insertedDomain":   insertedDomain}).Debug("Resolver: This is the Inserted Question")
					go routine_DoLookup(nameserver, dnsClient, &waitGroup, m, net, resultChannel, doID, true)
				}
			}
		}

		// check for response or interval tick
		select {
		case result := <-resultChannel:
			// exit early if we have an answer
			return result, nil
		default:
			log.WithFields(log.Fields{
				"ticker.C": ticker.C}).Debug("Resolver: time ticked sending query to another resolver")
			// when interval ticks, repeat loop
			continue
		}
	}

	// go routines have finished we check if we get anything on resultChannel otherwise it's a serve fail
	if Racing {
		lookupFinished := make(chan bool, 1)
		go func(lookupFinished chan bool, waitGroup *sync.WaitGroup) {
			log.WithFields(log.Fields{
				"question": question}).Debug("Resolver: Waiting for lookup queries to finish.")
			waitGroup.Wait() // wait for all the goroutines to finish
			log.WithFields(log.Fields{
				"question": question}).Debug("Resolver: All lookup queries have finished.")
			lookupFinished <- true
		}(lookupFinished, &waitGroup)

		// while waiting for previous go routines to finish, we are listening on result Channel for a resultmsg, if we get it,
		//we return early or are listening on lookupFinished channel for prev goroutines to finish
		select {
		case resultMessage := <-resultChannel:
			// at least one succeeded
			log.WithFields(log.Fields{
				"question": question,
				"response": resultMessage.String()}).Debug("Resolver: Early Response from nameserver")
			return resultMessage, nil
		case <-lookupFinished:
			log.WithFields(log.Fields{
				"question": question}).Debug("Resolver: WaitGroup done for all lookup queries")
		}
	} else {
		// racing is false so we just wait for go routines to finish
		log.WithFields(log.Fields{
			"id": doID}).Debug("Resolver: Racing disabled, Waiting for lookup queries to finish.")
		waitGroup.Wait() // wait for all the goroutines to finish
		log.WithFields(log.Fields{
			"id": doID}).Debug("Resolver: Racing disabled, All lookup queries have finished.")
	}

	// go routines have finished we check if we get anything on resultChannel otherwise it's a serve fail
	select {
	case resultMessage := <-resultChannel:
		// at least one succeeded
		log.WithFields(log.Fields{
			"id":       doID,
			"response": resultMessage.String()}).Debug("Resolver: Response from nameserver(s)")
		return resultMessage, nil
	default:
		// all had SERVFAIL errors
		log.WithFields(log.Fields{
			"id": doID}).Debug("Resolver: Response from nameserver(s) is: [nil]  (all SERVFAIL?)")
		qname := requestMessage.Question[0].Name
		return nil, ResolvError{qname, net, resolver.Nameservers()}
	}
}

// Lookup performs dns lookup at the specific resolver for the given message
// Returns dns response message
func (resolver *Resolver) Lookup(net string, requestMessage *dns.Msg, doID int, _proxy bool,
	ResolverMapping map[string][]string, PrivacyEnabled bool, Racing bool, Decentralized bool, BestResolvers []string, DNSDistribution map[string][]int64, DNSTime int, Top50Websites []string, Filter bloom.BloomFilter) (message *dns.Msg, err error) {
	nameservers := resolver.Config.Servers
	dohEnabled := true
	experiment := false

	return resolver.LookupAtNameservers(net, requestMessage, nameservers, doID, dohEnabled, experiment, _proxy, ResolverMapping, PrivacyEnabled, Racing, Decentralized, BestResolvers, DNSDistribution, DNSTime, Top50Websites, Filter)
}

// Nameservers return the array of nameservers, with port number appended.
// '#' in the name is treated as port separator, as with dnsmasq.
func (resolver *Resolver) Nameservers() (nameservers []string) {
	list := resolver.Config.Servers
	port := resolver.Config.Port

	return utils.AddPortToEach(list, port)
}

// Timeout returns a time duration specified in the configuration
func (resolver *Resolver) Timeout() time.Duration {
	return time.Duration(resolver.Config.Timeout) * time.Second
}
