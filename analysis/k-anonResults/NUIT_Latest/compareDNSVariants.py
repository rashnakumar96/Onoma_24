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
import numpy as np
import matplotlib


def DNSUDPResolution(site,runs):
	resolutionTimes=[]
	for run in range(runs):
		dns_start = time.time()
		ip_address = socket.gethostbyname(site)
		dns_end = time.time()
		resolutionTimes.append((dns_end - dns_start) * 1000)
	return resolutionTimes


def DNSTorResolution(site,runs):
    resolutionTimes=[]
    for run in range(runs):
        dns_start = time.time()
        subprocess.run(['tor-resolve', site], stdout=subprocess.PIPE).stdout.decode('utf-8')
        #tor-resolve google.com
        dns_end = time.time()
        resolutionTimes.append((dns_end - dns_start) * 1000)
    return resolutionTimes

def compareDNSVariants():
    racing = json.load(open("resResults/ResolutionTime_OnomaRacing.json"))
    sharding = json.load(open("resResults/ResolutionTime_OnomaSharding.json"))
    udp_tor = json.load(open("resResults/ResolutionTimeUDP_Tor.json"))
    udp = json.load(open("resResults/ResolutionTime_UDP.json"))
    google = json.load(open("resResults/ResolutionTime_GoogleDNS.json"))
    quad9 = json.load(open("resResults/ResolutionTime_Quad9DNS.json"))
    cloudflare = json.load(open("resResults/ResolutionTime_CloudflareDNS.json"))


    udp=udp["UDP"]
    tor=udp_tor["Tor"]
    racing=racing["OnomaRacing"]
    sharding=sharding["OnomaSharding"]
    google=google["GoogleDNS"]
    quad9=quad9["Quad9DNS"]
    cloudflare=cloudflare["CloudflareDNS"]


    dnsVariants=[udp,"third_party",racing,sharding,tor]
    colors=["blue","violet","pink","red"]
    i=0
    # variants=["UDPDNS","OnomaRacing","OnomaSharding","ToRDNS"]
    variants=["ISP DNS","Third-Party DNS","Onoma","Sharding","ToR DNS"]

    perfValues={}
    for dnsVariant in dnsVariants:
        data=[]
        # c=colors[i]
        N=0
        if dnsVariant=="third_party":
            for site in google:
                try:
                    resTime=max([max(google[site]),max(quad9[site]),max(cloudflare[site])])
                    # resTime=resTime+10
                    if resTime>5:
                        data.append(resTime)
                        N+=1
                except:
                    continue
        else:
            for site in dnsVariant:
                try:
                    resTime=max(dnsVariant[site])
                    # if dnsVariant!=tor:
                    #     resTime=resTime*10
                    if resTime>5:
                        data.append(resTime)
                        N+=1
                except:
                    continue
        perfValues[variants[i]]=data
        i+=1
    #     print (variants[i],statistics.median(data))
    #     x = np.sort(data)
    #     y = np.arange(N) / float(N)
    #     plt.plot(x, y, marker='o',color=c,label=variants[i])
    #     i+=1
    # plt.xlabel("DNS Resolution Times")
    # # plt.xlim([0,1])
    # plt.xscale('log')
    # plt.ylabel("CDF")
    # plt.legend()
    # plt.title('CDF using sorting the data')
    # plt.savefig("resResults/compareDNSPerf")

    # plt.show()
    return perfValues

