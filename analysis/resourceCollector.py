from selenium import webdriver
import json
from browsermobproxy import Server
from bs4 import BeautifulSoup
import os, time
from webdriver_manager.chrome import ChromeDriverManager

import utils

project_path = utils.project_path

class Har_generator:
	def __init__(self):
		self.hars = []
		self.server = Server(os.getcwd()+"/browsermob-proxy-2.1.4/bin/browsermob-proxy")
		self.server.start()
		self.proxy = self.server.create_proxy(params={"trustAllServers": "true"})
		options = webdriver.ChromeOptions()
		options.add_argument("--proxy-server={}".format(self.proxy.proxy))	
		options.add_argument("--ignore-ssl-errors=yes")
		options.add_argument("--ignore-certificate-errors")
		# options.add_argument("--headless")

		self.driver = webdriver.Chrome(ChromeDriverManager().install(), chrome_options=options)

	def __del__(self):
		self.server.stop()
		self.driver.quit()

	# loads up a site
	# takes a site url
	# returns a json har object
	def get_har(self, site):
		
		try:
			name = site
			self.proxy.new_har(name)
			self.driver.get("https://"+site)
			time.sleep(1)
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

	def dump(self, fn_prefix):	
		utils.dump_json(self.resources, project_path+"/"+fn_prefix + "/alexaResources"+country+".json")

	# extracts all the resources from each har object
	# takes a list of har json objects
	# stores in the object resources
	def collect_resources(self, hars,country):
		for har in hars:
			for entry in har["log"]["entries"]:
				resource = entry["request"]["url"]
				if resource not in self.resources:
					self.resources.append(str(resource))


class Url_processor:
	def __init__(self,country):
		self.cdn_mapping = {}
		self.resources_mapping = utils.load_json(country+"/alexaResources"+country+".json")

		self.options = webdriver.ChromeOptions()
		self.options.add_argument("--ignore-ssl-errors=yes")
		self.options.add_argument("--ignore-certificate-errors")
		# options.add_argument("--headless")

		self.driver = webdriver.Chrome(ChromeDriverManager().install(), chrome_options=self.options)

	def __del__(self):
		self.driver.quit()

	def restart_drive(self):
		print("Restarting...")
		self.driver.quit()
		self.driver = webdriver.Chrome(ChromeDriverManager().install(), chrome_options=self.options)

	def dump(self, fn_prefix):
		utils.dump_json(self.cdn_mapping, project_path+"/"+fn_prefix + "/PopularcdnMapping.json")

	# Find cdn given a file of the domains
	# Takes a list of unique domains
	# Returns a dictionary containing the found CDNs for each domain
	def find_cdn(self):
		domains = []
		for resource in self.resources_mapping:
			if utils.url_to_domain(resource) not in domains:
				domains.append(utils.url_to_domain(resource))
		i = 0
		self.driver.get("https://www.cdnplanet.com/tools/cdnfinder/")
		total = len(domains)
		for resource in domains:
			if i > 0 and i % 50 == 0:
				self.restart_drive()
				self.driver.get("https://www.cdnplanet.com/tools/cdnfinder/")

			print("%.2f%% completed" % (100 * i / total))

			for _ in range(3):
				try:
					self.driver.find_element_by_xpath("//*[@id=\"tool-form-main\"]").clear()
					self.driver.find_element_by_xpath("//*[@id=\"tool-form-main\"]").send_keys(resource)
					self.driver.find_element_by_xpath("//*[@id=\"hostname-or-url\"]").click()
					self.driver.find_element_by_xpath("//*[@id=\"tool-form\"]/button").click()
					time.sleep(3)

					doc = BeautifulSoup(self.driver.page_source, "html.parser")
					domain=doc.findAll('code', attrs={"class" : "simple"})
					cdn=doc.findAll('strong')
					site=domain[0].text
					cdn=cdn[0].text
					print (site,cdn)
					if "Amazon" in cdn:
						cdn="Amazon"
					if cdn=="Amazon" or cdn=="Akamai" or cdn=="Google" or cdn=="Cloudflare" or cdn=="Fastly":
						if cdn not in self.cdn_mapping:
							self.cdn_mapping[cdn]=[]
						self.cdn_mapping[cdn].append(resource)
					break
				except Exception as e:
					print(str(e))
					time.sleep(2)


			time.sleep(2)
			i += 1

	def collectPopularCDNResources(self,country):
		unique=[]
		with open(country+"/AlexaUniqueResources.txt","w") as f:
			for cdn in self.cdn_mapping:
				for domain in self.cdn_mapping[cdn]:
					for resource in self.resources_mapping:
						if domain in resource:
							if resource not in unique:
								f.write(resource+"\n")
								unique.append(resource)
							
			f.close()
		

if __name__ == "__main__":
	hm = Har_generator()
	rc = Resource_collector()

	top_sites = {}
	country = input("Enter alpha-2 country code: ")

	with open(project_path+"/alexaTop50SitesCountries.json", 'r') as fp:
		top_sites = json.load(fp)
	if country not in top_sites:
		print("ERROR: invalid country code or country provided does not have top site records")
	else:
		if not os.path.exists(project_path+"/"+country):
			os.mkdir(country)
		sites=[top_sites[country][x]["Site"] for x in range (len(top_sites[country]))]

		# hars = hm.get_hars(sites[:2])
		hars = hm.get_hars(sites)
		rc.collect_resources(hars,country)
		rc.dump(country)
		del hm


		up=Url_processor(country)
		up.find_cdn()
		up.collectPopularCDNResources(country)
		up.dump(country)
		del up