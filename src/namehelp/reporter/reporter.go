package reporter

import (
	"context"
	"fmt"
	"time"

	log "github.com/sirupsen/logrus"
	"go.mongodb.org/mongo-driver/mongo"
	"go.mongodb.org/mongo-driver/mongo/options"
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

	// DB settings
	reporter.MongoStr = "mongodb+srv://subrosa_client:subrosa@doh.eyeb4.mongodb.net/test?retryWrites=true&w=majority"

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

	// Data stores the actual data entry
	Data interface{}
}

// PushToMongoDB pushes data entry to the given database
// Takes a list of data objects to be pushed
// Each data object should be inheriting Schema
func (r *Reporter) PushToMongoDB(databaseName string, collectionName string, data ...interface{}) error {
	ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
	defer cancel()
	client, err := mongo.Connect(ctx, options.Client().ApplyURI(
		r.MongoStr,
	))
	if err != nil {
		log.WithFields(log.Fields{
			"reporter": r,
			"error":    err,
		}).Error("Reporter: Creating Mongo Client failed.")
		return err
	}
	// TODO: move client connection to initialization to avoid redundent reconnecting

	collection := client.Database(databaseName).Collection(collectionName)

	var operations []mongo.WriteModel

	for _, entry := range data {
		insert := mongo.NewInsertOneModel()
		var doc Schema

		doc.Country = ""
		doc.Time = time.Now().String()
		doc.Version = r.Version
		doc.Data = entry

		insert.SetDocument(doc)
		operations = append(operations, insert)
	}

	result, err := collection.BulkWrite(context.Background(), operations)
	if err != nil {
		log.WithFields(log.Fields{
			"result": result,
			"error":  err,
		}).Error("Reporter: MongoDB Bulkwrite failed.")
		return err
	}

	log.WithFields(log.Fields{
		"result":     result,
		"db":         databaseName,
		"collection": collectionName,
	}).Info("Reporter: MongoDB data store finished.")

	return nil
}

// PushToMongoDBMulti takes a map of data that specifies multiple db, collections and their data to be pushed
// Each data object should be inheriting Schema
// Input format:
//     dataMap[databaseName] = map[collectionName]data_points
func (r *Reporter) PushToMongoDBMulti(dataMap map[string]map[string][]interface{}) error {
	// TODO
	ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
	defer cancel()
	client, err := mongo.Connect(ctx, options.Client().ApplyURI(
		r.MongoStr,
	))
	if err != nil {
		log.WithFields(log.Fields{
			"client": client,
			"error":  err,
		}).Error("Reporter: Creating Mongo Client failed.")
		return err
	}
	// TODO: move client connection to initialization to avoid redundent reconnecting

	for databaseName, collectionMap := range dataMap {
		for collectionName, data := range collectionMap {
			collection := client.Database(databaseName).Collection(collectionName)

			var operations []mongo.WriteModel

			for _, entry := range data {
				insert := mongo.NewInsertOneModel()
				var doc Schema

				doc.Country = ""
				doc.Time = time.Now().String()
				doc.Version = r.Version
				doc.Data = entry

				insert.SetDocument(doc)
				operations = append(operations, insert)
			}

			collection.BulkWrite(context.Background(), operations)

			log.WithFields(log.Fields{
				"db":         databaseName,
				"collection": collectionName,
			}).Info("Reporter: MongoDB data store finished.")
		}
	}

	return nil
}
