package rpc

import log "github.com/sirupsen/logrus"

// Communicator is responsible for listenning to incomming command
//  from either local scripts or remote master server
type Communicator struct {
	// Port specifies the port number listening on
	//  Must be greater than 1024
	Port int
}

// NewCommunicator initialize a communicator object
func NewCommunicator(port int) *Communicator {
	if port < 1024 {
		log.Fatal("Error: Invalid port number")
	}
	communicator := Communicator{}
	communicator.Port = port

	return &communicator
}
