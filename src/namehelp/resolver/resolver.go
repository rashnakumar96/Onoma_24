// based heavily upon github.com/kenshinx/godns/resolver.go

package resolver

import (
	"bytes"
	"errors"
	"fmt"
	"math/rand"
	"os/exec"
	"strings"
	"sync"
	"time"

	// "namehelp/proxy"
	"namehelp/settings"
	"namehelp/utils"

	proxy "github.com/alexthemonk/DoH_Proxy"
	"github.com/miekg/dns"
	log "github.com/sirupsen/logrus"
)

// Client for resolver proxy that translate DNS to DoH
var Client proxy.Client

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
func routine_DoLookup(nameserver string, dnsClient *dns.Client, waitGroup *sync.WaitGroup, requestMessage *dns.Msg, net string, resultChannel chan *dns.Msg, doID int) {

	defer waitGroup.Done() // when this goroutine finishes, notify the waitGroup

	qname := requestMessage.Question[0].Name
	qType := requestMessage.Question[0].Qtype

	responseMessage, rtt, err := dnsClient.Exchange(requestMessage, nameserver)
	if err != nil {
		log.WithFields(log.Fields{
			"id":          doID,
			"query":       qname,
			"name server": nameserver}).Error("Socket error")
		log.WithFields(log.Fields{
			"id":    doID,
			"error": err.Error()}).Error("Error message for socket error")
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
			"name server": nameserver}).Info("Failed to get a valid answer for query from nameserver")
		if responseMessage.Rcode == dns.RcodeServerFailure {
			// SERVFAIL: don't provide response because other DNS servers may have better luck
			log.WithFields(log.Fields{"Rcode": responseMessage.Rcode}).Error("ServFail")
			return
		} else {
			log.WithFields(log.Fields{"Rcode": responseMessage.Rcode}).Error("NXDOMAIN ERROR")
		}
	} else {
		// success
		log.WithFields(log.Fields{
			"id":          doID,
			"domain name": utils.UnFullyQualifyDomainName(qname),
			"query type":  dns.TypeToString[qType],
			"name server": nameserver,
			"net":         net,
			"tll":         rtt}).Info("resolve successfully")
	}

	// use select statement with default to try the send without blocking
	select {
	// try to send response on channel
	case resultChannel <- responseMessage:
		log.WithFields(log.Fields{
			"id":          doID,
			"name server": nameserver}).Debug("name server won the resolver race.")
	default:
		// if another goroutine already sent on channel and the message is not yet read
		// we simply return in order to invoke the deferred waitGroup.Done() call
		log.WithFields(log.Fields{
			"id":          doID,
			"name server": nameserver}).Debug("name server DID NOT won the resolver race.")
		return
	}
}

