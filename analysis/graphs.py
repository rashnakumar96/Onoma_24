import json
import os
import matplotlib as mpl 
import numpy as np
from numpy import percentile
import matplotlib.colors as mcolors
import random
mpl.use('agg')
import matplotlib.pyplot as plt
import subprocess

def runtraceroutes(resultFile,dir):
	resFile=json.load(open(dir+resultFile))
	replicaIPs=[]
	for resolver in resFile:
		for site in resFile[resolver]:
			try:
				replica=resFile[resolver][site]['ReplicaIP']
				if replica not in replicaIPs:
					replicaIPs.append(replica)
			except:
				continue
	print (len(replicaIPs))
	dict={}
	dict['replicaIPs']=replicaIPs
	with open(dir+"replicaIPs.json",'w') as fp:
		json.dump(dict,fp,indent=4)
	# for hostname in replicaIPs:
	# 	traceroute = subprocess.Popen(["traceroute", '-w', '100',hostname],stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
	# 	for line in iter(traceroute.stdout.readline,""):
	# 		print(line)
	# 	break


def PingPlots(resultFile,dir):
	resFile=json.load(open(dir+resultFile))
	labels=[]
	CTEs=[]
	error=[]
	for resolver in resFile:
		labels.append(resolver)
		CTEs.append(float(resFile[resolver].split("/")[1]))
		print (resFile[resolver].split("/")[3].split(" ms")[0])
		error.append(float(resFile[resolver].split("/")[3].split(" ms")[0]))
	x_pos = np.arange(len(labels))
	fig, ax = plt.subplots()
	ax.bar(x_pos, CTEs,
	       yerr=error,
	       align='edge',
	       alpha=0.5,
	       ecolor='black',
	       capsize=10)
	ax.set_ylabel('Ping Times')
	# ax.tick_params(labelsize=7,rotation=20)
	ax.set_xticks(x_pos)
	ax.set_xticklabels(labels)
	plt.xticks(fontsize=7, rotation=28)
	ax.set_title("Ping Times of each resolver")
	ax.yaxis.grid(True)

	# Save the figure and show
	# plt.tight_layout()
	plt.savefig(dir+'graphs/ResolverPingTimes.png')
	

