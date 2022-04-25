import json, sys
from ripe.atlas.cousteau import AtlasResultsRequest
# from pymongo import MongoClient, InsertOne
from datetime import datetime
from copy import deepcopy
from os.path import isfile, join
import utils


project_path = utils.project_path

err = {}
country="DE"
dir=join(project_path, "analysis", "measurements", country)
tracerouteResult=json.load(open(join(dir, "tracerouteResult.json")))

# for record in measurement_collection.find():
for record in tracerouteResult:
    print (record)
    country_code = tracerouteResult[record]["country_code"]
    measurement_ids = tracerouteResult[record]["measurement_id"]

    end_error = True

    print(country_code, len(measurement_ids))
    count = 0
    wcount=0
    operations = []
    error = False
    # fetching
    for id in measurement_ids:
        print("Fetching %s" % id)
        kwargs = {
            "msm_id": id
        }
        is_success, results = AtlasResultsRequest(**kwargs).create()

        if is_success:
            if len(results) < 1:
                # scount+=1
                print("WARNING...", country_code)
                if country_code not in err:
                    err[country_code] = []
                if wcount==0:
                    sindex=count
                wcount+=1
                continue
            if wcount!=0:
                eindex=sindex+wcount
                wcount=0
                print (sindex,eindex,count)
                err[country_code].append([sindex, eindex])

            for r in results:
                result = deepcopy(r)
                result["country_code"] = country_code
                result["status"] = "new"
                result["run"] = "SEPT"
                
                operations.append(result)

        else:
            print("Fetch measurement failed")
        
        count += 1

    if error:
        print ("I don't get what is this error?")
        continue

    with open(join(dir,"tracerouteFetechedResult"+country_code+".json"), 'w') as fp:
        json.dump(operations, fp)
    
    print("Finish Writing to Json", country_code)

print("ERROR:", err)
