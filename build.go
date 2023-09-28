package main

//go:generate go get -u github.com/alexthemonk/DoH_Proxy/
//go:generate go get -u github.com/kardianos/osext/
//go:generate go get -u github.com/kardianos/service/
//go:generate go get -u github.com/miekg/dns/
//go:generate go get -u github.com/sirupsen/logrus/
//go:generate go get -u go.mongodb.org/mongo-driver/mongo
//go:generate go get -u gopkg.in/natefinch/lumberjack.v2
//go:generate go get github.com/bobesa/go-domain-util/domainutil
//go:generate go get -u github.com/bits-and-blooms/bloom

//go:generate go build -o bin/test/namehelp namehelp

// For Building other OS on MacOS
/*
//go:generate env GOOS=darwin GOARCH=amd64 go build -o Sub-Rosa/src/bin/MacOS/namehelp namehelp
//go:generate env GOOS=windows GOARCH=amd64 go build -o Sub-Rosa/src/bin/Windows/namehelp.exe namehelp
//go:generate env GOOS=linux GOARCH=amd64 go build -o Sub-Rosa/src/bin/Linux/namehelp namehelp
*/

func main() {}
