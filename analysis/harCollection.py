from selenium import webdriver
import json
from browsermobproxy import Server
import os

# Pass this function the site whose har file we want to download
def downloadHar(site):
	server = Server("/home/rashna/Downloads/browsermob-proxy-2.1.4-bin/browsermob-proxy-2.1.4/bin/browsermob-proxy", options={'port':9090})
	server.start()
	proxy = server.create_proxy()

	profile  = webdriver.FirefoxProfile()
	profile.set_proxy(proxy.selenium_proxy())
	driver = webdriver.Firefox(firefox_profile=profile)

	try:
		name=site[:-4]
		print (name)
		proxy.new_har("google")
		driver.get("http://"+site)
		with open(name+'.har', 'w') as har_file:
			json.dump(proxy.har, har_file)
	except Exception as e:
		print(str(e))

	server.stop()
	driver.quit()

# call this function to call downloadHar function on a list of alexa top sites
def harCollection():
	topSites=[]
	with open("USalexatop50.txt", 'r') as f:
		for site in f:
			topSites.append(site[:-1])

	x=0
	for site in topSites:
		print(100*x/len(topSites), " \% complete")
		downloadHar(site)
		x=x+1

# extracts all the resources from each harFile present in the directory 
def collectResources():
	harFiles=[]
	uniqueDomains=[]
	for file in os.listdir("/Users/rashnakumar/Documents/DoH/Sub-Rosa/harCollection"):
	    if file.endswith(".har"):
	        harFiles.append(file)
	print (len(harFiles))
	for harFile in harFiles:
		harFile= json.load(open(harFile))
		for x in range (0,len(harFile['log']['entries'])):
			resource=harFile['log']['entries'][x]['request']['url']
			if resource not in uniqueDomains:
				uniqueDomains.append(str(resource))
	print (uniqueDomains)
	print (len(uniqueDomains))
	with open('USalexatop50Resources.json','w') as f:
		json.dump(uniqueDomains,f)
collectResources()