// For initial DoH resolution
func routine_DoLookup_DoH(nameserver string, dnsClient *dns.Client, waitGroup *sync.WaitGroup, requestMessage *dns.Msg,
	net string, resultChannel chan *dns.Msg, doID int) {

	defer waitGroup.Done() // when this goroutine finishes, notify the waitGroup

	qname := requestMessage.Question[0].Name
	qType := requestMessage.Question[0].Qtype
	log.WithFields(log.Fields{"nameserver": nameserver}).Info("DoH look up at Namehelp")

	//Match the resolverName with the resolver
	var resolver proxy.Server
	for _, ns := range Client.Resolvers {
		if ns.Name == nameserver {
			resolver = ns
			break
		}
	}
	log.WithFields(log.Fields{"nameserver": resolver}).Info("DoH look up at Namehelp")

	responseMessage, err := Client.Resolve(requestMessage, resolver)

	if err != nil {
		log.WithFields(log.Fields{
			"id":          doID,
			"query":       qname,
			"name server": nameserver}).Error("Socket error")
		log.WithFields(log.Fields{
			"id":    doID,
			"error": err.Error()}).Error("Error message for socket error")
		return
	}
	log.Info("Response from DoH", nameserver)

	// If SERVFAIL happens, should return immediately and try another upstream resolver.
	// However, other Error codes like NXDOMAIN are a clear response stating
	// that it has been verified no such domain exists and asking other resolvers
	// would make no sense. See more about #20
	if responseMessage != nil && responseMessage.Rcode != dns.RcodeSuccess {
		// failure
		log.WithFields(log.Fields{
			"id":          doID,
			"query":       qname,
			"name server": nameserver}).Info("Failed to get a valid answer for query from nameserver")
		if responseMessage.Rcode == dns.RcodeServerFailure {
			// SERVFAIL: don't provide response because other DNS servers may have better luck
			log.WithFields(log.Fields{"Rcode": responseMessage.Rcode}).Error("ServFail")
			return
		} else {
			log.WithFields(log.Fields{"Rcode": responseMessage.Rcode}).Error("NXDOMAIN ERROR")

			// NXDOMAIN and other failures: confirmed failure so provide the response (jump to end of function)
		}
	} else {
		// success
		log.WithFields(log.Fields{
			"id":          doID,
			"domain name": utils.UnFullyQualifyDomainName(qname),
			"query type":  dns.TypeToString[qType],
			"name server": nameserver,
			"net":         net}).Info("resolve successfully")

	}

	// use select statement with default to try the send without blocking
	select {
	// try to send response on channel
	case resultChannel <- responseMessage:
		log.WithFields(log.Fields{
			"id":          doID,
			"name server": nameserver}).Info("name server won the resolver race.")
	default:
		// if another goroutine already sent on channel and the message is not yet read
		// we simply return in order to invoke the deferred waitGroup.Done() call
		log.WithFields(log.Fields{
			"id":          doID,
			"name server": nameserver}).Info("name server DID NOT win the resolver race.")
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
			"name server": nameserver}).Error("Trying to send query to self")
		return &dns.Msg{}, errors.New("Cannot send query to self")
	}

	log.WithFields(log.Fields{
		"id":           doID,
		"query":        requestMessage.Question[0].String(),
		"name server":  nameserver,
		"net":          net,
		"full request": requestMessage.String()}).Info("Performing lookup at nameserver for DR")

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
	go routine_DoLookup(nameserver, dnsClient, &waitGroup, requestMessage, net, resultChannel, doID)

	// but exit early, if we have an answer
	select {
	case resultMessage := <-resultChannel:
		log.WithFields(log.Fields{
			"id":          doID,
			"name server": nameserver,
			"message":     resultMessage.String()}).Info("Response from nameserver")
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
			"time out":    timeoutDuration.Nanoseconds() / 1e6}).Warn("DNS lookup at nameserver timed out.")
	}

	select {
	case resultMessage := <-resultChannel:
		// success
		log.WithFields(log.Fields{
			"id":          doID,
			"name server": nameserver,
			"message":     resultMessage.String()}).Info("Response from nameserver for DR successfull")
		return resultMessage, nil
	default:
		log.WithFields(log.Fields{
			"id":          doID,
			"name server": nameserver}).Info("Response from nameserver for DR is: [nil] (SERVFAIL?)")
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
	// cutOff := rand.Intn(len(Client.Resolvers)-1) + 1
	// cutOff:=3
	// return Client.Resolvers[:cutOff]
	log.WithFields(log.Fields{
		"resolvers": Client.Resolvers}).Info("These are the shuffled resolvers")
	return Client.Resolvers

}

