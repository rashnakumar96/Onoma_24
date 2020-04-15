import json
import urllib.request

_urlopen = urllib.request.urlopen
_Request = urllib.request.Request

def Resolve(resolverName,server,reqType,dohServers):
	site="test.ana-aqualab.cs.northwestern.edu"
	if resolverName not in dohServers:
		dohServers[resolverName]=[]
	try:
		req = _Request("https://%s?name=%s&type=%s" % (server,site,reqType), headers={"Accept": "application/dns-json"})
		content = _urlopen(req).read().decode()
		reply = json.loads(content)
		# print ('REPLY FROM RESOLVER: ',reply)
		if "Answer" in reply:
			answer = reply["Answer"]
			retval = [_["data"] for _ in answer]
			for ip in retval:
				if ip not in dohServers[resolverName]:
					dohServers[resolverName].append(ip)
					print ("New server ip discovered of ",resolverName)
	except Exception as e:
		print (str(e))

# This script runs for approximately a day and collects all the unicast servers of the 3 DoH resolvers from a particular location
dohServers=json.load(open('dohServers.json'))
x=1
duration=86400
for x in range(duration):
	print (100*x/duration," \% completed")
	Resolve("Google","8.8.8.8/resolve",'A',dohServers)
	Resolve("Cloudflare","1.1.1.1/dns-query",'A',dohServers)
	Resolve("Quad9","9.9.9.9:5053/dns-query",'A',dohServers)
	if x%10==0:
		with open("dohServers.json",'w') as fp:
			json.dump(dohServers,fp,indent=4)