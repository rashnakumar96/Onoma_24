import json
import statistics
import subprocess
import time
import socket
import matplotlib.pyplot as plt
import os
from dns import resolver
from tabulate import tabulate
import socket
import ipaddress
import pandas as pd


def parse_dns_string(reader, data):
    res = ''
    to_resue = None
    bytes_left = 0

    for ch in data:
        if not ch:
            break

        if to_resue is not None:
            resue_pos = chr(to_resue) + chr(ch)
            res += reader.reuse(resue_pos)
            break

        if bytes_left:
            res += chr(ch)
            bytes_left -= 1
            continue

        if (ch >> 6) == 0b11 and reader is not None:
            to_resue = ch - 0b11000000
        else:
            bytes_left = ch

        if res:
            res += '.'

    return res


class StreamReader:
    def __init__(self, data):
        self.data = data
        self.pos = 0

    def read(self, len_):
        pos = self.pos
        if pos >= len(self.data):
            raise

        res = self.data[pos: pos+len_]
        self.pos += len_
        return res

    def reuse(self, pos):
        pos = int.from_bytes(pos.encode(), 'big')
        return parse_dns_string(None, self.data[pos:])


def make_dns_query_domain(domain):
    def f(s):
        return chr(len(s)) + s

    parts = domain.split('.')
    parts = list(map(f, parts))
    return ''.join(parts).encode()


def make_dns_request_data(dns_query):
    req = b'\xaa\xbb\x01\x00\x00\x01\x00\x00\x00\x00\x00\x00'
    req += dns_query
    req += b'\x00\x00\x01\x00\x01'
    return req


def add_record_to_result(result, type_, data, reader):
    if type_ == 'A':
        item = str(ipaddress.IPv4Address(data))
    elif type_ == 'CNAME':
        item = parse_dns_string(reader, data)
    else:
        return

    result.setdefault(type_, []).append(item)


def parse_dns_response(res, dq_len, req):
    reader = StreamReader(res)

    def get_query(s):
        return s[12:12+dq_len]

    data = reader.read(len(req))
    assert(get_query(data) == get_query(req))

    def to_int(bytes_):
        return int.from_bytes(bytes_, 'big')

    result = {}
    res_num = to_int(data[6:8])
    for i in range(res_num):
        reader.read(2)
        type_num = to_int(reader.read(2))

        type_ = None
        if type_num == 1:
            type_ = 'A'
        elif type_num == 5:
            type_ = 'CNAME'

        reader.read(6)
        data = reader.read(2)
        data = reader.read(to_int(data))
        add_record_to_result(result, type_, data, reader)

    return result


def dns_lookup(domain, address):
    dns_query = make_dns_query_domain(domain)
    dq_len = len(dns_query)

    req = make_dns_request_data(dns_query)
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.settimeout(2)

    try:
        sock.sendto(req, (address, 53))
        res, _ = sock.recvfrom(1024 * 4)
        result = parse_dns_response(res, dq_len, req)
    except Exception:
        return
    finally:
        sock.close()

    return result

class PerformanceTests:
	def __init__(self):
		a=1

	def DNSResolutionTime(self,site,resolvers,runs):
		
		resolutionTime={}
		for resolver in resolvers:
			resolutionTimes=[]
			for run in range(runs):
				# res = resolver.Resolver()
				# res.nameservers = [resolver]
				dns_start = time.time()
				# answers = res.query(site)
				# for rdata in answers:
    # 				print (rdata.address)
				if not (dns_lookup(site, resolver)):
					print (resolver,site)
				dns_end = time.time()
				resolutionTimes.append((dns_end - dns_start) * 1000)
			resolutionTime[resolver]=resolutionTimes
		return resolutionTime

def runResolutionTimes(resolvers,day):
	top500Sites = json.load(open("alexaTop500SitesCountries.json"))
	countrycodes=["US","AR","DE","IN"]
	tests = PerformanceTests()
	runs=3

	
	if not os.path.exists("resTimes"):
		os.mkdir("resTimes")
	allSitesResolutionTime={}
	allSitesResolutionTime[country]={}
	top50 = top500Sites[country][:50]
	for site in top50:
		resolutionTime=tests.DNSResolutionTime(site,resolvers,runs)
		allSitesResolutionTime[country][site]=resolutionTime
	with open("resTimes/perSiteResolutionTime_"+country+day+".json", 'w') as fp:
		json.dump(allSitesResolutionTime, fp)

