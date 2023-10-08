import csv
import json
import ipaddress
import socket
import sys
import time
import dns.resolver
import statistics
import matplotlib.pyplot as plt
import subprocess
import math


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
    csvFilePath = "data/nameservers.csv"
    jsonFilePath = "data/publicDNSCountryLatest.json"
    make_json(csvFilePath, jsonFilePath)

    countries = ["US", "AR", "DE", "IN"]
    publicdns = json.load(open("data/publicDNSCountryLatest.json"))
    publicdnsIPs = ["8.8.8.8", "1.1.1.1", "9.9.9.9"]
    bigPublicDnsProviders = ["GOOGLE", "ULTRADNS", "CLOUDFLARENET"]
    publicDNS = {}
    for ip in publicdns:
        if publicdns[ip]["country_code"] in countries and float(
                publicdns[ip]["reliability"]) == 1.0 and check_ip_version(ip) == "IPv4":
            cc = publicdns[ip]["country_code"]
            if cc not in publicDNS:
                publicDNS[cc] = []
            if ip in publicdnsIPs:
                continue
            publicDNS[cc].append(ip)
    # second pass
    for cc in countries:
        removeList = []
        for ip in publicdns:
            if ip in publicDNS[cc] and publicdns[ip]["as_org"] not in bigPublicDnsProviders:
                removeList.append(ip)
        print(cc, "origin len: ", len(publicDNS[cc]), " remove len:", len(removeList))
        if len(publicDNS[cc]) - len(removeList) >= 30:
            publicDNS[cc] = list(set(publicDNS[cc]) - set(removeList))
        publicDNS[cc] = random.sample(publicDNS[cc], 30)

    with open("data/publicDNSMeasurementCountries.json", 'w', encoding='utf-8') as jsonf:
        jsonf.write(json.dumps(publicDNS, indent=4))

    for cc in countries:
        print(cc, len(publicDNS[cc]))


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
        print(100 * count / len(publicdns[country]))
        count += 1
        resolver = dns.resolver.Resolver()
        resolver.nameservers = [ns]
        resolver.lifetime = 1
        failures = 0
        for site in top50sites:
            if site == "microsoftonline.com":
                continue
            start_time = time.time()
            # print (site,ns)
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
                # sites_to_remove.append(site)

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


def scatterplot(country):
    # Example data (replace with your own)
    resTimesPerResolver = json.load(open("analysis/measurements/" + country + "/resTimesPerResolver.json"))
    medians = []
    stdevs = []
    for ns, lst in resTimesPerResolver.items():
        # mean = statistics.mean(lst)
        median = statistics.median(lst)
        stdev = statistics.stdev(lst)
        medians.append(median)
        stdevs.append(stdev)

    # Create the scatter plot
    plt.figure(figsize=(8, 6))
    plt.scatter(medians, stdevs, marker='o', color='blue')
    plt.xlim(0, 5)
    plt.ylim(0, 50)
    plt.title("Scatter Plot of Median vs. Stdevs")
    plt.xlabel("Median")
    plt.ylabel("Stdevs")

    # Add labels for each point (optional)
    # for i, txt in enumerate(['List1', 'List2', 'List3', 'List4', 'List5', 'List6', 'List7', 'List8']):
    #     plt.annotate(txt, (medians[i], variances[i]), fontsize=8, ha='right')

    # Show the plot
    plt.grid(True)
    plt.show()


import random
import numpy as np
from scipy import stats


