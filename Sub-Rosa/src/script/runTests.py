import json
import os
import time
import subprocess
from subprocess import call
from joblib import Parallel, delayed
import utils
import ipaddress
import re
import urllib.request
from pathlib import Path
from os import listdir
from os.path import isfile, join

project_path = utils.project_path

class WebPerformanceTests:
	def __init__(self, countryPath):
		self.countryPath = countryPath
		# resources=[]

	def resourcesttb(self, dir):
		onlyfiles = [f for f in listdir(dir) if isfile(join(dir, f))]
		approachList=[]
		for file in onlyfiles:
			if "lighthouseTTB" in file and ".json" in file:
				approach=file.split("lighthouseTTB")[1].split(".json")[0]
				approach=approach[:-1]
				if approach not in approachList:
					approachList.append(approach)
		print (approachList)

		resourcesttfb={}
		for approach in approachList:
			ttbDict=json.load(open(join(dir, "lighthouseTTB" + approach + "_.json")))
			for dict in ttbDict:
				if "ttfb" in dict.keys():
					if approach not in resourcesttfb:
						resourcesttfb[approach]={}
					if dict["website"] not in resourcesttfb[approach]:
						resourcesttfb[approach][dict["website"]]={}
					resourcesttfb[approach][dict["website"]]["ttfb"]=dict["ttfb"]

		
		utils.dump_json(resourcesttfb, join(dir,"lighthouseResourcesttb.json"))


	def resourcesttbbyCDN(self, ttbfile, cdnfile, tool, dir):
		ttbdict=json.load(open(ttbfile))
		cdndict=json.load(open(cdnfile))
		count=0
		dict={}
		for approach in ttbdict:
			for site in ttbdict[approach]:
				found=0
				domain=site
				if "https" in domain:
					domain=domain.split("https://")[1]
				elif "http" in domain:
					domain=domain.split("http://")[1]
				if "/" in domain:
					domain=domain.split("/")[0]
				if "www." in domain:
					domain=domain.split("www.")[1]
				for cdn in cdndict:
					if domain in cdndict[cdn]:
						if "Amazon" in cdn:
							cdn="Amazon"
						if cdn not in dict:
							dict[cdn]={}
						if site not in dict[cdn]:
							dict[cdn][site]={}
						if tool=="sitespeed":
							try:
								dict[cdn][site][approach]=ttbdict[approach][site]["ttfb"]["min"]
							except:
								print (site)
						elif tool=="lighthouse":
							dict[cdn][site][approach]=ttbdict[approach][site]["ttfb"]

						found=1
						break
				if found==0:
					count+=1

		print (count)
		utils.dump_json(dict, join(dir, "resourcesttbbyCDNLighthouse.json"))

	def paralleliseLighthouse(self,approach):
		resources=[]
		with open(join(self.countryPath, "AlexaUniqueResources.txt"),"r") as f:
			for resource in f:
				resources.append(resource.split("\n")[0])
		print (len(resources))
		chunkSize=int (len(resources)/5)
		start=0
		end=start+chunkSize
		lastIter=False
		chunks=[]
		while(1):
			chunk=[]	
			for i in range(start,end):
				chunk.append(resources[i])
			chunks.append(chunk)

			if (lastIter==True):
				break
			start=end
			end=end+chunkSize

			if (end+chunkSize>len(resources)):
				end=len(resources)		
				lastIter=True		
		print (len(chunks))

		for x in range(0,len(chunks),5):
			try:
				if (x+5>len(chunks)):
					screenshots = Parallel(n_jobs=-1)(delayed(self.runLighthouse)(approach,chunks[c],c) for c in range (len(chunks[x:])))
				else:
					screenshots = Parallel(n_jobs=-1)(delayed(self.runLighthouse)(approach,chunks[c],c) for c in range (len(chunks[x:x+5])))
			except Exception as e:
				print (str(e))

	def runLighthouse(self,approach,_resources,c):
		print ("Length of chunk: ",len(_resources),str(c))
		# print ("utils.project_path",project_path)
		# call(["node",project_path+"/runLighthouse.js",self.countryPath,approach,str(c)]+_resources)
		# stream = os.popen("node " + project_path+"/runLighthouse.js " + self.countryPath + approach + " " + str(c) + " " + str(_resources))
		# _ = stream.read()
		print ("Length of chunk: ",len(_resources),str(c))
		call(["node", join(project_path, "script", "runLighthouse.js"), self.countryPath, approach, str(c)] + _resources)

	def findminttb(self,approach,file1,file2,file3):
		ttbDict1=utils.load_json(join(self.countryPath, "lighthouseTTB" + file1 + ".json"))
		ttbDict2=utils.load_json(join(self.countryPath, "lighthouseTTB" + file2 + ".json"))
		ttbDict3=utils.load_json(join(self.countryPath, "lighthouseTTB" + file3 + ".json"))


		mergeddict={}
		for dict in ttbDict1:
			if "ttfb" in dict.keys():
				mergeddict[dict['website']]=dict['ttfb']
		for dict in ttbDict2:
			if "ttfb" in dict.keys():
				if dict['website'] in mergeddict:
					mergeddict[dict['website']]=min(mergeddict[dict['website']],dict['ttfb'])
				else:
					mergeddict[dict['website']]=dict['ttfb']
		for dict in ttbDict3:
			if "ttfb" in dict.keys():
				if dict['website'] in mergeddict:
					mergeddict[dict['website']]=min(mergeddict[dict['website']],dict['ttfb'])
				else:
					mergeddict[dict['website']]=dict['ttfb']

		minttbdict=[]
		for website in mergeddict:
			dict={}
			dict['website']=website
			dict['ttfb']=mergeddict[website]
			minttbdict.append(dict)
		utils.dump_json(minttbdict, join(self.countryPath, "lighthouseTTB" + approach + ".json"))

	def runWebPerformanceTests(self,approach):
		self.paralleliseLighthouse(approach)
		mergeddict={}
		for x in range(5):
			ttbDict=utils.load_json(join(self.countryPath, "lighthouseTTB" + approach + str(x) + ".json"))
			for dict in ttbDict:
				if "ttfb" in dict.keys():
					mergeddict[dict['website']]=dict['ttfb']
			call(["rm","-rf", join(self.countryPath, "lighthouseTTB" + approach + str(x) + ".json")])

		minttbdict=[]
		for website in mergeddict:
			dict={}
			dict['website']=website
			dict['ttfb']=mergeddict[website]
			minttbdict.append(dict)
		utils.dump_json(minttbdict, join(self.countryPath, "lighthouseTTB" + approach + ".json"))
		
	def runAllApproaches(self, country):
		self.runWebPerformanceTests("Google0")
		self.runWebPerformanceTests("Google1")
		self.runWebPerformanceTests("Google2")
		self.findminttb("Google_","Google0","Google1","Google2")
		print("Done Testing Google ")

		time.sleep(1*20)
		self.runWebPerformanceTests("Cloudflare0")
		self.runWebPerformanceTests("Cloudflare1")
		self.runWebPerformanceTests("Cloudflare2")
		self.findminttb("Cloudflare_","Cloudflare0","Cloudflare1","Cloudflare2")
		print("Done Testing Cloudflare ")

		time.sleep(1*20)
		self.runWebPerformanceTests("Quad90")
		self.runWebPerformanceTests("Quad91")
		self.runWebPerformanceTests("Quad92")
		self.findminttb("Quad9_","Quad90","Quad91","Quad92")
		print("Done Testing Quad9 ")

		publicDNSServers=json.load(open(join(country, "publicDNSServers.json")))

		for pDNS in publicDNSServers:
			time.sleep(1*20)
			self.runWebPerformanceTests(pDNS+"0")
			self.runWebPerformanceTests(pDNS+"1")
			self.runWebPerformanceTests(pDNS+"2")
			self.findminttb(pDNS+"_",pDNS+"0",pDNS+"1",pDNS+"2")
			print("Done Testing "+pDNS)

		# time.sleep(1*20)
		# self.runWebPerformanceTests("DoHProxy0")
		# self.runWebPerformanceTests("DoHProxy1")
		# self.runWebPerformanceTests("DoHProxy2")
		# self.findminttb("DoHProxy_","DoHProxy0","DoHProxy1","DoHProxy2")
		# print("Done Testing DoHProxy")

		time.sleep(1*20)
		self.runWebPerformanceTests("DoHProxyNP0")
		self.runWebPerformanceTests("DoHProxyNP1")
		self.runWebPerformanceTests("DoHProxyNP2")
		self.findminttb("DoHProxyNP_","DoHProxyNP0","DoHProxyNP1","DoHProxyNP2")
		print("Done Testing DoHProxyNP")

		# time.sleep(1*20)
		# self.runWebPerformanceTests("SubRosa0")
		# self.runWebPerformanceTests("SubRosa1")
		# self.runWebPerformanceTests("SubRosa2")
		# self.findminttb("SubRosa_","SubRosa0","SubRosa1","SubRosa2")
		# print("Done Testing SubRosa")


		time.sleep(1*20)
		self.runWebPerformanceTests("SubRosaNP0")
		self.runWebPerformanceTests("SubRosaNP1")
		self.runWebPerformanceTests("SubRosaNP2")
		self.findminttb("SubRosaNP_","SubRosaNP0","SubRosaNP1","SubRosaNP2")
		print("Done Testing SubRosaNP")

		time.sleep(1*20)
		self.runWebPerformanceTests("SubRosaNPR0")
		self.runWebPerformanceTests("SubRosaNPR1")
		self.runWebPerformanceTests("SubRosaNPR2")
		self.findminttb("SubRosaNPR_","SubRosaNPR0","SubRosaNPR1","SubRosaNPR2")
		print("Done Testing SubRosaNPR")

		self.resourcesttb(country) 
		self.resourcesttbbyCDN(join(country, "lighthouseResourcesttb.json"), join(country, "PopularcdnMapping.json"), "lighthouse", country)


