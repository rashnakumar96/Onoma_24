import json
import subprocess


def calcMinPing(resolver,server,resolverDistance):
	try:
		pingResponse = subprocess.Popen(["ping", "-c3", server], stdout=subprocess.PIPE).stdout.read()
		pingResponse=str(pingResponse)
		pingTimes=pingResponse.split("min/avg/max/stddev =")[1]
		minPingTime=pingTimes.split("/")[0]
		print (minPingTime)
		resolverDistance[resolver][server]={}
		resolverDistance[resolver][server]=minPingTime
	except Exception as e:
		print (str(e))
		print(pingResponse)
		print (resolver,server)

localResolvers=['129.105.49.1','165.124.49.21']
dohServers=json.load(open('dohServers.json'))
resolverDistance={}


for resolver in dohServers:
	resolverDistance[resolver]={}
	print ("Calculating network Distance of ",resolver," servers")
	count=0
	for server in dohServers[resolver]:
		print (100*count/len(dohServers[resolver])," \% completed")
		calcMinPing(resolver,server,resolverDistance)
		count=count+1
	with open('resolverDistance.json', 'w') as fp:
		json.dump(resolverDistance, fp, indent=4)

resolverDistance["localResolvers"]={}
print ("Calculating network Distance of local Resolvers")

for server in localResolvers:
	calcMinPing("localResolvers",server,resolverDistance)		

with open('resolverDistance.json', 'w') as fp:
	json.dump(resolverDistance, fp, indent=4)

	