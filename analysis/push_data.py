import utils
from pymongo import MongoClient, InsertOne

mongo_str = "mongodb+srv://admin:aqualab@dataserver.npwhs.mongodb.net/test?retryWrites=true&w=majority"
client = MongoClient(mongo_str)
db = client.SourceData

public_dns_data = utils.load_json("../data/country_public_dns.json")
operations = []
for country, data in public_dns_data.items():
    entry = {
        "country": country, 
        "data": data
    }
    operations.append(InsertOne(entry))
db.public_dns.bulk_write(operations)

# resource_data = utils.load_json("../data/resourcesDict.json")
# operations = []
# for country, data in resource_data.items():
#     entry = {
#         "country": country, 
#         "data": data
#     }
#     operations.append(InsertOne(entry))
# db.resource.bulk_write(operations)

# cdn_data = utils.load_json("../data/cdnMappingDict.json")
# operations = []
# for country, data in cdn_data.items():
#     entry = {
#         "country": country, 
#         "data": data
#     }
#     operations.append(InsertOne(entry))
# db.cdn_mapping.bulk_write(operations)