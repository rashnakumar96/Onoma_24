import csv
import json
import ipaddress
import numpy as np
import sys
import time
import dns.resolver
import statistics
import matplotlib.pyplot as plt
import subprocess
import requests

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
    countries = ["US", "AR", "DE", "IN"]
    publicdns = json.load(open("data/publicDNSMeasurementCountries_functional.json"))
    publicDNS = {}

    for ip in publicdns:
        if "country_code" not in publicdns[ip]:
            continue

        country = publicdns[ip]["country_code"]
        as_org = publicdns[ip]["as_org"]

        if country not in countries:
            continue

        if country not in publicDNS:
            publicDNS[country] = {}

        if as_org not in publicDNS[country]:
            publicDNS[country][as_org] = []

        publicDNS[country][as_org].append(ip)

    sorted_ip_map = {country: {as_org: ips for as_org, ips in sorted(as_orgs.items(), key=lambda x: len(x[1]), reverse=True)} for country, as_orgs in publicDNS.items()}

    with open("data/publicDNSMeasurementCountries_list.json", 'w', encoding='utf-8') as jsonf:
        jsonf.write(json.dumps(sorted_ip_map, indent=4))

    publicDnsMap = {}
    for country, as_orgs in sorted_ip_map.items():
        ips = []
        while len(ips) < 30:
            for as_org, ip_list in as_orgs.items():
                if ip_list:
                    ip = ip_list.pop(0)
                    ips.append(ip)
                if len(ips) >= 30:
                    break

        ips = ips[:30] if len(ips) >= 30 else ips[:10]
        publicDnsMap[country] = ips

    with open("data/publicDNSMeasurementCountries.json", 'w', encoding='utf-8') as jsonf:
        jsonf.write(json.dumps(publicDnsMap, indent=4))


def selectFunctionalPublicDNSResolvers():
    csvFilePath = "data/nameservers.csv"
    jsonFilePath = "data/publicDNSCountryLatest.json"
    make_json(csvFilePath, jsonFilePath)

    countries = ["US", "AR", "DE", "IN"]
    publicdns = json.load(open("data/publicDNSCountryLatest.json"))
    publicdnsIPs = ["8.8.8.8", "1.1.1.1", "9.9.9.9"]
    functional_public_dns = {}
    resolver = dns.resolver.Resolver()
    site = "google.com"
    for ip in publicdns:
        if publicdns[ip]["country_code"] in countries and float(
                publicdns[ip]["reliability"]) == 1.0 and check_ip_version(ip) == "IPv4":
            if ip not in functional_public_dns:
                functional_public_dns[ip] = {}
            if ip in publicdnsIPs:
                continue

            resolver.nameservers = [ip]
            resolver.lifetime = 1
            try:
                result = resolver.query(site, "A")
            except dns.resolver.Timeout:
                print(f"DNS resolution using {ip} for {site} timed out.")
                continue
            except dns.resolver.NXDOMAIN:
                print(f"Domain {site} does not exist.")
                continue
            except dns.exception.DNSException as e:
                print(f"DNS resolution failed: {e}")
                continue

            functional_public_dns[ip] = publicdns[ip]

    with open("data/publicDNSMeasurementCountries_functional.json", 'w', encoding='utf-8') as jsonf:
        jsonf.write(json.dumps(functional_public_dns, indent=4))


