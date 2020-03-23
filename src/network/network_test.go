package network

import (
	"testing"
	"github.com/stretchr/testify/assert"
	"fmt"
)

func TestDhcpGetDnsServersForInterface(t *testing.T) {
	networkInterface := "en0"
	listOfDnsServers := DhcpGetDnsServersForInterface(networkInterface)
	fmt.Printf("Local DNS servers %v for network interface [%s]\n", listOfDnsServers, networkInterface)

	assert.True(t, len(listOfDnsServers) > 0, "DHCP returned empty list of DNS servers: [%v]",
		listOfDnsServers)

	listOfDnsServers = DhcpGetDnsServersForInterface("fake_interface")
	assert.True(t, len(listOfDnsServers) == 0, "Expected empty list, got %v", listOfDnsServers)
}

func TestDhcpGetNumberOfInterfaces(t *testing.T) {
	numberOfInterfaces := DhcpGetNumberOfInterfaces()

	assert.True(t, numberOfInterfaces > 0, "Expected positive number of interfaces, got [%d]",
		numberOfInterfaces)
}

func TestDhcpGetLocalDnsServers(t *testing.T) {
	localDnsServers := DhcpGetLocalDnsServers()
	fmt.Printf("Local DNS servers %v\n", localDnsServers)

	assert.True(t, len(localDnsServers) > 0,
		"DHCP returned no local DNS servers on all searched network interfaces")
}
