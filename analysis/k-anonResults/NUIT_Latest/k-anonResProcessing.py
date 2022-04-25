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
from numpy import percentile
import statistics as stat




def jaccard_binary(x,y):
    """A function for finding the similarity between two binary vectors"""
    # It's a measure of similarity for the two sets of data, with a range from 0% to 100%. 
    # The higher the percentage, the more similar the two populations. This gives Jaccard Index. To get Jaccard Distance, we subtrcat 
    # this value from 1
    intersection = np.logical_and(x, y)
    union = np.logical_or(x, y)
    similarity = intersection.sum() / float(union.sum())
    return similarity

def calcKanon(Injected,k,filename,runs):
	shardingParameters=[1,2,4,8]
	for z in shardingParameters:
		dict={}
		jaccard_dict={}
		for run in range(runs):
			dict[run]={}
			jaccard_dict[run]={}
			if Injected:
				resFile=json.load(open("InjectedReqsLatest/Injectedsharding_value"+filename+'_'+str(z)+"run_"+str(run)+'_'+str(k)+".json"))
			else:
				# resFile=json.load(open("sharding_value"+str(z)+".json"))
				resFile={}
				with open("sharding_value"+str(z)+".json",'r') as f:
					for line in f:
						data = json.loads(line)
						for resolver in data:
							if resolver not in resFile:
								resFile[resolver]={}
							resFile[resolver]=data[resolver]
			for resolver in resFile:
				if resolver not in dict[run]:
					dict[run][resolver]={}
					jaccard_dict[run][resolver]={}
				uniqueUsers=[]
				totalResolutions=0
				# for user in resFile[resolver]:
					# for bit in resFile[resolver][user]:
					# 	if bit==1:
					# 		totalResolutions+=1
					# if user not in uniqueUsers:
						# uniqueUsers.append(user)
				uniqueUsers=list(set(resFile[resolver]))
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
							
					# dict[run][resolver]["clusterGroup"+str(clusterGroup)]=len(clusterDict[clusterGroup])
					if len(clusterDict[clusterGroup])==1:
						k1+=1
					clusterGroup+=1
				non_anonUsers=[]
				anonUsers=[]
				for clusterGroupKey in clusterDict:
					if len(clusterDict[clusterGroupKey])==1:
						non_anonUsers.append(clusterDict[clusterGroupKey][0])
					else:
						anonUsers.append(clusterDict[clusterGroupKey][0])

				print ("finding the closest match",len(anonUsers),len(non_anonUsers))
				count=0
				matched_non_anonUsers=[]
				for n_user in non_anonUsers:
					if count%100==0:
						print ("done for user: ",count,len(non_anonUsers))
					count+=1
					# if n_user in list(set(matched_non_anonUsers)):
					# 	continue

					jaccard_dict[run][resolver][n_user]=[]
					_maxSimilarUser=""
					_maxSimilarDist=0
					# for user in uniqueUsers:
					for user in anonUsers: #test with users with k>1
						if user==n_user:
							continue
						similarity=jaccard_binary(resFile[resolver][n_user],resFile[resolver][user])
						jaccard_dict[run][resolver][n_user].append(similarity)
						if similarity>_maxSimilarDist:
							_maxSimilarDist=similarity
							_maxSimilarUser=user
					for user in non_anonUsers: #test with even users with k=1
						if user==n_user:
							continue
						similarity=jaccard_binary(resFile[resolver][n_user],resFile[resolver][user])
						jaccard_dict[run][resolver][n_user].append(similarity)
						if similarity>_maxSimilarDist:
							_maxSimilarDist=similarity
							_maxSimilarUser=user
							# if similarity>0.3:
							# 	matched_non_anonUsers.append(_maxSimilarUser)
							# 	break
					# print (max(jaccard_dict[run][resolver][n_user]),_maxSimilarDist)
					if _maxSimilarDist>0.3:
						for clusterGroupKey in clusterDict:
							if _maxSimilarUser in clusterDict[clusterGroupKey]:
								clusterDict[clusterGroupKey].append(n_user)
							if n_user in clusterDict[clusterGroupKey] and len(clusterDict[clusterGroupKey])==1:
								clusterDict[clusterGroupKey].remove(n_user)

				for clusterGroupKey in clusterDict:
					if len(clusterDict[clusterGroupKey])==0:
						continue
					dict[run][resolver]["clusterGroup"+str(clusterGroupKey)]=len(clusterDict[clusterGroupKey])



		# print (resolver," number of clusters: ",len(clusterDict)," total resolutions: ",totalResolutions," k1: ",k1)
		if Injected:
			with open("InjectedReqsLatest/Injectedsharding_value"+filename+'_'+str(z)+'_'+str(k)+"Result.json", 'w') as fp:
				json.dump(dict, fp)
			with open("InjectedReqsLatest/Jaccardsharding_value"+filename+'_'+str(z)+'_'+str(k)+"Result.json", 'w') as fp:
				json.dump(jaccard_dict, fp)
		else:
			with open("sharding_value"+filename+str(z)+"Result.json", 'w') as fp:
				json.dump(dict, fp)