def selectXBestResolvers(country):
    # Define confidence levels (e.g., 95% confidence interval)
    confidence_level = 0.95

    # # Define the desired confidence interval widths for mean and standard deviation
    # median_confidence_interval_width = 5  # Adjust as needed
    # std_deviation_confidence_interval_width = 10  # Adjust as needed

    resTimesPerResolver = json.load(open("analysis/measurements/" + country + "/resTimesPerResolver.json"))

    # Initialize variables to store the list with the lowest median and standard deviation
    lowest_iqr = float('inf')
    lowest_median = float('inf')
    lowest_mean = float('inf')
    lowest_std_deviation = float('inf')

    # Calculate confidence intervals for each list and find the lowest median and standard deviation
    # for list_name, data in lists.items():
    for ns, lst in resTimesPerResolver.items():
        sample_median = np.median(lst)
        sample_mean = np.mean(lst)
        sample_std_deviation = np.std(lst, ddof=1)  # Use ddof=1 for sample standard deviation
        q1, q3 = np.percentile(lst, [25, 75])
        sample_iqr = q3 - q1

        if sample_median < lowest_median:
            lowest_median = sample_median

        if sample_mean < lowest_mean:
            lowest_mean = sample_mean

        if sample_std_deviation < lowest_std_deviation:
            lowest_std_deviation = sample_std_deviation

        if sample_iqr < lowest_iqr:
            lowest_iqr = sample_iqr

    # Set 'desired_median' and 'desired_std_deviation' to the lowest median and standard deviation
    desired_median = lowest_median
    desired_mean = lowest_mean
    desired_std_deviation = lowest_std_deviation
    desired_iqr = lowest_iqr

    # Initialize a list to store the selected lists
    selected_lists = []

    # Calculate confidence intervals for each list
    for ns, lst in resTimesPerResolver.items():
        sample_median = np.median(lst)
        sample_mean = np.mean(lst)
        sample_std_deviation = np.std(lst, ddof=1)  # Use ddof=1 for sample standard deviation
        q1, q3 = np.percentile(lst, [25, 75])
        sample_iqr = q3 - q1

        # n_bootstrap_samples = 1000  # Number of bootstrap samples
        # bootstrap_medians = np.zeros(n_bootstrap_samples)

        # for i in range(n_bootstrap_samples):
        #     # Resample the data with replacement
        #     resampled_data = np.random.choice(lst, size=len(lst), replace=True)
        #     # Calculate the median for the resampled data
        #     bootstrap_median = np.median(resampled_data)
        #     bootstrap_medians[i] = bootstrap_median

        # Calculate the margin of error for the median based on the bootstrap distribution
        # median_margin_error = (np.percentile(bootstrap_medians, (1 + confidence_level) / 2 * 100) - np.percentile(bootstrap_medians, (1 - confidence_level) / 2 * 100)) / 2

        # The margin of error for standard deviation is calculated using the chi-squared distribution.
        # std_deviation_margin_error = stats.chi2.ppf((1 + confidence_level) / 2, df=len(lst) - 1) * sample_std_deviation / np.sqrt(len(lst)) - stats.chi2.ppf((1 - confidence_level) / 2, df=len(lst) - 1) * sample_std_deviation / np.sqrt(len(lst))
        mean_margin_error = stats.t.ppf(1 - (1 - confidence_level) / 2, len(lst) - 1) * sample_std_deviation / np.sqrt(
            len(lst))
        # Calculate the margin of error for the IQR (interquartile range)
        iqr_margin_error = (np.percentile(lst, (1 + confidence_level) / 2 * 100) - np.percentile(lst, (
                    1 - confidence_level) / 2 * 100)) / 2

        # Check if the median,standard deviation, iqr are within the desired confidence intervals
        # if (sample_mean - mean_margin_error <= desired_mean <= sample_mean + mean_margin_error) and (sample_std_deviation - std_deviation_margin_error <= desired_std_deviation <= sample_std_deviation + std_deviation_margin_error) and (sample_iqr - iqr_margin_error <= desired_iqr <= sample_iqr + iqr_margin_error):
        #     selected_lists.append(ns)

        if (sample_mean - mean_margin_error <= desired_mean <= sample_mean + mean_margin_error) and (
                sample_iqr - iqr_margin_error <= desired_iqr <= sample_iqr + iqr_margin_error):
            selected_lists.append(ns)
            # print (sample_mean,)

    # Print the selected lists
    print("Selected Lists: ", len(selected_lists))
    # for ns in selected_lists:
    #     print(ns)
    data_to_plot = [resTimesPerResolver[ns] for ns in selected_lists]

    iqr_values = [np.percentile(data, 75) - np.percentile(data, 25) for data in data_to_plot]

    # Define a threshold for significantly larger IQR (adjust as needed)
    threshold = 2  # Adjust the threshold based on your criteria

    # Find the lists with IQR significantly larger than the threshold
    largerSpreadNs = [ns for i, ns in enumerate(selected_lists) if iqr_values[i] > threshold * np.median(iqr_values)]
    print("largerSpreadNs: ", len(largerSpreadNs))
    # for ns in largerSpreadNs:
    #     print (ns)

    # Create a boxplot for the selected lists
    plt.figure(figsize=(8, 6))
    bp = plt.boxplot(data_to_plot, showfliers=False, patch_artist=True)

    box_colors = ['red' if ns in largerSpreadNs else 'lightblue' for ns in selected_lists]

    for box, color in zip(bp['boxes'], box_colors):
        box.set(color=color, linewidth=2)
        box.set(facecolor='none')

    plt.title(
        "Boxplots for Selected Resolvers in " + country + "\n best Resolvers: " + str(len(selected_lists)) + "(" + str(
            len(resTimesPerResolver)) + ")\n Resolvers to Race: " + str(len(largerSpreadNs)))
    plt.xlabel("Resolvers")
    plt.ylabel("Resolution Time (ms)")
    plt.savefig("analysis/measurements/" + country + "/bestResolvers.png")

    # for ns in largerSpreadNs:
    # # Plot each list separately with a label
    #     x_position = list(selected_lists).index(ns) + 1
    #     y_data = resTimesPerResolver[ns]
    #     plt.scatter([x_position] * len(y_data), y_data, color='red', label=f'{ns}')

    # # Highlight the lists with significantly larger IQR and remove outliers
    # for ns in largerSpreadNs:
    #     # Get the list's data
    #     y_data = resTimesPerResolver[ns]

    #     # Define a criterion for identifying outliers (e.g., outside the range of Q1 - 1.5 * IQR to Q3 + 1.5 * IQR)
    #     q1, q3 = np.percentile(y_data, [25, 75])
    #     iqr = q3 - q1
    #     lower_bound = q1 - 1.5 * iqr
    #     upper_bound = q3 + 1.5 * iqr

    #     # Filter out the outliers
    #     non_outliers = [data_point for data_point in y_data if lower_bound <= data_point <= upper_bound]

    #     # Plot the non-outlier data points
    #     x_positions = [list(resTimesPerResolver.keys()).index(ns) + 1] * len(non_outliers)
    #     plt.scatter(x_positions, non_outliers, color='red', label=f'{ns} (Significantly Larger IQR)')

    # plt.lim(0, 400)
    # Show the plot
    # plt.legend()
    plt.show()