def testDoHResolvers(country):
    # doh_urls=["https://dns.quad9.net:5053/dns-query","https://cloudflare-dns.com/dns-query","https://dns.google/resolve"]
    # doh_urls = [
    #     "Google": "8.8.8.8/resolve",
    #     "Cloudflare": "1.1.1.1/dns-query",
    #     "Quad9": "9.9.9.9:5053/dns-query"
    # ]

    doh_urls = ["https://8.8.8.8/resolve", "https://1.1.1.1/dns-query", "https://9.9.9.9:5053/dns-query"]

    top500sites = json.load(open("data/alexaTop500SitesPerCountry.json"))
    resTimesPerResolver = json.load(open("analysis/measurements/"+country+"/resTimesPerResolver.json"))

    try:
        subprocess.run(["sudo", "dscacheutil", "-flushcache"], check=True)
        print("DNS cache flushed successfully on macOS.")
    except subprocess.CalledProcessError as e:
        print(f"Error flushing DNS cache on macOS: {e}")

    top50sites = top500sites[country][:50]
    headers = {
        "accept": "application/dns-json"
    }
    for doh_url in doh_urls:
        for site in top50sites:
            if site == "microsoftonline.com":
                continue
            # Construct the query parameters
            params = {
                "name": site,
                "type": "A"  # You can change the type to AAAA for IPv6 records
            }

            start_time = time.time()
            response = requests.get(doh_url, params=params, headers=headers, verify=False)
            end_time = time.time()

            # Check if the request was successful (HTTP status code 200)
            if response.status_code == 200:
                resolution_time_ms = (end_time - start_time) * 1000
                if doh_url not in resTimesPerResolver:
                    resTimesPerResolver[doh_url] = []
                resTimesPerResolver[doh_url].append(resolution_time_ms)
            else:
                print(f"Failed to resolve {site}. Status code: {response.status_code}")
    with open("analysis/measurements/"+country+"/resTimesPerResolver.json", 'w', encoding='utf-8') as jsonf:
        jsonf.write(json.dumps(resTimesPerResolver, indent=4))


def configBestResolvers(country):
    top500sites = json.load(open("data/alexaTop500SitesPerCountry.json"))
    publicdns = json.load(open("data/publicDNSMeasurementCountries.json"))

    try:
        subprocess.run(["sudo", "dscacheutil", "-flushcache"], check=True)
        print("DNS cache flushed successfully on macOS.")
    except subprocess.CalledProcessError as e:
        print(f"Error flushing DNS cache on macOS: {e}")

    top50sites = top500sites[country][:50]
    resTimesPerResolver = {}
    count = 0
    elements_to_remove = []
    sites_to_remove = []
    publicdns[country] = set(["8.8.8.8", "1.1.1.1", "9.9.9.9"] + publicdns[country])
    for ns in publicdns[country]:
        # print(100 * count / len(publicdns[country]))
        count += 1
        resolver = dns.resolver.Resolver()
        resolver.nameservers = [ns]
        resolver.lifetime = 1
        failures = 0
        for site in top50sites:
            if site == "microsoftonline.com":
                continue
            start_time = time.time()
            try:
                result = resolver.query(site, "A")
                end_time = time.time()
                resolution_time_ms = (end_time - start_time) * 1000
                if ns not in resTimesPerResolver:
                    resTimesPerResolver[ns] = []
                resTimesPerResolver[ns].append(resolution_time_ms)
            except dns.resolver.Timeout:
                print(f"DNS resolution for {site} and {ns} timed out.")
                failures += 1
                if site == "google.com" or failures >= 3:
                    elements_to_remove.append(ns)
                    break
            except dns.resolver.NXDOMAIN:
                print(f"Domain {site} does not exist.")
            except dns.exception.DNSException as e:
                print(f"DNS resolution failed: {e}")
                failures += 1
                if site == "google.com" or failures >= 3:
                    elements_to_remove.append(ns)
                    break

        top50sites = [x for x in top50sites if x not in sites_to_remove]

    filtered_list = [x for x in publicdns[country] if x not in elements_to_remove]
    publicdns[country] = filtered_list

    with open("analysis/measurements/" + country + "/resTimesPerResolver.json", 'w', encoding='utf-8') as jsonf:
        jsonf.write(json.dumps(resTimesPerResolver, indent=4))
    with open("data/publicDNSMeasurementCountries.json", 'w', encoding='utf-8') as jsonf:
        jsonf.write(json.dumps(publicdns, indent=4))


def calculate_total_score(keys, metrics_dict):
    total_mean = sum(metrics_dict[key][0] for key in keys)
    total_median = sum(metrics_dict[key][1] for key in keys)
    total_variance = sum(metrics_dict[key][2] for key in keys)
    return total_mean + total_median + total_variance