def DNSLatencyPlots(resultFile,metric,feature,_type,dir):
	resFile=json.load(open(resultFile))
	SubRosa=[]
	GoogleDoH=[]
	Quad9DoH=[]
	CloudflareDoH=[]
	DoHProxy=[]

	myresolvers=["SubRosa","SubRosaNP","SubRosaNPR","DoHProxy","DoHProxyNP"]
	dict={}
	publicDNSResolvers=json.load(open(dir+"publicDNSServers.json"))
	# print ("publicDNSResolvers: ",publicDNSResolvers)


	mainResolvers=["Google","Quad9","Cloudflare","DoHProxy","SubRosa"]
	
	#set a threshold, if a resolver has sites less than threshold, discard that resolver
	_max=0
	resolverlengths=[]
	for resolver in resFile:
		resolverlengths.append(len(resFile[resolver]))
	_max=max(resolverlengths)
	threshhold=(0.1*_max)

	workingResolvers=0
	for resolver in resFile:
		if len(resFile[resolver])<threshhold:
			continue
		workingResolvers+=1
		for site in resFile[resolver]:
			if site not in dict:
				dict[site]={}
			try:
				if metric=="DNS Resolution Time":
					values=[]
					for value in resFile[resolver][site][metric]:
						values.append(int(value.split(" ms")[0]))
					if resolver not in dict[site]:
						dict[site][resolver]={}
					dict[site][resolver][metric]={}
					dict[site][resolver][metric]['min']=min(values)
					dict[site][resolver][metric]['max']=max(values)
				elif metric=="Replica Ping":
					value=resFile[resolver][site][metric]
					if resolver not in dict[site]:
						dict[site][resolver]={}
					dict[site][resolver][metric]={}
					dict[site][resolver][metric]['min']=float(value.split("/")[0])
					dict[site][resolver][metric]['max']=float(value.split("/")[2])
			except Exception as e:
				# print (resolver,site,metric)
				continue
	# with open(dir+"dnsLatenciesbyResolver.json",'w') as fp:
	# 	json.dump(dict,fp,indent=4)
	# print (len(resolverlengths),workingResolvers)
	
	graphdict={}
	for site in dict:
		if len(dict[site])<workingResolvers:
			continue
		for resolver in dict[site]:
			_resolver=""

			if resolver=="SubRosa" and feature=="":
				_resolver="SubRosa"
			elif resolver=="DoHProxy" and feature=="":
				_resolver="DoHProxy"
			elif resolver=="SubRosaNP" and feature=="PrivacyDisabled":
				_resolver="SubRosa"
			elif resolver=="DoHProxyNP" and feature=="PrivacyDisabled":
				_resolver="DoHProxy"
			elif resolver=="SubRosaNPR" and feature=="Privacy+RacingDisabled":
				_resolver="SubRosa"
			elif resolver=="DoHProxyNP" and feature=="Privacy+RacingDisabled":
				_resolver="DoHProxy"
			elif resolver not in myresolvers:
				_resolver=resolver
			if (_resolver not in mainResolvers and _resolver not in publicDNSResolvers):
				continue
			if _resolver not in graphdict:
				graphdict[_resolver]={}
				graphdict[_resolver][metric]=[]
			# print (resolver,_resolver,metric,_type,dict[site][resolver],site)

			graphdict[_resolver][metric].append(dict[site][resolver][metric][_type])
			# except:
				# continue
	# print (graphdict.keys())
	for resolver in graphdict:
		print (resolver,len(graphdict[resolver][metric]))
	# 	if len (graphdict[resolver]["ReplicaPing"])==0:
	# 		print (metric,graphdict[resolver])
	# 		continue
	# 	# print (metric,graphdict[resolver])
		q25, q75 = percentile(graphdict[resolver][metric], 25), percentile(graphdict[resolver][metric], 75)
		iqr = q75 - q25
		cut_off = iqr * 1.5
		lower, upper = q25 - cut_off, q75 + cut_off
		graphdict[resolver]["percentile"]=[x for x in graphdict[resolver][metric] if x >= lower and x <= upper]

	for resolver in graphdict:
		if "percentile" not in graphdict[resolver]:
			continue
		graphdict[resolver]["sorted"]=np.sort(graphdict[resolver]["percentile"])

	for resolver in graphdict:
		if "sorted" not in graphdict[resolver]:
			continue
		graphdict[resolver]["p"]=1. * np.arange(len(graphdict[resolver]["sorted"]))/(len(graphdict[resolver]["sorted"]) - 1)

	plt.clf()
	mainResolvers=["Google","Quad9","Cloudflare","DoHProxy","SubRosa"]
	colorArray=[]
	for key in mcolors.CSS4_COLORS:
		colorArray.append(key)

	for resolver in graphdict:
		if resolver in mainResolvers or "sorted" not in graphdict[resolver]:
			continue
		else:
			while 1:
				rcolor=random.randint(0,len(colorArray)-1)
				# print (colorArray[rcolor])
				if "green" not in colorArray[rcolor] and "red" not in colorArray[rcolor] and "white" not in colorArray[rcolor] and "snow" not in colorArray[rcolor]:
					break
			plt.plot(graphdict[resolver]["sorted"],graphdict[resolver]["p"],color=colorArray[rcolor],marker='.',label=resolver)


	plt.plot(graphdict["Google"]["sorted"],graphdict["Google"]["p"],color='c',marker='.',label="GoogleDoH")
	plt.plot(graphdict["Quad9"]["sorted"],graphdict["Quad9"]["p"],color='y',marker='.',label="Quad9DoH")
	plt.plot(graphdict["Cloudflare"]["sorted"],graphdict["Cloudflare"]["p"],color='m',marker='.',label="CloudflareDoH")
	plt.plot(graphdict["DoHProxy"]["sorted"],graphdict["DoHProxy"]["p"],color='r',marker='.',label="DoHProxy")
	plt.plot(graphdict["SubRosa"]["sorted"],graphdict["SubRosa"]["p"],color='g',marker='.',label="SubRosa")

	plt.legend(loc='lower right')
	if metric=="Replica Ping":
		plt.title(metric+' of domains of Alexa Top sites')
	else:
		plt.title("DNS Resolution Time"+' of domains of Alexa Top sites')

	plt.xlabel('Time in ms')
	plt.ylabel('CDF')
	plt.margins(0.02)

	if metric=="Replica Ping":
		plt.savefig(dir+'graphs/'+_type+metric+feature)
	else:
		plt.savefig(dir+'graphs/'+_type+"DNS Resolution Time"+feature)


def resourcesttb(dir):
	from os import listdir
	from os.path import isfile, join

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
		ttbDict=json.load(open(dir+"lighthouseTTB"+approach+"_.json"))
		for dict in ttbDict:
			if "ttfb" in dict.keys():
				if approach not in resourcesttfb:
					resourcesttfb[approach]={}
				if dict["website"] not in resourcesttfb[approach]:
					resourcesttfb[approach][dict["website"]]={}
				resourcesttfb[approach][dict["website"]]["ttfb"]=dict["ttfb"]

	with open(dir+"lighthouseResourcesttb.json",'w') as fp:
		json.dump(resourcesttfb,fp,indent=4)

