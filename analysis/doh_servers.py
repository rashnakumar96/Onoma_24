import json, os
import urllib.request

import utils

_urlopen = urllib.request.urlopen
_Request = urllib.request.Request

ana_url="test.ana-aqualab.cs.northwestern.edu"

project_path = utils.project_path

class Resolver_collector:
	# Initialize result dictionary with a list of resolver names
	# resolvers: dictionary with keys as resolver name and value as resolver url
	def __init__(self, resolvers):
		self.resolvers = resolvers
		self.resolver_ips = {}

		for resolver in self.resolvers:
			self.resolver_ips[resolver] = set()

	def resolve(self, resolver, type):
		if resolver not in self.resolvers:
			print("ERROR: unsupported resolver")
			return
		server = self.resolvers[resolver]

		try:
			req = _Request("https://%s?name=%s&type=%s" % (server, ana_url, type), headers={"Accept": "application/dns-json"})
			content = _urlopen(req).read().decode()
			reply = json.loads(content)
			print ('%s REPLY FROM RESOLVER: %s' % (resolver, reply))
			if "Answer" in reply:
				answer = reply["Answer"]
				retval = [_["data"] for _ in answer]
				for ip in retval:
					self.resolver_ips[resolver].add(ip)
		except Exception as e:
			print(str(e))

	def collect_all(self):
		for resolver in self.resolvers:
			self.resolve(resolver, 'A')
	
	def dump(self, fn_prefix):
		ip_dir = project_path + "/server_ips/"
		if not os.path.exists(ip_dir):
			os.mkdir(ip_dir)
		
		for resolver in self.resolver_ips:
			self.resolver_ips[resolver] = list(self.resolver_ips[resolver])

		utils.dump_json(self.resolver_ips, ip_dir + fn_prefix + "_resources.json")

if __name__ == "__main__":
	# This script runs for approximately a day and collects all the unicast servers of the 3 DoH resolvers from a particular location
	x = 1

	country = input("Enter alpha-2 country code: ")

	resolvers = {
		"Google": "8.8.8.8/resolve", 
		"Cloudflare": "1.1.1.1/dns-query", 
		"Quad9": "9.9.9.9:5053/dns-query"
	}

	rc = Resolver_collector(resolvers)

	rc.collect_all()
	rc.dump(country)