package reporter

import (
	"fmt"
)

// Reporter is responsible for communicating data with remote server
type Reporter struct {
	// MongoStr stores the connection string for MongoDB
	MongoStr string

	// Version stores the current app version
	// This entry is to be included in the schema when posting data
	Version string
}

// NewReporter declares and initializes a reporter
func NewReporter(version string) *Reporter {
	fmt.Println("TODO", version)

	reporter := Reporter{}
	reporter.Version = version
	return &reporter
}

// Schema is the root class interface for data entry
type Schema struct {
	// Country holds the client's current location, using Alpha-2 country code
	Country string

	// Time holds the client's measurement time
	// This value is the string returned by time.Now(), and parsed using .String() method
	Time string

	// Version stores the current version of the client side app
	Version string
}

// PushToMongoDB pushes data entry to the given database
func (r *Reporter) PushToMongoDB(data interface{}) error {
	return nil
}
