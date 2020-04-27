import json
import os
import matplotlib as mpl 

## agg backend is used to create plot as a .png file
mpl.use('agg')
import matplotlib.pyplot as plt



def lighthouseAnalysis(dirname,results):
	for path in os.listdir(dirname):
		full_path = os.path.join(dirname, path)
		if os.path.isfile(full_path):
			try:
				lighthouseRes=json.load(open(full_path))
			except Exception as e:
				print str(e)
				continue

			site=path.split("Lighthouse")[0]
			approach=dirname.split("lighthouseResults")[1]

			if site not in results:
				results[site]={}
			if approach not in results[site]:
				results[site][approach]={}

			try:

				results[site][approach]["firstContentfulPaint"]=lighthouseRes['audits']["first-contentful-paint"]["numericValue"]
				results[site][approach]["firstMeaningfulPaint"]=lighthouseRes['audits']["first-meaningful-paint"]["numericValue"]
				results[site][approach]["speedIndex"]=lighthouseRes['audits']["speed-index"]["numericValue"]
				results[site][approach]["timeToFirstByte"]=lighthouseRes['audits']["time-to-first-byte"]["numericValue"]
				results[site][approach]["interactive"]=lighthouseRes['audits']["interactive"]["numericValue"]
			

			except Exception as e:
				print str(e)


def lighthouseScatterPlots(resultFile,metric):
	lighthouseRes=json.load(open(resultFile))
	DoHProxy=[]
	LocalR=[]
	SubRosa=[]
	count=1
	for site in lighthouseRes:
		for approach in lighthouseRes[site]:
			try:
				if approach=="DoHProxy":
					DoHProxy.append(lighthouseRes[site][approach][metric])
					count+=1
				elif approach=="LocalR":
					LocalR.append(lighthouseRes[site][approach][metric])

				elif approach=="SubRosa":
					SubRosa.append(lighthouseRes[site][approach][metric])
					
			except Exception as e:
				print (str(e),site)
				break
	sites = [site for site in range(1,count)]
	print (len(sites),len(DoHProxy),len(LocalR),len(SubRosa))
	doh=plt.scatter(sites, DoHProxy, marker="o",color="r" )
	local=plt.scatter(sites, LocalR, marker="s",color='b')
	subrosa=plt.scatter(sites, SubRosa, marker="^",color='g')
	plt.xlabel('Sites')
	plt.ylabel('Time in ms')
	plt.legend((doh, local, subrosa),
           ('DoHProxy', 'LocalR', 'SubRosa'),
           scatterpoints=1,
           loc='upper right')
	plt.xlim(0,50)
	plt.title(metric+' of Alexa Top US sites with the three approaches')
	plt.grid(True)
	plt.show()


def lighthouseBoxPlot(resultFile,metric):
	lighthouseRes=json.load(open(resultFile))
	DoHProxy=[]
	LocalR=[]
	SubRosa=[]
	count=1
	for site in lighthouseRes:
		for approach in lighthouseRes[site]:
			try:
				if approach=="DoHProxy":
					DoHProxy.append(lighthouseRes[site][approach][metric])
					# sites.append(site)
					count+=1
				elif approach=="LocalR":
					LocalR.append(lighthouseRes[site][approach][metric])

				elif approach=="SubRosa":
					SubRosa.append(lighthouseRes[site][approach][metric])
					
			except Exception as e:
				print (str(e),site)
				break
	data_to_plot = [LocalR, SubRosa, DoHProxy]
	fig = plt.figure(1, figsize=(9, 6))
	plt.ylabel('Time in ms')
	plt.title(metric+' of Alexa Top US sites across the three approaches')


	# Create an axes instance
	ax = fig.add_subplot(111)

	# Create the boxplot
	bp = ax.boxplot(data_to_plot,patch_artist=True)
	## change outline color, fill color and linewidth of the boxes
	for box in bp['boxes']:
	    # change outline color
	    box.set( color='#7570b3', linewidth=2)
	    # change fill color
	    box.set( facecolor = '#1b9e77' )

	## change color and linewidth of the whiskers
	for whisker in bp['whiskers']:
	    whisker.set(color='#7570b3', linewidth=2)

	## change color and linewidth of the caps
	for cap in bp['caps']:
	    cap.set(color='#7570b3', linewidth=2)

	## change color and linewidth of the medians
	for median in bp['medians']:
	    median.set(color='#b2df8a', linewidth=2)

	## change the style of fliers and their fill
	for flier in bp['fliers']:
	    flier.set(marker='o', color='#e7298a', alpha=0.5)

	## Custom x-axis labels
	ax.set_xticklabels(['LocalR', 'SubRosa', 'DoHProxy'])

	## Remove top axes and right axes ticks
	ax.get_xaxis().tick_bottom()
	ax.get_yaxis().tick_left()
	# Save the figure
	fig.savefig('graphs/'+metric+'BoxPlot.png', bbox_inches='tight')

def main():
#########################################################
# Uncomment the following lines to obtain a single json file consisting of page load metrics for each approach
	# results={}
	# lighthouseAnalysis("lighthouseResultsLocalR",results)
	# lighthouseAnalysis("lighthouseResultsSubRosa",results)
	# lighthouseAnalysis("lighthouseResultsDoHProxy",results)
	# with open("lighthouseAnalysis.json",'w') as fp:
	# 	json.dump(results,fp)

#########################################################
# Uncomment the following lines to obtain a scatter plot of each metric
	# lighthousePlots("lighthouseAnalysis.json","timeToFirstByte")
	# lighthousePlots("lighthouseAnalysis.json","speedIndex")
	# lighthousePlots("lighthouseAnalysis.json","interactive")
	# lighthousePlots("lighthouseAnalysis.json","firstContentfulPaint")
	# lighthousePlots("lighthouseAnalysis.json","firstMeaningfulPaint")



#########################################################
# Uncomment the following lines to obtain a box plot of each metric
	# lighthouseBoxPlots("lighthouseAnalysis.json","timeToFirstByte")
	# lighthouseBoxPlots("lighthouseAnalysis.json","speedIndex")
	# lighthouseBoxPlots("lighthouseAnalysis.json","interactive")
	# lighthouseBoxPlots("lighthouseAnalysis.json","firstContentfulPaint")
	lighthouseBoxPlot("lighthouseAnalysis.json","firstMeaningfulPaint")




