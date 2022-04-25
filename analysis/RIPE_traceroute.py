import sys
import json
import random
import argparse
import time
# from pymongo import MongoClient
from bson import ObjectId
from datetime import (
    datetime, 
    timedelta
)
from ripe.atlas.cousteau import (
    Traceroute,
    AtlasSource,
    AtlasCreateRequest
)
import utils
from os.path import isfile, join


project_path = utils.project_path


# mongo_config = None
# ripe_config = None
# with open("../config.json", 'r') as fp:
#     config = json.load(fp)
#     mongo_config = config["mongo_str"]
#     ripe_config = config["ripe_api"]
# mongo_client = MongoClient(mongo_config)

# usage:
# add probes
# add measurement to be performed on these probes
# submit request
# if successful, output measurement id
class RIPE_requester:
    def __init__(self):
        # self.keys = ripe_config
        self.keys = ["b7fb25c3-a5fc-4785-8f35-6830a6fdb6a4"]

        
        self.is_oneoff = True  # single measurement

        self.measurements = []
        self.probe_sources = []
        self.measurement_ids = []

        self.no_probe = 0

    # Use RIPE probe selector to select probes based on country code
    # input: code: country code in iso alpha-2
    #        num: number of probes wanted, default 1
    def add_country_probes_auto(self, code, num=1):
        self.probe_sources.append(
            AtlasSource(
                type = "country",
                value = code,
                requested = num
            )
        )

    # input: code: country code in iso alpha-2
    #        num: number of probes wanted, default 1
    # def add_country_probes(self, code, num=1):
    #     # set measurement to target probes in a given country code
    #     probe_ids = []
    #     if code in probes.keys():
    #         probe_ids = probes[code][:num]
    #         if len(probe_ids) == 0:
    #             print("ERROR: no probe selected")
    #             self.no_probe += 1
    #     else:
    #         sys.exit("invalid country code")
        

    #     self.probe_sources.append(
    #         AtlasSource(
    #             type = "probes",
    #             value = ",".join(probe_ids),
    #             requested = num
    #         )
    #     )
    
    def clear_country_probes(self):
        self.probe_sources = []
    
    def clear_measurement_ids(self):
        self.measurement_ids = []
    
    def add_traceroute_measurement(self, target_ip, protocol="ICMP"):
        # add a RIPE traceroute measurement with given destination ip and protocol
        if len(target_ip.split('.')) == 4:
            # IPv4
            self.measurements.append(
                Traceroute(
                    af = 4,  # IPv4
                    target = target_ip,
                    description = "Traceroute Target %s %s" % (target_ip, str(datetime.now())),
                    max_hops = 30,
                    timeout = 4000,
                    paris = 16,  # use Paris Traceroute to avoid load balancing
                    protocol = protocol,
                    is_public = False,
                    resolve_on_probe = True  # use probe's locally assigned DNS
                )
            )
        else:
            # IPv6
            self.measurements.append(
                Traceroute(
                    af = 6,  # IPv6
                    target = target_ip,
                    description = "Traceroute Target %s %s" % (target_ip, str(datetime.now())),
                    max_hops = 30,
                    timeout = 4000,
                    paris = 16,  # use Paris Traceroute to avoid load balancing
                    protocol = protocol,
                    is_public = False,
                    resolve_on_probe = True  # use probe's locally assigned DNS
                )
            )

    def clear_measurement(self):
        self.measurements = []
    
    def submit(self, key):
        # create the measurements
        start_time=datetime.utcnow()+timedelta(0, 0, 0, 0, 1) # start in a minute
        self.request = AtlasCreateRequest(
            key = key,
            measurements = self.measurements,
            sources = self.probe_sources,
            # start_time = start_time,
            is_oneoff = self.is_oneoff
        )

        (is_success, response) = self.request.create()
        if is_success:
            self.measurement_ids.extend(response["measurements"])
            print("SUCCESS: measurement created: %s" % response["measurements"])
        else:
            raise Exception("failed to create measurement: %s" % response)


    def save_ids(self, path="tmp_measurement_ids.json"):
        # save successful measurement ids
        with open(path, 'w') as fp:
            json.dump(self.measurement_ids, fp)

    def replace_ids(self, path,sindex,eindex,file_path,country):
        # save successful measurement ids
        print ("path: ",path)
        # country="DE"
        dir=join(project_path, "analysis", "measurements", country)
        file = join(dir,"temptracerouteResult.json")
        print (join(dir,"temptracerouteResult.json"))
        print (len(self.measurement_ids))
        with open(file, 'w') as fp:
            json.dump(self.measurement_ids, fp)

    def save_ids_db(self, code, collection):
        
        record = {
            "country_code": code, 
            "measurement_id": self.measurement_ids, 
            "timestamp": str(datetime.now()), 
            "measurement_type": "traceroute", 
            "status": "new"
        }
        collection[code]=record

