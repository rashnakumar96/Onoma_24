package main

//go:generate go get -u github.com/kardianos/osext/
//go:generate go get -u github.com/kardianos/service/
//go:generate go get -u github.com/miekg/dns/
//go:generate go get -u github.com/sirupsen/logrus/
//go:generate go get -u go.mongodb.org/mongo-driver/mongo
//go:generate go get -u gopkg.in/natefinch/lumberjack.v2
//go:generate go get github.com/bobesa/go-domain-util/domainutil
//go:generate go get -u github.com/bits-and-blooms/bloom

//go:generate go build -o bin/test/namehelp namehelp
//go:generate go get github.com/cloudflare/odoh-client-go
//go:generate go build -o bin/test/odoh-client github.com/cloudflare/odoh-client-go/cmd

func main() {}
