import json
import urllib.request
import time
import dns
# from dnslib import DNSRecord
import dns.resolver



_urlopen = urllib.request.urlopen
_Request = urllib.request.Request

def ResolveDoH(resolverName,server,site,reqType,dohPerformance):
	try:
		req = _Request("https://%s?name=%s&type=%s" % (server,site,reqType), headers={"Accept": "application/dns-json"})
		start=time.time()
		content = _urlopen(req).read().decode()
		reply = json.loads(content)
		stop=time.time()
		respTime=stop-start
		# print ('REPLY FROM RESOLVER: ',reply)
		dohPerformance[site][resolverName]=respTime
		
	except Exception as e:
		print (str(e))

def ResolveDNS(server,site,reqType,dohPerformance):

	my_resolver = dns.resolver.Resolver()

	my_resolver.nameservers = [server]

	try:
		start=time.time()
		response = my_resolver.query(site)
		stop=time.time()
		respTime=stop-start
		# for data in response:
		# 	print (data)
		dohPerformance[site][server]=respTime

	except Exception as e:
		print (str(e))


# Resolution time of each website in alexa top 50 websites of a country using different resolvers
def websitesResolveTime():
	dohPerformance={}
	topSites=[]
	with open('USalexatop50.txt','r') as f:
		for site in f:
			topSites.append(site[:-1])
	print(topSites)
	for site in topSites:
		dohPerformance[site]={}
		ResolveDoH("Google","8.8.8.8/resolve",site,'A',dohPerformance)
		ResolveDoH("Cloudflare","1.1.1.1/dns-query",site,'A',dohPerformance)
		ResolveDoH("Quad9","9.9.9.9:5053/dns-query",site,'A',dohPerformance)
		ResolveDNS("129.105.49.1",site,'A',dohPerformance)
		ResolveDNS("165.124.49.21",site,'A',dohPerformance)
	with open("websitesResolveTime.json",'w') as fp:
		json.dump(dohPerformance, fp, indent=4)


# Resolution time of each unique resource in alexa top 50 websites of a country using different resolvers

def resourcesResolveTime():
	dohPerformance={}

	# loads all the unique resources collected from alexa top 50 websites of a country
	alexaResources= json.load(open('USalexatop50Resources.json'))

	uniqueDomains=[]
	for resource in alexaResources:
		if "https" in resource:
			domain=resource.split("https://")[1]
		elif "http" in resource:
			domain=resource.split("http://")[1]
		domain=domain.split("/")[0]
		if domain not in uniqueDomains:
			uniqueDomains.append(domain)
	print (len(uniqueDomains),": Meauring response time of these many domains")
	x=0
	for domain in uniqueDomains:
		print(100*x/len(uniqueDomains)," \% complete")
		x=x+1
		dohPerformance[domain]={}
		try:
			ResolveDoH("Google","8.8.8.8/resolve",domain,'A',dohPerformance)
			ResolveDoH("Cloudflare","1.1.1.1/dns-query",domain,'A',dohPerformance)
			ResolveDoH("Quad9","9.9.9.9:5053/dns-query",domain,'A',dohPerformance)
			ResolveDNS("129.105.49.1",domain,'A',dohPerformance)
			ResolveDNS("165.124.49.21",domain,'A',dohPerformance)
		except Exception as e:
			print (domain)
			print (str(e))
	with open("resourcesResolveTime.json",'w') as fp:
		json.dump(dohPerformance, fp, indent=4)
resourcesResolveTime()