def traceroute_error(code_index_list,country):
    tracerouter = RIPE_requester()

    # country="DE"
    dir=join(project_path, "analysis", "measurements", country)
    latencyDict=json.load(open(join(dir, "dnsLatencies.json")))
    file_path = join(dir,"temp.json")



    print(code_index_list)

    
    tracerouter.clear_measurement()
    tracerouter.clear_country_probes()
    tracerouter.clear_measurement_ids()
    all_ip_list = []


    replicaIPs=[]
    for approach in latencyDict:
        for site in latencyDict[approach]:
            try:    
                if latencyDict[approach][site]["ReplicaIP"] not in replicaIPs:
                    replicaIPs.append(latencyDict[approach][site]["ReplicaIP"])
            except:
                print (approach,site)
    print ("replicaIPs: ",len(replicaIPs))
    for ip in replicaIPs:
        all_ip_list.append(ip.replace('_', "."))
    code = country

    dict={}
        
    
    for code_index in code_index_list[code]:

        index_start = code_index[0]
        index_end = code_index[1]
        ip_list = all_ip_list[index_start:index_end]

        print(code, len(ip_list),index_start,index_end)

        if len(ip_list) == 0:
            print("No IP fetched. Check your Country Code")
            exit()
        
        tracerouter.add_country_probes_auto(code)

        trials = int(len(ip_list) / 80) + 1
        i = 0


        # tracerouter.measurement_ids = tracerouter.measurement_ids["measurement_id"][:index_start]
        # print("already done", len(tracerouter.measurement_ids) + len(measurement_ids["measurement_id"][index_end:]))

        while i < trials:
            done = False
            for key in tracerouter.keys:
                tracerouter.clear_measurement()
                print("Measurement from %d to %d" % (i*80, (i+1)*80))
                for ip in ip_list[i*80:(i+1)*80]:
                    tracerouter.add_traceroute_measurement(ip)

                print("Total measurements:", len(tracerouter.measurements))
                if len(tracerouter.measurements) == 0:
                    done = True
                    break

                # while True:
                    # try:
                print("Requesting with key #%d" % (i % len(tracerouter.keys)))
                tracerouter.submit(key)
                        # break
                    # except Exception as e:
                    #     print("ERROR creating measurements:", e)
                    #     time.sleep(60*2)
                try:
                    tracerouter.replace_ids(file_path + '.Rmeasurement_ids.json',index_start,index_end,file_path,country)
                    # tracerouter.save_ids(file_path + '.measurement_ids.json')
                except Exception as e:
                    print("ERROR saving measurement id:", e)
                i += 1

                if i >= trials:
                    done = True
                    break

            if done:
                break

            print("Round finished, waiting...")
            time.sleep(60*10)
        
        # tracerouter.measurement_ids.extend(measurement_ids["measurement_id"][index_end:])

    try:
        print("Done; Saving measurement IDs")
        tracerouter.save_ids_db(code, dict)
    except Exception as e:
        print("ERROR saving measurement id:", e)

    with open(join(dir,"RtracerouteResult.json"), 'w') as fp:
        json.dump(dict, fp)

