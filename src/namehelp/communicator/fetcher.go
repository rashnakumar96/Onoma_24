package communicator

import (
	"context"
	"time"

	log "github.com/sirupsen/logrus"
	"go.mongodb.org/mongo-driver/mongo"
	"go.mongodb.org/mongo-driver/mongo/options"
)

// Fetcher is responsible for down-flow data communicator
//  by fetching data in one-direction from the server to local
type Fetcher struct {
	// MongoStr stores the connection string for MongoDB
	MongoStr string
}

// NewFetcher declares and initializes a fetcher
func NewFetcher() *Fetcher {
	fetcher := Fetcher{}

	// DB settings
	// Read only
	fetcher.MongoStr = "mongodb+srv://client:client@dataserver.npwhs.mongodb.net/test?retryWrites=true&w=majority"

	return &fetcher
}

// FetchOne contacts the MongoDB and fetch data from specified db and collection with given filters
// Return the decoded map of string as keys and interface as values
func (c *Fetcher) FetchOne(databaseName string, collectionName string, filter map[string]string) (map[string]interface{}, error) {
	ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
	defer cancel()
	client, err := mongo.Connect(ctx, options.Client().ApplyURI(
		c.MongoStr,
	))
	if err != nil {
		log.WithFields(log.Fields{
			"fetcher": c,
			"error":   err,
		}).Error("Fetcher: Creating Mongo Client failed")
		return nil, err
	}

	collection := client.Database(databaseName).Collection(collectionName)

	result := collection.FindOne(context.Background(), filter)
	var data map[string]interface{}
	err = result.Decode(&data)
	if err != nil {
		log.WithFields(log.Fields{
			"fetcher": c,
			"error":   err,
		}).Error("Fetcher: Decoding Failed")
		return nil, err
	}

	log.WithFields(log.Fields{
		"result":     result,
		"db":         databaseName,
		"collection": collectionName,
	}).Info("Fetcher: Data Fetched.")

	return data, nil
}