def analyseResolutionTimes(resolvers,country,day):
	allSitesResolutionTime = json.load(open("resTimes/perSiteResolutionTime_"+country+day+".json"))

	table=[]
	row=["resolver","top-1","top-2","top-3"]
	table.append(row)
	resolverRanking={}
	medianResTime={}
	for site in allSitesResolutionTime[country]:
		medianResTime[site]={}
		for resolver in allSitesResolutionTime[country][site]:
			medianResTime[site][resolver]=statistics.median(allSitesResolutionTime[country][site][resolver])
	for site in medianResTime:
		sortedResTimes = sorted(medianResTime[site], key=medianResTime[site].get,reverse=False)[:3]
		x=1
		for res in sortedResTimes:
			if res not in resolverRanking:
				resolverRanking[res]={}
			topx="top-"+str(x)
			if topx not in resolverRanking[res]:
				resolverRanking[res][topx]=0
			resolverRanking[res][topx]+=1
			x+=1
		# for res in allSitesResolutionTime[country][site]:
		# 	row.append(allSitesResolutionTime[country][site][res])
	# 	table.append(row)

	print (resolverRanking)
	for res in resolverRanking:
		for x in range(1,4):
			if "top-"+str(x) not in resolverRanking[res]:
				resolverRanking[res]["top-"+str(x)]=0
		row=[res,resolverRanking[res]["top-1"],resolverRanking[res]["top-2"],resolverRanking[res]["top-3"]]
		table.append(row)
	print(tabulate(table, headers='firstrow', tablefmt='fancy_grid'))
	content=tabulate(table, headers='firstrow', tablefmt="tsv")


	text_file=open("resTimes/perSiteResolutionTime_"+country+day+".csv","w")
	text_file.write(content)
	text_file.close()

# def bumpchart(resolverWeight,day,df, ax,j,show_rank_axis= True, rank_axis_distance= 1.1, 
#                scatter= False, holes= False,
#               line_args= {}, scatter_args= {}, hole_args= {}):
    
#     if ax is None:
#         left_yaxis= plt.gca()
#     else:
#         left_yaxis = ax

#     # Creating the right axis.
#     right_yaxis = left_yaxis.twinx()
    
#     axes = [left_yaxis, right_yaxis]
    
#     # Creating the far right axis if show_rank_axis is True
#     if show_rank_axis:
#         far_right_yaxis = left_yaxis.twinx()
#         axes.append(far_right_yaxis)
#     print (df)
#     for col in df.columns:
#         y = df[col]
#         x = df.index.values
#         print("col: ",col)

#         # Plotting blank points on the right axis/axes 
#         # so that they line up with the left axis.
#         for axis in axes[1:]:
#             axis.plot(x, y, alpha= 0)
#         print ("x: ",[X for X in x],len(x))
#         print ("y: ",[Y for Y in y],len(y))


#         left_yaxis.plot(x, y, **line_args, solid_capstyle='round')
        
#         # Adding scatter plots
#         if scatter:
#             # s = [20*4**n for n in range(len(x))]
#             s=[]
#             for n in range(len(x)):
#             	country=x[n]
#             	res=col
#             	if y[n]==1:
#             		print ("s_size: ",resolverWeight[country][res]["top-"+str(y[n])],country,res,"top-"+str(y[n]),col)
#             		s.append((10)*resolverWeight[country][res]["top-"+str(y[n])])
#             	else:
#             		s.append(50)
#             print ("s: ",s)
#             ss= {"s": s, "alpha": 0.8}
#             left_yaxis.scatter(x, y, **ss)
            
#             #Adding see-through holes
#             if holes:
#                 bg_color = left_yaxis.get_facecolor()
#                 left_yaxis.scatter(x, y, color= bg_color, **hole_args)

