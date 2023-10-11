import csv
import json
import ipaddress
from urllib.parse import urlparse


def get_domain_from_url(url):
    parsed_url = urlparse(url)
    if parsed_url.netloc:
        domain = parsed_url.netloc
        if domain.startswith('www.'):
            domain = domain[4:]  # Remove 'www' prefix
        return domain
    else:
        return ""


def get_top_million_websites():
    # Open the input CSV file
    csv_file_path = "data/202308.csv"
    output_data = []
    count = 0

    with open(csv_file_path, 'r') as input_file:
        reader = csv.DictReader(input_file)

        for row in reader:
            try:
                # print(row)
                # Extract the IP address from the "origin" column
                url = row['origin']
                ip = get_domain_from_url(url)
                # ip = url.split('//')[1]
                rank = int(row['rank'])

                if rank == 1000000:
                    output_data.append(ip)
                    count += 1
            except (ipaddress.AddressValueError, ValueError):
                pass

    print(count)
    # Write the output data to a JSON file
    with open('data/top_million_websites.json', 'w') as json_file:
        json.dump(output_data, json_file, indent=4)


get_top_million_websites()