def plotK_ValuesPerInsertion(Injected,k,filename):
	shardingParameters=[8,4,2,1]
	alphas=[1,0.75,0.5,0.25]
	# shardingParameters=[2,4]
	# colors=['c','y','g','m','b','r','orange','purple']
	colors=['m','g','y','c']
	ind=0
	_max=0
	avgKdict={}
	# styles=['o','*','.']
	styles=['solid', 'dashed', 'dashdot', 'dotted']


	# dataFile=json.load(open("InjectedReqsLatest/Injectedsharding_value"+str(z)+".json"))

	for z in shardingParameters:
		avgKdict["sharding_value"+str(z)]={}
		if Injected:
			resFile=json.load(open("InjectedReqsLatest/Injectedsharding_value"+filename+'_'+str(z)+'_'+str(k)+"Result.json"))
		else:
			resFile=json.load(open("sharding_value"+filename+str(z)+"Result.json"))
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

		# q25, q75 = percentile(avgk_values, 25), percentile(avgk_values, 75)
		# iqr = q75 - q25
		# cut_off = iqr * 1.5
		# lower, upper = q25 - cut_off, q75 + cut_off
		# avgk_values=[x for x in avgk_values if x >= lower and x <= upper]
		sortedData=np.sort(avgk_values)
		# print (sortedData)
		count=0
		for value in sortedData:
			if value>=2:
				count+=1
		print ("insertion_value: ",k," and sharding_value: ",z," % 2-anonymised: ",100*count/len(sortedData))
		count=0
		for value in sortedData:
			if value>=4:
				count+=1
		print ("insertion_value: ",k," and sharding_value: ",z," % 4-anonymised: ",100*count/len(sortedData))

			# sortedData=np.sort(list(resFile[resolver].values()))
		
		pData=1. * np.arange(len(sortedData))/(len(sortedData)-1)
		# print (sortedData)

		if z==1:
			plt.plot(sortedData,pData,linestyle=styles[ind],color=colors[ind],label="no sharding",linewidth=2)
		else:	
			plt.plot(sortedData,pData,linestyle=styles[ind],color=colors[ind],label="sharding_value"+str(z),linewidth=2)
			# plt.plot(sortedData,pData,color=colors[c],label=str(resolver)+";resolutions made: "+str(totalResolutions))

			c+=1
		ind+=1
		# break
	# overheadPerUser=json.load(open("InjectedReqsLatest/overhead.json"))
	# avgOverhead=sum(overheadPerUser.values())/len(overheadPerUser.values())

	plt.xlabel("K-Value")
	plt.ylabel("CDF")
	plt.xlim(0,30)
	print (sortedData[-1])
	dim=np.arange(0,30,2);
	plt.xticks(dim)
	plt.margins(0.02)
	# plt.title("With Insertion Factor "+str(k)+" and overhead "+str(avgOverhead)[:5]+"%")
	# if k==0:
	# 	plt.title("No Insertion Factor")
	# else:
	# 	plt.title("Insertion Factor = "+str(k))
	plt.grid()
	plt.legend(loc="lower right")
	if not os.path.exists("InjectedReqsLatest/graphs"):
		os.mkdir("InjectedReqsLatest/graphs")
	if Injected:
		plt.savefig("InjectedReqsLatest/graphs/InjectedK_valuesCDF_"+filename+"_insertion_"+str(k))
	else:
		plt.savefig("graphs/K_valuesCDF"+filename)
	plt.clf()
	print (avgKdict)

