package communicator

import (
	"fmt"
	"net"
	"net/http"
	"net/rpc"

	log "github.com/sirupsen/logrus"
)

// RPCOperator is responsible for listenning to incomming rpc calls
//  from either local scripts or remote master server
type RPCOperator struct {
	// Port specifies the port number listening on
	//  Must be greater than 1024
	Port int

	// ShutDown channel looks for shutdown signals and stop the server
	ShutDown chan bool
}

// NewOperator initialize a rpcOperator object
func NewOperator(port int) *RPCOperator {
	if port < 1024 {
		log.Fatal("RPCOperator: Invalid port number - Must use non privileged port (>= 1024)")
	}
	rpcOperator := RPCOperator{}
	rpcOperator.Port = port
	rpcOperator.ShutDown = make(chan bool)

	return &rpcOperator
}

// Message is the rpc message struct
type Message struct{}

// Response is the rpc response struct
type Response struct{}

// Server is the rpc server struct
type Server struct{}

// Serve starts the rpc server and listen on port for incoming messages
func (c *RPCOperator) Serve() {
	server := new(Server)
	rpc.Register(server)
	rpc.HandleHTTP()
	portString := fmt.Sprintf(":%d", c.Port)
	listen, err := net.Listen("tcp", portString)

	if err != nil {
		log.WithFields(log.Fields{
			"error": err,
		}).Fatal("RPCOperator: rpc listen error")
	}
	go http.Serve(listen, nil)
	<-c.ShutDown
	close(c.ShutDown)
}

// HandleMessage is the rpc called by client and parse the message
//  to specific actions
func (c *RPCOperator) HandleMessage(msg *Message, res *Response) error {
	// TODO
	return nil
}
