package handler

import (
	"namehelp/utils"
	"testing"

	"github.com/miekg/dns"
	"github.com/stretchr/testify/assert"
)

func TestDoSimpleDirectResolutionOfCname(t *testing.T) {
	namehelpProgram.initializeDnsServers()

	answerMessage := utils.BuildDnsQuery("doesn't matter", dns.TypeA, 42, true)
	cName := "clients.l.google.com."

	namehelpProgram.dnsQueryHandler.doSimpleDirectResolutionOfCname("tcp", answerMessage, cName, 0)
	namehelpProgram.dnsQueryHandler.doSimpleDirectResolutionOfCname("udp", answerMessage, cName, 0)
}

func TestAddOriginalDnsServers(t *testing.T) {
	originalDnsServersMap := map[string][]string{
		"Wi-Fi":                []string{"8.8.8.8", "1.2.3.4"},
		"Thunderbolt Ethernet": []string{"8.8.8.8", "1.2.3.4", "0.0.0.0"},
	}
	newList := addOriginalDnsServers(PublicDnsServers, originalDnsServersMap)
	goldlist := append(PublicDnsServers, "1.2.3.4", "0.0.0.0")
	assert.Equal(t, goldlist, newList, "newList [%v] does not equal goldList [%v]", newList, goldlist)

	originalDnsServersMap = map[string][]string{
		"Wi-Fi":                []string{"empty"},
		"Thunderbolt Ethernet": []string{""},
	}
	newList = addOriginalDnsServers(PublicDnsServers, originalDnsServersMap)
	goldlist = PublicDnsServers
	assert.Equal(t, goldlist, newList, "newList [%v] does not equal goldList [%v]", newList, goldlist)

	// NOTE we do not want to add localhost to our list of servers.  The client has already asked localhost (namehelp)
	//      for a lookup; we do not want to turn around and ask ourselves
	originalDnsServersMap = map[string][]string{
		"Wi-Fi":                []string{"127.0.0.1"},
		"Thunderbolt Ethernet": []string{"127.0.0.1"},
	}
	newList = addOriginalDnsServers(PublicDnsServers, originalDnsServersMap)
	goldlist = PublicDnsServers
	assert.Equal(t, goldlist, newList, "newList [%v] does not equal goldList [%v]", newList, goldlist)
}
