import json
import os
import json
import time
import subprocess
from subprocess import call
from joblib import Parallel, delayed
import utils

project_path = utils.project_path


class WebPerformanceTests:
	def __init__(self,countryPath):
		self.countryPath=countryPath
		self.resources=[]

	def paralleliseLighthouse(self,approach):
		with open(self.countryPath+"AlexaUniqueResources.txt","r") as f:
			for resource in f:
				self.resources.append(resource.split("\n")[0])
		print (len(self.resources))
		chunkSize=int (len(self.resources)/5)
		start=0
		end=start+chunkSize
		lastIter=False
		chunks=[]
		while(1):
			chunk=[]	
			for i in range(start,end):
				chunk.append(self.resources[i])
			chunks.append(chunk)

			if (lastIter==True):
				break
			start=end
			end=end+chunkSize

			if (end+chunkSize>len(self.resources)):
				end=len(self.resources)		
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
		call(["node",project_path+"/runLighthouse.js",self.countryPath,approach,str(c)]+_resources)

	def findminttb(self,approach,file1,file2,file3):
		ttbDict1=utils.load_json(self.countryPath+"lighthouseTTB"+file1+".json")
		ttbDict2=utils.load_json(self.countryPath+"lighthouseTTB"+file2+".json")
		ttbDict3=utils.load_json(self.countryPath+"lighthouseTTB"+file3+".json")


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
		utils.dump_json(minttbdict,self.countryPath+"lighthouseTTB"+approach+".json")

	def runWebPerformanceTests(self,approach):
		self.paralleliseLighthouse(approach)
		mergeddict={}
		for x in range(5):
			ttbDict=utils.load_json(self.countryPath+"lighthouseTTB"+approach+str(x)+".json")
			for dict in ttbDict:
				if "ttfb" in dict.keys():
					mergeddict[dict['website']]=dict['ttfb']
			call(["rm","-rf",self.countryPath+"lighthouseTTB"+approach+str(x)+".json"])

		minttbdict=[]
		for website in mergeddict:
			dict={}
			dict['website']=website
			dict['ttfb']=mergeddict[website]
			minttbdict.append(dict)
		utils.dump_json(minttbdict, self.countryPath+"lighthouseTTB"+approach+".json")
		
	def runAllApproaches(self):
		self.runWebPerformanceTests("GoogleDoH0")
		self.runWebPerformanceTests("GoogleDoH1")
		self.runWebPerformanceTests("GoogleDoH2")
		self.findminttb("GoogleDoH","GoogleDoH0","GoogleDoH1","GoogleDoH2")
		print("Done Testing Google DoH")

		time.sleep(1*20)
		self.runWebPerformanceTests("CloudflareDoH0")
		self.runWebPerformanceTests("CloudflareDoH1")
		self.runWebPerformanceTests("CloudflareDoH2")
		self.findminttb("CloudflareDoH","CloudflareDoH0","CloudflareDoH1","CloudflareDoH2")
		print("Done Testing Cloudflare DoH")

		time.sleep(1*20)
		self.runWebPerformanceTests("Quad9DoH0")
		self.runWebPerformanceTests("Quad9DoH1")
		self.runWebPerformanceTests("Quad9DoH2")
		self.findminttb("Quad9DoH","Quad9DoH0","Quad9DoH1","Quad9DoH2")
		print("Done Testing Quad9 DoH")


		time.sleep(1*20)
		self.runWebPerformanceTests("DoHProxy0")
		self.runWebPerformanceTests("DoHProxy1")
		self.runWebPerformanceTests("DoHProxy2")
		self.findminttb("DoHProxy","DoHProxy0","DoHProxy1","DoHProxy2")
		print("Done Testing DoHProxy")

		time.sleep(1*20)
		self.runWebPerformanceTests("DoHProxyNP0")
		self.runWebPerformanceTests("DoHProxyNP1")
		self.runWebPerformanceTests("DoHProxyNP2")
		self.findminttb("DoHProxyNP","DoHProxyNP0","DoHProxyNP1","DoHProxyNP2")
		print("Done Testing DoHProxyNP")

		time.sleep(1*20)
		self.runWebPerformanceTests("SubRosa0")
		self.runWebPerformanceTests("SubRosa1")
		self.runWebPerformanceTests("SubRosa2")
		self.findminttb("SubRosa","SubRosa0","SubRosa1","SubRosa2")
		print("Done Testing SubRosa")


		time.sleep(1*20)
		self.runWebPerformanceTests("SubRosaNP0")
		self.runWebPerformanceTests("SubRosaNP1")
		self.runWebPerformanceTests("SubRosaNP2")
		self.findminttb("SubRosaNP","SubRosaNP0","SubRosaNP1","SubRosaNP2")
		print("Done Testing SubRosaNP")

		time.sleep(1*20)
		self.runWebPerformanceTests("SubRosaNPR0")
		self.runWebPerformanceTests("SubRosaNPR1")
		self.runWebPerformanceTests("SubRosaNPR2")
		self.findminttb("SubRosaNPR","SubRosaNPR0","SubRosaNPR1","SubRosaNPR2")
		print("Done Testing SubRosaNPR")

if __name__ == "__main__":
	#select country code you want to test with
	country = input("Enter alpha-2 country code: ")
	if not os.path.exists("measurements"):
		os.mkdir("measurements")
	tests=WebPerformanceTests("measurements"+"/")
	tests.runAllApproaches()
	del tests