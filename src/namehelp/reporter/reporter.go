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
func NewReporter() {
	fmt.Println("TODO")
}
