package main

// Dependencies
// github.com/alexthemonk/aquarium
// gopkg.in/natefinch/lumberjack.v2
// github.com/kardianos/service
// github.com/miekg/dns
// github.com/konsorten/go-windows-terminal-sequences
// github.com/alexthemonk/DoH_Proxy
// go.mongodb.org/mongo-driver/mongo
// github.com/inconshreveable/go-update
// github.com/blang/semver
// github.com/rhysd/go-github-selfupdate/selfupdate

//go:generate go build -o bin/namehelp namehelp

// For Building other OS on MacOS
/*
//go:generate env GOOS=darwin GOARCH=amd64 go build -o Sub-Rosa/src/bin/MacOS/namehelp namehelp
//go:generate env GOOS=windows GOARCH=amd64 go build -o Sub-Rosa/src/bin/Windows/namehelp.exe namehelp
//go:generate env GOOS=linux GOARCH=amd64 go build -o Sub-Rosa/src/bin/Linux/namehelp namehelp
*/

func main() {}
