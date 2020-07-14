from selenium import webdriver
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
import os, time
import subprocess
import tldextract

import utils

project_path = utils.project_path

class Url_processor:
	def __init__(self):
		self.cdn_mapping = {}
		self.ttb_mapping = {}

		options = webdriver.ChromeOptions()
		options.add_argument("--ignore-ssl-errors=yes")
		options.add_argument("--ignore-certificate-errors")
		options.add_argument("--headless")

		self.driver = webdriver.Chrome(project_path+"/bin/chromedriver", chrome_options=options)

	def __del__(self):
		self.driver.quit()

	def dump(self, fn_prefix):
		dump_dir = project_path + "/find_cdn/"
		if not os.path.exists(dump_dir):
			os.mkdir(dump_dir)
		
		utils.dump_json(self.cdn_mapping, dump_dir + fn_prefix + "_cdn_mapping.json")
		utils.dump_json(self.ttb_mapping, dump_dir + fn_prefix + "_ttb_mapping.json")

	# Find cdn given a file of the domains
	# Takes a list of unique domains
	# Returns a dictionary containing the found CDNs for each domain
	def find_cdn(self, domains):
		i = 0
		self.driver.get("https://www.whatsmycdn.com/")

		total = len(domains)
		for resource in domains:
			print("%.2f%% completed" % (100 * i / total))

			for _ in range(3):
				try:
					self.driver.find_element_by_id("exampleEmailInput").clear()
					self.driver.find_element_by_id("exampleEmailInput").send_keys(resource)

					self.driver.find_element_by_xpath("//*[@id=\"location\"]/option").click() # Enters Global as Region
					
					self.driver.find_element_by_id('pageDemo1').click()

					# url = "https://www.whatsmycdn.com/?uri=%s&location=GL" % resource
					# res = requests.get(url)

					doc = BeautifulSoup(self.driver.page_source, "html.parser")
					# doc = BeautifulSoup(res.text, "html.parser")

					cdns = doc.findAll('div', attrs={ "style" : "margin-left: 2px; word-wrap:break-word;"})
					regions = doc.findAll('div', attrs={ "style" : "word-wrap:break-word;"})

					print(resource)
					# print(resource, res.status_code)

					count = 0
					for _region in regions:
						region = _region.text
						cdn = cdns[count].text
						print(region,": ",cdn)
						if resource not in self.cdn_mapping:
							self.cdn_mapping[resource] = {}
						self.cdn_mapping[resource][region] = cdn
						count += 1

					break
				except:
					print("retry")

			time.sleep(0.25)
			i += 1

		return self.cdn_mapping

	# Takes a list of unique resources in full url
	# Returns a dictionary for resource and its ttb, and a list of failed urls
	def measure_ttb(self, resources, resolver_type):
		err = []

		# print (len(unique_resources))
		i = 0
		for resource in resources:
			print(i)
			i = i + 1
			try:
				curl_command = "curl -w \"Connect time: %{time_connect} Time to first byte: %{time_starttransfer} Total time: %{time_total} \n\" -o /dev/null "+resource
				_, output = subprocess.getstatusoutput(curl_command)
				ttb = str(output).split("Time to first byte:")[1].split("Total time:")[0]
			except:
				if resource not in err:
					err.append(resource)
				continue

			print (resource,": ",ttb)
			if resource not in self.ttb_mapping:
				self.ttb_mapping[resource] = {}
			if resolver_type not in self.ttb_mapping[resource]:
				self.ttb_mapping[resource][resolver_type] = []
			self.ttb_mapping[resource][resolver_type].append(ttb)

		return self.ttb_mapping, err

	# group the resources by their cdn and store in a file along with the ttb of each resource loaded with each approach
	def group_by_cdn(self):
		grouped_result = {}
		for resource in self.ttb_mapping:
			domain = utils.url_to_domain(resource)
			for cdn in self.cdn_mapping:
				if domain in self.cdn_mapping[cdn]:
					if "Amazon" in cdn:
						cdn="Amazon"
					if cdn not in grouped_result:
						grouped_result[cdn]={}
					grouped_result[cdn][resource] = self.ttb_mapping[resource]
					break

		return grouped_result		

	# cdnGrouping("cdn_mapping.json","resource_ttb.json")

# load each resource with selenium (just for testing DR caching in SUB Rosa)
def loadResourceSelenium(file):
	resources = utils.load_json(file)
	options = webdriver.ChromeOptions()
	options.add_argument("--ignore-ssl-errors=yes")
	options.add_argument("--ignore-certificate-errors")
	# options.add_argument("--headless")

	driver = webdriver.Chrome("/usr/local/bin/chromedriver", chrome_options=options)
	i = 0
	for cdn in resources:
		# if "Verizon" in cdn:
		r = 0
		for resource in resources[cdn]:
			r += 1
		print(cdn,": ",i," : ",r)
		i += 1
			# 	driver.get(resource)
			# 	time.sleep(1)
	driver.quit()
# loadResourceSelenium("ttbbyCDN.json")