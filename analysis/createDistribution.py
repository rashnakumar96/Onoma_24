import numpy.random as rnd
import random
import numpy as np
import json
import time, sys
import pybloomfilter
import tldextract
import os
import matplotlib as mpl
mpl.use("agg")
import matplotlib.pyplot as plt
from numpy.random import choice
from collections import Counter



def createDistribution(topSites,weights,sampling_size):
	sampleList = topSites
	randomList = random.choices(sampleList, weights=tuple(weights), k=sampling_size)
	return randomList

def parseTopAlexaSites(siteCount):
	topSites=[]
	index=0
	with open("topmillionsites.txt",'r') as f:
		for line in f:
			if index==siteCount:
				break
			site=line.split(",")[1]
			topSites.append(site[:-1])
			index+=1
	return topSites

def weightGeneration(siteCount):
	a=2
	s = np.random.zipf(a,siteCount)
	result = (s/float(max(s)))
	weights=result
	weights[::-1].sort()
	return weights

def createUserProfiles():
	
	siteCount=10000
	topSites=parseTopAlexaSites(siteCount)
	weights=weightGeneration(siteCount)
	sampling_size=1000
	users=200
	allSites=[]
	userLog={}
	for x in range(users):
		sample=createDistribution(topSites,weights,sampling_size)
		userLog["user_"+str(x)]=sample
	with open("k-anonResults/userLog.json", 'w') as fp:
		json.dump(userLog, fp)

def injectRequests(userLog,k):
	overheadPerUser={}
	siteCount=500
	topSites=parseTopAlexaSites(siteCount)
	bloom_filter = pybloomfilter.BloomFilter(capacity=len(topSites), error_rate=0.0001)
	for topSite in topSites:
		bloom_filter.add(topSite)
	
	siteCount=100
	topSites=parseTopAlexaSites(siteCount)
	weights=weightGeneration(siteCount)

	for user in userLog:
		count=0
		for site in userLog[user]:
			if site not in bloom_filter:
				count+=1
		# print (count)
		#(k is the insertion factor)
		sampling_size=count*k
		sample=createDistribution(topSites,weights,sampling_size)

		injectedReqs=sample
		for req in injectedReqs:
		   userLog[user].insert(random.randrange(0, len(userLog[user])-1),req)
		overheadPerUser[user]=100*(sampling_size/len(userLog[user]))

	print (overheadPerUser)
	return userLog

def preprocessBrowsingLog(userLog,injected,run):
	browsingHists={} #stores the freq of occurrence urls per user
	urlFreq={} #stores the freq of occurrence urls across all users (will help in creating bit vector ranking)
	for userId in userLog:
		if userId not in browsingHists:
			browsingHists[userId]={}
		for url in userLog[userId]:
			if url not in browsingHists[userId]:
				browsingHists[userId][url]=0
			browsingHists[userId][url]+=1


	urlUnion=[] #stores the union of top50 sites of each user
	popularSitesPerUserDict={} #stores top50 sites of each user
	for userId in browsingHists:
		popularSitesPerUser=dict(Counter(browsingHists[userId]).most_common(50)).keys()
		popularSitesPerUserDict[userId]=popularSitesPerUser
		for site in popularSitesPerUser:
			if site not in urlUnion:
				urlUnion.append(site)

	index=0
	topUrlIndex={} #this stores the index of url's position in bit vector
	for url in urlUnion:
		topUrlIndex[url]=index
		index+=1

	urlIndexPerUser={} #this stores the index of the url's position in bit vector per user
	for userId in browsingHists:
		if userId not in urlIndexPerUser:
			urlIndexPerUser[userId]={}
		for site in popularSitesPerUserDict[userId]:
			urlIndexPerUser[userId][site]=topUrlIndex[site]

	bitVectorLength=len(urlUnion)

	shardingAlgo(bitVectorLength,popularSitesPerUserDict,urlIndexPerUser,injected,run)


def shardingAlgo(bitVectorLength,browsingHist,urlIndexPerUser,injected,run):

	shardingParameters=[1,2,4,8]
	_resolvers=[x for x in range(8)]

	for value in shardingParameters:
		print ("running for sharding value: ",str(value))
		userResolverMap={} #stores bitvector per resolver per user
		domainResolverMap={} #for domain sharding
		resolvers=_resolvers[:value] #select the number of resolvers to shard to
		for user in browsingHist:
			for url in browsingHist[user]:
				domain=tldextract.extract(url).domain
				if domain in domainResolverMap:
					resolverIndex=domainResolverMap[domain]
				else:
					resolverIndex=random.randint(0,value-1) #shard to a random resolver
					domainResolverMap[domain]=resolverIndex
				resolver="resolver_"+str(resolvers[resolverIndex])
				if resolver not in userResolverMap:
					userResolverMap[resolver]={}
				_user=user
				if _user not in userResolverMap[resolver]:
					userResolverMap[resolver][_user]=[0 for x in range(bitVectorLength)]

				# if url in popularSitesPerUserDict[user]:
				bitVector=userResolverMap[resolver][_user]
				ind=urlIndexPerUser[user][url] #gives index where url should be stored in the bit vector
				bitVector[ind]=1
				userResolverMap[resolver][_user]=bitVector
				# del bitVector

		if not os.path.exists("k-anonResults/InjectedReqs"):
			os.mkdir("k-anonResults/InjectedReqs")
		if injected:
			with open("k-anonResults/InjectedReqs/Injectedsharding_value"+str(value)+"run_"+str(run)+".json", 'w') as fp:
			# with open("k-anonResults/InjectedReqs/Injectedsharding_value"+str(value)+".json", 'w') as fp:
				json.dump(userResolverMap, fp)
		else:
			with open("k-anonResults/sharding_value"+str(value)+".json", 'w') as fp:
				json.dump(userResolverMap, fp)

def plotFreqDistr(sample,K):
	# urlFreq={}
	# for url in sample:
	# 	if url not in urlFreq:
	# 		urlFreq[url]=0
	# 	urlFreq[url]+=1

	# weights=weightGeneration(100000)
	# sortedData=np.sort(list(urlFreq.values()))
	# print (sortedData)
	# pData=1. * np.arange(len(sortedData))/(len(sortedData)-1)
	# plt.plot(sortedData,pData,color='c')
	overhead=[]
	for user in sample:
		overhead.append(100*((len(userLog[user])-1000)/len(userLog[user])))
	overhead.sort()
	indexes=[x for x in range(200)]
	plt.plot(indexes,overhead,color='b',linewidth=2)
	plt.xlabel("Users")
	plt.ylabel("Percentage overhead from Privacy")
	if not os.path.exists("k-anonResults/InjectedReqs/graphs"):
		os.mkdir("k-anonResults/InjectedReqs/graphs")
	plt.savefig("k-anonResults/InjectedReqs/graphs/Privacy_Overhead"+str(K))
	plt.clf()
		
if __name__ == "__main__":
	sample=createUserProfiles() #creates userProfile of 200 users
	userLog=json.load(open("k-anonResults/userLog.json"))
	runs=5
	#(k is the insertion factor)
	K=60 
	for x in range(runs):
		userLogInjected=injectRequests(userLog,K)
		plotFreqDistr(userLogInjected,K)
		preprocessBrowsingLog(userLogInjected,True,x)

	# createDistribution(topSites,weights,sampling_size)
	# plotFreqDistr(sample)

