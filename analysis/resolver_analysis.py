import json, subprocess, time, os
import urllib.request
import dns.resolver

import utils

project_path = utils.project_path

_urlopen = urllib.request.urlopen
_Request = urllib.request.Request

class Resolver_analyzer:
	def __init__(self, doh_servers):
		self.doh_servers = doh_servers
		self.local_resolvers = '129.105.49.1'
		# '165.124.49.21'

		self.resolver_distance = {}
		self.resolver_performance = {}

		for resolver in doh_servers:
			self.resolver_distance[resolver] = {}

	# Get the network distance for each fetched resolver
	def get_distance(self):
		for resolver in self.doh_servers:
			self.resolver_distance[resolver]={}
			print ("Calculating network Distance of ",resolver," servers")
			count=0
			for server in self.doh_servers[resolver]:
				print("%d %% completed" % (100 * count / len(self.doh_servers[resolver])))
				result = ping(server)
				self.resolver_distance[resolver][server] = result
				count=count+1

	# Get the resolution performance for resolver
	def get_performance(self, sites):
		for site in sites:
			self.resolver_performance[site] = {}
			self.resolver_performance[site]["Google"] = resolve_DoH("8.8.8.8/resolve", site, 'A')
			self.resolver_performance[site]["Cloudflare"] = resolve_DoH("1.1.1.1/dns-query", site, 'A')
			self.resolver_performance[site]["Quad9"] = resolve_DoH("9.9.9.9:5053/dns-query", site, 'A')
			self.resolver_performance[site]["Local"] = resolve_DNS(self.local_resolvers, site, 'A')

	def dump(self, fn_prefix):
		dump_dir = project_path + "/resolver_analysis/"
		if not os.path.exists(dump_dir):
			os.mkdir(dump_dir)
		
		utils.dump_json(self.resolver_distance, dump_dir + fn_prefix + "_resolver_distance.json")
		utils.dump_json(self.resolver_performance, dump_dir + fn_prefix + "_resolver_performance.json")

	
# Ping the destination server
# Returns the minimum rtt
def ping(dst_server):
	min_time = ""
	
	try:
		ping_response = subprocess.Popen(["ping", "-c3", dst_server], stdout=subprocess.PIPE).stdout.read()
		ping_response = str(ping_response)
		ping_times = ping_response.split("min/avg/max/stddev =")[1]
		min_time = ping_times.split("/")[0]
	except Exception as e:
		print(str(e))
		print(ping_response)

	return min_time

# Resolve using DoH
# Returns the resolution time
def resolve_DoH(server, site, req_type):
	resolve_time = None

	try:
		req = _Request("https://%s?name=%s&type=%s" % (server, site, req_type), headers={"Accept": "application/dns-json"})
		start = time.time()
		_urlopen(req)
		stop = time.time()
		respTime = stop - start
		resolve_time = respTime
	except Exception as e:
		print (str(e))

	return resolve_time

# Resolve using DNS
# Returns the resolution time
def resolve_DNS(server, site, req_type):
	resolve_time = None
	my_resolver = dns.resolver.Resolver()
	my_resolver.nameservers = [server]

	try:
		start=time.time()
		my_resolver.query(site)
		stop=time.time()
		resolve_time = stop - start
	except Exception as e:
		print (str(e))

	return resolve_time