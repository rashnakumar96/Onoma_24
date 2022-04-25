import json
import random
from pandas import *
from pathlib import Path
from collections import Counter
import matplotlib.pyplot as plt
import numpy as np
import tldextract
import collections
import os
import sys
import re
import memory_profiler


def shardingAlgo(browsingHist,bitVectorLength,popularSitesPerUserDict,urlIndexPerUser):
	shardingParameters=[1,2,4,8]
	_resolvers=[x for x in range(8)]

	for value in shardingParameters:
		userResolverMap={} #stores bitvector per resolver per user
		domainResolverMap={} #for domain sharding
		resolvers=_resolvers[:value] #select the number of resolvers to shard to
		for user in browsingHist:
			if len(browsingHist[user])<75:
				continue
			for url in browsingHist[user]:
				if url not in popularSitesPerUserDict[user]:
					continue
				domain=tldextract.extract(url).domain
				if domain in domainResolverMap:
					resolverIndex=domainResolverMap[domain]
				else:
					resolverIndex=random.randint(0,value-1) #shard to a random resolver
					domainResolverMap[domain]=resolverIndex
				resolver="resolver_"+str(resolvers[resolverIndex])
				if resolver not in userResolverMap:
					userResolverMap[resolver]={}
				_user="user_"+str(user)
				if _user not in userResolverMap[resolver]:
					userResolverMap[resolver][_user]=[0 for x in range(bitVectorLength)]

				bitVector=userResolverMap[resolver][_user]

				ind=urlIndexPerUser[user][url] #gives index where url should be stored in the bit vector
				bitVector[ind]=1
				userResolverMap[resolver][_user]=bitVector
		if not os.path.exists("k-anonResults"):
			os.mkdir("k-anonResults")
		with open("k-anonResults/sharding_value"+str(value)+".json", 'w') as fp:
			json.dump(userResolverMap, fp)
				

def preprocessBrowsingLog(log):
	#log has seq of urls against each userId
	browsingHists={} #stores the freq of occurrence urls per user
	urlFreq={} #stores the freq of occurrence urls across all users (will help in creating bit vector ranking)
	for userId in log:
		if userId not in browsingHists:
			browsingHists[userId]={}
		for url in log[userId]:
			if url not in urlFreq:
				urlFreq[url]=0
			urlFreq[url]+=1
			if url not in browsingHists[userId]:
				browsingHists[userId][url]=0
			browsingHists[userId][url]+=1

	sorted_urlFreq= dict(Counter(urlFreq).most_common(len(urlFreq))) #sorts urlFreq dict by frequency of urls

	urlUnion=[] #stores the union of top50 sites of each user
	popularSitesPerUserDict={} #stores top50 sites of each user
	for userId in browsingHists:
		popularSitesPerUser=dict(Counter(browsingHists[userId]).most_common(25)).keys()
		popularSitesPerUserDict[userId]=popularSitesPerUser
		for site in popularSitesPerUser:
			if site not in urlUnion:
				urlUnion.append(site)
	index=0
	topUrlIndex={} #this stores the index of url's position in bit vector
	for url in sorted_urlFreq:
		if url in urlUnion:
			topUrlIndex[url]=index
			index+=1

	del urlUnion
	del sorted_urlFreq

	urlIndexPerUser={} #this stores the index of the url's position in bit vector per user
	for userId in browsingHists:
		if userId not in urlIndexPerUser:
			urlIndexPerUser[userId]={}
		for site in popularSitesPerUserDict[userId]:
			urlIndexPerUser[userId][site]=topUrlIndex[site]

	bitVectorLength=index

	del topUrlIndex
	del browsingHists
	del urlFreq

	shardingAlgo(log,bitVectorLength,popularSitesPerUserDict,urlIndexPerUser)

def takeInput():
	inputLog={}
	hashedLog={}
	# filename=sys.argv[1]
	m1 = memory_profiler.memory_usage()
	with open("clientRequestsLog.txt",'r') as f:
		for line in f:
			line=str(line)
			if "query:" in line:
				query=line.split("query: ")[1].split(" IN")[0]
				userIdString=line.split("#")[0].split("client")[1]
				userId=re.findall(r'(?:\d{1,3}\.)+(?:\d{1,3})',userIdString)[0]
				if userId not in inputLog:
					inputLog[userId]=[]
				inputLog[userId].append(query)
				key=str(hash(userId))
				if key not in hashedLog:
					hashedLog[key]=[]
				hashedLog[key].append(query)
	if not os.path.exists("k-anonResults"):
		os.mkdir("k-anonResults")			
	with open("k-anonResults/resFile.json", 'w') as fp:
		json.dump(hashedLog, fp)
	del hashedLog
	m2 = memory_profiler.memory_usage()

	mem_diff = m2[0] - m1[0]
	print(f"It took {mem_diff} Mb to execute this method")

	m1 = memory_profiler.memory_usage()
	preprocessBrowsingLog(inputLog)
	m2 = memory_profiler.memory_usage()
	mem_diff = m2[0] - m1[0]
	print(f"It took {mem_diff} Mb to execute this method")

if __name__ == "__main__":
	takeInput()
	

	












