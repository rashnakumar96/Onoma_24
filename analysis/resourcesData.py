import json
import utils
from os.path import isfile, join
import resourceCollector
import time


project_path = utils.project_path

#precompiles a list of resources and their cdnMapping
def collectResources()
	alexaCountries=json.load(open(join(project_path, "data","alexaTop50SitesCountries.json")))

	resourcesDict={}
	cdnMappingDict={}
	from os import walk

	dir=join(project_path,"analysis","measurements")
	f = []
	for (dirpath, dirnames, filenames) in walk(dir):
	    f=dirnames
	    break
	print (f)
	countries=[]
	for country in alexaCountries:
		print (country)
		if str(country) in f:
			continue
		else:
			countries.append(country)
	print (len(countries),len(alexaCountries))
	for country in countries:	
		print ("measuring for country: ",country)
		resourceCollector.runResourceCollector(country)
		
		resources=[]
		with open(join(project_path,"analysis","measurements",country,"AlexaUniqueResources.txt"),"r") as f:
			for resource in f:
				resources.append(resource.split("\n")[0])
		resourcesDict[country]=resources

		cdnMapping=json.load(open(join(project_path,"analysis","measurements",country,"PopularcdnMapping.json")))
		cdnMappingDict[country]=cdnMapping

		with open(join(project_path, "data","resourcesDict.json"),'w') as fp:
			json.dump(resourcesDict, fp, indent=4)

		with open(join(project_path, "data","cdnMappingDict.json"),'w') as fp:
			json.dump(cdnMappingDict, fp, indent=4)
		time.sleep(60)

collectResources()


