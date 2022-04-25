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
from threading import Timer
from os.path import isfile, join
import pandas as pd




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
	# dict['replicaIPs']=replicaIPs
	timeout_sec=60
	for hostname in replicaIPs:
		print (hostname)
		traceroute = subprocess.Popen(["traceroute", '-w', '100',hostname],stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
		timer = Timer(timeout_sec, traceroute.kill)
		try:
			timer.start()
			stdout, stderr = traceroute.communicate()
		finally:
			timer.cancel()
		print (str(stdout))
		dict[hostname]=str(stdout)
		
	with open(dir+"traceroutereplicaIPs.json",'w') as fp:
		json.dump(dict,fp,indent=4)

def CDNDistribution():
	import pandas as pd

	cdnList=["Akamai","Fastly","Amazon"]
	countryList=["AR","DE","IN","US"]
	countryCDN={}
	for country in countryList:
		CDNDistribution=json.load(open("measurements/"+country+"/resourcesttbbyCDNLighthouse.json"))
		dict={}
		for cdn in CDNDistribution:
			dict[cdn]=[]	
			if cdn in cdnList:
				if cdn not in countryCDN:
					countryCDN[cdn]=[]
				for site in CDNDistribution[cdn]:
					if site not in dict[cdn]:
						dict[cdn].append(site)
				print (country,cdn,len(dict[cdn]))
				countryCDN[cdn].append(len(dict[cdn]))
	print (countryCDN)

    # Creating dataframe
	exam_data = {'Countries': countryList,
                'Akamai': countryCDN["Akamai"],
                'Amazon': countryCDN["Amazon"],
                'Fastly': countryCDN["Fastly"]}

	df = pd.DataFrame(exam_data, columns = ['Countries', 'Akamai', 'Amazon', 'Fastly'])
	print(); print(df)
	clrs=['brown','blue','orange','purple','lightcoral','tan','slategrey','aquamarine'] 
	# Setting the positions and width for the bars
	pos = list(range(len(df['Akamai'])))
	width = 0.25

	# Plotting the bars
	fig, ax = plt.subplots(figsize=(10,5))

	# Creating a bar with Akamai data
	plt.bar(pos, 100*df['Akamai']/(df['Akamai']+df['Amazon']+df['Fastly']), width, alpha=0.5, color='c')
	#plt.show()

	# Creating a bar with Amazon data,
	plt.bar([p + width for p in pos], 100*df['Amazon']/(df['Akamai']+df['Amazon']+df['Fastly']), width, alpha=0.5, color='purple')
	#plt.show()

	# Creating a bar with Fastly data,
	plt.bar([p + width*2 for p in pos], 100*df['Fastly']/(df['Akamai']+df['Amazon']+df['Fastly']), width, alpha=0.5, color='red')
	#plt.show()

	# Setting the y axis label
	ax.set_ylabel('Percentage of resources hosted on each CDN')

	# Setting the chart's title
	ax.set_title('Difference in CDN Distribution across different Countries')

	# Setting the position of the x ticks
	ax.set_xticks([p + 1.5 * width for p in pos])

	# Setting the labels for the x ticks
	ax.set_xticklabels(df['Countries'])
	ax.grid()
	# Setting the x-axis and y-axis limits
	plt.xlim(min(pos)-width, max(pos)+width*4)
	# plt.ylim([0, max(df['Akamai'] + df['Amazon'] + df['Fastly'])] )
	# plt.ylim([0, 900] )


	# Adding the legend and showing the plot
	plt.legend(['Akamai', 'Amazon', 'Fastly'], loc='upper left')
	plt.savefig("CDNDistribution")


def plotDNSDistribution(dir):
	mainResolvers=["Google","Quad9","Cloudflare"]
	
	clrs=['brown','blue','orange','purple','lightcoral','tan','slategrey','aquamarine'] 
	from sklearn import preprocessing
	from matplotlib.patches import Rectangle
	import matplotlib.gridspec as gridspec
	import statistics

	
	files=["DNSDistributionPerformance1 copy","DNSDistributionPerformance2 copy","DNSDistributionPerformance3 copy"]

	datas=[]
	
	for file in files:
		data =[]
		PerformanceCost=json.load(open(dir+file+".json"))
		for approach in PerformanceCost:
			for time in PerformanceCost[approach]:
				data.append(int(time[:-3]))
			
		datas.append(data)
		# _mean=statistics.mean(data)
		# stdev=statistics.stdev(data)
		# print (file,len(data),"mean: ","{:.2f}".format(_mean),"stdev: ","{:.2f}".format(stdev))

	
	X=[(2,3,1), (2,3,2), (2,3,3), (2,3,(4,6))]
	fig =plt.figure(figsize=(6,4))
	plt.subplots_adjust(wspace=0, hspace=0)
	z=0
	width = 2
	height = 0.7

	files=["DNSDistribution1 copy","DNSDistribution2 copy","DNSDistribution3 copy"]
	tempPlots=[]
	for fname in files:
		if z==0:
			sub=fig.add_subplot(X[z][0],X[z][1],X[z][2])
		if z!=0:
			sub=fig.add_subplot(X[z][0],X[z][1],X[z][2],sharey=tempPlots[0])
		tempPlots.append(sub)

		if z!=0:
			sub.axvline(x=0,ymin=0,linestyle="solid",c="black",linewidth=8,zorder=0, clip_on=True)
		
		numbers=[]
		DNSDistribution=json.load(open(dir+fname+".json"))
		TotalRequests=0
		requestsPerResolver=[]

		resolvers=[]
		i=0
		dict={}
		
		for resolver in DNSDistribution:
			y=[]
			if resolver not in dict:
				dict[resolver]=[]
			for x in (DNSDistribution[resolver]):
				y.append(i)
				dict[resolver].append((x))
				if x not in numbers:
					numbers.append(x)
			if resolver not in mainResolvers:
				_label=resolver[:3]+".x.x."+resolver[-1]
			else:
				_label=resolver

			resolvers.append(_label)

			a=(dict[resolver],y)
			a_zipped = zip(*a)
			if resolver=="Google":
				sub.scatter(dict[resolver],y,color='c',marker='*', s=2,label=_label)
			elif resolver=="Cloudflare":
				sub.scatter(dict[resolver],y,color='m',marker='*', s=2,label=_label)
			elif resolver=="Quad9":
				sub.scatter(dict[resolver],y,color='y',marker='*', s=2,label=_label)
			else:
				sub.scatter(dict[resolver],y,color=clrs[i],marker='*', s=2,label=_label)
			for a_x, a_y in a_zipped:
				if resolver=="Google":
					sub.add_patch(Rectangle(xy=(a_x-width/2, a_y-height/2) ,width=width, height=height, linewidth=1, color='c', fill=True,alpha=0.5))
				elif resolver=="Cloudflare":
					sub.add_patch(Rectangle(xy=(a_x-width/2, a_y-height/2) ,width=width, height=height, linewidth=1, color='m', fill=True,alpha=0.5))
				elif resolver=="Quad9":
					sub.add_patch(Rectangle(xy=(a_x-width/2, a_y-height/2) ,width=width, height=height, linewidth=1, color='y', fill=True,alpha=0.5))
				else:
					sub.add_patch(Rectangle(xy=(a_x-width/2, a_y-height/2) ,width=width, height=height, linewidth=1, color=clrs[i], fill=True,alpha=0.5))
			if z!=0 and z!=2:
				sub.spines['left'].set_visible(False)
				sub.spines['right'].set_visible(False)
			elif z==2:
				sub.spines['left'].set_visible(False)
			i+=1
		# 	requestsPerResolver.append(len(dict[resolver]))

		# print (fname,"totalRequests: ",sum(requestsPerResolver),requestsPerResolver)
		# fractionrequestsPerResolver=[]
		# for x in requestsPerResolver:
		# 	fractionrequestsPerResolver.append(100*x/len(numbers))
		# _max=max(fractionrequestsPerResolver)
		# _avg=statistics.mean(fractionrequestsPerResolver)
		
		# print ("max \% of req/resolver: ","{:.2f}".format(_max),"avg \% of req/resolver: ","{:.2f}".format(_avg))
		# numbers.sort()

		# missing=[]
		# for b in range(numbers[0],numbers[-1]):
		# 	if b not in numbers:
		# 		missing.append(b)

		# print (missing,len(numbers))
		sub.set_xlim([0, None])

		
		
		
		z+=1

	x1 = [0,1,2,3,4,5,6,7]
	for ax in tempPlots:

		ax.label_outer()
		ax.tick_params(
	    axis='x',          # changes apply to the x-axis
	    which='both',      # both major and minor ticks are affected
	    bottom=False,      # ticks along the bottom edge are off
	    top=False,         # ticks along the top edge are off
	    labelbottom=False)

		ax.tick_params(axis='y',which='both',left=False,right=False,labelbottom=False)

	plt.yticks(x1, resolvers)
	
	
	sub=fig.add_subplot(X[3][0],X[3][1],X[3][2])
	sub.set_xticks([])
	# sub.set_yticks([])


	bp = sub.boxplot(datas,patch_artist=True)
	## change outline color, fill color and linewidth of the boxes
	for box in bp['boxes']:
	    # change outline color
	    box.set( color='#7570b3', linewidth=1)
	    # change fill color
	    box.set( facecolor = '#1b9e77' )
	for whisker in bp['whiskers']:
		whisker.set(color='#7570b3', linewidth=1)

	## change color and linewidth of the caps
	for cap in bp['caps']:
	    cap.set(color='#7570b3', linewidth=1)

	## change color and linewidth of the medians
	for median in bp['medians']:
	    median.set(color='#b2df8a', linewidth=1)

	## change the style of fliers and their fill
	for flier in bp['fliers']:
	    flier.set(marker='o', color='#e7298a', alpha=0.5)

	sub.set_xticklabels(["No racing","Racing 2","Racing 3"])
	sub.get_xaxis().tick_bottom()
	sub.get_yaxis().tick_left()
	sub.set_ylim(10, 250)
	sub.set_ylabel("Res.Time(ms)")

	# plt.show()
	# plt.set_title("Comparing ")
	plt.savefig(dir+"graphs/stackedboxPlot")





# def mergePlots(dir):
	
	# print (dict)


def tracerouteAnalysis(dir):

	replicaFile=json.load(open(dir+"dnsLatencies.json"))
	#make dict to store traceroute results
	if not os.path.exists(join(dir,"tracerouteResults")):
		os.mkdir(dir+"tracerouteResults")
	tracerouteFile=json.load(open(dir+"tracerouteFetechedResult"+dir[-3:-1]+".json"))
	print (dir+"tracerouteFetechedResult"+dir[-3:-1]+".json")
	combinedTraceRoute={}

	for approach in replicaFile:
		#remove this resolver for INDIA
		# if approach=="111.93.163.56":
			# continue
		dict={}
		count=0
		countDone=0
		countrtt=0
		combinedTraceRoute[approach]={}
		for site in replicaFile[approach]:
			try:
				dict[site]={}
				combinedTraceRoute[approach][site]={}
				dict[site]["ReplicaIP"]=replicaFile[approach][site]["ReplicaIP"]
				combinedTraceRoute[approach][site]["ReplicaIP"]=replicaFile[approach][site]["ReplicaIP"]
				for _dict in tracerouteFile:
					if _dict["dst_addr"]==replicaFile[approach][site]["ReplicaIP"]:
						dict[site]["tracerouteResult"]=_dict
						try:
							hopCount=0
							tracerouteTime=0

							for hop in _dict["result"]:
								hopCount+=1
								# sum=0
								# for _time in hop["result"]:
								# 	sum+=_time["rtt"] 
								# avg=float(sum)/3
								# tracerouteTime+=avg/2
							# combinedTraceRoute[approach][site]["tracerouteTime"]=tracerouteTime
							combinedTraceRoute[approach][site]["hopCount"]=hopCount

						except:
							countrtt+=1
							del combinedTraceRoute[approach][site]
				countDone+=1
			except Exception as e:
				count+=1
				del combinedTraceRoute[approach][site]
			if site in combinedTraceRoute[approach]:
				# if "tracerouteTime" not in combinedTraceRoute[approach][site]:
				if "hopCount" not in combinedTraceRoute[approach][site]:
					del combinedTraceRoute[approach][site]

		print (approach,countDone,"Missing replica count: ",count,countrtt)
		with open(dir+"tracerouteResults/_tracerouteResult"+approach+".json",'w') as fp:
			json.dump(dict,fp,indent=4)

		__dict={}
		for resolver in combinedTraceRoute:
			for site in combinedTraceRoute[resolver]:
				if site not in __dict:
					__dict[site]={}
				__dict[site][resolver]=combinedTraceRoute[resolver][site]
		
		with open(dir+"tracerouteAnalysis.json",'w') as fp:
			json.dump(__dict,fp,indent=4)

		# for approach in replicaFile:
		# 	for site in replicaFile[approach]:
		# 		try:
		# 			replicaFile[approach][site]["tracerouteTime"]=combinedTraceRoute[approach][site]["tracerouteTime"]

def traceRoutePlots(resultFile,feature,dir):
	resFile=json.load(open(resultFile))
	
	myresolvers=["SubRosa","SubRosaNP","SubRosaNPR","DoHProxy","DoHProxyNP"]
	dict={}
	publicDNSResolvers=json.load(open(dir+"publicDNSServers.json"))
	#remove this resolver for INDIA
	# publicDNSResolvers.remove("111.93.163.56")

	mainResolvers=["Google","Quad9","Cloudflare","DoHProxy","SubRosa"]

	workingResolvers=len(publicDNSResolvers)+len(mainResolvers[:3])+4
	siteCount=0
	print ("workingResolvers: ",workingResolvers)
	graphdict={}
	_graphdict={}
	for site in resFile:
		if len(resFile[site])<workingResolvers:
			continue
		_resolver=""
		siteCount+=1
		resolverList=[]
		
		for resolver in set(resFile[site]):
			if resolver=="SubRosa" and feature=="":
				_resolver="SubRosa"
			elif resolver=="DoHProxyNP" and feature=="":
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
			if _resolver not in _graphdict and (_resolver in mainResolvers or _resolver in publicDNSResolvers): 
				_graphdict[_resolver]={}
				_graphdict[_resolver]["hopCount"]={}
			if _resolver in _graphdict and ((_resolver=="DoHProxy" and resolver=="DoHProxyNP") or (_resolver=="SubRosa" and(resolver=="SubRosa" or resolver=="SubRosaNP" or resolver=="SubRosaNPR")) or _resolver==resolver):
				_graphdict[_resolver]["hopCount"][site]=resFile[site][resolver]["hopCount"]

	for key in _graphdict:
		if key not in graphdict:
			graphdict[key]={}
			graphdict[key]["hopCount"]=[]
			
		for site in _graphdict[key]["hopCount"]: 
			graphdict[key]["hopCount"].append(_graphdict[key]["hopCount"][site])
		print(key,len(graphdict[key]["hopCount"]),siteCount)

	for resolver in graphdict:
		q25, q75 = percentile(graphdict[resolver]["hopCount"], 25), percentile(graphdict[resolver]["hopCount"], 75)
		iqr = q75 - q25
		cut_off = iqr * 1.5
		lower, upper = q25 - cut_off, q75 + cut_off
		graphdict[resolver]["percentile"]=[x for x in graphdict[resolver]["hopCount"] if x >= lower and x <= upper]
	for resolver in graphdict:
		graphdict[resolver]["sorted"]=np.sort(graphdict[resolver]["percentile"])

	for resolver in graphdict:
		graphdict[resolver]["p"]=1. * np.arange(len(graphdict[resolver]["sorted"]))/(len(graphdict[resolver]["sorted"]) - 1)
	
	avoidColors=["green","red","white","snow","smoke"]
	clrs=['brown','blue','orange','purple','lightcoral','tan','slategrey','aquamarine'] 
	i=0
	for resolver in graphdict:
		if resolver in mainResolvers:
			continue
		else:
			rcolor=clrs[i]
			plt.plot(graphdict[resolver]["sorted"],graphdict[resolver]["p"],color=rcolor,marker='.',label=resolver)
			i=i+1
			

	plt.plot(graphdict["Google"]["sorted"],graphdict["Google"]["p"],color='c',marker='.',label="GoogleDoH")
	plt.plot(graphdict["Quad9"]["sorted"],graphdict["Quad9"]["p"],color='y',marker='.',label="Quad9DoH")
	plt.plot(graphdict["Cloudflare"]["sorted"],graphdict["Cloudflare"]["p"],color='m',marker='.',label="CloudflareDoH")
	plt.plot(graphdict["DoHProxy"]["sorted"],graphdict["DoHProxy"]["p"],color='r',marker='.',label="Sharding")
	plt.plot(graphdict["SubRosa"]["sorted"],graphdict["SubRosa"]["p"],color='g',marker='.',label="SubRosa")


	plt.legend()
	plt.title("hopCount of Alexa Top sites")
	plt.xlabel('Number of hops')
	plt.ylabel('CDF')
	plt.margins(0.02)
	# plt.axis([0, None, None, None])
	if not os.path.exists(dir+"graphs"):
		os.mkdir(dir+"graphs")
	print (dir+"graphs/hopCount"+feature)

	plt.savefig(dir+"graphs/hopCount"+feature)
	plt.clf()

	
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
					if sum(values)/len(values)==0:
						# print (values)
						continue
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
			elif resolver=="DoHProxyNP" and feature=="":
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
	print ("\n")

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
	clrs=['brown','blue','orange','purple','lightcoral','tan','slategrey','aquamarine'] 

	for key in mcolors.CSS4_COLORS:
		colorArray.append(key)

	i=0
	for resolver in graphdict:
		if resolver in mainResolvers or "sorted" not in graphdict[resolver]:
			continue
		else:
			rcolor=clrs[i]
			plt.plot(graphdict[resolver]["sorted"],graphdict[resolver]["p"],color=rcolor,marker='.',label=resolver)
			i=i+1


	plt.plot(graphdict["Google"]["sorted"],graphdict["Google"]["p"],color='c',marker='.',label="GoogleDoH")
	plt.plot(graphdict["Quad9"]["sorted"],graphdict["Quad9"]["p"],color='y',marker='.',label="Quad9DoH")
	plt.plot(graphdict["Cloudflare"]["sorted"],graphdict["Cloudflare"]["p"],color='m',marker='.',label="CloudflareDoH")
	plt.plot(graphdict["DoHProxy"]["sorted"],graphdict["DoHProxy"]["p"],color='r',marker='.',label="DoHProxy")
	plt.plot(graphdict["SubRosa"]["sorted"],graphdict["SubRosa"]["p"],color='g',marker='.',label="SubRosa")

	plt.legend()
	if metric=="Replica Ping":
		plt.title(metric+' of domains of Alexa Top sites')
	else:
		plt.title("DNS Resolution Time"+' of domains of Alexa Top sites')

	plt.xlabel('Time in ms')
	plt.ylabel('CDF')
	plt.margins(0.02)
	plt.axis([0, None, None, None])

	if not os.path.exists(dir+"graphs"):
		os.mkdir(dir+"graphs")

	if metric=="Replica Ping":
		plt.savefig(dir+'graphs/'+_type+metric+feature)
	else:
		plt.savefig(dir+'graphs/'+_type+"DNS Resolution Time"+feature)

def DNSLatencyPlotsRelative(resultFile,metric,feature,_type,dir):
	resFile=json.load(open(resultFile))
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
					# print (resolver,sum(values)/len(values))
					if len(values)==0:
						# print (resolver,sum(values)/len(values))
						continue
					# else:
						# print (min(values))
					if resolver not in dict[site]:
						dict[site][resolver]={}
					dict[site][resolver][metric]={}
					dict[site][resolver][metric]['min']=min(values)
					dict[site][resolver][metric]['max']=max(values)
					# print (dict[site][resolver][metric]['min'])
				elif metric=="Replica Ping":
					value=resFile[resolver][site][metric]
					if resolver not in dict[site]:
						dict[site][resolver]={}
					dict[site][resolver][metric]={}
					dict[site][resolver][metric]['min']=float(value.split("/")[0])
					dict[site][resolver][metric]['max']=float(value.split("/")[2])
			except Exception as e:
				# print (resolver,site,metric,str(e))
				continue
	# with open(dir+"dnsLatenciesbyResolver.json",'w') as fp:
	# 	json.dump(dict,fp,indent=4)

	
	graphdict={}
	for site in dict:
		if len(dict[site])<workingResolvers:
			continue
		for resolver in dict[site]:
			_resolver=""

			if resolver=="SubRosa" and feature=="":
				_resolver="SubRosa"
			elif resolver=="DoHProxyNP" and feature=="":
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
			
	#IN
	publicResolvers=["182.71.213.139","111.93.163.56"]
	#PK
	# publicResolvers=["58.27.149.70","202.44.80.25"]
	#AR
	# publicResolvers=["190.151.144.21","200.110.130.194"]
	#US
	# publicResolvers=["208.67.222.222","208.67.220.220"]
	#DE
	# publicResolvers=["46.182.19.48","159.69.114.157"]
	# print (graphdict.keys())
	bestResolver=""
	_min=0
	relativeResolvers=[]
	for resolver in graphdict:
		if resolver in mainResolvers[:4] or resolver in publicResolvers:
			if _min==0 or (percentile(graphdict[resolver][metric], 50))<_min:
				_min=percentile(graphdict[resolver][metric], 50)
				bestResolver=resolver
			# print ("CDN: ",cdn,"resolver: ",resolver," 50percentile: ",percentile(graphdict[resolver]["ttb"], 50),min,bestResolver)
			relativeResolvers.append(resolver)

	print ("best resolver: ",bestResolver)
	relativeResolvers.remove(bestResolver)
	print ("relativeResolvers: ",relativeResolvers)
	# exit()
	for resolver in graphdict:
		if resolver in relativeResolvers:
			# print (len(graphdict[resolver]["ttb"]),len(graphdict[bestResolver]["ttb"]))
			graphdict[resolver]["relative"]=[(graphdict[resolver][metric][x]-graphdict[bestResolver][metric][x]) for x in range(len(graphdict[resolver][metric]))]


	for resolver in graphdict:
		# print (resolver,len(graphdict[resolver][metric]))
		if resolver in relativeResolvers:

			q25, q75 = percentile(graphdict[resolver]["relative"], 25), percentile(graphdict[resolver]["relative"], 75)
			iqr = q75 - q25
			cut_off = iqr * 1.5
			lower, upper = q25 - cut_off, q75 + cut_off
			graphdict[resolver]["percentile"]=[x for x in graphdict[resolver]["relative"] if x >= lower and x <= upper]
	# print ("\n")

	for resolver in graphdict:
		if "percentile" not in graphdict[resolver]:
			continue
		if resolver in relativeResolvers:
			graphdict[resolver]["sorted"]=np.sort(graphdict[resolver]["percentile"])

	for resolver in graphdict:
		if "sorted" not in graphdict[resolver]:
			continue
		if resolver in relativeResolvers:
			graphdict[resolver]["p"]=1. * np.arange(len(graphdict[resolver]["sorted"]))/(len(graphdict[resolver]["sorted"]) - 1)

	plt.clf()
	mainResolvers=["Google","Quad9","Cloudflare","DoHProxy","SubRosa"]
	colorArray=[]
	clrs=['brown','blue','orange','purple','lightcoral','tan','slategrey','aquamarine'] 


	i=0
	styles=['solid', 'dashed', 'dashdot', 'dotted']
	s=0
	for resolver in graphdict:
		if resolver in mainResolvers or "sorted" not in graphdict[resolver] or resolver not in publicResolvers:
			continue
		else:
			if resolver in relativeResolvers:
				rcolor=clrs[i]
				if resolver==publicResolvers[0]:
					_label="Regional1"
				elif resolver==publicResolvers[1]:
					_label="Regional2"
				plt.plot(graphdict[resolver]["sorted"],graphdict[resolver]["p"],color=rcolor,label=_label,linewidth=3,linestyle=styles[s])
				s+=1
				i=i+1

	if "Google"!=bestResolver:
		plt.plot(graphdict["Google"]["sorted"],graphdict["Google"]["p"],color='c',label="GoogleDoH",linewidth=3,linestyle=styles[s])
		s+=1

	if "Quad9"!=bestResolver:
		plt.plot(graphdict["Quad9"]["sorted"],graphdict["Quad9"]["p"],color='y',label="Quad9DoH",linewidth=3,linestyle=styles[s])
		s+=1

	if "Cloudflare"!=bestResolver:
		plt.plot(graphdict["Cloudflare"]["sorted"],graphdict["Cloudflare"]["p"],color='m',label="CloudflareDoH",linewidth=3,linestyle=styles[s])
		s+=1

	if "DoHProxy"!=bestResolver:
		plt.plot(graphdict["DoHProxy"]["sorted"],graphdict["DoHProxy"]["p"],color='r',label="Sharding",linewidth=3,linestyle='solid')
		s+=1
		
	# plt.plot(graphdict["DoHProxy"]["sorted"],graphdict["DoHProxy"]["p"],color='r',marker='.',label="DoHProxy")
	# plt.plot(graphdict["SubRosa"]["sorted"],graphdict["SubRosa"]["p"],color='g',marker='.',label="SubRosa")

	plt.legend()
	if metric=="Replica Ping":
		plt.title(metric+' of resources of Alexa Top sites')
	else:
		plt.title("DNS Resolution Time"+' of domains of Alexa Top sites')

	if bestResolver in publicResolvers: 
		plt.xlabel('Time in ms relative to '+bestResolver+"(Regional)")
	else:
		plt.xlabel('Time in ms relative to '+bestResolver)

	plt.ylabel('CDF')
	plt.margins(0.02)
	plt.axis([0, None, None, None])
	plt.grid()

	if not os.path.exists(dir+"resolverPerformance"):
		os.mkdir(dir+"resolverPerformance")

	if metric=="Replica Ping":
		plt.savefig(dir+'resolverPerformance/'+_type+metric+feature)
	else:
		plt.savefig(dir+'resolverPerformance/'+_type+"DNS Resolution Time"+feature)

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
		# if approach=="SubRosaNPR":
		# 	continue
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

def resourcesbyCDN(ttbfile,cdnfile,metric,dir):
	
	timedict=json.load(open(ttbfile))
	cdndict=json.load(open(cdnfile))
	dict={}
	totalSites=0
	for approach in timedict:
		count=0
		for site in timedict[approach]:
			found=0
			totalSites+=1
			domain=site
			if "https://" in domain:
				domain=domain.split("https://")[1]
			elif "http://" in domain:
				print (domain)
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
					dict[cdn][site][approach]=timedict[approach][site][metric]

					found=1
					break
			if found==0:
				count+=1

		print (approach,count,"sites not found in cdnDict out of ",totalSites)
	with open(dir+"resources"+metric+"byCDN.json",'w') as fp:
		json.dump(dict, fp, indent=4)	



def resourcesCDF(file,cdn,dir,feature):
	import matplotlib.pyplot as plt
	
	ttbdict=json.load(open(file))
	publicDNSResolvers=json.load(open(dir+"publicDNSServers.json"))

	graphdict={}
	_graphdict={}

	myresolvers=["SubRosa","SubRosaNP","SubRosaNPR","DoHProxyNP"]
	mainResolvers=["Google","Quad9","Cloudflare","DoHProxy","SubRosa"]
	cdns=["Google","Akamai","Fastly","Cloudflare","Amazon"]

	workingResolvers=len(publicDNSResolvers)+len(mainResolvers[:3])+len(myresolvers)
	siteCount=0
	print ("workingResolvers: ",workingResolvers)
	if cdn=="allCDNs":
		for _cdn in cdns:
			ttbByCDN=ttbdict[_cdn]
			for site in ttbByCDN:
				if len(ttbByCDN[site])<workingResolvers:
					continue
				_resolver=""
				siteCount+=1
				resolverList=[]
				
				for resolver in set(ttbByCDN[site]):
					if resolver=="SubRosa" and feature=="":
						_resolver="SubRosa"
					elif resolver=="DoHProxyNP" and feature=="":
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
					if _resolver not in _graphdict and (_resolver in mainResolvers or _resolver in publicDNSResolvers): 
						_graphdict[_resolver]={}
						_graphdict[_resolver]["ttb"]={}
					if _resolver in _graphdict and ((_resolver=="DoHProxy" and resolver=="DoHProxyNP") or (_resolver=="SubRosa" and(resolver=="SubRosa" or resolver=="SubRosaNP" or resolver=="SubRosaNPR")) or _resolver==resolver):
						_graphdict[_resolver]["ttb"][site]=ttbByCDN[site][resolver]
	else:
		ttbByCDN=ttbdict[cdn]
		for site in ttbByCDN:
			if len(ttbByCDN[site])<workingResolvers:
				continue	
			_resolver=""
			siteCount+=1
			for resolver in set(ttbByCDN[site]):
				if resolver=="SubRosa" and feature=="":
					_resolver="SubRosa"
				elif resolver=="DoHProxyNP" and feature=="":
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
				if _resolver not in _graphdict and (_resolver in mainResolvers or _resolver in publicDNSResolvers): 
					_graphdict[_resolver]={}
					_graphdict[_resolver]["ttb"]={}
				if _resolver in _graphdict and ((_resolver=="DoHProxy" and resolver=="DoHProxyNP") or (_resolver=="SubRosa" and(resolver=="SubRosa" or resolver=="SubRosaNP" or resolver=="SubRosaNPR")) or _resolver==resolver):
					_graphdict[_resolver]["ttb"][site]=ttbByCDN[site][resolver]
					# print (_resolver,resolver,ttbByCDN[site][resolver])
			# print ("done site")
			# print ("\n")

	for key in _graphdict:
		if key not in graphdict:
			graphdict[key]={}
			graphdict[key]["ttb"]=[]
			
		for site in _graphdict[key]["ttb"]: 
			graphdict[key]["ttb"].append(_graphdict[key]["ttb"][site])
		# print(key,len(graphdict[key]["ttb"]),siteCount)
		# print ("\n")
		
	# avg=[]
	# bars=[]
	# for resolver in mainResolvers:
	# 	if resolver=="DoHProxy":
	# 		continue
	# 	bars.append(resolver)
	# 	# avg.append(min(graphdict[resolver]['ttb'])/len(graphdict[resolver]['ttb']))
	# 	avg.append(sum(graphdict[resolver]['ttb'])/len(graphdict[resolver]['ttb']))
	# 	print (resolver+": ",sum(graphdict[resolver]['ttb'])/len(graphdict[resolver]['ttb']))	

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

	colorArray=[]
	for key in mcolors.CSS4_COLORS:
		colorArray.append(key)
	selectedColors=[]
	avoidColors=["green","red","white","snow","smoke"]
	clrs=['brown','blue','orange','purple','lightcoral','tan','slategrey','aquamarine'] 
	i=0
	

	for resolver in graphdict:
		if resolver in mainResolvers:
			continue
		else:		
			rcolor=clrs[i]
			plt.plot(graphdict[resolver]["sorted"],graphdict[resolver]["p"],color=rcolor,marker='.',label=resolver)
			i=i+1
			

	plt.plot(graphdict["Google"]["sorted"],graphdict["Google"]["p"],color='c',marker='.',label="GoogleDoH")
	plt.plot(graphdict["Quad9"]["sorted"],graphdict["Quad9"]["p"],color='y',marker='.',label="Quad9DoH")
	plt.plot(graphdict["Cloudflare"]["sorted"],graphdict["Cloudflare"]["p"],color='m',marker='.',label="CloudflareDoH")
	plt.plot(graphdict["DoHProxy"]["sorted"],graphdict["DoHProxy"]["p"],color='r',marker='.',label="Sharding")
	plt.plot(graphdict["SubRosa"]["sorted"],graphdict["SubRosa"]["p"],color='g',marker='.',label="SubRosa")


	plt.legend()
	plt.title("TTFB"+' of Alexa Top sites hosted on '+cdn)
	plt.xlabel('Time in ms')
	plt.ylabel('CDF')
	plt.margins(0.02)
	# plt.axis([0, None, None, None])
	if not os.path.exists(dir+"graphs"):
		os.mkdir(dir+"graphs")
	print (dir+"graphs/lighthouseTTFB"+cdn+feature)

	plt.savefig(dir+"graphs/lighthouseTTFB"+cdn+feature)
	plt.clf()

def resourcesCDFRelative(file,cdn,dir,feature):
	import matplotlib.pyplot as plt
	
	ttbdict=json.load(open(file))
	publicDNSResolvers=json.load(open(dir+"publicDNSServers.json"))

	graphdict={}
	_graphdict={}

	myresolvers=["SubRosa","SubRosaNP","SubRosaNPR","DoHProxyNP"]
	mainResolvers=["Google","Quad9","Cloudflare","DoHProxy","SubRosa"]
	cdns=["Google","Akamai","Fastly","Cloudflare","Amazon"]

	#recent runs
	workingResolvers=len(publicDNSResolvers)+len(mainResolvers[:3])+len(myresolvers)
	#US and DE
	# workingResolvers=14
	siteCount=0
	print ("workingResolvers: ",workingResolvers)
	if cdn=="allCDNs":
		for _cdn in cdns:
			ttbByCDN=ttbdict[_cdn]
			for site in ttbByCDN:
				if len(ttbByCDN[site])<workingResolvers:
					continue
				_resolver=""
				siteCount+=1
				resolverList=[]
				
				for resolver in set(ttbByCDN[site]):
					if resolver=="SubRosa" and feature=="":
						_resolver="SubRosa"
					elif resolver=="DoHProxyNP" and feature=="":
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
					if _resolver not in _graphdict and (_resolver in mainResolvers or _resolver in publicDNSResolvers): 
						_graphdict[_resolver]={}
						_graphdict[_resolver]["ttb"]={}
					if _resolver in _graphdict and ((_resolver=="DoHProxy" and resolver=="DoHProxyNP") or (_resolver=="SubRosa" and(resolver=="SubRosa" or resolver=="SubRosaNP" or resolver=="SubRosaNPR")) or _resolver==resolver):
						_graphdict[_resolver]["ttb"][site]=ttbByCDN[site][resolver]
	else:
		ttbByCDN=ttbdict[cdn]
		for site in ttbByCDN:
			if len(ttbByCDN[site])<workingResolvers:
				continue	
			_resolver=""
			siteCount+=1
			for resolver in set(ttbByCDN[site]):
				if resolver=="SubRosa" and feature=="":
					_resolver="SubRosa"
				elif resolver=="DoHProxyNP" and feature=="":
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
				if _resolver not in _graphdict and (_resolver in mainResolvers or _resolver in publicDNSResolvers): 
					_graphdict[_resolver]={}
					_graphdict[_resolver]["ttb"]={}
				if _resolver in _graphdict and ((_resolver=="DoHProxy" and resolver=="DoHProxyNP") or (_resolver=="SubRosa" and(resolver=="SubRosa" or resolver=="SubRosaNP" or resolver=="SubRosaNPR")) or _resolver==resolver):
					_graphdict[_resolver]["ttb"][site]=ttbByCDN[site][resolver]
					# print (_resolver,resolver,ttbByCDN[site][resolver])
			# print ("done site")
			# print ("\n")

	for key in _graphdict:
		if key not in graphdict:
			graphdict[key]={}
			graphdict[key]["ttb"]=[]
			
		for site in _graphdict[key]["ttb"]: 
			graphdict[key]["ttb"].append(_graphdict[key]["ttb"][site])
		# print(key,len(graphdict[key]["ttb"]),siteCount)
		# print ("\n")
		
	
	#IN
	# publicResolvers=["182.71.213.139","111.93.163.56"]
	#PK
	# publicResolvers=["58.27.149.70","202.44.80.25"]
	#AR
	# publicResolvers=["190.151.144.21","200.110.130.194"]
	#US
	publicResolvers=["208.67.222.222","208.67.220.220"]
	#DE
	# publicResolvers=["46.182.19.48","159.69.114.157"]

	# print (graphdict.keys())
	bestResolver=""
	min=0
	relativeResolvers=[]
	for resolver in graphdict:
		if resolver in mainResolvers[:3] or resolver in publicResolvers:
			if min==0 or (percentile(graphdict[resolver]["ttb"], 50))<min:
				min=percentile(graphdict[resolver]["ttb"], 50)
				bestResolver=resolver
			# print ("CDN: ",cdn,"resolver: ",resolver," 50percentile: ",percentile(graphdict[resolver]["ttb"], 50),min,bestResolver)
			relativeResolvers.append(resolver)

	print ("CDN: ",cdn,"best resolver: ",bestResolver)
	relativeResolvers.remove(bestResolver)
	print ("relativeResolvers: ",relativeResolvers)

	for resolver in graphdict:
		if resolver in relativeResolvers:
			# print (len(graphdict[resolver]["ttb"]),len(graphdict[bestResolver]["ttb"]))
			graphdict[resolver]["relative"]=[100*(graphdict[resolver]["ttb"][x]-graphdict[bestResolver]["ttb"][x])/(graphdict[bestResolver]["ttb"][x]) for x in range(len(graphdict[resolver]["ttb"]))]


	# GoogleDNSRelative=[(GoogleDNS[x]-LocalR[x]) for x in range(len(GoogleDNS))]
	# CloudflareDNSRelative=[(CloudflareDNS[x]-LocalR[x]) for x in range(len(CloudflareDNS))]
	# Quad9DNSRelative=[(Quad9DNS[x]-LocalR[x]) for x in range(len(Quad9DNS))]

	for resolver in graphdict:
		if resolver in relativeResolvers:
			q25, q75 = percentile(graphdict[resolver]["relative"], 25), percentile(graphdict[resolver]["relative"], 75)
			iqr = q75 - q25
			cut_off = iqr * 1.5
			lower, upper = q25 - cut_off, q75 + cut_off
			graphdict[resolver]["percentile"]=[x for x in graphdict[resolver]["relative"] if x >= lower and x <= upper]
			

	for resolver in graphdict:
		if resolver in relativeResolvers:
			graphdict[resolver]["sorted"]=np.sort(graphdict[resolver]["percentile"])

	for resolver in graphdict:
		if resolver in relativeResolvers:
			graphdict[resolver]["p"]=1. * np.arange(len(graphdict[resolver]["sorted"]))/(len(graphdict[resolver]["sorted"]) - 1)

	clrs=['brown','blue','orange','purple','lightcoral','tan','slategrey','aquamarine'] 
	i=0
	
	styles=['solid', 'dashed', 'dashdot', 'dotted']
	s=0
	for resolver in graphdict:
		if resolver in mainResolvers or resolver not in publicResolvers:
			continue
		if resolver in relativeResolvers:
			rcolor=clrs[i]
			if resolver==publicResolvers[0]:
				_label="Regional1"
			elif resolver==publicResolvers[1]:
				_label="Regional2"
			plt.plot(graphdict[resolver]["sorted"],graphdict[resolver]["p"],color=rcolor,label=_label,linewidth=3.0,linestyle=styles[s])
			i=i+1
			s+=1
			
	if "Google"!=bestResolver:
		plt.plot(graphdict["Google"]["sorted"],graphdict["Google"]["p"],color='c',label="GoogleDoH",linewidth=3.0,linestyle=styles[s])
		s+=1
	if "Quad9"!=bestResolver:
		plt.plot(graphdict["Quad9"]["sorted"],graphdict["Quad9"]["p"],color='y',label="Quad9DoH",linewidth=3.0,linestyle=styles[s])
		s+=1
	if "Cloudflare"!=bestResolver:
		plt.plot(graphdict["Cloudflare"]["sorted"],graphdict["Cloudflare"]["p"],color='m',label="CloudflareDoH",linewidth=3.0,linestyle=styles[s])
		s+=1
	

	plt.legend()
	plt.title("TTFB"+' of resources of Alexa Top sites hosted on '+cdn)
	if bestResolver in publicResolvers:
		plt.xlabel('Percentage difference in Time relative to '+bestResolver+"(Regional)")
	else:
		plt.xlabel('Percentage difference in Time relative to '+bestResolver)

	plt.ylabel('CDF')
	plt.margins(0.02)
	plt.grid()
	# plt.axis([0, None, None, None])
	if not os.path.exists(dir+"resolverPerformance"):
		os.mkdir(dir+"resolverPerformance")
	print (dir+"resolverPerformance/"+cdn+"_ttfb"+feature)

	plt.savefig(dir+"resolverPerformance/"+cdn+"_ttfb"+feature)
	plt.clf()
	# exit()
def resourcesCDFRelativewSubRosa(file,cdn,dir,feature):
	import matplotlib.pyplot as plt
	
	ttbdict=json.load(open(file))
	publicDNSResolvers=json.load(open(dir+"publicDNSServers.json"))

	graphdict={}
	_graphdict={}

	myresolvers=["SubRosa","SubRosaNP","SubRosaNPR","DoHProxyNP"]
	mainResolvers=["Google","Quad9","Cloudflare","SubRosa","DoHProxy"]
	cdns=["Google","Akamai","Fastly","Cloudflare","Amazon"]

	workingResolvers=len(publicDNSResolvers)+len(mainResolvers[:3])+len(myresolvers)
	
	siteCount=0
	print ("workingResolvers: ",workingResolvers)
	if cdn=="allCDNs":
		for _cdn in cdns:
			ttbByCDN=ttbdict[_cdn]
			for site in ttbByCDN:
				if len(ttbByCDN[site])<workingResolvers:
					continue
				_resolver=""
				siteCount+=1
				resolverList=[]
				
				for resolver in set(ttbByCDN[site]):
					if resolver=="SubRosa" and feature=="":
						_resolver="SubRosa"
					elif resolver=="DoHProxyNP" and feature=="":
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
					if _resolver not in _graphdict and (_resolver in mainResolvers or _resolver in publicDNSResolvers): 
						_graphdict[_resolver]={}
						_graphdict[_resolver]["ttb"]={}
					if _resolver in _graphdict and ((_resolver=="DoHProxy" and resolver=="DoHProxyNP") or (_resolver=="SubRosa" and(resolver=="SubRosa" or resolver=="SubRosaNP" or resolver=="SubRosaNPR")) or _resolver==resolver):
						_graphdict[_resolver]["ttb"][site]=ttbByCDN[site][resolver]
	else:
		ttbByCDN=ttbdict[cdn]
		for site in ttbByCDN:
			if len(ttbByCDN[site])<workingResolvers:
				continue	
			_resolver=""
			siteCount+=1
			for resolver in set(ttbByCDN[site]):
				if resolver=="SubRosa" and feature=="":
					_resolver="SubRosa"
				elif resolver=="DoHProxyNP" and feature=="":
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
				if _resolver not in _graphdict and (_resolver in mainResolvers or _resolver in publicDNSResolvers): 
					_graphdict[_resolver]={}
					_graphdict[_resolver]["ttb"]={}
				if _resolver in _graphdict and ((_resolver=="DoHProxy" and resolver=="DoHProxyNP") or (_resolver=="SubRosa" and(resolver=="SubRosa" or resolver=="SubRosaNP" or resolver=="SubRosaNPR")) or _resolver==resolver):
					_graphdict[_resolver]["ttb"][site]=ttbByCDN[site][resolver]
					

	for key in _graphdict:
		if key not in graphdict:
			graphdict[key]={}
			graphdict[key]["ttb"]=[]
			
		for site in _graphdict[key]["ttb"]: 
			graphdict[key]["ttb"].append(_graphdict[key]["ttb"][site])
		print(key,len(graphdict[key]["ttb"]),siteCount)
		print ("\n")
		
	
	#IN
	# publicResolvers=["182.71.213.139","111.93.163.56"]
	#PK
	# publicResolvers=["58.27.149.70","202.44.80.25"]
	#AR
	# publicResolvers=["190.151.144.21","200.110.130.194"]
	#US
	# publicResolvers=["208.67.222.222","208.67.220.220"]
	#DE
	publicResolvers=["46.182.19.48","159.69.114.157"]

	# print (graphdict.keys())
	bestResolver=""
	min=0
	relativeResolvers=[]
	for resolver in graphdict:
		if resolver in mainResolvers[:3] or resolver in publicResolvers:
			if min==0 or (percentile(graphdict[resolver]["ttb"], 50))<min:
				min=percentile(graphdict[resolver]["ttb"], 50)
				bestResolver=resolver
			relativeResolvers.append(resolver)

	relativeResolvers.append("SubRosa")
	# relativeResolvers.append("DoHProxy")

	print ("CDN: ",cdn,"best resolver: ",bestResolver)
	relativeResolvers.remove(bestResolver)
	print ("relativeResolvers: ",relativeResolvers)

	for resolver in graphdict:
		if resolver in relativeResolvers:
			graphdict[resolver]["relative"]=[100*(graphdict[resolver]["ttb"][x]-graphdict[bestResolver]["ttb"][x])/(graphdict[bestResolver]["ttb"][x]) for x in range(len(graphdict[resolver]["ttb"]))]

	for resolver in graphdict:
		if resolver in relativeResolvers:
			q25, q75 = percentile(graphdict[resolver]["relative"], 25), percentile(graphdict[resolver]["relative"], 75)
			iqr = q75 - q25
			cut_off = iqr * 1.5
			lower, upper = q25 - cut_off, q75 + cut_off
			graphdict[resolver]["percentile"]=[x for x in graphdict[resolver]["relative"] if x >= lower and x <= upper]
			

	for resolver in graphdict:
		if resolver in relativeResolvers:
			graphdict[resolver]["sorted"]=np.sort(graphdict[resolver]["percentile"])

	for resolver in graphdict:
		if resolver in relativeResolvers:
			graphdict[resolver]["p"]=1. * np.arange(len(graphdict[resolver]["sorted"]))/(len(graphdict[resolver]["sorted"]) - 1)

	clrs=['brown','blue','orange','purple','lightcoral','tan','slategrey','aquamarine'] 
	i=0
	

	for resolver in graphdict:
		if resolver in mainResolvers or resolver not in publicResolvers:
			continue
		if resolver in relativeResolvers:
			rcolor=clrs[i]
			plt.plot(graphdict[resolver]["sorted"],graphdict[resolver]["p"],color=rcolor,label=resolver,linewidth=4.0)
			i=i+1
			
	if "Google"!=bestResolver:
		plt.plot(graphdict["Google"]["sorted"],graphdict["Google"]["p"],color='c',label="GoogleDoH",linewidth=4.0)
	if "Quad9"!=bestResolver:
		plt.plot(graphdict["Quad9"]["sorted"],graphdict["Quad9"]["p"],color='y',label="Quad9DoH",linewidth=4.0)
	if "Cloudflare"!=bestResolver:
		plt.plot(graphdict["Cloudflare"]["sorted"],graphdict["Cloudflare"]["p"],color='m',label="CloudflareDoH",linewidth=4.0)
	if "SubRosa"!=bestResolver:
		plt.plot(graphdict["SubRosa"]["sorted"],graphdict["SubRosa"]["p"],color='g',label="Onoma",linewidth=4.0)
	# if "DoHProxy"!=bestResolver:
	# 	plt.plot(graphdict["DoHProxy"]["sorted"],graphdict["DoHProxy"]["p"],color='r',label="Sharding")
	

	plt.legend()
	plt.title("TTFB"+' of resources of Alexa Top sites hosted on '+cdn)
	plt.xlabel('Percentage difference in Time relative to '+bestResolver)
	plt.ylabel('CDF')
	plt.margins(0.02)
	plt.grid()

	if not os.path.exists(dir+"qoegraphswSubrosa"):
		os.mkdir(dir+"qoegraphswSubrosa")
	print (dir+"qoegraphswSubrosa/lighthouseTTFBOnoma"+cdn+feature)

	plt.savefig(dir+"qoegraphswSubrosa/lighthouseTTFBOnoma"+cdn+feature)
	plt.clf()

def resourcesCDFProxywSubRosa(file,cdn,dir,feature):
	import matplotlib.pyplot as plt
	
	ttbdict=json.load(open(file))
	publicDNSResolvers=json.load(open(dir+"publicDNSServers.json"))

	graphdict={}
	_graphdict={}

	myresolvers=["SubRosa","SubRosaNP","SubRosaNPR","DoHProxyNP"]
	mainResolvers=["Google","Quad9","Cloudflare","SubRosa","DoHProxy"]
	cdns=["Google","Akamai","Fastly","Cloudflare","Amazon"]

	#recent runs
	workingResolvers=len(publicDNSResolvers)+len(mainResolvers[:3])+len(myresolvers)
	
	siteCount=0
	# print ("workingResolvers: ",workingResolvers)
	if cdn=="allCDNs":
		for _cdn in cdns:
			ttbByCDN=ttbdict[_cdn]
			for site in ttbByCDN:
				if len(ttbByCDN[site])<workingResolvers:
					continue
				_resolver=""
				siteCount+=1
				resolverList=[]
				
				for resolver in set(ttbByCDN[site]):
					if resolver=="SubRosa" and feature=="":
						_resolver="SubRosa"
					elif resolver=="DoHProxyNP" and feature=="":
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
					if _resolver not in _graphdict and (_resolver in mainResolvers or _resolver in publicDNSResolvers): 
						_graphdict[_resolver]={}
						_graphdict[_resolver]["ttb"]={}
					if _resolver in _graphdict and ((_resolver=="DoHProxy" and resolver=="DoHProxyNP") or (_resolver=="SubRosa" and(resolver=="SubRosa" or resolver=="SubRosaNP" or resolver=="SubRosaNPR")) or _resolver==resolver):
						_graphdict[_resolver]["ttb"][site]=ttbByCDN[site][resolver]
	else:
		ttbByCDN=ttbdict[cdn]
		for site in ttbByCDN:
			if len(ttbByCDN[site])<workingResolvers:
				continue	
			_resolver=""
			siteCount+=1
			for resolver in set(ttbByCDN[site]):
				if resolver=="SubRosa" and feature=="":
					_resolver="SubRosa"
				elif resolver=="DoHProxyNP" and feature=="":
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
				if _resolver not in _graphdict and (_resolver in mainResolvers or _resolver in publicDNSResolvers): 
					_graphdict[_resolver]={}
					_graphdict[_resolver]["ttb"]={}
				if _resolver in _graphdict and ((_resolver=="DoHProxy" and resolver=="DoHProxyNP") or (_resolver=="SubRosa" and(resolver=="SubRosa" or resolver=="SubRosaNP" or resolver=="SubRosaNPR")) or _resolver==resolver):
					_graphdict[_resolver]["ttb"][site]=ttbByCDN[site][resolver]
					

	for key in _graphdict:
		if key not in graphdict:
			graphdict[key]={}
			graphdict[key]["ttb"]=[]
			
		for site in _graphdict[key]["ttb"]: 
			graphdict[key]["ttb"].append(_graphdict[key]["ttb"][site])
		# print(key,len(graphdict[key]["ttb"]),siteCount)
		# print ("\n")
		
	
	#IN
	# publicResolvers=["182.71.213.139","111.93.163.56"]
	#PK
	# publicResolvers=["58.27.149.70","202.44.80.25"]
	#AR
	# publicResolvers=["190.151.144.21","200.110.130.194"]
	#US
	publicResolvers=["208.67.222.222","208.67.220.220"]
	#DE
	# publicResolvers=["46.182.19.48","159.69.114.157"]

	# print (graphdict.keys())
	bestResolver=""
	min=0
	relativeResolvers=[]
	for resolver in graphdict:
		if resolver in mainResolvers[:3] or resolver in publicResolvers:
			if min==0 or (percentile(graphdict[resolver]["ttb"], 50))<min:
				min=percentile(graphdict[resolver]["ttb"], 50)
				bestResolver=resolver
			# print ("CDN: ",cdn,"resolver: ",resolver," 50percentile: ",percentile(graphdict[resolver]["ttb"], 50),min,bestResolver)
			# relativeResolvers.append(resolver)

	relativeResolvers.append("SubRosa")
	relativeResolvers.append("DoHProxy")

	# print ("CDN: ",cdn,"best resolver: ",bestResolver)
	# relativeResolvers.remove(bestResolver)
	# print ("relativeResolvers: ",relativeResolvers)

	for resolver in graphdict:
		if resolver in relativeResolvers:
			graphdict[resolver]["relative"]=[100*(graphdict[resolver]["ttb"][x]-graphdict[bestResolver]["ttb"][x])/(graphdict[bestResolver]["ttb"][x]) for x in range(len(graphdict[resolver]["ttb"]))]
			if resolver=="SubRosa":
				avgO=sum(graphdict[resolver]["ttb"])/len(graphdict[resolver]["ttb"])
			elif resolver=="DoHProxy":
				avgS=sum(graphdict[resolver]["ttb"])/len(graphdict[resolver]["ttb"])


	bestResolverAvg=sum(graphdict[bestResolver]["ttb"])/len(graphdict[bestResolver]["ttb"])
	improvementO=100*(abs(avgS-avgO))/avgO
	print (cdn,improvementO)
	improvementB=100*(abs(bestResolverAvg-avgO))/avgO

	print (cdn,bestResolver,improvementB)
	for resolver in graphdict:
		if resolver in relativeResolvers:
			# q25, q75 = percentile(graphdict[resolver]["relative"], 25), percentile(graphdict[resolver]["relative"], 75)
			q25, q75 = percentile(graphdict[resolver]["relative"], 25), percentile(graphdict[resolver]["relative"], 75)
			iqr = q75 - q25
			cut_off = iqr * 1.5
			lower, upper = q25 - cut_off, q75 + cut_off
			graphdict[resolver]["percentile"]=[x for x in graphdict[resolver]["relative"] if x >= lower and x <= upper]
			

	for resolver in graphdict:
		if resolver in relativeResolvers:
			graphdict[resolver]["sorted"]=np.sort(graphdict[resolver]["percentile"])

	for resolver in graphdict:
		if resolver in relativeResolvers:
			graphdict[resolver]["p"]=1. * np.arange(len(graphdict[resolver]["sorted"]))/(len(graphdict[resolver]["sorted"]) - 1)

	clrs=['brown','blue','orange','purple','lightcoral','tan','slategrey','aquamarine'] 
	i=0
	s=0
	styles=['solid', 'dashed', 'dashdot', 'dotted']
	for resolver in graphdict:
		if resolver in mainResolvers or resolver not in publicResolvers:
			continue
		if resolver in relativeResolvers:
			rcolor=clrs[i]
			plt.plot(graphdict[resolver]["sorted"],graphdict[resolver]["p"],color=rcolor,label=resolver,linestyle=styles[s])
			s+=1
			i=i+1
			
	# if "Google"!=bestResolver:
	# 	plt.plot(graphdict["Google"]["sorted"],graphdict["Google"]["p"],color='c',label="GoogleDoH")
	# if "Quad9"!=bestResolver:
	# 	plt.plot(graphdict["Quad9"]["sorted"],graphdict["Quad9"]["p"],color='y',label="Quad9DoH")
	# if "Cloudflare"!=bestResolver:
	# 	plt.plot(graphdict["Cloudflare"]["sorted"],graphdict["Cloudflare"]["p"],color='m',label="CloudflareDoH")
	if "SubRosa"!=bestResolver:
		plt.plot(graphdict["SubRosa"]["sorted"],graphdict["SubRosa"]["p"],color='g',label="Onoma",linewidth=4.0,linestyle=styles[s])
		s+=1
	if "DoHProxy"!=bestResolver:
		plt.plot(graphdict["DoHProxy"]["sorted"],graphdict["DoHProxy"]["p"],color='r',label="Sharding",linewidth=4.0,linestyle=styles[s])
		s+=1
	

	plt.legend()
	# plt.title("TTFB"+' of resources of Alexa Top sites hosted on '+cdn)
	plt.xlabel('Percentage difference in Time relative to '+bestResolver)
	plt.ylabel('CDF')
	plt.margins(0.02)
	plt.grid()
	# plt.axis([0, None, None, None])
	if not os.path.exists(dir+"qoegraphswSubrosa"):
		os.mkdir(dir+"qoegraphswSubrosa")
	print (dir+"qoegraphswSubrosa/SubRosavsProxy"+cdn+feature)

	plt.savefig(dir+"qoegraphswSubrosa/SubRosavsProxy"+cdn+feature)
	plt.clf()

def plotLighthouseGraphs(countrycode):

	# resourcesttb(countrycode) 
	# resourcesttbbyCDN(countrycode+"lighthouseResourcesttb.json",countrycode+"PopularcdnMapping.json","lighthouse",countrycode)
	
	resourcesCDF(countrycode+"resourcesttbbyCDNLighthouse.json","Google",countrycode,"")
	resourcesCDF(countrycode+"resourcesttbbyCDNLighthouse.json","Cloudflare",countrycode,"")
	resourcesCDF(countrycode+"resourcesttbbyCDNLighthouse.json","Amazon",countrycode,"")
	resourcesCDF(countrycode+"resourcesttbbyCDNLighthouse.json","Fastly",countrycode,"")
	resourcesCDF(countrycode+"resourcesttbbyCDNLighthouse.json","Akamai",countrycode,"")
	resourcesCDF(countrycode+"resourcesttbbyCDNLighthouse.json","allCDNs",countrycode,"")

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

def plotLighthouseGraphsRelative(countrycode):
	# resourcesCDFRelative(countrycode+"resourcesttbbyCDNLighthouse.json","Google",countrycode,"")
	# resourcesCDFRelative(countrycode+"resourcesttbbyCDNLighthouse.json","Cloudflare",countrycode,"")
	# resourcesCDFRelative(countrycode+"resourcesttbbyCDNLighthouse.json","Amazon",countrycode,"")
	resourcesCDFRelative(countrycode+"resourcesttbbyCDNLighthouse.json","Fastly",countrycode,"")
	# resourcesCDFRelative(countrycode+"resourcesttbbyCDNLighthouse.json","Akamai",countrycode,"")
	# resourcesCDFRelative(countrycode+"resourcesttbbyCDNLighthouse.json","allCDNs",countrycode,"")

def plotLighthouseGraphsRelativewSubRosa(countrycode):
	# resourcesCDFRelativewSubRosa(countrycode+"resourcesttbbyCDNLighthouse.json","Google",countrycode,"")
	# resourcesCDFRelativewSubRosa(countrycode+"resourcesttbbyCDNLighthouse.json","Cloudflare",countrycode,"")
	resourcesCDFRelativewSubRosa(countrycode+"resourcesttbbyCDNLighthouse.json","Amazon",countrycode,"")
	resourcesCDFRelativewSubRosa(countrycode+"resourcesttbbyCDNLighthouse.json","Fastly",countrycode,"")
	resourcesCDFRelativewSubRosa(countrycode+"resourcesttbbyCDNLighthouse.json","Akamai",countrycode,"")
	resourcesCDFRelativewSubRosa(countrycode+"resourcesttbbyCDNLighthouse.json","allCDNs",countrycode,"")

	# resourcesCDFRelativewSubRosa(countrycode+"resourcesttbbyCDNLighthouse.json","Google",countrycode,"PrivacyDisabled")
	# # resourcesCDFRelativewSubRosa(countrycode+"resourcesttbbyCDNLighthouse.json","Cloudflare",countrycode,"PrivacyDisabled")
	# resourcesCDFRelativewSubRosa(countrycode+"resourcesttbbyCDNLighthouse.json","Amazon",countrycode,"PrivacyDisabled")
	# resourcesCDFRelativewSubRosa(countrycode+"resourcesttbbyCDNLighthouse.json","Fastly",countrycode,"PrivacyDisabled")
	# resourcesCDFRelativewSubRosa(countrycode+"resourcesttbbyCDNLighthouse.json","Akamai",countrycode,"PrivacyDisabled")
	# resourcesCDFRelativewSubRosa(countrycode+"resourcesttbbyCDNLighthouse.json","allCDNs",countrycode,"PrivacyDisabled")

def plotLighthouseGraphsProxywSubRosa(countrycode):
	# resourcesCDFProxywSubRosa(countrycode+"resourcesttbbyCDNLighthouse.json","Google",countrycode,"")
	# resourcesCDFProxywSubRosa(countrycode+"resourcesttbbyCDNLighthouse.json","Cloudflare",countrycode,"")
	resourcesCDFProxywSubRosa(countrycode+"resourcesttbbyCDNLighthouse.json","Amazon",countrycode,"")
	resourcesCDFProxywSubRosa(countrycode+"resourcesttbbyCDNLighthouse.json","Fastly",countrycode,"")
	resourcesCDFProxywSubRosa(countrycode+"resourcesttbbyCDNLighthouse.json","Akamai",countrycode,"")
	# resourcesCDFProxywSubRosa(countrycode+"resourcesttbbyCDNLighthouse.json","allCDNs",countrycode,"")

	# resourcesCDFProxywSubRosa(countrycode+"resourcesttbbyCDNLighthouse.json","Google",countrycode,"PrivacyDisabled")
	# # resourcesCDFProxywSubRosa(countrycode+"resourcesttbbyCDNLighthouse.json","Cloudflare",countrycode,"PrivacyDisabled")
	# resourcesCDFProxywSubRosa(countrycode+"resourcesttbbyCDNLighthouse.json","Amazon",countrycode,"PrivacyDisabled")
	# resourcesCDFProxywSubRosa(countrycode+"resourcesttbbyCDNLighthouse.json","Fastly",countrycode,"PrivacyDisabled")
	# resourcesCDFProxywSubRosa(countrycode+"resourcesttbbyCDNLighthouse.json","Akamai",countrycode,"PrivacyDisabled")
	# resourcesCDFProxywSubRosa(countrycode+"resourcesttbbyCDNLighthouse.json","allCDNs",countrycode,"PrivacyDisabled")

def plotDNSLatencyGraphsRelative(countrycode):
	# DNSLatencyPlotsRelative(countrycode+"/dnsLatencies.json","DNS Resolution Time","PrivacyDisabled","min",countrycode+"/")
	DNSLatencyPlotsRelative(countrycode+"/dnsLatencies.json","DNS Resolution Time","","min",countrycode+"/")

def plotDNSLatencyGraphs(countrycode):
	DNSLatencyPlots(countrycode+"/dnsLatencies.json","DNS Resolution Time","","min",countrycode+"/")
	# # DNSLatencyPlots(countrycode+"/dnsLatencies.json","DNS Resolution Time","","max",countrycode+"/")
	DNSLatencyPlots(countrycode+"/dnsLatencies.json","Replica Ping","","min",countrycode+"/")
	# # DNSLatencyPlots(countrycode+"/dnsLatencies.json","Replica Ping","","max",countrycode+"/")

	DNSLatencyPlots(countrycode+"/dnsLatencies.json","DNS Resolution Time","PrivacyDisabled","min",countrycode+"/")
	# DNSLatencyPlots(countrycode+"/dnsLatencies.json","DNS Resolution Time","PrivacyDisabled","max",countrycode+"/")
	DNSLatencyPlots(countrycode+"/dnsLatencies.json","Replica Ping","PrivacyDisabled","min",countrycode+"/")
	# DNSLatencyPlots(countrycode+"/dnsLatencies.json","Replica Ping","PrivacyDisabled","max",countrycode+"/")

	DNSLatencyPlots(countrycode+"/dnsLatencies.json","DNS Resolution Time","Privacy+RacingDisabled","min",countrycode+"/")
	# DNSLatencyPlots(countrycode+"/dnsLatencies.json","DNS Resolution Time","Privacy+RacingDisabled","max",countrycode+"/")
	DNSLatencyPlots(countrycode+"/dnsLatencies.json","Replica Ping","Privacy+RacingDisabled","min",countrycode+"/")
	# DNSLatencyPlots(countrycode+"/dnsLatencies.json","Replica Ping","Privacy+RacingDisabled","max",countrycode+"/")

def plotTracerouteGraphs(dir):
	traceRoutePlots(dir+"tracerouteAnalysis.json","",dir)
	traceRoutePlots(dir+"tracerouteAnalysis.json","PrivacyDisabled",dir)
	traceRoutePlots(dir+"tracerouteAnalysis.json","Privacy+RacingDisabled",dir)

def resolverResolutionPerformance(dir):
	mainResolvers=["Google","Quad9","Cloudflare"]
	countryList=["PK","IN","AR","US","DE"]
	cdns=["Google","Akamai","Cloudflare","Fastly","Amazon"]

	for country in countryList:
		print (country)
		resourcesbyCDN(dir+country+"/dnsLatencies.json", dir+country+"/PopularcdnMapping.json","DNS Resolution Time",dir+country+"/")

	for resolver in mainResolvers:
		dict={}
		cdnDict={}
		for country in countryList:
			dict[country]={}
			resolutionTime=[]
			DNSREsolutionByCDN=json.load(open(dir+country+"/resourcesDNS Resolution TimebyCDN.json"))
			missingCount=0
			for cdn in DNSREsolutionByCDN:
				if cdn not in cdnDict:
					cdnDict[cdn]={}
				if country not in cdnDict[cdn]:
					cdnDict[cdn][country]={}
				cdnResolutionTime=[]
				for site in DNSREsolutionByCDN[cdn]:
					try:
						times=[]
						for time in DNSREsolutionByCDN[cdn][site][resolver]:
							times.append(int(time[:-3]))
						if min(times)==0:
							continue
						resolutionTime.append(min(times))
						cdnResolutionTime.append(min(times))
					except:
						missingCount+=1
				cdnDict[cdn][country]["DNS Resolution Time"]=cdnResolutionTime
			dict[country]["DNS Resolution Time"]=resolutionTime
			print (resolver+" missing in country: "+country,missingCount)


			qoeTime=[]
			ttbByCDN=json.load(open(dir+country+"/resourcesttbbyCDNLighthouse.json"))
			missingCount=0
			for cdn in ttbByCDN:
				if cdn not in cdnDict:
					cdnDict[cdn]={}
				if country not in cdnDict[cdn]:
					cdnDict[cdn][country]={}
				cdnqoeTime=[]
				for site in ttbByCDN[cdn]:
					try:
						qoeTime.append(ttbByCDN[cdn][site][resolver])
						cdnqoeTime.append(ttbByCDN[cdn][site][resolver])
					except:
						missingCount+=1
				cdnDict[cdn][country]["Ttfb"]=cdnqoeTime
			dict[country]["Ttfb"]=qoeTime
			print (resolver+" missing in country: "+country,missingCount)
		resolverPerformanceCDF(dict,"Ttfb",resolver,dir,"")
		resolverPerformanceCDF(dict,"DNS Resolution Time",resolver,dir,"")
		for cdn in cdns:
			resolverPerformanceCDF(cdnDict[cdn],"Ttfb",resolver,dir,cdn)
			resolverPerformanceCDF(cdnDict[cdn],"DNS Resolution Time",resolver,dir,cdn)


def resolverPerformanceCDF(graphdict,metric,resolver,dir,cdn):

	for country in graphdict:
		print (len(graphdict[country][metric]))

		q25, q75 = percentile(graphdict[country][metric], 25), percentile(graphdict[country][metric], 75)
		iqr = q75 - q25
		cut_off = iqr * 1.5
		lower, upper = q25 - cut_off, q75 + cut_off
		graphdict[country][metric+"percentile"]=[x for x in graphdict[country][metric] if x >= lower and x <= upper]

	for country in graphdict:
		graphdict[country][metric+"sorted"]=np.sort(graphdict[country][metric+"percentile"])

	for country in graphdict:
		graphdict[country][metric+"p"]=1. * np.arange(len(graphdict[country][metric+"sorted"]))/(len(graphdict[country][metric+"sorted"]) - 1)
	
	clrs=['brown','blue','orange','purple','lightcoral','tan','slategrey','aquamarine'] 
	i=0
	for country in graphdict:
		rcolor=clrs[i]
		plt.plot(graphdict[country][metric+"sorted"],graphdict[country][metric+"p"],color=rcolor,marker='.',label=country)
		i=i+1
		
	plt.legend()
	if cdn!="":
		plt.title(metric+" with "+resolver+" public DNS Resolver on "+cdn)
	else:
		plt.title(metric+" with "+resolver+" public DNS Resolver")

	plt.xlabel('time in ms')
	plt.ylabel('CDF')
	plt.margins(0.02)
	plt.axis([0, None, None, None])
	if cdn!="":
		if not os.path.exists(dir+"resolverPerformanceperCDN"):
			os.mkdir(dir+"resolverPerformanceperCDN")
		print (dir+"resolverPerformanceperCDN/"+resolver+cdn+metric)
		plt.savefig(dir+"resolverPerformanceperCDN/"+resolver+cdn+"CDN"+metric)
	else:
		if not os.path.exists(dir+"resolverPerformance"):
			os.mkdir(dir+"resolverPerformance")
		print (dir+"resolverPerformance/"+resolver+cdn+"CDN"+metric)

		plt.savefig(dir+"resolverPerformance/"+resolver+cdn+metric)
	plt.clf()

def shardingBoxPlot(file,cdn,dir,feature):
	import matplotlib.pyplot as plt
	
	ttbdict=json.load(open(file))
	publicDNSResolvers=json.load(open(dir+"publicDNSServers.json"))

	graphdict={}
	_graphdict={}

	myresolvers=["SubRosa","SubRosaNP","SubRosaNPR","DoHProxyNP"]
	mainResolvers=["Google","Quad9","Cloudflare","SubRosa","DoHProxy"]
	cdns=["Google","Akamai","Fastly","Cloudflare","Amazon"]

	workingResolvers=len(publicDNSResolvers)+len(mainResolvers[:3])+len(myresolvers)
	
	siteCount=0
	# print ("workingResolvers: ",workingResolvers)
	if cdn=="allCDNs":
		for _cdn in cdns:
			ttbByCDN=ttbdict[_cdn]
			for site in ttbByCDN:
				if len(ttbByCDN[site])<workingResolvers:
					continue
				_resolver=""
				siteCount+=1
				resolverList=[]
				
				for resolver in set(ttbByCDN[site]):
					if resolver=="SubRosa" and feature=="":
						_resolver="SubRosa"
					elif resolver=="DoHProxyNP" and feature=="":
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
					if _resolver not in _graphdict and (_resolver in mainResolvers or _resolver in publicDNSResolvers): 
						_graphdict[_resolver]={}
						_graphdict[_resolver]["ttb"]={}
					if _resolver in _graphdict and ((_resolver=="DoHProxy" and resolver=="DoHProxyNP") or (_resolver=="SubRosa" and(resolver=="SubRosa" or resolver=="SubRosaNP" or resolver=="SubRosaNPR")) or _resolver==resolver):
						_graphdict[_resolver]["ttb"][site]=ttbByCDN[site][resolver]
	else:
		ttbByCDN=ttbdict[cdn]
		for site in ttbByCDN:
			if len(ttbByCDN[site])<workingResolvers:
				continue	
			_resolver=""
			siteCount+=1
			for resolver in set(ttbByCDN[site]):
				if resolver=="SubRosa" and feature=="":
					_resolver="SubRosa"
				elif resolver=="DoHProxyNP" and feature=="":
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
				if _resolver not in _graphdict and (_resolver in mainResolvers or _resolver in publicDNSResolvers): 
					_graphdict[_resolver]={}
					_graphdict[_resolver]["ttb"]={}
				if _resolver in _graphdict and ((_resolver=="DoHProxy" and resolver=="DoHProxyNP") or (_resolver=="SubRosa" and(resolver=="SubRosa" or resolver=="SubRosaNP" or resolver=="SubRosaNPR")) or _resolver==resolver):
					_graphdict[_resolver]["ttb"][site]=ttbByCDN[site][resolver]
					

	for key in _graphdict:
		if key not in graphdict:
			graphdict[key]={}
			graphdict[key]["ttb"]=[]
			
		for site in _graphdict[key]["ttb"]: 
			graphdict[key]["ttb"].append(_graphdict[key]["ttb"][site])
		# print(key,len(graphdict[key]["ttb"]),siteCount)
		# print ("\n")
		
	
	#IN
	publicResolvers=["182.71.213.139","111.93.163.56"]
	#PK
	# publicResolvers=["58.27.149.70","202.44.80.25"]
	#AR
	# publicResolvers=["190.151.144.21","200.110.130.194"]
	#US
	# publicResolvers=["208.67.222.222","208.67.220.220"]
	#DE
	# publicResolvers=["46.182.19.48","159.69.114.157"]

	# print (graphdict.keys())
	bestResolver=""
	min=0
	relativeResolvers=[]
	for resolver in graphdict:
		if resolver in mainResolvers[:3] or resolver in publicResolvers:
			if min==0 or (percentile(graphdict[resolver]["ttb"], 50))<min:
				min=percentile(graphdict[resolver]["ttb"], 50)
				bestResolver=resolver
			relativeResolvers.append(resolver)

	relativeResolvers.append("SubRosa")
	# relativeResolvers.append("DoHProxy")

	print ("CDN: ",cdn,"best resolver: ",bestResolver)
	relativeResolvers.remove(bestResolver)
	print ("relativeResolvers: ",relativeResolvers)

	for resolver in graphdict:
		if resolver in relativeResolvers:
			graphdict[resolver]["relative"]=[100*(graphdict[resolver]["ttb"][x]-graphdict[bestResolver]["ttb"][x])/(graphdict[bestResolver]["ttb"][x]) for x in range(len(graphdict[resolver]["ttb"]))]

	for resolver in graphdict:
		if resolver in relativeResolvers:
			q25, q75 = percentile(graphdict[resolver]["relative"], 25), percentile(graphdict[resolver]["relative"], 75)
			iqr = q75 - q25
			print (dir,cdn, resolver, iqr)
			cut_off = iqr * 1.5
			lower, upper = q25 - cut_off, q75 + cut_off
			graphdict[resolver]["percentile"]=[x for x in graphdict[resolver]["relative"] if x >= lower and x <= upper]
			
	datas=[]
	r=0
	resolver_names=[]
	for resolver in graphdict:
		if resolver in relativeResolvers:
			graphdict[resolver]["sorted"]=np.sort(graphdict[resolver]["percentile"])
			# if resolver!="DoHProxy":
			if resolver!="SubRosa":
				datas.append(graphdict[resolver]["sorted"])
				if resolver not in mainResolvers:
					r+=1
					# _label=resolver[:3]+".x.x."+resolver[-1]
					if resolver==publicResolvers[0]:
						_label="Regional1"
					elif resolver==publicResolvers[1]:
						_label="Regional2"

				else:
					_label=resolver
				resolver_names.append(_label)
	resolver_names.append("Onoma")
	datas.append(graphdict["SubRosa"]["sorted"])

	# resolver_names.append("Sharding")
	# datas.append(graphdict["DoHProxy"]["sorted"])
	
	# print (datas[0])
	# exit()
	# for resolver in resolver_name
	for resolver in graphdict:
		if resolver in relativeResolvers:
			graphdict[resolver]["p"]=1. * np.arange(len(graphdict[resolver]["sorted"]))/(len(graphdict[resolver]["sorted"]) - 1)

	plt.clf()
	fig = plt.figure(1, figsize=(9, 6))

	ax = fig.add_subplot(111)

	  
	bp = ax.boxplot(datas, patch_artist=True)

	for box in bp['boxes']:
		if box==bp['boxes'][-1]:
			# box.set( color='#7570b3', linewidth=2)
			box.set( color='#7570b3', linewidth=2)
			#sharding
			# box.set( facecolor = '#ff0000')	
			#Onoma
			box.set( facecolor = '#00008b')	

		else:
			box.set( color='#7570b3', linewidth=2)
			box.set( facecolor = '#1b9e77' )

	for whisker in bp['whiskers']:
	    whisker.set(color='#7570b3', linewidth=2)

	for cap in bp['caps']:
	    cap.set(color='#7570b3', linewidth=2)

	for median in bp['medians']:
	    median.set(color='#b2df8a', linewidth=2)

	for flier in bp['fliers']:
	    flier.set(marker='o', color='#e7298a', alpha=0.5)

	ax.set_xticklabels(resolver_names)
	plt.title("TTFB"+' of resources of Alexa Top sites hosted on '+cdn)
	if bestResolver not in mainResolvers:
		plt.ylabel('Percentage difference in time relative to '+bestResolver+"(Regional)")
	else:
		plt.ylabel('Percentage difference in time relative to '+bestResolver)

	plt.savefig(dir+"qoegraphswSubrosa/_"+cdn+"_ttfb_Onoma.png")

	  
	# show plot 
	# plt.show() 
	# clrs=['brown','blue','orange','purple','lightcoral','tan','slategrey','aquamarine'] 
	# i=0
	

	# for resolver in graphdict:
	# 	if resolver in mainResolvers or resolver not in publicResolvers:
	# 		continue
	# 	if resolver in relativeResolvers:
	# 		rcolor=clrs[i]
	# 		plt.plot(graphdict[resolver]["sorted"],graphdict[resolver]["p"],color=rcolor,label=resolver)
	# 		i=i+1
			
	# if "Google"!=bestResolver:
	# 	plt.plot(graphdict["Google"]["sorted"],graphdict["Google"]["p"],color='c',label="GoogleDoH")
	# if "Quad9"!=bestResolver:
	# 	plt.plot(graphdict["Quad9"]["sorted"],graphdict["Quad9"]["p"],color='y',label="Quad9DoH")
	# if "Cloudflare"!=bestResolver:
	# 	plt.plot(graphdict["Cloudflare"]["sorted"],graphdict["Cloudflare"]["p"],color='m',label="CloudflareDoH")
	# # if "SubRosa"!=bestResolver:
	# # 	plt.plot(graphdict["SubRosa"]["sorted"],graphdict["SubRosa"]["p"],color='g',label="SubRosa")
	# if "DoHProxy"!=bestResolver:
	# 	plt.plot(graphdict["DoHProxy"]["sorted"],graphdict["DoHProxy"]["p"],color='r',label="Sharding")
	

	# plt.legend()
	# plt.title("TTFB"+' of resources of Alexa Top sites hosted on '+cdn)
	# plt.xlabel('percentage difference in Time relative to '+bestResolver)
	# plt.ylabel('CDF')
	# plt.margins(0.02)
	# if not os.path.exists(dir+"qoegraphswSubrosa"):
	# 	os.mkdir(dir+"qoegraphswSubrosa")
	# print (dir+"qoegraphswSubrosa/lighthouseTTFBSharding"+cdn+feature)

	# plt.savefig(dir+"qoegraphswSubrosa/lighthouseTTFBSharding"+cdn+feature)
	# plt.clf()
def plotLighthouseGraphsShardingBoxPlot(countrycode):
	# resourcesCDFRelativewSubRosa(countrycode+"resourcesttbbyCDNLighthouse.json","Google",countrycode,"")
	# resourcesCDFRelativewSubRosa(countrycode+"resourcesttbbyCDNLighthouse.json","Cloudflare",countrycode,"")
	shardingBoxPlot(countrycode+"resourcesttbbyCDNLighthouse.json","Amazon",countrycode,"")
	shardingBoxPlot(countrycode+"resourcesttbbyCDNLighthouse.json","Fastly",countrycode,"")
	shardingBoxPlot(countrycode+"resourcesttbbyCDNLighthouse.json","Akamai",countrycode,"")
	# resourcesCDFRelativewSubRosa(countrycode+"resourcesttbbyCDNLighthouse.json","allCDNs",countrycode,"")

def KendallDistance(values1,values2,distances):
	import numpy as np
	n = len(values1)
	assert len(values2) == n, "Both lists have to be of equal length"
	i, j = np.meshgrid(np.arange(n), np.arange(n))
	a = np.argsort(values1)
	b = np.argsort(values2)
	ndisordered = np.logical_or(np.logical_and(a[i] < a[j], b[i] > b[j]), np.logical_and(a[i] > a[j], b[i] < b[j])).sum()
	distances.append(ndisordered / (n * (n - 1)))
	# return ndisordered / (n * (n - 1))

def calKendallResolutionTimes():
	#Kendall Distance for Resolution Times
	US=["Q","l1","l2","C","G"]
	IN=["C","G","Q","l1","l2"]
	AR=["l1","C","Q","G","l2"]
	DE=["Q","l1","C","G","l2"]


	import itertools
	data=[US,IN,AR,DE]
	
	distances=[]
	KendallDistance(US,IN,distances)
	KendallDistance(US,AR,distances)
	KendallDistance(US,DE,distances)
	KendallDistance(IN,AR,distances)
	KendallDistance(IN,DE,distances)
	KendallDistance(AR,DE,distances)
	print (distances)
	avg=sum(distances)/len(distances)
	_max=max(distances)
	print(_max,avg)

def calKendallTTFB():
	#Kendall Distance for TTFB AKAMAI
	# US=["C","l2","l1","Q","G"]
	# IN=["l2","l1","C","Q","G"]
	# AR=["l1","C","Q","G","l2"]
	# DE=["C","l2","l1","Q","G"]

	#Kendall Distance for TTFB AMAZON
	# US=["l1","Q","C","l2","G"]
	# IN=["l2","l1","Q","C","G"]
	# AR=["G","l1","Q","l2","C"]
	# DE=["C","Q","l1","G","l2"]

	# #Kendall Distance for TTFB Fastly
	US=["l1","C","l2","Q","G"]
	IN=["l2","l1","Q","G","C"]
	AR=["Q","l1","G","C","l2"]
	DE=["l1","l2","Q","G","C"]

	
	import itertools
	data=[US,IN,AR,DE]
	
	distances=[]
	KendallDistance(US,IN,distances)
	KendallDistance(US,AR,distances)
	KendallDistance(US,DE,distances)
	KendallDistance(IN,AR,distances)
	KendallDistance(IN,DE,distances)
	KendallDistance(AR,DE,distances)
	print (distances)
	avg=sum(distances)/len(distances)
	_max=max(distances)
	print(_max,avg)

def bumpchart(df, show_rank_axis= True, rank_axis_distance= 1.1, 
              ax= None, scatter= False, holes= False,
              line_args= {}, scatter_args= {}, hole_args= {}):
    
    if ax is None:
        left_yaxis= plt.gca()
    else:
        left_yaxis = ax

    # Creating the right axis.
    right_yaxis = left_yaxis.twinx()
    
    axes = [left_yaxis, right_yaxis]
    
    # Creating the far right axis if show_rank_axis is True
    if show_rank_axis:
        far_right_yaxis = left_yaxis.twinx()
        axes.append(far_right_yaxis)
    
    for col in df.columns:
        y = df[col]
        x = df.index.values
        # Plotting blank points on the right axis/axes 
        # so that they line up with the left axis.
        for axis in axes[1:]:
            axis.plot(x, y, alpha= 0)

        left_yaxis.plot(x, y, **line_args, solid_capstyle='round')
        
        # Adding scatter plots
        if scatter:
            left_yaxis.scatter(x, y, **scatter_args)
            
            #Adding see-through holes
            if holes:
                bg_color = left_yaxis.get_facecolor()
                left_yaxis.scatter(x, y, color= bg_color, **hole_args)

    # Number of lines
    lines = len(df.columns)

    y_ticks = [*range(1, lines + 1)]
    
    # Configuring the axes so that they line up well.
    for axis in axes:
        axis.invert_yaxis()
        axis.set_yticks(y_ticks)
        axis.set_ylim((lines + 0.5, 0.5))
    
    # Sorting the labels to match the ranks.
    left_labels = df.iloc[0].sort_values().index
    right_labels = df.iloc[-1].sort_values().index
    
    left_yaxis.set_yticklabels(left_labels)
    right_yaxis.set_yticklabels(right_labels)
    
    # Setting the position of the far right axis so that it doesn't overlap with the right axis
    if show_rank_axis:
        far_right_yaxis.spines["right"].set_position(("axes", rank_axis_distance))
    
    return axes

def	plotDNSRankingBumpChart():
	
	#DNS Resolution Times
	data = {"Quad9":[1,3,3,1],"Regional_2":[2,4,5,2],"Regional_1":[3,5,1,5],"Cloudflare":[4,1,2,3],"Google":[5,2,4,4]}

	df = pd.DataFrame(data, index=['US','IN','AR','DE'])
	plt.figure(figsize=(12, 5))
	bumpchart(df, show_rank_axis= True, scatter= True, holes= False,
	          line_args= {"linewidth": 5, "alpha": 0.5}, scatter_args= {"s": 100, "alpha": 0.8}) ## bump chart class with nice examples can be found on github
	plt.savefig("DNSResolutionTimesRanking")

	#Akamai
	data = {"Quad9":[4,4,3,4],"Regional_2":[2,1,5,2],"Regional_1":[3,2,1,3],"Cloudflare":[1,3,2,1],"Google":[5,5,4,5]}

	df = pd.DataFrame(data, index=['US','IN','AR','DE'])
	plt.figure(figsize=(12, 5))
	bumpchart(df, show_rank_axis= True, scatter= True, holes= False,
	          line_args= {"linewidth": 5, "alpha": 0.5}, scatter_args= {"s": 100, "alpha": 0.8}) ## bump chart class with nice examples can be found on github
	plt.savefig("DNSRankingTTFBAkamai")

	#Amazon
	data = {"Quad9":[2,3,3,2],"Regional_2":[4,1,4,5],"Regional_1":[1,2,2,3],"Cloudflare":[3,4,5,1],"Google":[5,5,1,4]}

	df = pd.DataFrame(data, index=['US','IN','AR','DE'])
	plt.figure(figsize=(12, 5))
	bumpchart(df, show_rank_axis= True, scatter= True, holes= False,
	          line_args= {"linewidth": 5, "alpha": 0.5}, scatter_args= {"s": 100, "alpha": 0.8}) ## bump chart class with nice examples can be found on github
	plt.savefig("DNSRankingTTFBAmazon")

	#Fastly
	data = {"Quad9":[4,3,1,3],"Regional_2":[3,1,5,2],"Regional_1":[1,2,2,1],"Cloudflare":[2,5,4,5],"Google":[5,4,3,4]}

	df = pd.DataFrame(data, index=['US','IN','AR','DE'])
	plt.figure(figsize=(12, 5))
	bumpchart(df, show_rank_axis= True, scatter= True, holes= False,
	          line_args= {"linewidth": 5, "alpha": 0.5}, scatter_args= {"s": 100, "alpha": 0.8}) ## bump chart class with nice examples can be found on github
	plt.savefig("DNSRankingTTFBFastly")


def main():
	countryPath="measurements/US"
	# plotLighthouseGraphs(countryPath+"/")
	# plotDNSLatencyGraphs(countryPath)
	# PingPlots("pingServers.json",countryPath+"/")
	# tracerouteAnalysis(countryPath+"/")
	# plotTracerouteGraphs(countryPath+"/")

	# resolverResolutionPerformance("measurements/")
	# plotLighthouseGraphsRelative(countryPath+"/")
	# plotDNSLatencyGraphsRelative(countryPath)

	plotDNSDistribution(countryPath+"/")

	#sharding or Onoma relative to the rest of resolvers
	# plotLighthouseGraphsRelativewSubRosa(countryPath+"/")

	#sharding or Onoma relative to the rest of resolvers (boxplot)
	# plotLighthouseGraphsShardingBoxPlot(countryPath+"/")
	# print (countryPath)
	# plotLighthouseGraphsProxywSubRosa(countryPath+"/")

	# CDNDistribution()

	# calKendallResolutionTimes()
	# calKendallTTFB()

	# plotDNSRankingBumpChart()



main()

# KendallDistanceResolution Times
# 0.6 0.3666666666666667
# KendallDistanceTTFB:
# Akamai: 0.4 0.26666666666666666
# Amazon: 0.7 0.5333333333333333
#Fastly: 0.5 0.3666666666666667




