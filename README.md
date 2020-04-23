# Sub Rosa
More software engineering version of Name-Secure

[Sub Rosa](https://en.wikipedia.org/wiki/Sub_rosa)

## Build
```
export GOPATH=`pwd`
go generate
```
After this step you will have a binary named ```namehelp``` in ```/bin``` directory

### To run the service directly:
From the project home directory
```
sudo ./bin/namehelp --service install
sudo ./bin/namehelp --sertice start
```

### To stop the service:
```
sudo ./bin/namehelp --service stop
```

### To uninstall:
```
./bin/namehelp --service uninstall
```

## Build app for MacOS
The app is based on Electron framework
From the project home directory
```
cd Sub-Rosa/
npm make-mac
```
In the current directory a new folder ```out``` will be created
The app will be in ```out/Sub-Rosa-darwin-x64/``` directory
The package of the app will be in ```out/make/``` directory

### To run app without building 
From the project home directory
```
cd Sub-Rosa/
npm start
```