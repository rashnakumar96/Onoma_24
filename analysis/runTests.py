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
import resourceCollector
import random
import math

project_path = utils.project_path

class WebPerformanceTests:
	def __init__(self, countryPath,resources):
		self.countryPath = countryPath
		self.resources=resources

	def checkResolver(self,ip):
		host_name="google.com"
		cmd='dig @'+ip+' '+host_name
		print (cmd)

		out = subprocess.Popen(["dig","@"+ip,host_name], 
           stdout=subprocess.PIPE, 
           stderr=subprocess.STDOUT)
		stdout,stderr = out.communicate()

		
		list=str(stdout).split(';')
		for ele in  list:
			if " connection timed out" in ele:
				return False
		return True

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
		if not os.path.exists(join(project_path,"analysis","measurements/"+country+"/AlexaUniqueWResources.txt")):
			# with open(self.countryPath+"/AlexaUniqueResources.txt","r") as f:
			# 	for resource in f:
			# 		resources.append(resource.split("\n")[0])
			resources=self.resources
		else:
			with open(self.countryPath+"/AlexaUniqueWResources.txt","r") as f:
				for resource in f:
					resources.append(resource.split("\n")[0])

		
		print ("# of resources",len(resources))

		#for the client randomly shuffle 100 resources and carry measurements on that
		chunkSize=math.ceil (len(resources)/5)
		# TODO: this fails if len is less than 5 (chunkSize = 0 and while loop never ends)
		start=0
		end=start+chunkSize
		lastIter=False
		chunks=[]
		if (end+chunkSize>len(resources)):
			end=len(resources)		
			lastIter=True	

		while 1:
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
		print ("# of chunks",len(chunks))
		for chunk in chunks:
			print ("chunksize: ",len(chunk))
			

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
		call(["node", join(project_path, "analysis", "runLighthouse.js"), self.countryPath, approach, str(c)] + _resources)

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

	def collectWorkingResources(self,file):
		workingResources=[]
		ttbDict=utils.load_json(join(self.countryPath, "lighthouseTTB" + file+ ".json"))

		count=0
		for dict in ttbDict:
			count+=1
			if "ttfb" in dict.keys():
				workingResources.append(dict["website"])
		print (count,len(workingResources))
		# join(self.countryPath,
		# with open(self.countryPath,"AlexaUniqueWResources.txt","w") as f:
		with open(join(self.countryPath,"AlexaUniqueWResources.txt"),"w") as f:
			for resource in workingResources:
				f.write(resource+"\n")
			f.close()

	def runWebPerformanceTests(self,approach):
		self.paralleliseLighthouse(approach)
		mergeddict={}
		for x in range(5):
			if os.path.exists(join(self.countryPath, "lighthouseTTB" + approach + str(x) + ".json")):
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
		#if workingresources not present in directory collect that and rerun measurement with Google
		# print (country+"/AlexaUniqueWResources.txt")
		if not os.path.exists(join(project_path,"analysis","measurements/"+country+"/AlexaUniqueWResources.txt")):
			self.collectWorkingResources("Google0")
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
	# country = input("Enter alpha-2 country code: ")
	if not os.path.exists(join(project_path, "analysis", "measurements")):
		os.mkdir(join(project_path, "analysis", "measurements"))
	
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

	if not os.path.exists(join(project_path, "analysis", "measurements", country)):
		os.mkdir(join(project_path, "analysis", "measurements", country))

	publicDNSServers=[]
	allpublicDNSServers = json.load(open(join(project_path, "data", "country_public_dns.json")))
	mainpDNS=["8.8.8.8","9.9.9.9","1.1.1.1"]


	if not os.path.exists(join(project_path,"analysis","measurements/"+country+"/AlexaUniqueResources.txt")):
		resourceCollector.runResourceCollector()

	resources=[]
	with open(join(project_path,"analysis","measurements/"+country+"/AlexaUniqueResources.txt"),"r") as f:
		for resource in f:
			resources.append(resource.split("\n")[0])

	#for the client randomly shuffle 100 resources and carry measurements on that	
	random.shuffle(resources)
	resources=resources[:100]
	tests = WebPerformanceTests(join(project_path, "analysis", "measurements", country),resources)


	for pDNS in allpublicDNSServers[country]:
		if len(publicDNSServers)>8:
			break
		if pDNS["reliability"]>=0.95 and pDNS["ip"] not in mainpDNS:
			try:
				ipaddress.IPv4Network(pDNS["ip"])
				if tests.checkResolver(pDNS["ip"])==False:
					print("Failed: %s not valid" % pDNS["ip"])
					continue
				print("Succeeded: adding %s to test list" % pDNS["ip"])
				publicDNSServers.append(pDNS["ip"])
			except Exception as e:
				print ("Invalid IP", pDNS["ip"], e)
				continue
	print("Done filtering")

	if len(publicDNSServers)>8:
		publicDNSServers=publicDNSServers[:8]
	with open(join(project_path, "analysis", "measurements", country, "publicDNSServers.json"),'w') as fp:
		json.dump(publicDNSServers, fp, indent=4)

	while 1:
		if os.path.exists(join(project_path, "dat")):
			print ("starting measurements")
			break
		time.sleep(1)

	
	tests.runAllApproaches(join(project_path, "analysis", "measurements", country))
	del tests