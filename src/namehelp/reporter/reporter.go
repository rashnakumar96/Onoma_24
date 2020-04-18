package reporter

import (
	"fmt"
)

// Reporter is responsible for communicating data with remote server
type Reporter struct {
	// Source is the data center source url or IP
	Source string
}

// NewReporter declare and initialize a reporter
func NewReporter() *Reporter {
	fmt.Println("TODO")

	reporter := Reporter{
		Source: "127.0.0.1",
	}
	return &reporter
}