def plotK_ValuesPerSharding(Injected,z,filename):
	alphas=[1,0.75,0.5,0.25]
	insertion_values=[3,2,1,0]
	# shardingParameters=[2,4]
	# colors=['c','y','g','m','b','r','orange','purple']
	colors=['m','g','y','c']
	# styles=['-',':','.']
	styles=['solid', 'dashed', 'dashdot', 'dotted']

	# styles=['o','*','.']

	ind=0
	_max=0
	avgKdict={}
	# dataFile=json.load(open("InjectedReqsLatest/Injectedsharding_value"+str(z)+".json"))

	for i in insertion_values:
		avgKdict["insertion_value"+str(z)]={}
		if Injected:
			resFile=json.load(open("InjectedReqsLatest/Injectedsharding_value"+filename+'_'+str(z)+'_'+str(i)+"Result.json"))
		else:
			resFile=json.load(open("sharding_value"+filename+str(z)+"Result.json"))
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
			avgk_values.extend([key for x in range(int(avg))])

		# q25, q75 = percentile(avgk_values, 25), percentile(avgk_values, 75)
		# iqr = q75 - q25
		# cut_off = iqr * 1.5
		# lower, upper = q25 - cut_off, q75 + cut_off
		# avgk_values=[x for x in avgk_values if x >= lower and x <= upper]
		sortedData=np.sort(avgk_values)
			# sortedData=np.sort(list(resFile[resolver].values()))

		pData=1. * np.arange(len(sortedData))/(len(sortedData)-1)
		# print (sortedData)

		if i==0:
			plt.plot(sortedData,pData,linestyle=styles[ind],color=colors[ind],label="no insertion",linewidth=2)
		else:	
			plt.plot(sortedData,pData,linestyle=styles[ind],color=colors[ind],label="insertion_value"+str(i),linewidth=2)
			# plt.plot(sortedData,pData,color=colors[c],label=str(resolver)+";resolutions made: "+str(totalResolutions))

			c+=1
		ind+=1
		# break
	# overheadPerUser=json.load(open("InjectedReqsLatest/overhead.json"))
	# avgOverhead=sum(overheadPerUser.values())/len(overheadPerUser.values())

	plt.xlabel("K-Value")
	plt.ylabel("CDF")
	plt.xlim(0,30)
	print (sortedData[-1])
	dim=np.arange(0,30,2);
	plt.xticks(dim)
	plt.margins(0.02)
	# if z==1:
	# 	plt.title("No Sharding")
	# else:
	# 	plt.title("Sharding value = "+str(z))
	plt.grid()
	plt.legend(loc="lower right")
	if not os.path.exists("InjectedReqsLatest/graphs"):
		os.mkdir("InjectedReqsLatest/graphs")
	if Injected:
		plt.savefig("InjectedReqsLatest/graphs/InjectedK_valuesCDF_"+filename+"_sharding_"+str(z))
	else:
		plt.savefig("graphs/K_valuesCDF"+filename)
	plt.clf()
	print (avgKdict)

def calcAverageOverhead(filename,i):
	resFile=json.load(open("InjectedReqs/overhead_"+filename+str(i)+"_"+str(0)+".json"))
	_list=list(resFile.values())
	print ("IF: ",i," Overhead in % bytes: ", sum(_list)/len(_list)," std: ",stat.stdev(_list))
	

	


def JaccardDist(Injected,k):
	shardingParameters=[8,4,2,1]
	colors=['c','y','g','m','b','r','orange','purple']
	ind=0
	avgKdict={}

	for z in shardingParameters:
		resFile=json.load(open("InjectedReqsLatest/Jaccardsharding_value"+'_'+str(z)+'_'+str(k)+"Result.json"))
		avgDict={}
		for run in resFile:
			for resolver in resFile[run]:
				for user in resFile[run][resolver]:
					_max=max(resFile[run][resolver][user])
					avgDict[user]=_max
		indexes=[x for x in range(len(avgDict))]

		sortedData=np.sort(list(avgDict.values()))
		pData=1. * np.arange(len(sortedData))/(len(sortedData)-1)
		if z==1:
			plt.plot(sortedData,pData,color=colors[ind],label="no sharding")
		else:	
			plt.plot(sortedData,pData,color=colors[ind],label="sharding_value"+str(z))
		ind+=1
		
	plt.legend()
	plt.xlabel("Maximum JaccardDist(Similarity) with a Cluster")
	plt.ylabel("CDF")
	plt.margins(0.02)
	plt.title("With Insertion Factor"+str(k))
	if not os.path.exists("InjectedReqsLatest/graphs"):
		os.mkdir("InjectedReqsLatest/graphs")
	if Injected:
		plt.savefig("InjectedReqsLatest/graphs/JaccardDist_"+str(k))
	else:
		plt.savefig("graphs/JaccardDist_")
	plt.clf()