#     # Number of lines
#     lines = len(df.columns)
#     print ("lines: ",lines)

#     y_ticks = [*range(1, lines + 1)]
    
#     # Configuring the axes so that they line up well.
#     for axis in axes:
#         axis.invert_yaxis()
#         print (axis)
#         # if j%2==1:

#         axis.set_yticks(y_ticks)
#         axis.set_ylim((lines + 0.5, 0.5))
    
#     # Sorting the labels to match the ranks.
#     if j%2==0:
#     	left_labels = df.iloc[0].sort_values().index
#     	left_yaxis.set_yticklabels(left_labels)
#     # else:
#     # 	right_labels = df.iloc[-1].sort_values().index


#     # 	right_yaxis.set_yticklabels(right_labels)
    
#     # Setting the position of the far right axis so that it doesn't overlap with the right axis
#     # if show_rank_axis:
#     #     far_right_yaxis.spines["right"].set_position(("axes", rank_axis_distance))
#     # if j%2==0:
#     # 	# ax.tick_params(left = False)
#     # 	ax.set_yticks([])
#     # 	right_yaxis
#     print (show_rank_axis)
#     return axes

def bumpchart(df, show_rank_axis= True, rank_axis_distance= 1.1, 
              ax= None, scatter= False, holes= False,
              line_args= {}, scatter_args= {}, hole_args= {}):
    
    if ax is None:
        left_yaxis= plt.gca()
    else:
        left_yaxis = ax

    # Creating the right axis.
    right_yaxis = left_yaxis.twinx()
    
    axes = [left_yaxis, right_yaxis]
    
    # Creating the far right axis if show_rank_axis is True
    if show_rank_axis:
        far_right_yaxis = left_yaxis.twinx()
        axes.append(far_right_yaxis)
    
    for col in df.columns:
        y = df[col]
        x = df.index.values
        # Plotting blank points on the right axis/axes 
        # so that they line up with the left axis.
        for axis in axes[1:]:
            axis.plot(x, y, alpha= 0)

        left_yaxis.plot(x, y, **line_args, solid_capstyle='round')
        
        # Adding scatter plots
        if scatter:
            left_yaxis.scatter(x, y, **scatter_args)
            
            #Adding see-through holes
            if holes:
                bg_color = left_yaxis.get_facecolor()
                left_yaxis.scatter(x, y, color= bg_color, **hole_args)

    # Number of lines
    lines = len(df.columns)

    y_ticks = [*range(1, lines + 1)]
    
    # Configuring the axes so that they line up well.
    for axis in axes:
        axis.invert_yaxis()
        axis.set_yticks(y_ticks)
        axis.set_ylim((lines + 0.5, 0.5))
    
    # Sorting the labels to match the ranks.
    left_labels = df.iloc[0].sort_values().index
    right_labels = df.iloc[-1].sort_values().index
    
    left_yaxis.set_yticklabels(left_labels)
    right_yaxis.set_yticklabels(right_labels)
    
    # Setting the position of the far right axis so that it doesn't overlap with the right axis
    if show_rank_axis:
        far_right_yaxis.spines["right"].set_position(("axes", rank_axis_distance))
    
    return axes