def resourcesttbbyCDN(ttbfile,cdnfile,tool,dir):
	
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
	with open(dir+"resourcesttbbyCDNLighthouse.json",'w') as fp:
		json.dump(dict, fp, indent=4)	



def resourcesCDF(file,cdn,dir,feature):
	import matplotlib.pyplot as plt
	GoogleDoH=[]
	CloudflareDoH=[]
	SubRosa=[]
	Quad9DoH=[]
	DoHProxy=[]
	SubRosa2=[]
	Verisign=[]
	Verizon=[]
	LocalR=[]
	ttbdict=json.load(open(file))
	# publicDNSResolvers=json.load(open(dir+"publicDNSServers.json"))
	publicDNSResolvers=[]

	graphdict={}
	myresolvers=["SubRosa","SubRosaNP","SubRosaNPR","DoHProxy","DoHProxyNP"]
	mainResolvers=["Google","Quad9","Cloudflare","DoHProxy","SubRosa"]
	cdns=["Google","Akamai","Fastly","Cloudflare","Amazon"]
	if cdn=="allCDNs":
		for _cdn in cdns:
			ttbByCDN=ttbdict[_cdn]
			for site in ttbByCDN:
				if feature=="":
					if "SubRosa" not in ttbByCDN[site].keys() or "DoHProxy" not in ttbByCDN[site].keys():
						continue
				elif feature=="PrivacyDisabled":
					if "SubRosaNP" not in ttbByCDN[site].keys() or "DoHProxyNP" not in ttbByCDN[site].keys():
						continue
				elif feature=="Privacy+RacingDisabled":
					if "SubRosaNPR" not in ttbByCDN[site].keys() or "DoHProxyNP" not in ttbByCDN[site].keys():
						continue
				shouldContinue=False
				for resolver in mainResolvers[:3]:
					if resolver not in ttbByCDN[site].keys():
						shouldContinue=True
				if shouldContinue:
					continue
				_resolver=""
				for resolver in ttbByCDN[site]:
					if resolver=="SubRosa" and feature=="":
						_resolver="SubRosa"
					elif resolver=="DoHProxy" and feature=="":
						_resolver="DoHProxy"
					elif resolver=="SubRosaNP" and feature=="PrivacyDisabled":
						_resolver="SubRosa"
					elif resolver=="DoHProxyNP" and feature=="PrivacyDisabled":
						_resolver="DoHProxy"
					elif resolver=="SubRosaNPR" and feature=="Privacy+RacingDisabled":
						_resolver="SubRosa"
					elif resolver=="DoHProxyNP" and feature=="Privacy+RacingDisabled":
						_resolver="DoHProxy"
					elif resolver not in myresolvers:
						_resolver=resolver
					if _resolver not in graphdict and (_resolver in mainResolvers or _resolver in publicDNSResolvers):
						graphdict[_resolver]={}
						graphdict[_resolver]["ttb"]=[]
					if _resolver in mainResolvers or _resolver in publicDNSResolvers:
						graphdict[_resolver]["ttb"].append(ttbByCDN[site][resolver])
					


	else:
		ttbByCDN=ttbdict[cdn]

		for site in ttbByCDN:
			if feature=="":
				if "SubRosa" not in ttbByCDN[site].keys() or "DoHProxy" not in ttbByCDN[site].keys():
					continue
			elif feature=="PrivacyDisabled":
				if "SubRosaNP" not in ttbByCDN[site].keys() or "DoHProxyNP" not in ttbByCDN[site].keys():
					continue
			elif feature=="Privacy+RacingDisabled":
				if "SubRosaNPR" not in ttbByCDN[site].keys() or "DoHProxyNP" not in ttbByCDN[site].keys():
					continue
			shouldContinue=False
			for resolver in mainResolvers[:3]:
				if resolver not in ttbByCDN[site].keys():
					shouldContinue=True
			if shouldContinue:
				continue
			_resolver=""
			for resolver in ttbByCDN[site]:
				if resolver=="SubRosa" and feature=="":
					_resolver="SubRosa"
				elif resolver=="DoHProxy" and feature=="":
					_resolver="DoHProxy"
				elif resolver=="SubRosaNP" and feature=="PrivacyDisabled":
					_resolver="SubRosa"
				elif resolver=="DoHProxyNP" and feature=="PrivacyDisabled":
					_resolver="DoHProxy"
				elif resolver=="SubRosaNPR" and feature=="Privacy+RacingDisabled":
					_resolver="SubRosa"
				elif resolver=="DoHProxyNP" and feature=="Privacy+RacingDisabled":
					_resolver="DoHProxy"
				elif resolver not in myresolvers:
					_resolver=resolver
				if _resolver not in graphdict and (_resolver in mainResolvers or _resolver in publicDNSResolvers):
					graphdict[_resolver]={}
					graphdict[_resolver]["ttb"]=[]
				if _resolver in mainResolvers or _resolver in publicDNSResolvers:
					graphdict[_resolver]["ttb"].append(ttbByCDN[site][resolver])
			
	for key in graphdict:
		print(key,len(graphdict[key]["ttb"]))

	avg=[]
	bars=[]
	for resolver in mainResolvers:
		if resolver=="DoHProxy":
			continue
		bars.append(resolver)
		# avg.append(min(graphdict[resolver]['ttb'])/len(graphdict[resolver]['ttb']))
		avg.append(sum(graphdict[resolver]['ttb'])/len(graphdict[resolver]['ttb']))
		print (resolver+": ",sum(graphdict[resolver]['ttb'])/len(graphdict[resolver]['ttb']))	

	# y_pos = np.arange(len(bars))
	# fig, ax = plt.subplots()

	# ax.bar(y_pos, avg, color=('c','hotpink','sandybrown','mediumseagreen'))
	# ax.set_xticks(y_pos)
	# ax.set_xticklabels(bars)
	# ax.set_title("Average Time to first Byte of Alexa top sites' resources")
	# ax.set_ylabel('ms')


	# ax.yaxis.grid(True)
	# plt.savefig(dir+"graphs/siteTTFB"+cdn+feature)

	
	for resolver in graphdict:
		q25, q75 = percentile(graphdict[resolver]["ttb"], 25), percentile(graphdict[resolver]["ttb"], 75)
		iqr = q75 - q25
		cut_off = iqr * 1.5
		lower, upper = q25 - cut_off, q75 + cut_off
		graphdict[resolver]["percentile"]=[x for x in graphdict[resolver]["ttb"] if x >= lower and x <= upper]

	for resolver in graphdict:
		graphdict[resolver]["sorted"]=np.sort(graphdict[resolver]["percentile"])

	for resolver in graphdict:
		graphdict[resolver]["p"]=1. * np.arange(len(graphdict[resolver]["sorted"]))/(len(graphdict[resolver]["sorted"]) - 1)

	plt.clf()
	colorArray=[]
	for key in mcolors.CSS4_COLORS:
		colorArray.append(key)
	selectedColors=[]
	avoidColors=["green","red","white","snow","smoke"]
	for resolver in graphdict:
		if resolver in mainResolvers:
			continue
		else:
			while 1:
				rcolor=random.randint(0,len(colorArray)-1)
				if colorArray[rcolor] not in avoidColors and colorArray[rcolor] not in selectedColors:					
					selectedColors.append(colorArray[rcolor])
					break
			plt.plot(graphdict[resolver]["sorted"],graphdict[resolver]["p"],color=colorArray[rcolor],marker='.',label=resolver)
	# print (graphdict)

	plt.plot(graphdict["Google"]["sorted"],graphdict["Google"]["p"],color='c',marker='.',label="GoogleDoH")
	plt.plot(graphdict["Quad9"]["sorted"],graphdict["Quad9"]["p"],color='y',marker='.',label="Quad9DoH")
	plt.plot(graphdict["Cloudflare"]["sorted"],graphdict["Cloudflare"]["p"],color='m',marker='.',label="CloudflareDoH")
	plt.plot(graphdict["DoHProxy"]["sorted"],graphdict["DoHProxy"]["p"],color='r',marker='.',label="DoHProxy")
	plt.plot(graphdict["SubRosa"]["sorted"],graphdict["SubRosa"]["p"],color='g',marker='.',label="SubRosa")


	plt.legend()
	plt.title("TTFB"+' of Alexa Top sites hosted on '+cdn)
	plt.xlabel('Time in ms')
	plt.ylabel('CDF')
	plt.margins(0.02)
	# plt.axis([0, None, None, None])
	if not os.path.exists(dir+"graphs"):
		os.mkdir(dir+"graphs")
	print (dir+"graphs/lighthouseTTFB"+cdn)
	plt.savefig(dir+"graphs/lighthouseTTFB"+cdn+feature)

