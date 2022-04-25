import json
import utils
from os.path import isfile, join

project_path = utils.project_path


def mergeDNSLatencies():
	country="DE"
	dnsLatency1 = json.load(open(join(project_path, "analysis", "measurements", country, "dnsLatenciesNSubRosa.json")))
	dnsLatency2 = json.load(open(join(project_path, "analysis", "measurements", country, "dnsLatenciesSubRosa"+".json")))

	for key in dnsLatency2:
		dnsLatency1[key]=dnsLatency2[key]

	with open(join(project_path, "analysis", "measurements", country, "dnsLatencies.json"),'w') as fp:
		json.dump(dnsLatency1, fp, indent=4)

def mergeTResults(list,replicas):

	for result in list:
		if result['dst_addr'] not in replicas:
			replicas.append(result['dst_addr'])
	return replicas

def mergeTraceroutes():
	countryList=["DE","IN","US","PK"]
	replicas=[]
	for country in countryList:
		fname="RtracerouteFetechedResult"+country+".json"
		print (len(replicas))
		try:
			print ("opening file: ")
			file = json.load(open(join(project_path, "analysis", "measurements",country,fname)))
			_results=mergeTResults(file,replicas)

			count=0
			replicas=replicas+_results
			print (len(_results),fname)

			# for r in _results:
			# 	replicas.append(r)
			# 	print (100*count/len(_results))
			# 	count+=1
		except Exception as e:
			print (str(e))
			# print (fname+" doesn't exist")
		fname="tracerouteFetechedResult"+country+".json"
		try:
			file = json.load(open(join(project_path, "analysis", "measurements", country,fname)))
			_results=mergeTResults(file,replicas)
			replicas=replicas+_results
			print (len(_results),fname)


			# for r in _results:
			# 	replicas.append(r)
		except Exception as e:
			# print (fname+" doesn't exist")
			print (str(e))

	unique=[]
	for r in replicas:
		unique.append(r)
	print (len(unique))
	with open(join(project_path, "analysis", "measurements", "combinedTracerouteResults"),'w') as fp:
		json.dump(unique, fp, indent=4)

# mergeTraceroutes()

# def mergeResourceFiles():
# mergeDNSLatencies()

def _try():
	import  matplotlib.pyplot as plt
	import numpy as np 
	np.random.seed(10) 
	data = np.random.normal(100, 20, 200) 
	X=[(2,3,1), (2,3,2), (2,3,3), (2,3,(4,6))]
	fig =plt.figure(figsize=(6,4))
	plt.subplots_adjust(wspace=0, hspace=0)

	datas=[]
	for i in range(3):
		datas.append(data)
	i=0
	for nrows, ncols, plot_number in X:
		sub = fig.add_subplot(nrows, ncols, plot_number)
		sub.set_xticks([])
		sub.set_yticks([])
		print (i)
		if i==3:
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
			sub.set_ylabel("Time in ms")
			# sub.boxplot(data) 
		i+=1


	plt.show()
_try()