def compareDNSPerfandPrivacy():
    # perf=[18,21,51,200]
    privacy=[12,12,51,100,100]
    variants=["ISP DNS","Third-Party DNS","Sharding","ToR DNS","Onoma"]
    colors=["blue","yellow","violet","red","green"]
    perf=compareDNSVariants()
    print (perf.keys())

    # i=0
    # for variant in variants:
    #     plt.scatter(perf[variant],[privacy[i] for x in range(len(perf[variant]))],marker='x',color=colors[i],label=variant)
    #     i+=1
    # plt.xlabel('Performance (ms)')
    # plt.xscale('log')

    # plt.ylabel("K-anonymity (%)")
    # plt.legend()
    # # plt.title('CDF using sorting the data')
    # plt.savefig("resResults/compareDNSPerfandPrivacy")

    data=[perf[variants[i]] for i in range(len(variants))]
    print (data)
    # data=[]
    for i in range(len(data)):
        print (variants[i],len(data[i]))
    #     data.append(perf[variants[i]])
     
    fig = plt.figure(figsize =(10, 7))
    ax = fig.add_subplot(111)
     
    # Creating axes instance
    bp = ax.boxplot(data, patch_artist = True,
                    notch ='True', vert = 0)
     
    # colors = ['#0000FF', '#00FF00',
    #           '#FFFF00', '#FF00FF']
     
    for patch, color in zip(bp['boxes'], colors):
        patch.set_facecolor(color)
     
    # changing color and linewidth of
    # whiskers
    for whisker in bp['whiskers']:
        whisker.set(color ='#8B008B',
                    linewidth = 1.5,
                    linestyle =":")
     
    # changing color and linewidth of
    # caps
    for cap in bp['caps']:
        cap.set(color ='#8B008B',
                linewidth = 2)
     
    # changing color and linewidth of
    # medians
    for median in bp['medians']:
        median.set(color ='purple',
                   linewidth = 3)
     
    # changing style of fliers
    for flier in bp['fliers']:
        flier.set(marker ='D',
                  color ='#e7298a',
                  alpha = 0.5)
    # num_boxes = len(data)
    # pos = np.arange(num_boxes) + 1
    # # upper_labels = [str(round(s, 2)) for s in medians]
    # weights = ['bold', 'semibold']
    # for tick, label in zip(range(num_boxes), ax.get_xticklabels()):
    #     k = tick
    #     print ("tick",k)
    #     ax.text(pos[tick],privacy[tick]+20, variants[tick],
    #          horizontalalignment='center')
    import math

    k=0
    x=[]
    for element in ['medians']:
        for line in bp[element]:
            # Get the position of the element. y is the label you want
            (x_l, y),(x_r, _) = line.get_xydata()
            # Make sure datapoints exist 
            # (I've been working with intervals, should not be problem for this case)
            if not np.isnan(y): 
                x_line_center = x_l + (x_r - x_l)/2
                y_line_center = y  # Since it's a line and it's horisontal
                # overlay the value:  on the line, from center to right
                x_shift=0.15*x_line_center
                print (variants[k],x_line_center,x_shift,y_line_center)
                x.append(x_line_center)
                ax.text(x_line_center-x_shift, (y_line_center-0.25), # Position
                        variants[k], # Value (3f = 3 decimal float)
                        verticalalignment='center', # Centered vertically with line 
                        fontsize=15)
                k+=1
    # x-axis labels
    ax.set_yticklabels(privacy)
    # ax.set_yticklabels(['data_1', 'data_2',
    #                     'data_3', 'data_4'])
     
    # Adding title
    # plt.title("Customized box plot")
     
    # Removing top axes and right axes
    # ticks
    ax.get_xaxis().tick_bottom()
    ax.get_yaxis().tick_left()
    # ax.legend([bp["boxes"][0], bp["boxes"][1],bp["boxes"][2],bp["boxes"][3],bp["boxes"][4]], variants, loc='lower right')
    # plt.xscale('log')
    ax.set_xscale('log')
    # plt.ylim(max(privacy), min(privacy))
    ax.set_xticks([10,100,500])
    ax.get_xaxis().set_major_formatter(matplotlib.ticker.ScalarFormatter())
    # ax.xaxis([1, 10000, 1, 100000])
    # ax.loglog()
    ax.set_ylim(ax.get_ylim()[::-1])
    plt.xlabel('DNS Resolution Time (ms)')

    plt.ylabel("K-anonymity (%) - (inverted axis)")

    plt.savefig("resResults/compareDNSPerfandPrivacy")


if __name__ == "__main__":
    top500Sites = json.load(open("alexaTop500SitesCountries.json"))
    runs=3

    if not os.path.exists("resResults"):
        os.mkdir("resResults")
    allSitesResolutionTime={}
    # allSitesResolutionTime["OnomaSharding"]={}
    # allSitesResolutionTime["OnomaRacing"]={}
    allSitesResolutionTime["UDP"]={}
    # allSitesResolutionTime["Tor"]={}
    # allSitesResolutionTime["GoogleDNS"]={}
    # allSitesResolutionTime["Quad9DNS"]={}
    # allSitesResolutionTime["CloudflareDNS"]={}


    top50 = top500Sites["US"][:50]

    i=0
    for site in top50:
        print (100*i/50,"sites done")
        i+=1
        # try:
        #     resolutionTime=DNSUDPResolution(site,runs)
        #     allSitesResolutionTime["UDP"][site]=resolutionTime
        # except Exception as e:
        #     print (site,str(e))
        # try:
        #     resolutionTime=DNSUDPResolution(site,runs)
        #     allSitesResolutionTime["GoogleDNS"][site]=resolutionTime
        # except Exception as e:
        #     print (site,str(e))
        # try:
        #     resolutionTime=DNSUDPResolution(site,runs)
        #     allSitesResolutionTime["Quad9DNS"][site]=resolutionTime
        # except Exception as e:
        #     print (site,str(e))
        # try:
        #     resolutionTime=DNSUDPResolution(site,runs)
        #     allSitesResolutionTime["CloudflareDNS"][site]=resolutionTime
        # except Exception as e:
        #     print (site,str(e))
        # try:
        #     resolutionTime=DNSTorResolution(site,runs)
        #     allSitesResolutionTime["Tor"][site]=resolutionTime
        # except Exception as e:
        #     print (site,str(e))

        # run onoma with only sharding enabled and test this function
        # try:
        #     resolutionTime=DNSUDPResolution(site,runs)
        #     allSitesResolutionTime["OnomaSharding"][site]=resolutionTime
        # except Exception as e:
        #     print (site,str(e))

        # run onoma with  sharding and Racing enabled and test this function

    #     try:
    #         resolutionTime=DNSUDPResolution(site,runs)
    #         allSitesResolutionTime["OnomaRacing"][site]=resolutionTime
    #     except Exception as e:
    #         print (site,str(e))
    # with open("resResults/ResolutionTime_UDP.json", 'w') as fp: 
    #     json.dump(allSitesResolutionTime, fp)

    # compareDNSVariants()
    compareDNSPerfandPrivacy()