def processNUITDATA():
	_dict={}
	resFile=json.load(open(r"C:Users/byungjinjun/Documents/NUIT_K_anon/resFile.json"))
	import ijson


	resFile = ijson.parse(open("resFile.json", 'r'))
	_dict={}
	with open("resFile.json",'r') as f:
	    for line in f:
	        data = json.loads(line)
	        for user in data:
	        	_dict[user]=len(data[user])
	popularusers=list(dict(Counter(_dict).most_common(200)).keys())
	with open("200Users.json", 'w') as fp:
		json.dump(popularusers, fp)

	users=json.load(open("200Users.json"))
	dict={}
	with open("resFile.json",'r') as f:
	    for line in f:
	        data = json.loads(line)
	        for user in data:
	        	if user in users:
	        		dict[user]=data[user]
	with open("200UsersDistr.json", 'w') as fp:
		json.dump(dict, fp)

	_dict={}
	z=0
	userDistr=json.load(open("200UsersDistr.json"))
	for user in userDistr:
		domains=[]
		i=0
		for url in userDistr[user]:
			if "." in url:
				domains.append(url)
				# print (url)
		_dict[user]=domains
	with open("200UsersDistrwDomains.json", 'w') as fp:
		json.dump(_dict, fp)

	_dict={}
	# userDistr=json.load(open("200UsersDistrwDomains.json"))
	userDistr=json.load(open("200UsersDistrwDomains.json"))
	for user in userDistr:
		for url in userDistr[user]:
			if url not in _dict:
				_dict[url]=0
			_dict[url]+=1
	indexes=[x for x in range(len(_dict))]

	freq=list(_dict.values())
	freq.sort()

	# print (indexes)
	plt.plot(indexes,freq,color='c')
	plt.xlabel("urls")
	plt.ylabel("Freq")
	plt.yscale('log')
	plt.margins(0.02)
	if not os.path.exists("graphs"):
		os.mkdir("graphs")
	plt.savefig("graphs/urlFreq")

	# with open('resFile.json') as data_file:    
	# 	resFile = json.load(data_file)
	# _dict={}
	# for user in resFile:
	# 	print (resFile[user])
	# 	# urls=[]
	# 	# for url in resFile[user]:
	# 	# 	if url not in urls:
	# 	# 		urls.append(url)
	# 	_dict[user]=len(resFile[user])
	# 		# urlFreq[url]+=1
	# popularusers=dict(Counter(_dict).most_common(200))
	# # print (popularusers.keys())
	# print (len(popularusers.keys()))

	# usersLog={}
	# for user in popularusers:
	# 	usersLog[user]=resFile[user]
	# # 	bitC=0	
	# # 	for bit in resFile[resolver][user]:
	# # 		if bit==1:
	# # 			bitC+=1
	# # 	_dict[user]=bitC
	# with open("200UsersDistr.json", 'w') as fp:
	# 		# with open("InjectedReqsLatest/Injectedsharding_value"+str(value)+".json", 'w') as fp:
	# 	json.dump(usersLog, fp)
		
if __name__ == "__main__":

	# calcKanon(False,0)
	# plotK_Values(False,0)
	filename="week1_7_25"
	k=3 #Insertion Factor
	avgs=[]
	runs=2
	# for x in range(runs):
	# 	try:
	# 		overheadDict=json.load(open("InjectedReqsLatest/overhead_"+filename+str(k)+"_"+str(x)+".json"))
	# 		avg=sum(overheadDict.values())/len(overheadDict)
	# 		print ("Avg overhead with insertion factor of k: ",k,avg," min: ",min(overheadDict.values())," max: ",max(overheadDict.values()),np.median(np.array(list(overheadDict.values()))))
	# 		avgs.append(avg)
	# 	except:
	# 		continue
	# print (sum(avgs)/len(avgs))
	# calcKanon(True,k,filename,runs)
	insertion_values=[3,2,1,0]
	for i in insertion_values:
		plotK_ValuesPerInsertion(True,i,filename)
		calcAverageOverhead(filename,i)

	# sharding_values=[8,4,2,1]
	# for z in sharding_values:
		# plotK_ValuesPerSharding(True,z,filename)

	# JaccardDist(True,k)
	# import os

	# arr = os.listdir("/Users/rashnakumar/Documents/Github/Sub-Rosa6-NSDI_22/analysis/k-anonResults/InjectedReqsLatest")
	# for ele in arr:
	# 	if "Injectedsharding_" in ele:
	# 		print (ele+'\n')
# processNUITDATA()