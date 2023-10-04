import csv
import json
import ipaddress
import socket
import time
import dns.resolver
import statistics
import matplotlib.pyplot as plt
import subprocess


def make_json(csvFilePath, jsonFilePath):
    data = {}
    with open(csvFilePath, encoding='utf-8') as csvf:
        csvReader = csv.DictReader(csvf)
        
        for rows in csvReader:
            key = rows['ip_address']
            data[key] = rows
    with open(jsonFilePath, 'w', encoding='utf-8') as jsonf:
        jsonf.write(json.dumps(data, indent=4))


def check_ip_version(ip_address_str):
    try:
        ip = ipaddress.ip_address(ip_address_str)
        if ip.version == 4:
            return "IPv4"
        elif ip.version == 6:
            return "IPv6"
        else:
            return "Invalid IP address"
    except ValueError:
        return "Invalid IP address"

def selectpublicDNSResolvers():
    csvFilePath="data/nameservers.csv"
    jsonFilePath="data/publicDNSCountryLatest.json"
    make_json(csvFilePath, jsonFilePath)

    countries=["US","AR","DE","IN"]
    publicdns=json.load(open("data/publicDNSCountryLatest.json")) 
    publicdnsIPs=["8.8.8.8","1.1.1.1","9.9.9.9"]
    publicDNS={}
    for ip in publicdns:
        if publicdns[ip]["country_code"] in countries and float(publicdns[ip]["reliability"])==1.0 and check_ip_version(ip)=="IPv4":
            cc=publicdns[ip]["country_code"]
            if cc not in publicDNS:
                publicDNS[cc]=[]
            if ip in publicdnsIPs:
                continue
            publicDNS[cc].append(ip)
    with open("data/publicDNSMeasurementCountries.json", 'w', encoding='utf-8') as jsonf:
        jsonf.write(json.dumps(publicDNS, indent=4))

    for cc in countries:
        print (cc,len(publicDNS[cc]))

def configBestResolvers(country):
    top500sites=json.load(open("data/alexaTop500SitesPerCountry.json")) 
    publicdns=json.load(open("data/publicDNSMeasurementCountries.json")) 

    try:
        subprocess.run(["sudo", "dscacheutil", "-flushcache"], check=True)
        print("DNS cache flushed successfully on macOS.")
    except subprocess.CalledProcessError as e:
        print(f"Error flushing DNS cache on macOS: {e}")

    top50sites=top500sites[country][:50]
    resTimesPerResolver={}
    count=0
    elements_to_remove=[]
    sites_to_remove=[]
    publicdns[country]=["8.8.8.8","1.1.1.1","9.9.9.9"]+publicdns[country]
    for ns in publicdns[country]:
        print (100*count/len(publicdns[country]))
        count+=1
        resolver = dns.resolver.Resolver()
        resolver.nameservers = [ns]
        resolver.lifetime = 5
        failures=0
        for site in top50sites:
            start_time = time.time()
            # print (site,ns)
            try:
                result = resolver.query(site, "A")
                end_time = time.time()
                resolution_time_ms = (end_time - start_time) * 1000
                if ns not in resTimesPerResolver:
                    resTimesPerResolver[ns]=[]
                resTimesPerResolver[ns].append(resolution_time_ms)
            except dns.resolver.Timeout:
                print(f"DNS resolution for {site} and {ns} timed out.")
                failures+=1
                if site=="google.com" or failures>=3:
                    elements_to_remove.append(ns)
                    break
            except dns.resolver.NXDOMAIN:
                print(f"Domain {site} does not exist.")
            except dns.exception.DNSException as e:
                print(f"DNS resolution failed: {e}")
                sites_to_remove.append(site)
            except Exception as e:
                print("An error occurred:", e)

            
        top50sites = [x for x in top50sites if x not in sites_to_remove]

    filtered_list = [x for x in publicdns[country] if x not in elements_to_remove]
    publicdns[country]=filtered_list

    with open("analysis/measurements/"+country+"/resTimesPerResolver.json", 'w', encoding='utf-8') as jsonf:
        jsonf.write(json.dumps(resTimesPerResolver, indent=4))
    with open("data/publicDNSMeasurementCountries.json", 'w', encoding='utf-8') as jsonf:
        jsonf.write(json.dumps(publicdns, indent=4))


def calculate_total_score(keys, metrics_dict):
    total_mean = sum(metrics_dict[key][0] for key in keys)
    total_median = sum(metrics_dict[key][1] for key in keys)
    total_variance = sum(metrics_dict[key][2] for key in keys)
    return total_mean + total_median + total_variance

def selectBestResolverstoShard(country):

# We sort the dictionary items based on the sum of the metrics (mean, median, variance) for each list. 
# Sorting by the sum allows us to select the lists that have the least combined metrics.
# We maintain a set selected_keys to keep track of the keys of the 8 lists with the least combined mean, median, and variance. 
# We add keys from each of the sorted lists until we have 8 unique keys.
# Finally, we create best_subset as a dictionary that contains the selected keys and their corresponding lists 
# from the original lists_dict. This best_subset will contain both the keys and lists for the 8 lists with the least 
# combined mean, median, and variance.
# Now, best_subset will be a dictionary where each key corresponds to one of the 8 selected lists with the least combined metrics, and the values are the lists themselves.
    resTimesPerResolver=json.load(open("analysis/measurements/"+country+"/resTimesPerResolver.json")) 


    metrics = {}

    for ns, lst in resTimesPerResolver.items():
        mean = statistics.mean(lst)
        median = statistics.median(lst)
        variance = statistics.variance(lst)
        metrics[ns] = (mean, median, variance)


    sorted_by_metrics = sorted(metrics.items(), key=lambda x: sum(x[1]))

    
    selected_keys = set()
    for i in range(8):
        selected_keys.add(sorted_by_metrics[i][0])


    best_subset = {key: resTimesPerResolver[key] for key in selected_keys}
    for key in best_subset:
        print (key,len(best_subset[key]),best_subset[key],"\n")

    data = list(best_subset.values())

    plt.figure(figsize=(10, 6))
    plt.boxplot(data)
    plt.title("Boxplots of Resolution Time of the 8 Best Resolvers in "+country)
    plt.xlabel("Resolvers")
    plt.ylabel("Resolution Time (ms)")
    plt.xticks(range(1, 9), best_subset.keys())  # Set x-axis labels to the keys
    plt.savefig("analysis/measurements/"+country+"/bestResolvers.png")

countries=["US","AR","IN","DE"]
for country in countries:
    print (country)
    configBestResolvers(country)
    selectBestResolverstoShard(country)
    print ("\n\n")

# select resolvers from the file, resolve 50 domains and record the resolution times.
         