def plotLighthouseGraphs(countrycode):

	# resourcesttb(countrycode) 
	# resourcesttbbyCDN(countrycode+"lighthouseResourcesttb.json",countrycode+"cdnMapping.json","lighthouse",countrycode)
	
	# resourcesCDF(countrycode+"resourcesttbbyCDNLighthouse.json","Google",countrycode,"")
	# resourcesCDF(countrycode+"resourcesttbbyCDNLighthouse.json","Cloudflare",countrycode,"")
	# resourcesCDF(countrycode+"resourcesttbbyCDNLighthouse.json","Amazon",countrycode,"")
	# resourcesCDF(countrycode+"resourcesttbbyCDNLighthouse.json","Fastly",countrycode,"")
	# resourcesCDF(countrycode+"resourcesttbbyCDNLighthouse.json","Akamai",countrycode,"")
	# resourcesCDF(countrycode+"resourcesttbbyCDNLighthouse.json","allCDNs",countrycode,"")

	resourcesCDF(countrycode+"resourcesttbbyCDNLighthouse.json","Google",countrycode,"PrivacyDisabled")
	resourcesCDF(countrycode+"resourcesttbbyCDNLighthouse.json","Cloudflare",countrycode,"PrivacyDisabled")
	resourcesCDF(countrycode+"resourcesttbbyCDNLighthouse.json","Amazon",countrycode,"PrivacyDisabled")
	resourcesCDF(countrycode+"resourcesttbbyCDNLighthouse.json","Fastly",countrycode,"PrivacyDisabled")
	resourcesCDF(countrycode+"resourcesttbbyCDNLighthouse.json","Akamai",countrycode,"PrivacyDisabled")
	resourcesCDF(countrycode+"resourcesttbbyCDNLighthouse.json","allCDNs",countrycode,"PrivacyDisabled")

	resourcesCDF(countrycode+"resourcesttbbyCDNLighthouse.json","Google",countrycode,"Privacy+RacingDisabled")
	resourcesCDF(countrycode+"resourcesttbbyCDNLighthouse.json","Cloudflare",countrycode,"Privacy+RacingDisabled")
	resourcesCDF(countrycode+"resourcesttbbyCDNLighthouse.json","Amazon",countrycode,"Privacy+RacingDisabled")
	resourcesCDF(countrycode+"resourcesttbbyCDNLighthouse.json","Fastly",countrycode,"Privacy+RacingDisabled")
	resourcesCDF(countrycode+"resourcesttbbyCDNLighthouse.json","Akamai",countrycode,"Privacy+RacingDisabled")
	resourcesCDF(countrycode+"resourcesttbbyCDNLighthouse.json","allCDNs",countrycode,"Privacy+RacingDisabled")