if __name__ == "__main__":
	#select country code you want to test with
	# country = input("Enter alpha-2 country code: ")
	if not os.path.exists(join(project_path, "script", "measurements")):
		os.mkdir(join(project_path, "script", "measurements"))
	
	country = ""
	try:
		url = 'http://ipinfo.io/json'
		response = urllib.request.urlopen(url)
		data = json.load(response)
		country = data['country']
	except:
		url = "https://extreme-ip-lookup.com/json"
		response = urllib.request.urlopen(url)
		data = json.load(response)
		country = data['countryCode']

	if not os.path.exists(join(project_path, "script", "measurements", country)):
		os.mkdir(join(project_path, "script", "measurements", country))

	publicDNSServers=[]
	allpublicDNSServers = json.load(open(join(project_path, "data", "country_public_dns.json")))
	mainpDNS=["8.8.8.8","9.9.9.9","1.1.1.1"]

	for pDNS in allpublicDNSServers[country]:
		if pDNS["reliability"]>=0.95 and pDNS["ip"] not in mainpDNS:
			try:
				ipaddress.IPv4Network(pDNS["ip"])
				publicDNSServers.append(pDNS["ip"])
			except:
				# print ("Not an IPv4 address: ",pDNS["ip"])
				continue

	if len(publicDNSServers)>8:
		publicDNSServers=publicDNSServers[:8]
	with open(join(project_path, "script", "measurements", country, "publicDNSServers.json"),'w') as fp:
		json.dump(publicDNSServers, fp, indent=4)

	while 1:
		if os.path.exists(join(str(Path(os.getcwd()).parent), "dat")):
			print ("starting measurements")
			break
	
	tests = WebPerformanceTests(join("measurements", country))
	tests.runAllApproaches(join("measurements", country))
	del tests