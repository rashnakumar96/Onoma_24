from selenium import webdriver
from bs4 import BeautifulSoup
import json
import time
import subprocess

# Find cdn given a file of the domains of the resources
def findCdn(file):
	resources=json.load(open(file))
	cdnMapping={}
	options = webdriver.ChromeOptions()
	options.add_argument("--ignore-ssl-errors=yes")
	options.add_argument("--ignore-certificate-errors")
	options.add_argument("--headless")

	driver = webdriver.Chrome("/usr/local/bin/chromedriver", chrome_options=options)
	i=0
	driver.get("https://www.whatsmycdn.com/")

	for resource in resources:
		print(100*i/len(resources)," \% completed")
		print (i)
		driver.find_element_by_id("exampleEmailInput").clear()
		driver.find_element_by_id("exampleEmailInput").send_keys(resource)
		driver.find_element_by_xpath("//*[@id=\"location\"]/optgroup[1]/option[3]").click()# Enters North America as Region
		driver.find_element_by_id('pageDemo1').click()

		doc = BeautifulSoup(driver.page_source, "html.parser")
		cdns=doc.findAll('div', attrs={ "style" : "margin-left: 2px; word-wrap:break-word;"})
		domains=doc.findAll('div', attrs={ "style" : "word-wrap:break-word;"})

		count=0
		for _domain in domains:
			domain=_domain.text
			cdn=cdns[count].text
			print (domain,": ",cdn)
			if cdn not in cdnMapping:
				cdnMapping[cdn]=[]
			cdnMapping[cdn].append(resource)
			count=count+1


		time.sleep(0.5)
		i=i+1
		
	driver.quit()
	with open("cdnMapping.json",'w') as fp:
		json.dump(cdnMapping, fp, indent=4)

# findCdn("harCollection/USalexatopUniqueResources.json")

# Take 3 runs to measure ttb of resources
def measureTTB(file,ttbDict,resolverType,err):
	resources=json.load(open(file))
	domainCheck=[]
	uniqueResources=[]

	for resource in resources:
		if "https" in resource:
			domain=resource.split("https://")[1]
		elif "http" in resource:
			domain=resource.split("http://")[1]
		if "www." in domain:
			domain=domain.split("www.")[1]
		if domain not in domainCheck:
			domainCheck.append(domain)
			uniqueResources.append(resource)


	print (len(uniqueResources))
	i=0
	for resource in uniqueResources:
		print (i)
		i=i+1
		try:
			CurlUrl="curl -w \"Connect time: %{time_connect} Time to first byte: %{time_starttransfer} Total time: %{time_total} \n\" -o /dev/null "+resource
			status, output = subprocess.getstatusoutput(CurlUrl)
			ttb=str(output).split("Time to first byte:")[1].split("Total time:")[0]
		except:
			if resource not in err:
				err.append(resource)
			continue

		print (resource,": ",ttb)
		if resource not in ttbDict:
			ttbDict[resource]={}
		if resolverType not in ttbDict[resource]:
			ttbDict[resource][resolverType]=[]
		ttbDict[resource][resolverType].append(ttb)

# for run in range(3):
# 	try:
# 		ttbDict=json.load(open("Resourcesttb.json"))
# 	except:
# 		ttbDict={}
# 	try:
# 		err=json.load(open("errttb.json"))
# 	except:
# 		err=[]
# 	measureTTB("harCollection/USalexatop50Resources.json",ttbDict,"SubRosa",err)
# 	with open("Resourcesttb.json",'w') as fp:
# 		json.dump(ttbDict, fp, indent=4)
# 	with open("errttb.json",'w') as fp:
# 			json.dump(err, fp, indent=4)

# group the resources by their cdn and store in a file along with the ttb of each resource loaded with each approach
def cdnGrouping(cdnMapping,Resourcesttb):
	ttbDict=json.load(open(Resourcesttb))
	cdnDict=json.load(open(cdnMapping))
	dict={}
	for resource in ttbDict:
		if "https" in resource:
			domain=resource.split("https://")[1]
		elif "http" in resource:
			domain=resource.split("http://")[1]
		domain=domain.split("/")[0]
		if "www." in domain:
			domain=domain.split("www.")[1]
		for cdn in cdnDict:
			if domain in cdnDict[cdn]:
				if "Amazon" in cdn:
					cdn="Amazon"
				if cdn not in dict:
					dict[cdn]={}
				dict[cdn][resource]=ttbDict[resource]
				break
	with open("ttbbyCDN.json",'w') as fp:
		json.dump(dict, fp, indent=4)		

# cdnGrouping("cdnMapping.json","Resourcesttb.json")

# load each resource with selenium (just for testing DR caching in SUB Rosa)
def loadResourceSelenium(file):
	resources=json.load(open(file))
	options = webdriver.ChromeOptions()
	options.add_argument("--ignore-ssl-errors=yes")
	options.add_argument("--ignore-certificate-errors")
	# options.add_argument("--headless")

	driver = webdriver.Chrome("/usr/local/bin/chromedriver", chrome_options=options)
	i=0
	for cdn in resources:
		# if "Verizon" in cdn:
		r=0
		for resource in resources[cdn]:
			r=r+1
		print(cdn,": ",i," : ",r)
		i=i+1
			# 	driver.get(resource)
			# 	time.sleep(1)
	driver.quit()
loadResourceSelenium("ttbbyCDN.json")