// LookupAtNameservers asks each nameserver in top-to-bottom fashion
// Starts a new request on every interval tick
// Will return as early as possible (have an answer)
// It returns an error if no request has succeeded.
func (resolver *Resolver) LookupAtNameservers(net string, requestMessage *dns.Msg, nameservers []string,
	doID int, dohEnabled bool, experiment bool, proxy bool, ResolverMapping map[string][]string, 
	PrivacyEnabled bool, Racing bool) 
	(resultMessage *dns.Msg, err error) {

	if experiment && !dohEnabled {
		nameservers = utils.AddPortToEach(nameservers, resolver.Config.Port)
	}

	dnsClient := &dns.Client{
		Net:          net,
		ReadTimeout:  resolver.Timeout(),
		WriteTimeout: resolver.Timeout(),
	}

	resultChannel := make(chan *dns.Msg, 1)
	defer close(resultChannel)
	var waitGroup sync.WaitGroup

	ticker := time.NewTicker(time.Duration(settings.NamehelpSettings.ResolvConfig.Interval) * time.Millisecond)
	defer ticker.Stop()
	// Start lookup on each nameserver top-down, in every second
	//if resolver provided use that, otherwise shard
	var resolvers []string

	_question := requestMessage.Question[0]
	question := strings.Split(_question.String()[1:], ".\tIN\t")[0]
	var mutex = &sync.Mutex{}
	var stdout bytes.Buffer
	var domain string
	// The eperiment flag is turned on when testing individual resolvers and is off when testing DoHProxy and SubRosa
	if experiment {
		// Experiment mode, testing only the specified resolver
		resolvers = nameservers
	} else if !experiment && PrivacyEnabled {
		// This condition is true when Privacy flag is turned on for DoHProxy and SubRosa, and all same 2lds go to the same resolver
		val := strings.Split(question, "\\")
		if len(val) == 1 {
			domain = question
			log.WithFields(log.Fields{
				"website": domain}).Info("Using original website name")
		} else {
			domain = val[0]
			log.WithFields(log.Fields{
				"website": domain}).Info("This is the domain of the website")
		}
		cmd := exec.Command("python3", "2ld.py", "https://"+domain)
		cmd.Stdout = &stdout
		err := cmd.Run()
		if err != nil {
			log.WithFields(log.Fields{
				"error":   err.Error(),
				"website": domain}).Info("Error: finding second level domain")
		} else {
			log.WithFields(log.Fields{
				"domain": domain,
				"2ld":    stdout.String()}).Info("Found second level domain")
			domain = stdout.String()
		}
		if val, ok := ResolverMapping[domain]; ok {
			//do something here
			if !proxy && len(val) == 1 {
				//if the resolvermapping has only one resolver and we are testing SubRosa, then add another resolver to the dictionary
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
				"website":   domain}).Info("These resolvers assigned to the domain")
		} else {
			//if domain not found in resolvermapping and if testing DoHProxy, shard and select a random resolver
			if proxy {
				dohResolvers := resolver.Shard()
				for _, resolver := range dohResolvers {
					resolvers = append(resolvers, resolver.Name)
					break
				}
				mutex.Lock()
				ResolverMapping[domain] = resolvers
				mutex.Unlock()
			} else {
				//if domain not found in the resolvermapping and if testing SubRosa, shard and select two random resolvers for racing

				dohResolvers := resolver.Shard()
				dohResolvers = dohResolvers[:2]
				for _, resolver := range dohResolvers {
					resolvers = append(resolvers, resolver.Name)
				}
				mutex.Lock()
				ResolverMapping[domain] = resolvers
				mutex.Unlock()
			}
		}

	} else {
		//if experiment is false and privacy is also not enabled and
		//if we are testing with DoHProxy or with racing disabled in SubRosa, pick one random resolver each time
		if proxy || !Racing {
			dohResolvers := resolver.Shard()
			for _, resolver := range dohResolvers {
				resolvers = append(resolvers, resolver.Name)
				break
			}

		} else {
			//otherwise race between two resolvers
			dohResolvers := resolver.Shard()
			dohResolvers = dohResolvers[:2]
			for _, resolver := range dohResolvers {
				resolvers = append(resolvers, resolver.Name)
			}
		}
	}
	log.WithFields(log.Fields{
		"proxy":          proxy,
		"PrivacyEnabled": PrivacyEnabled,
		"Racing":         Racing,
		"resolvers":      resolvers}).Info("These are the resolvers assigned")
	// for _, nameserver := range nameservers {
	for _, nameserver := range resolvers {
		if strings.Contains(nameserver, "127.0.0.1") {
			continue // don't send query to yourself (infinite recursion sort of)
		}

		// add to waitGroup and launch goroutine to do lookup
		waitGroup.Add(1)
		//if doh enabled use that otherwise use dnslookup
		if !dohEnabled {
			go routine_DoLookup(nameserver, dnsClient, &waitGroup, requestMessage, net, resultChannel, doID)
		} else {
			// go routine_DoLookup_DoH(nameserver.Name, dnsClient, &waitGroup, requestMessage, net, resultChannel, doID)
			go routine_DoLookup_DoH(nameserver, dnsClient, &waitGroup, requestMessage, net, resultChannel, doID)

		}

		// check for response or interval tick
		select {
		case result := <-resultChannel:
			// exit early if we have an answer
			return result, nil
		// case <-ticker.C:
		// 	log.WithFields(log.Fields{
		// 		"ticker.C": ticker.C}).Info("time ticked sending query to another resolver")
		// 	// when interval ticks, repeat loop
		// 	continue
		default:
			log.WithFields(log.Fields{
				"ticker.C": ticker.C}).Info("time ticked sending query to another resolver")
			// when interval ticks, repeat loop
			continue
		}

	}

	// // if we get here, all queries have been launched
	// log.WithFields(log.Fields{
	// 	"id": doID}).Info("Waiting for lookup queries to finish.")
	// waitGroup.Wait() // wait for all the goroutines to finish
	// log.WithFields(log.Fields{
	// 	"id": doID}).Info("All lookup queries have finished.")

	// if Racing enabled in subrosa wait for the go routines to finish in another go routine and when done write in lookupFinished channel
	if Racing {
		lookupFinished := make(chan bool, 1)
		go func(lookupFinished chan bool, waitGroup sync.WaitGroup) {
			log.WithFields(log.Fields{
				"question": question}).Info("Waiting for lookup queries to finish.")
			waitGroup.Wait() // wait for all the goroutines to finish
			log.WithFields(log.Fields{
				"question": question}).Info("All lookup queries have finished.")
			lookupFinished <- true
		}(lookupFinished, waitGroup)

		// while waiting for previous go routines to finish, we are listening on result Channel for a resultmsg, if we get it,
		//we return early or are listening on lookupFinished channel for prev goroutines to finish
		for {
			waitDone := false
			select {
			case resultMessage := <-resultChannel:
				// at least one succeeded
				log.WithFields(log.Fields{
					"question": question,
					"response": resultMessage.String()}).Info("Early Response from nameserver")
				return resultMessage, nil
			case <-lookupFinished:
				log.WithFields(log.Fields{
					"question": question}).Info("WaitGroup done for all lookup queries")
				waitDone = true
			}
			if waitDone {
				break
			}
		}
	} else {
		//racing is false so we just wait for go routines to finish
		log.WithFields(log.Fields{
			"id": doID}).Info("Racing disabled,Waiting for lookup queries to finish.")
		waitGroup.Wait() // wait for all the goroutines to finish
		log.WithFields(log.Fields{
			"id": doID}).Info("Racing disabled,All lookup queries have finished.")
	}

	//go routines have finished we check if we get anything on resultChannel otherwise it's a serve fail
	select {
	case resultMessage := <-resultChannel:
		// at least one succeeded
		log.WithFields(log.Fields{
			"id":       doID,
			"response": resultMessage.String()}).Info("Response from nameserver(s)")
		return resultMessage, nil
	default:
		// all had SERVFAIL errors
		log.WithFields(log.Fields{
			"id": doID}).Info("Response from nameserver(s) is: [nil]  (all SERVFAIL?)")
		qname := requestMessage.Question[0].Name
		return nil, ResolvError{qname, net, resolver.Nameservers()}
	}
}

// Lookup performs dns lookup at the specific resolver for the given message
// Returns dns response message
func (resolver *Resolver) Lookup(net string, requestMessage *dns.Msg, doID int, proxy bool, ResolverMapping map[string][]string, PrivacyEnabled bool, Racing bool) (message *dns.Msg, err error) {
	nameservers := resolver.Config.Servers
	dohEnabled := true
	experiment := false
	//    if (handler.DoHEnabled && handler.Experiment){
	// 	dnsServersToQuery=handler.DoHServersToTest
	// }else if (!handler.DoHEnabled && handler.Experiment){
	// 	dnsServersToQuery=handler.DNSServersToTest
	// }
	return resolver.LookupAtNameservers(net, requestMessage, nameservers, doID, dohEnabled, experiment, proxy, ResolverMapping, PrivacyEnabled, Racing)
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
