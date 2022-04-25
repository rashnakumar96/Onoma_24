import json
import numpy as np
from itertools import combinations
import matplotlib as mpl
mpl.use("agg")
import matplotlib.pyplot as plt
import os
import statistics
from collections import Counter
from urllib.parse import urlparse



def jaccard_binary(x,y):
    """A function for finding the similarity between two binary vectors"""
    intersection = np.logical_and(x, y)
    union = np.logical_or(x, y)
    similarity = intersection.sum() / float(union.sum())
    return similarity

def calcKanon(Injected):
	shardingParameters=[1,2,4,8]
	for z in shardingParameters:
		dict={}
		for run in range(5):
			dict[run]={}
			if Injected:
				resFile=json.load(open("k-anonResults/InjectedReqs/Injectedsharding_value"+str(z)+"run_"+str(run)+".json"))
			else:
				resFile=json.load(open("k-anonResults/sharding_value"+str(z)+".json"))
			for resolver in resFile:
				if resolver not in dict[run]:
					dict[run][resolver]={}
				uniqueUsers=[]
				totalResolutions=0
				for user in resFile[resolver]:
					for bit in resFile[resolver][user]:
						if bit==1:
							totalResolutions+=1
					if user not in uniqueUsers:
						uniqueUsers.append(user)
				print ("sharding_value"+str(z)," resolver: ",resolver," len of uniqueUsers: ",len(uniqueUsers))
				clusterGroup=0
				clusterDict={}
				marked=[]
				k1=0
				for x in range(len(uniqueUsers)):
					if uniqueUsers[x] in marked:
						continue
					if clusterGroup not in clusterDict:
						clusterDict[clusterGroup]=[]
					clusterDict[clusterGroup].append(uniqueUsers[x])
					
					if x+1==len(uniqueUsers):
						continue
					for y in range(x+1,len(uniqueUsers)):
						if uniqueUsers[y] in marked:
							continue
						try:
							arr1=resFile[resolver][uniqueUsers[x]]
							arr2=resFile[resolver][uniqueUsers[y]]
						except:
							print (" bit op: ",x,y,len(uniqueUsers))
							continue
						matched=True
						for n in range(len(arr1)):
							if arr1[n]^arr2[n]==1:
								matched=False
								break
						if matched:
							clusterDict[clusterGroup].append(uniqueUsers[y])
							marked.append(uniqueUsers[y])
							
					dict[run][resolver]["clusterGroup"+str(clusterGroup)]=len(clusterDict[clusterGroup])
					if len(clusterDict[clusterGroup])==1:
						k1+=1
					
					clusterGroup+=1
			# print (resolver," number of clusters: ",len(clusterDict)," total resolutions: ",totalResolutions," k1: ",k1)
		if Injected:
			with open("k-anonResults/InjectedReqs/Injectedsharding_value"+str(z)+"Result.json", 'w') as fp:
				json.dump(dict, fp)
		else:
			with open("k-anonResults/sharding_value"+str(z)+"Result.json", 'w') as fp:
				json.dump(dict, fp)

def plotK_Values(Injected):
	shardingParameters=[8,4,2,1]
	colors=['c','y','g','m','b','r','orange','purple']
	ind=0
	_max=0
	avgKdict={}
	dataFile=json.load(open("k-anonResults/InjectedReqs/Injectedsharding_value8"+".json"))

	for z in shardingParameters:
		avgKdict["sharding_value"+str(z)]={}
		if Injected:
			resFile=json.load(open("k-anonResults/InjectedReqs/Injectedsharding_value"+str(z)+"Result.json"))
		else:
			resFile=json.load(open("k-anonResults/sharding_value"+str(z)+"Result.json"))
		r=0
		c=0
		avgDict={}
		for run in resFile:
			k_values=[]
			dict={}
			for resolver in resFile[run]:
				k_values+=list(resFile[run][resolver].values())
				
			for value in k_values:
				if value not in dict:
					dict[value]=0
				dict[value]+=1
			for key in dict:
				if key not in avgDict:
					avgDict[key]=[]
				avgDict[key].append(dict[key])
				# totalResolutions=0
				# for user in dataFile[resolver]:
				# 	for bit in dataFile[resolver][user]:
				# 		if bit==1:
				# 			totalResolutions+=1
		avgk_values=[]
		for key in avgDict:
			avg=sum(avgDict[key])/len(avgDict[key])
			avgk_values.extend([key for i in range(int(avg))])
		sortedData=np.sort(avgk_values)
			# sortedData=np.sort(list(resFile[resolver].values()))
		
		pData=1. * np.arange(len(sortedData))/(len(sortedData)-1)
		# print (sortedData)

		if z==1:
			plt.plot(sortedData,pData,color=colors[ind],label="no sharding")
		else:	
			plt.plot(sortedData,pData,color=colors[ind],label="sharding_value"+str(z))
			# plt.plot(sortedData,pData,color=colors[c],label=str(resolver)+";resolutions made: "+str(totalResolutions))

			c+=1
		ind+=1
	plt.legend()
	plt.xlabel("K-Value")
	plt.ylabel("CDF")
	plt.margins(0.02)
	k=60 #Insertion Factor
	plt.title("With Insertion Factor"+str(k))
	if not os.path.exists("k-anonResults/InjectedReqs/graphs"):
		os.mkdir("k-anonResults/InjectedReqs/graphs")
	if Injected:
		plt.savefig("k-anonResults/InjectedReqs/graphs/InjectedK_valuesCDF_"+str(k))
	else:
		plt.savefig("k-anonResults/graphs/K_valuesCDF")
	plt.clf()
	print (avgKdict)

def plotuserHistDistr():
	_dict={}
	resFile=json.load(open("k-anonResults/NUITFullLog.json"))
	_dict={}
	for user in resFile:
		# urls=[]
		# for url in resFile[user]:
		# 	if url not in urls:
		# 		urls.append(url)
		_dict[user]=len(resFile[user])
			# urlFreq[url]+=1
	popularusers=dict(Counter(_dict).most_common(200))
	# print (popularusers.keys())
	print (len(popularusers.keys()))

	usersLog={}
	for user in popularusers:
		usersLog[user]=resFile[user]
	# 	bitC=0	
	# 	for bit in resFile[resolver][user]:
	# 		if bit==1:
	# 			bitC+=1
	# 	_dict[user]=bitC
	with open("k-anonResults/NUITResults/200UsersDistr.json", 'w') as fp:
			# with open("k-anonResults/InjectedReqs/Injectedsharding_value"+str(value)+".json", 'w') as fp:
		json.dump(usersLog, fp)
if __name__ == "__main__":

# calcKanon(False)
# plotK_Values(False)

	calcKanon(True)
	plotK_Values(True)
	# plotuserHistDistr()