def selectXBestResolversModified(country):
    # Define confidence levels (e.g., 95% confidence interval)
    confidence_level = 0.99

    # # Define the desired confidence interval widths for mean and standard deviation

    resTimesPerResolver = json.load(open("analysis/measurements/" + country + "/resTimesPerResolver.json"))

    # Initialize variables to store the list with the lowest median and standard deviation
    lowest_iqr = float('inf')
    lowest_iqr_ns = None
    lowest_median = float('inf')
    lowest_median_ns = None
    lowest_mean = float('inf')
    lowest_mean_ns = None
    lowest_meanstd = float('inf')
    lowest_std_deviation = float('inf')
    lowest_std_deviation_ns = None

    # Calculate confidence intervals for each list and find the lowest median and standard deviation
    # for list_name, data in lists.items():
    for ns, lst in resTimesPerResolver.items():
        sample_median = np.median(lst)
        sample_mean = np.mean(lst)
        sample_std_deviation = np.std(lst, ddof=1)  # Use ddof=1 for sample standard deviation
        q1, q3 = np.percentile(lst, [25, 75])
        sample_iqr = q3 - q1

        if sample_median < lowest_median:
            lowest_median = sample_median
            lowest_median_ns = ns

        if sample_mean < lowest_mean:
            lowest_mean = sample_mean
            lowest_mean_ns = ns
            lowest_meanstd = sample_std_deviation

        if sample_std_deviation < lowest_std_deviation:
            lowest_std_deviation = sample_std_deviation
            lowest_std_deviation_ns = ns

        if sample_iqr < lowest_iqr:
            lowest_iqr = sample_iqr
            lowest_iqr_ns = ns

    # Initialize a list to store the selected lists
    selected_lists = []

    mean_critical_value = stats.t.ppf(1 - (1 - confidence_level) / 2, len(resTimesPerResolver[lowest_mean_ns]) - 1)
    mean_standard_error = lowest_meanstd / np.sqrt(len(resTimesPerResolver[lowest_mean_ns]))
    mean_margin_error = mean_critical_value * mean_standard_error
    # Calculate the margin of error for the IQR (interquartile range)
    # iqr_margin_error = (np.percentile(resTimesPerResolver[lowest_iqr_ns], (1 + confidence_level) / 2 * 100) - np.percentile(resTimesPerResolver[lowest_iqr_ns], (1 - confidence_level) / 2 * 100)) / 2
    std_deviation_margin_error = stats.chi2.ppf((1 + confidence_level) / 2, df=len(
        resTimesPerResolver[lowest_std_deviation_ns]) - 1) * lowest_std_deviation / np.sqrt(
        len(resTimesPerResolver[lowest_std_deviation_ns])) - stats.chi2.ppf((1 - confidence_level) / 2, df=len(
        resTimesPerResolver[lowest_std_deviation_ns]) - 1) * lowest_std_deviation / np.sqrt(
        len(resTimesPerResolver[lowest_std_deviation_ns]))

    # Define the number of bootstrap samples
    n_bootstrap_samples = 10000  # Adjust as needed

    # Initialize a list to store bootstrap medians
    bootstrap_medians_lowest_median = []

    # Perform bootstrapping to estimate the distribution of the lowest median
    for _ in range(n_bootstrap_samples):
        # Resample the data with replacement
        resampled_data = np.random.choice(resTimesPerResolver[lowest_median_ns],
                                          size=len(resTimesPerResolver[lowest_median_ns]), replace=True)
        # Calculate the median for the resampled data
        bootstrap_median = np.median(resampled_data)
        bootstrap_medians_lowest_median.append(bootstrap_median)

    # Calculate the confidence interval for the lowest median
    lower_percentile = (1 - confidence_level) / 2 * 100
    upper_percentile = (1 + confidence_level) / 2 * 100
    confidence_interval = np.percentile(bootstrap_medians_lowest_median, [lower_percentile, upper_percentile])

    q1, q3 = np.percentile(resTimesPerResolver[lowest_median_ns], [25, 75])
    iqr_lowest_median_list = q3 - q1
    # Calculate the margin of error for the lowest median
    median_margin_error = (confidence_interval[1] - confidence_interval[0]) / 2

    # print (median_margin_error,mean_margin_error)

    # Calculate confidence intervals for each list
    for ns, lst in resTimesPerResolver.items():
        sample_median = np.median(lst)
        sample_mean = np.mean(lst)
        sample_std_deviation = np.std(lst, ddof=1)  # Use ddof=1 for sample standard deviation
        q1, q3 = np.percentile(lst, [25, 75])
        sample_iqr = q3 - q1

        # The margin of error for standard deviation is calculated using the chi-squared distribution.
        # std_deviation_margin_error = stats.chi2.ppf((1 + confidence_level) / 2, df=len(lst) - 1) * sample_std_deviation / np.sqrt(len(lst)) - stats.chi2.ppf((1 - confidence_level) / 2, df=len(lst) - 1) * sample_std_deviation / np.sqrt(len(lst))
        # mean_margin_error = stats.t.ppf(1 - (1 - confidence_level) / 2, len(lst) - 1) * sample_std_deviation / np.sqrt(len(lst))
        # Calculate the margin of error for the IQR (interquartile range)
        # iqr_margin_error = (np.percentile(lst, (1 + confidence_level) / 2 * 100) - np.percentile(lst, (1 - confidence_level) / 2 * 100)) / 2

        # if (sample_mean <= lowest_mean + mean_margin_error):
        #     selected_lists.append(ns)
        if (sample_median <= lowest_median + median_margin_error):
            #     selected_lists.append(ns)
            # if confidence_interval[0] <= sample_median <= confidence_interval[1]:
            # selected_lists.append(ns)
            # Calculate the IQR for the current list
            q1_current, q3_current = np.percentile(lst, [25, 75])
            iqr_current = q3_current - q1_current

            # Check if the IQRs of the current list and lowest median list overlap
            if min(q3_current, q3) - max(q1_current, q1) >= 0:
                selected_lists.append(ns)

    # Print the selected lists
    print("Selected Lists: ", len(selected_lists))

    data_to_plot = [resTimesPerResolver[ns] for ns in selected_lists]

    iqr_values = [np.percentile(data, 75) - np.percentile(data, 25) for data in data_to_plot]

    # Define a threshold for significantly larger IQR (adjust as needed)
    threshold = 2  # Adjust the threshold based on your criteria

    # Find the lists with IQR significantly larger than the threshold
    largerSpreadNs = [ns for i, ns in enumerate(selected_lists) if iqr_values[i] > threshold * np.median(iqr_values)]
    print("largerSpreadNs: ", len(largerSpreadNs))

    # Create a boxplot for the selected lists
    plt.figure(figsize=(8, 6))
    bp = plt.boxplot(data_to_plot, showfliers=False, patch_artist=True)

    box_colors = ['red' if ns in largerSpreadNs else 'lightblue' for ns in selected_lists]

    for box, color in zip(bp['boxes'], box_colors):
        box.set(color=color, linewidth=2)
        box.set(facecolor='none')

    plt.title(
        "Boxplots for Selected Resolvers in " + country + "\n best Resolvers: " + str(len(selected_lists)) + "(" + str(
            len(resTimesPerResolver)) + ")\n Resolvers to Race: " + str(len(largerSpreadNs)))
    plt.xlabel("Resolvers")
    plt.ylabel("Resolution Time (ms)")
    # plt.savefig("analysis/easurements/"+country+"/bestResolvers.png")

    plt.show()


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

    # sorted_by_metrics = sorted(metrics.items(), key=lambda x: math.prod(x[1]))
    sorted_by_median = sorted(metrics.items(), key=lambda x: x[1])

    # print (sorted_by_metrics)

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

    print("best_upper_whisker: ", best_upper_whisker)

    selected_keys = []
    for key in selected_keysI:
        q1_current, q3_current = np.percentile(resTimesPerResolver[key], [25, 75])
        iqr_current = q3_current - q1_current
        upper_whisker_current = q3_current + (1.5 * iqr_current)

        if upper_whisker_current <= 1.5 * best_upper_whisker:
            selected_keys.append(key)

    data_to_plot = [resTimesPerResolver[ns] for ns in selected_keys]

    iqr_values = [np.percentile(data, 75) - np.percentile(data, 25) for data in data_to_plot]

    # Define a threshold for significantly larger IQR (adjust as needed)
    threshold = 1.5  # Adjust the threshold based on your criteria

    # Find the lists with IQR significantly larger than the threshold
    largerSpreadNs = [ns for i, ns in enumerate(selected_keys) if iqr_values[i] > threshold * np.median(iqr_values)]
    print("best resolvers: ", len(selected_keys))
    print("largerSpreadNs: ", len(largerSpreadNs))

    configMap = dict()
    configMap[currentIpAddr] = {"best_resolvers": list(set(selected_keys)-set(largerSpreadNs)), "high_spread": largerSpreadNs}

    with open("analysis/measurements/" + country + "/config.json", 'w', encoding='utf-8') as jsonf:
        jsonf.write(json.dumps(configMap, indent=4))

    best_subset = {key: resTimesPerResolver[key] for key in selected_keys}
    # for key in best_subset:
    #     print (key,len(best_subset[key]),best_subset[key],"\n")

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
    # plt.xticks(range(1, 9), best_subset.keys())  # Set x-axis labels to the keys
    plt.savefig("analysis/measurements/" + country + "/bestResolverstoShard.png")
    plt.show()


# # countries=["US","AR","DE"]
currentIpAddr = sys.argv[1]
country = sys.argv[2]
print(country)
configBestResolvers(country)
selectBestResolverstoShard(currentIpAddr, country)

# select resolvers from the file, resolve 50 domains and record the resolution times.
