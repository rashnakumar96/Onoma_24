package main

//go:generate go build -o bin/namehelp namehelp
//go:generate go build -o Sub-Rosa/src/bin/MacOS/namehelp namehelp
//go:generate go build -o bin/Sub-Rosa
//go:generate env GOOS=windows GOARCH=amd64 go build -o Sub-Rosa/src/bin/Windows/namehelp namehelp
//go:generate env GOOS=linux GOARCH=amd64 go build -o Sub-Rosa/src/bin/Linux/namehelp namehelp

// Dependencies
// github.com/alexthemonk/aquarium
// gopkg.in/natefinch/lumberjack.v2
// github.com/kardianos/service
// github.com/miekg/dns
// github.com/konsorten/go-windows-terminal-sequences
