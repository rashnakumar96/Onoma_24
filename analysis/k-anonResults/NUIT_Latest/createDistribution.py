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
	with open("distributionUserLog.json", 'w') as fp:
		json.dump(userLog, fp)

def injectRequests(userLog,k,x,filename,users):
	overheadPerUser={}
	siteCount=500
	topSites=parseTopAlexaSites(siteCount)
	bloom_filter = pybloomfilter.BloomFilter(capacity=len(topSites), error_rate=0.0001)
	for topSite in topSites:
		domain=tldextract.extract(topSite).domain #uncomment for NUIT
		# print ("alexa: ",domain)
		bloom_filter.add(domain.encode()) #uncomment for NUIT
		# bloom_filter.add(topSite.encode())
	
	siteCount=50
	topSites=parseTopAlexaSites(siteCount)
	weights=weightGeneration(siteCount)
	print ("Length of userLog is: ",len(userLog))
	userCount=0
	for user in userLog:
		if userCount%100==0:
			print ("Done for user Count: ",userCount)
		userCount+=1
		count=0
		if len(set(userLog[user]))<50:
			continue
		# for site in userLog[user][:10000]:
		for site in userLog[user]:
			site=tldextract.extract(site).domain #uncomment for NUIT
			# print ("NUIT: ",site)
			if site.encode() not in bloom_filter:
				count+=1
				# print (site.encode())
			# else:
				# print (site.encode())
					
		# print (count)
		#(k is the insertion factor)
		sampling_size=k*count
		# print ("count: ",count,len(userLog[user]))
		sample=createDistribution(topSites,weights,sampling_size)

		# userLog[user]=userLog[user][:10000] #what about this replacement thing look into this
		# userLog[user]=userLog[user] #what about this replacement thing look into this
		initialBytes=0
		for req in userLog[user]:
			initialBytes+=len(req.encode('utf-16-le'))

		injectedReqs=sample
		injectedReqsBytes=0
		for req in injectedReqs:
			injectedReqsBytes+=len(req.encode('utf-16-le'))
			userLog[user].insert(random.randrange(0, len(userLog[user])-1),req)
		# injectedReqsBytes=sys.getsizeof(injectedReqs)
				# userLog[user].append(req)
		# overheadPerUser[user]=100*(sampling_size/len(userLog[user]))
		totalBytes=sys.getsizeof(userLog[user])
		overheadPerUser[user]=100*(injectedReqsBytes/(injectedReqsBytes+initialBytes))
		# print ("overhead: ",sampling_size,len(userLog[user]),100*(sampling_size/len(userLog[user])))
	if not os.path.exists("InjectedReqsTemp"):
		os.mkdir("InjectedReqsTemp")

	# with open("InjectedReqsTemp/overhead_"+filename+str(k)+"_"+str(x)+"_users_"+str(users)+".json", 'w') as fp:
	# 	json.dump(overheadPerUser, fp)
	# print (overheadPerUser)
	return userLog

def preprocessBrowsingLog(userLog,injected,run,K,filename,users):
	browsingHists={} #stores the freq of occurrence urls per user
	urlFreq={} #stores the freq of occurrence urls across all users (will help in creating bit vector ranking)
	userCount=0 #no of users we want to process
	for userId in userLog:
		if userCount>users:
			break
		if len(set(userLog[userId]))<50:
			continue
		userCount+=1
		if userId not in browsingHists:
			browsingHists[userId]={}
		for url in userLog[userId]:
			if url not in browsingHists[userId]:
				browsingHists[userId][url]=0
			browsingHists[userId][url]+=1
	print ("Number of users: ",len(browsingHists))
	urlUnion=[] #stores the union of top50 sites of each user
	popularSitesPerUserDict={} #stores top50 sites of each user
	for userId in browsingHists:
		popularSitesPerUser=dict(Counter(browsingHists[userId]).most_common(100)).keys()
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
	# print (urlUnion)
	shardingAlgo(bitVectorLength,popularSitesPerUserDict,urlIndexPerUser,injected,run,K,filename,users)


def shardingAlgo(bitVectorLength,browsingHist,urlIndexPerUser,injected,run,K,filename,users):

	shardingParameters=[1,2,4,8] #should be 1,2,4,8
	# shardingParameters=[1] #should be 1,2,4,8
	_resolvers=[x for x in range(8)]
	for value in shardingParameters:
		print ("running for sharding value: ",str(value))
		count=0
		userResolverMap={} #stores bitvector per resolver per user
		domainResolverMap={} #for domain sharding
		resolvers=_resolvers[:value] #select the number of resolvers to shard to
		for user in browsingHist:
			if count%100==0:
				print ("Done for user Count: ",count)
			count+=1
			for url in browsingHist[user]:
				# domain=url
				domain=tldextract.extract(url).domain #uncomment for create distribution example
				# print (domain,url)
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
				del bitVector
		print ("Done for sharding value: ",str(value))

		if not os.path.exists("InjectedReqsTemp"):
			os.mkdir("InjectedReqsTemp")
		if injected:
			with open("InjectedReqsTemp/Injectedsharding_value"+filename+'_'+str(value)+"run_"+str(run)+'_'+str(K)+"_users_"+str(users)+".json", 'w') as fp:
			# with open("k-anonResults/InjectedReqs/Injectedsharding_value"+str(value)+".json", 'w') as fp:
				json.dump(userResolverMap, fp)
		else:
			with open("InjectedReqsTemp/sharding_value"+filename+str(value)+"_users_"+str(users)+".json", 'w') as fp:
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
		overhead.append(100*((len(userLog[user])-10000)/len(userLog[user])))
	overhead.sort()
	indexes=[x for x in range(200)]
	plt.plot(indexes,overhead,color='b',linewidth=2)
	plt.xlabel("Users")
	plt.ylabel("Percentage overhead from Privacy")
	if not os.path.exists("InjectedReqsTemp/graphs"):
		os.mkdir("InjectedReqsTemp/graphs")
	plt.savefig("InjectedReqsTemp/graphs/Privacy_Overhead"+str(K))
	plt.clf()
		
if __name__ == "__main__":
	# sample=createUserProfiles() #creates userProfile of 200 users
	# userLog=json.load(open("distributionUserLog.json")) #createdDistribution
	filename="week1/7_25"
	# filename="week1/allFiles"

	userLog=json.load(open(filename+".json"))
	# filename="allFiles"
	filename="week1_7_25"
	
	if not os.path.exists("InjectedReqsTemp"):
		os.mkdir("InjectedReqsTemp")

	runs=2 #use 2 runs
	K_values=[0,1,2,3]#(k is the insertion factor)
	# K_values=[0]#(k is the insertion factor)
	users=[20]
	print (users,K_values)
	for user in users:
		for K in K_values:
			for x in range(runs):
				print ("running run: ",x,K)
				userLogInjected=injectRequests(userLog,K,x,filename,user)
				preprocessBrowsingLog(userLogInjected,True,x,K,filename,user)

	# dirs=["week1"]
	# users={}
	# for _dir in dirs:
	# 	arr = os.listdir(_dir)
	# 	for ele in arr:
	# 		print (ele)
	# 		try:
	# 			userLog=json.load(open(_dir+"/"+ele))
	# 			for key in userLog:
	# 				if key not in users:
	# 					users[key]=[]
	# 				users[key]+=userLog[key]
	# 			# print (ele,len(users))
	# 		except Exception as e:
	# 			print (str(e))
	# 	with open(_dir+"/allFiles.json", 'w') as fp:
	# 		json.dump(users, fp)


# Injectedsharding_valueweek1_7_25_1run_0_0_users_[200]