def plotbumpChart(countries,presolvers,cresolvers):
	# data = {"Quad9":[1,3,3,1],"Regional_2":[2,4,5,2],"Regional_1":[3,5,1,5],"Cloudflare":[4,1,2,3],"Google":[5,2,4,4]}
	# fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2)
	# axes=[ax1,ax2,ax3,ax4]
	days=["day1","day2","day3","day4","day5","day6"]
	j=0
	for day in days:
		resRankedPerCountry={}
		resToRankMap={}
		resolverRankingPerSite={}
		resolverWeight={}
		for country in countries:
			allSitesResolutionTime = json.load(open("resTimes/perSiteResolutionTime_"+country+day+".json"))
			medianResTime={}

			resTimePerResolver={}
			for site in allSitesResolutionTime[country]:
				medianResTime[site]={}
				for resolver in allSitesResolutionTime[country][site]:
					if day=="":
						medianResTime[site][resolver]=allSitesResolutionTime[country][site][resolver]
					else:
						medianResTime[site][resolver]=min(allSitesResolutionTime[country][site][resolver])
					if resolver not in resTimePerResolver:
						resTimePerResolver[resolver]=[]
					resTimePerResolver[resolver].append(medianResTime[site][resolver])

			rankedResolvers={}

			for res in resTimePerResolver:
				rankedResolvers[res]=statistics.median(resTimePerResolver[res])
			# print (country,rankedResolvers)

			sortedRes = sorted(rankedResolvers, key=rankedResolvers.get,reverse=False)
			resRankedPerCountry[country]=sortedRes
			resolverWeight[country]={}
			for site in medianResTime:
				sortedResTimes = sorted(medianResTime[site], key=medianResTime[site].get,reverse=False)
				x=1
				for res in sortedResTimes:
					if res in cresolvers[country]:
						r=1
						for cr in cresolvers[country]:
							if res==cr:
								ind=r
							r+=1
						_res="R_"+str(ind)
					else:
						_res=res
					if _res not in resolverWeight[country]:
						resolverWeight[country][_res]={}
					topx="top-"+str(x)
					if topx not in resolverWeight[country][_res]:
						resolverWeight[country][_res][topx]=0
					resolverWeight[country][_res][topx]+=1
					x+=1

		print (resRankedPerCountry,"\n\n")


		resRankPerCountry={}
		for country in resRankedPerCountry:
			resRankPerCountry[country]={}
			i=1
			for res in resRankedPerCountry[country]:
				if res in cresolvers[country]:
					r=1
					for cr in cresolvers[country]:
						if res==cr:
							ind=r
						r+=1
					_res="R_"+str(ind)
				else:
					_res=res
				resRankPerCountry[country][_res]=i
				i+=1

		# print(resRankPerCountry)

		rankPerResolver={}
		for res in resRankPerCountry["US"]:
			rankPerResolver[res]=[]
			for country in resRankPerCountry:
				rankPerResolver[res].append(resRankPerCountry[country][res])


		for country in resolverWeight:
			for res in resolverWeight[country]:
				for i in range(1,5):
					if "top-"+str(i) not in resolverWeight[country][res]:
						resolverWeight[country][res]["top-"+str(i)]=0

			
		print(rankPerResolver)

		for country in countries:
			print (country,resolverWeight[country],"\n\n")


		df = pd.DataFrame(rankPerResolver, index=countries)

	# plt.figure(figsize=(12, 5))
	# fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2)


		# bumpchart(resolverWeight,day,df,axes[j],j,show_rank_axis= True,scatter= True, holes= False,
	 #          line_args= {"linewidth": 5, "alpha": 0.5}, scatter_args= {"s": 50, "alpha": 0.8}) ## bump chart class with nice examples can be found on github
		# axes[j].set_title("day"+str(j+1))
		# if j==0:
		# 	axes[j].get_yaxis().tick_left()
		# elif j==1:
		# 	axes[j].get_yaxis().tick_right()
		# elif j==2:
		# 	axes[j].get_yaxis().tick_left()
		# 	axes[j].get_xaxis().tick_bottom()
		# elif j==3:
		# 	axes[j].get_yaxis().tick_right()
		# 	axes[j].get_xaxis().tick_bottom()
		plt.figure(figsize=(12, 5))
		bumpchart(df, show_rank_axis= True, scatter= True, holes= False,
	          line_args= {"linewidth": 5, "alpha": 0.5}, scatter_args= {"s": 100, "alpha": 0.8}) ## bump chart class with nice examples can be found on github
		plt.savefig(day)
		plt.clf()


		
		j+=1

	# bumpchart(resolverWeight,df, show_rank_axis= True, scatter= True, holes= False,
	#           line_args= {"linewidth": 5, "alpha": 0.5}, scatter_args= {"s": 50, "alpha": 0.8})


	# plt.show()
	# j=0
	# for ax in fig.get_axes():
	# 	ax.label_outer()
	# 	# if j==0:
	# 	# 	axes[j].get_yaxis().tick_left()
	# 	# elif j==1:
	# 	# 	axes[j].get_yaxis().tick_right()
	# 	# elif j==2:
	# 	# 	axes[j].get_yaxis().tick_left()
	# 	# 	axes[j].get_xaxis().tick_bottom()
	# 	# elif j==3:
	# 	# 	axes[j].get_yaxis().tick_right()
	# 	# 	axes[j].get_xaxis().tick_bottom()
	# 	# print (j)
	# for j in range(4):
	# 	if j%2==1:
	# 		axes[j].tick_params(
	# 		    axis='y',          # changes apply to the x-axis
	# 		    which='both',      # both major and minor ticks are affected
	# 		    right=True,      # ticks along the bottom edge are off
	# 		    labelright=True) # labels along the bottom edge are off
	# 	if j%2==0:
	# 		axes[j].tick_params(
	# 		    axis='y',          # changes apply to the x-axis
	# 		    which='both',      # both major and minor ticks are affected
	# 		    right=False,      # ticks along the bottom edge are off
	# 		    labelright=False) # labels along the bottom edge are off


	# plt.savefig("days")

	# fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2)
	# fig.suptitle('Sharing x per column, y per row')
