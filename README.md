# Ónoma

**Ónoma** is an end-system resolver that enables users to leverage the benefits of third-party DNS services without 
sacrificing privacy or performance.

## Introduction
- **Ónoma** avoids DNS-based user-reidentification by inserting and sharding requests across
  resolvers, and improves performance by running resolution races among resolvers and reinstating the
  client-resolver proximity assumption content delivery networks rely on.

- This README provides instructions for installation, building, running, and uninstalling Ónoma.

## Installation

### Go Installation

```bash
brew update
brew install go
go version
```

### Python installation
```bash
brew update
brew install python
python3 --version
```

## Build Ónoma
```
export GOPATH=`pwd`
export GO111MODULE=auto
go generate
```
After this step you will have a binary named ```namehelp``` in ```/bin/test/``` directory

### To run the service directly:
From the project home directory
```
sudo ./bin/test/namehelp
```

In case log file is read-only status, run
```
sudo chmod -R 777 bin/test/namehelp.log
```

### To uninstall:
```
sudo ./bin/test/namehelp --service uninstall
```