def selectBestResolverstoShard(currentIpAddr, country):
    # We sort the dictionary items based on the sum of the metrics (mean, median, variance) for each list.
    # Sorting by the sum allows us to select the lists that have the least combined metrics.
    # We maintain a set selected_keys to keep track of the keys of the 8 lists with the least combined mean, median, and variance.
    # We add keys from each of the sorted lists until we have 8 unique keys.
    # Finally, we create best_subset as a dictionary that contains the selected keys and their corresponding lists
    # from the original lists_dict. This best_subset will contain both the keys and lists for the 8 lists with the least
    # combined mean, median, and variance.
    # Now, best_subset will be a dictionary where each key corresponds to one of the 8 selected lists with the least combined metrics, and the values are the lists themselves.
    resTimesPerResolver = json.load(open("analysis/measurements/" + country + "/resTimesPerResolver.json"))

    metrics = {}
    for ns, lst in resTimesPerResolver.items():
        median = statistics.median(lst)
        metrics[ns] = (median)

    sorted_by_median = sorted(metrics.items(), key=lambda x: x[1])
    best = sorted_by_median[0][0]
    q1, q3 = np.percentile(resTimesPerResolver[best], [25, 75])

    selected_keysI = []
    stdevdict = {}
    for i in range(len(sorted_by_median)):
        key = sorted_by_median[i][0]
        q1_current, q3_current = np.percentile(resTimesPerResolver[key], [25, 75])
        iqr_current = q3_current - q1_current
        upper_whisker_current = q3_current + (1.5 * iqr_current)

        stdev_current = np.std(resTimesPerResolver[key], ddof=1)
        # Check if the IQRs of the current list and lowest median list overlap
        if min(q3_current, q3) - max(q1_current, q1) >= 0:
            stdevdict[key] = (upper_whisker_current)
            selected_keysI.append(key)

    sorted_by_stdev = sorted(stdevdict.items(), key=lambda x: x[1])
    leastVar = sorted_by_stdev[0][0]
    best_upper_whisker = stdevdict[leastVar]

    selected_keys = []
    for key in selected_keysI:
        q1_current, q3_current = np.percentile(resTimesPerResolver[key], [25, 75])
        iqr_current = q3_current - q1_current
        upper_whisker_current = q3_current + (1.9 * iqr_current)

        if upper_whisker_current <= 1.9 * best_upper_whisker:
            selected_keys.append(key)

    data_to_plot = [resTimesPerResolver[ns] for ns in selected_keys]

    iqr_values = [np.percentile(data, 75) - np.percentile(data, 25) for data in data_to_plot]

    threshold = 1.9  # Adjust the threshold based on your criteria

    # Find the lists with IQR significantly larger than the threshold
    largerSpreadNs = [ns for i, ns in enumerate(selected_keys) if iqr_values[i] > threshold * np.median(iqr_values)]

    configMap = dict()
    configMap[currentIpAddr] = {"best_resolvers": list(set(selected_keys)-set(largerSpreadNs)), "high_spread": largerSpreadNs}

    with open("analysis/measurements/" + country + "/config.json", 'w', encoding='utf-8') as jsonf:
        jsonf.write(json.dumps(configMap, indent=4))

    best_subset = {key: resTimesPerResolver[key] for key in selected_keys}
    data = list(best_subset.values())

    plt.figure(figsize=(10, 6))
    bp = plt.boxplot(data, showfliers=False, patch_artist=True)
    box_colors = ['red' if ns in largerSpreadNs else 'lightblue' for ns in selected_keys]

    for box, color in zip(bp['boxes'], box_colors):
        box.set(color=color, linewidth=2)
        box.set(facecolor='none')

    plt.title(
        "Boxplots for Selected Resolvers in " + country + "\n best Resolvers: " + str(len(selected_keys)) + "(" + str(
            len(resTimesPerResolver)) + ")\n Resolvers to Race: " + str(len(largerSpreadNs)))
    plt.xlabel("Resolvers")
    plt.ylabel("Resolution Time (ms)")
    plt.savefig("analysis/measurements/" + country + "/bestResolverstoShard.png")


currentIpAddr = sys.argv[1]
country = sys.argv[2]
selectpublicDNSResolvers()
configBestResolvers(country)
selectBestResolverstoShard(currentIpAddr, country)
