from selenium import webdriver
import json
from browsermobproxy import Server
import os, time

project_path = os.getcwd()

class Har_generator:
	def __init__(self):
		self.hars = []

		self.server = Server(project_path+"/browsermob-proxy-2.1.4/bin/browsermob-proxy", options={"port":9090})
		self.server.start()
		self.proxy = self.server.create_proxy(params={"trustAllServers": "true"})

		options = webdriver.ChromeOptions()
		options.add_argument("--proxy-server={}".format(self.proxy.proxy))
		options.add_argument("--ignore-ssl-errors=yes")
		options.add_argument("--ignore-certificate-errors")
		options.add_argument("--headless")

		self.driver = webdriver.Chrome(project_path+"/bin/chromedriver", chrome_options=options)

	def __del__(self):
		self.server.stop()
		self.driver.quit()

	# loads up a site
	# takes a site url
	# returns a json har object
	def get_har(self, site):
		try:
			name=site[:-4]
			self.proxy.new_har(name)
			self.driver.get("https://"+site)
			time.sleep(3)
			return self.proxy.har
		except Exception as e:
			print(str(e))
			return None

	# calls get_har for each site
	# takes a list of site urls
	# returns a dictionary of site url and json har objects
	def get_hars(self, sites):
		x = 0
		hars = []
		for site in sites:
			print("%d: Working on %s" % (x, site))
			har = self.get_har(site)
			hars.append(har)
			self.hars.append(har)
			x = x + 1
		return hars

class Resource_collector:
	def __init__(self):
		self.resources = []
	
	def dump(self, fn):
		har_dir = project_path + "/resource"
		if not os.path.exists(har_dir):
			os.mkdir(har_dir)
		with open(har_dir+'/'+fn, 'w') as f:
			json.dump(self.resources, f, indent=4)

	# extracts all the resources from each har object
	# takes a list of har json objects
	# stores in the object resources
	def collect_resources(self, hars):
		for har in hars:
			for entry in har["log"]["entries"]:
				resource = entry["request"]["url"]
				if resource not in self.resources:
					self.resources.append(str(resource))

if __name__ == "__main__":
	hm = Har_generator()
	rc = Resource_collector()

	top_sites = {}
	country = input("Enter alpha-2 country code: ")

	with open(project_path+"/alexa_top_50_20200215.json", 'r') as fp:
		top_sites = json.load(fp)

	if country not in top_sites:
		print("ERROR: invalid country code or country provided does not have top site records")

	sites = [x["Site"] for x in top_sites[country]]

	hars = hm.get_hars(sites[:1])
	rc.collect_resources(hars)
	rc.dump(country+"_resources.json")

	del rc
	del hm