def plotDNSLatencyGraphs(countrycode):
	# DNSLatencyPlots(countrycode+"/dnsLatencies.json","DNS Resolution Time","","min",countrycode+"/")
	# DNSLatencyPlots(countrycode+"/dnsLatencies.json","DNS Resolution Time","","max",countrycode+"/")
	# DNSLatencyPlots(countrycode+"/dnsLatencies.json","Replica Ping","","min",countrycode+"/")
	# DNSLatencyPlots(countrycode+"/dnsLatencies.json","Replica Ping","","max",countrycode+"/")

	DNSLatencyPlots(countrycode+"/dnsLatencies.json","DNS Resolution Time","PrivacyDisabled","min",countrycode+"/")
	DNSLatencyPlots(countrycode+"/dnsLatencies.json","DNS Resolution Time","PrivacyDisabled","max",countrycode+"/")
	DNSLatencyPlots(countrycode+"/dnsLatencies.json","Replica Ping","PrivacyDisabled","min",countrycode+"/")
	DNSLatencyPlots(countrycode+"/dnsLatencies.json","Replica Ping","PrivacyDisabled","max",countrycode+"/")

	DNSLatencyPlots(countrycode+"/dnsLatencies.json","DNS Resolution Time","Privacy+RacingDisabled","min",countrycode+"/")
	DNSLatencyPlots(countrycode+"/dnsLatencies.json","DNS Resolution Time","Privacy+RacingDisabled","max",countrycode+"/")
	DNSLatencyPlots(countrycode+"/dnsLatencies.json","Replica Ping","Privacy+RacingDisabled","min",countrycode+"/")
	DNSLatencyPlots(countrycode+"/dnsLatencies.json","Replica Ping","Privacy+RacingDisabled","max",countrycode+"/")


def main():
	countryPath="IN"
	plotLighthouseGraphs(countryPath+"/")
	# PingPlots("pingServers.json",countryPath+"/")
	# plotDNSLatencyGraphs(countryPath)

main()



