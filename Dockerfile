FROM golang:1.15
RUN mkdir -p /app
WORKDIR /app
ADD . /app
ENV GOPATH=/app
RUN pwd
RUN go get github.com/alexthemonk/DoH_Proxy/
RUN go get github.com/kardianos/osext/
RUN go get github.com/kardianos/service/
RUN go get github.com/miekg/dns/
RUN go get github.com/sirupsen/logrus/
RUN go get go.mongodb.org/mongo-driver/mongo
RUN go get gopkg.in/natefinch/lumberjack.v2
RUN go generate
CMD ["./bin/namehelp"]
