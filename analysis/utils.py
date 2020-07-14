import tldextract, json, os

project_path = os.getcwd()

# Convert a url (string) to the domain name (string) of the index page
def url_to_domain(url):
    ext = tldextract.extract(url)
    return ".".join(ext)

# Load file into a json object
def load_json(fn):
    data = None
    with open(fn, 'r') as fp:
        data = json.load(fp)
    return data

# Dump a json object into a file
def dump_json(data, fn):
    with open(fn, 'w') as fp:
        json.dump(data, fp)