def traceroute_all(country):
    tracerouter = RIPE_requester()


    # records = []
    
    # for record in mongo_client[db]["ips"].find():
    #     records.append(record)

    # print(len(records))

    # for record in records:
        # !!!!!!!!!!!!!!!!!!!!!!!!!!!!!
    dict={}
    tracerouter.clear_measurement()
    tracerouter.clear_country_probes()
    tracerouter.clear_measurement_ids()

    ip_list = []
    # country="DE"

    dir=join(project_path, "analysis", "measurements", country)
    latencyDict=json.load(open(join(dir, "dnsLatencies.json")))
    donereplicas=json.load(open(join(project_path, "analysis", "combinedTracerouteResults")))
    file_path = join(dir,"temp.json")


    replicaIPs=[]
    totalReplicas=[]
    for approach in latencyDict:
        for site in latencyDict[approach]:
            try:  
                if (latencyDict[approach][site]["ReplicaIP"]=="0.0.0.0" or latencyDict[approach][site]["ReplicaIP"]=="127.0.0.1"):
                    continue
                # if latencyDict[approach][site]["ReplicaIP"] not in replicaIPs and latencyDict[approach][site]["ReplicaIP"] not in donereplicas:
                #     replicaIPs.append(latencyDict[approach][site]["ReplicaIP"])
                if latencyDict[approach][site]["ReplicaIP"] not in totalReplicas:
                    totalReplicas.append(latencyDict[approach][site]["ReplicaIP"])
            except:
                # print (approach,site)
                continue

    print ("replicaIPs: ",len(replicaIPs),len(totalReplicas),country)
    # exit()
    # replicaIPs=replicaIPs[:10]
    for ip in totalReplicas:
    # for ip in replicaIPs:
    # for ip in record["match_ips"]:
        ip_list.append(ip.replace('_', "."))

    # code = record["country_code"]
    code=country

    print(code, len(ip_list))

    if len(ip_list) == 0:
        print("No IP fetched. Check your Country Code")
        exit()
    
    tracerouter.add_country_probes_auto(code)

    trials = int(len(ip_list) / 80) + 1
    i = 0

    while i < trials:
        done = False
        for key in tracerouter.keys:
            tracerouter.clear_measurement()
            print("Measurement from %d to %d" % (i*80, (i+1)*80))
            for ip in ip_list[i*80:(i+1)*80]:
                tracerouter.add_traceroute_measurement(ip)

            print("Total measurements:", len(tracerouter.measurements))
            if len(tracerouter.measurements) == 0:
                done = True
                break

            while True:
                try:
                    print("Requesting with key #%d" % (i % len(tracerouter.keys)))
                    tracerouter.submit(key)
                    break
                except Exception as e:
                    print("ERROR creating measurements:", e)
                    time.sleep(60*2)
            try:
                tracerouter.save_ids(file_path + '.measurement_ids.json')
            except Exception as e:
                print("ERROR saving measurement id:", e)
            i += 1

            if i >= trials:
                done = True
                break
        if done:
            break

        print("Round finished, waiting...")
        time.sleep(60*10)

    try:
        print("Done; Saving measurement IDs")
        # tracerouter.save_ids_db(code, mongo_client[db]["measurement_ids"])
        tracerouter.save_ids_db(code, dict)

    except Exception as e:
        print("ERROR saving measurement id:", e)

    # mongo_client[db]["ips"].update_one({"_id": record["_id"]}, {"$set": {"status": "geolocated_tracerouted"}})
    with open(join(dir,"tracerouteResult.json"), 'w') as fp:
        json.dump(dict, fp)
  
if __name__ == "__main__":
    # db = sys.argv[1]
    country="DE"
    traceroute_all(country)
    # e_dict= {'IN': [[640, 720]]}
    # traceroute_error(e_dict,country)