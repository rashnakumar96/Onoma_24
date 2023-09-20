# Sub Rosa
More software engineering version of Name-Secure

[Sub Rosa](https://en.wikipedia.org/wiki/Sub_rosa)

## Build
```
export GOPATH=`pwd`
go generate
```
After this step you will have a binary named ```namehelp``` in ```/bin/test``` directory

### To run the service directly:
From the project home directory
```
sudo ./bin/test/namehelp --service install
sudo ./bin/test/namehelp --sertice start
```

### To stop the service:
```
sudo ./bin/test/namehelp --service stop
```

### To uninstall:
```
./bin/test/namehelp --service uninstall
```
Output/debug statements generated in log files in the bin folder where the executable is -> either in bin or bin/test. Change service command accordingly.
