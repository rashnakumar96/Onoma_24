package rpc

import (
	"fmt"
	"net"
	"net/http"
	"net/rpc"

	log "github.com/sirupsen/logrus"
)

// Communicator is responsible for listenning to incomming command
//  from either local scripts or remote master server
type Communicator struct {
	// Port specifies the port number listening on
	//  Must be greater than 1024
	Port int

	// ShutDown channel looks for shutdown signals and stop the server
	ShutDown chan bool
}

// NewCommunicator initialize a communicator object
func NewCommunicator(port int) *Communicator {
	if port < 1024 {
		log.Fatal("Communicator: Invalid port number - Must use non privileged port (>= 1024)")
	}
	communicator := Communicator{}
	communicator.Port = port
	communicator.ShutDown = make(chan bool)

	return &communicator
}

// Message is the rpc message struct
type Message struct{}

// Response is the rpc response struct
type Response struct{}

// Server is the rpc server struct
type Server struct{}

// Serve starts the rpc server and listen on port for incoming messages
func (c *Communicator) Serve() {
	server := new(Server)
	rpc.Register(server)
	rpc.HandleHTTP()
	portString := fmt.Sprintf(":%d", c.Port)
	listen, err := net.Listen("tcp", portString)

	if err != nil {
		log.WithFields(log.Fields{
			"error": err,
		}).Fatal("Communicator: rpc listen error")
	}
	go http.Serve(listen, nil)
	<-c.ShutDown
	close(c.ShutDown)
}

// HandleMessage is the rpc called by client and parse the message
//  to specific actions
func (c *Communicator) HandleMessage(msg *Message, res *Response) error {
	// TODO
	return nil
}
