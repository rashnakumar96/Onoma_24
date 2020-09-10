package main

// Dependencies
//go:generate go get -u github.com/alexthemonk/aquarium
//go:generate go get -u gopkg.in/natefinch/lumberjack.v2
//go:generate go get -u github.com/kardianos/service
//go:generate go get -u github.com/miekg/dns
//go:generate go get -u github.com/konsorten/go-windows-terminal-sequences
//go:generate go get -u github.com/alexthemonk/DoH_Proxy
//go:generate go get -u go.mongodb.org/mongo-driver
//go:generate go get -u github.com/inconshreveable/go-update
//go:generate go get -u github.com/alexthemonk/DoH_Proxy

//go:generate go build -o bin/namehelp namehelp
//go:generate env GOOS=darwin GOARCH=amd64 go build -o Sub-Rosa/src/bin/MacOS/namehelp namehelp
//go:generate env GOOS=windows GOARCH=amd64 go build -o Sub-Rosa/src/bin/Windows/namehelp namehelp
//go:generate env GOOS=linux GOARCH=amd64 go build -o Sub-Rosa/src/bin/Linux/namehelp namehelp

func main() {}