# 	ax1.plot(x, y)
# 	ax2.plot(x, y**2, 'tab:orange')
# 	ax3.plot(x, -y, 'tab:green')
# 	ax4.plot(x, -y**2, 'tab:red')

# for ax in fig.get_axes():
#     ax.label_outer()

def plotbumpChartPerSite(countries,presolvers,cresolvers):
	# data = {"Quad9":[1,3,3,1],"Regional_2":[2,4,5,2],"Regional_1":[3,5,1,5],"Cloudflare":[4,1,2,3],"Google":[5,2,4,4]}
	# fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2)
	# axes=[ax1,ax2,ax3,ax4]
	days=["day1","day2","day3","day4","day5","day6"]
	# days=[]
	j=0
	for day in days:
		resRankedPerCountry={}
		resToRankMap={}
		resolverRankingPerSite={}
		resolverWeight={}
		resolverPerSite={}
		for country in countries:
			allSitesResolutionTime = json.load(open("resTimes/perSiteResolutionTime_"+country+day+".json"))
			medianResTime={}

			resTimePerResolver={}
			for site in allSitesResolutionTime[country]:
				medianResTime[site]={}
				for resolver in allSitesResolutionTime[country][site]:
					# if day=="":
					# 	medianResTime[site][resolver]=allSitesResolutionTime[country][site][resolver]
					# else:
					medianResTime[site][resolver]=min(allSitesResolutionTime[country][site][resolver])
					if resolver not in resTimePerResolver:
						resTimePerResolver[resolver]=[]
					resTimePerResolver[resolver].append(medianResTime[site][resolver])

			rankedResolvers={}

			for res in resTimePerResolver:
				rankedResolvers[res]=statistics.median(resTimePerResolver[res])
			# print (country,rankedResolvers)

			# sortedRes = sorted(rankedResolvers, key=rankedResolvers.get,reverse=False)
			# resRankedPerCountry[country]=sortedRes
			# resolverWeight[country]={}
			resolverPerSite[country]={}
			for site in medianResTime:
				resolverPerSite[country][site]=[]
				sortedResTimes = sorted(medianResTime[site], key=medianResTime[site].get,reverse=False)
				# print (country,site,sortedResTimes)
				x=1
				sortedRes=[]
				for res in sortedResTimes:
					if res in cresolvers[country]:
						r=1
						for cr in cresolvers[country]:
							if res==cr:
								ind=r
							r+=1
						_res="R_"+str(ind)
					else:
						_res=res
					sortedRes.append(_res)
				resolverPerSite[country][site]=sortedRes
					# if _res not in resolverWeight[country]:
					# 	resolverWeight[country][_res]={}
					# topx="top-"+str(x)
					# if topx not in resolverWeight[country][_res]:
					# 	resolverWeight[country][_res][topx]=0
					# resolverWeight[country][_res][topx]+=1
					# x+=1

		# print (resRankedPerCountry,"\n\n")
		print (resolverPerSite.keys(),"\n\n")

		resRankPerSite={}
		for site in resolverPerSite['US']:
			i=1
			resRankPerSite[site]={}
			for res in resolverPerSite['US'][site]:
				resRankPerSite[site][res]=i
				i+=1

		rankPerResolver={}
		for res in resRankPerSite["google.com"]:
			rankPerResolver[res]=[]
			for site in resRankPerSite:
				rankPerResolver[res].append(resRankPerSite[site][res])
			print (day,res,len(rankPerResolver[res]))

		# for country in resRankedPerCountry:
		# 	resRankPerCountry[country]={}
		# 	i=1
		# 	for res in resRankedPerCountry[country]:
		# 		if res in cresolvers[country]:
		# 			r=1
		# 			for cr in cresolvers[country]:
		# 				if res==cr:
		# 					ind=r
		# 				r+=1
		# 			_res="R_"+str(ind)
		# 		else:
		# 			_res=res
		# 		resRankPerCountry[country][_res]=i
		# 		i+=1

		# resRankPerCountry={}
		# for country in resRankedPerCountry:
		# 	resRankPerCountry[country]={}
		# 	i=1
		# 	for res in resRankedPerCountry[country]:
		# 		if res in cresolvers[country]:
		# 			r=1
		# 			for cr in cresolvers[country]:
		# 				if res==cr:
		# 					ind=r
		# 				r+=1
		# 			_res="R_"+str(ind)
		# 		else:
		# 			_res=res
		# 		resRankPerCountry[country][_res]=i
		# 		i+=1

		# # print(resRankPerCountry)

		# rankPerResolver={}
		# for res in resRankPerCountry["US"]:
		# 	rankPerResolver[res]=[]
		# 	for country in resRankPerCountry:
		# 		rankPerResolver[res].append(resRankPerCountry[country][res])


		# for country in resolverWeight:
		# 	for res in resolverWeight[country]:
		# 		for i in range(1,5):
		# 			if "top-"+str(i) not in resolverWeight[country][res]:
		# 				resolverWeight[country][res]["top-"+str(i)]=0

			
		print(day,rankPerResolver,"\n\n")

		# for country in countries:
		# 	print (country,resolverWeight[country],"\n\n")


		df = pd.DataFrame(rankPerResolver, index=[i for i in range(50)])
		fig = plt.figure()

		fig.set_size_inches(15, 5)
		# plt.figure(figsize=(12, 5))
		bumpchart(df, show_rank_axis= True, scatter= True, holes= False,
	          line_args= {"linewidth": 5, "alpha": 0.5}, scatter_args= {"s": 20, "alpha": 0.8}) ## bump chart class with nice examples can be found on github
		plt.rcParams["figure.figsize"] = (40,3)
		plt.savefig(day+"perSite")
		plt.clf()


		

if __name__ == "__main__":
	presolvers=["8.8.8.8","1.1.1.1","9.9.9.9"]
	# cresolvers={"US":["68.87.68.162","208.67.222.222","208.67.220.220","156.154.71.1","74.82.42.42"],
	# "AR":["190.151.144.21","170.150.153.222","170.80.173.44","200.110.130.194","181.16.234.72"],
	# "DE":["46.182.19.48","81.27.162.100","159.69.114.157","195.243.214.4","84.200.69.80"],
	# "IN":["202.134.52.105","182.19.95.34","61.95.143.59","203.201.60.12","164.100.138.248"]}

	cresolvers={"US":["208.67.222.222","208.67.220.220"],
	"AR":["190.151.144.21","170.150.153.222"],
	"DE":["46.182.19.48","159.69.114.157"],
	"IN":["182.19.95.34","111.93.163.56"]}
	
	country="IN"
	resolvers=presolvers+cresolvers[country]
	# runResolutionTimes(resolvers,"day6")
	# analyseResolutionTimes(resolvers,country)
	countries=["US","IN","AR","DE"]
	# plotbumpChart(countries,presolvers,cresolvers)
	plotbumpChartPerSite(countries,presolvers,cresolvers)



