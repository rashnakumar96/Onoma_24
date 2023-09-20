//go:generate go get -u github.com/alexthemonk/DoH_Proxy/
//go:generate go get -u github.com/kardianos/osext/
//go:generate go get -u github.com/kardianos/service/
//go:generate go get -u github.com/miekg/dns/
//go:generate go get -u github.com/sirupsen/logrus/
//go:generate go get -u go.mongodb.org/mongo-driver/mongo
//go:generate go get -u gopkg.in/natefinch/lumberjack.v2
//go:generate go get github.com/bobesa/go-domain-util/domainutil
//go:generate go get -u github.com/bits-and-blooms/bloom

package main

import (
	"bufio"
	"encoding/json"
	"flag"
	"fmt"
	"hash/fnv"
	"io"
	"io/ioutil"
	"math/rand"
	"net"
// 	"net/http"
	"net/url"
	"os"
	"os/exec"
	"os/signal"
	"path"
	"path/filepath"
	"reflect"
	"runtime"
	"strconv"
	"strings"
	"syscall"
	"time"

	// "namehelp/network"

	"namehelp/reporter"

	"namehelp/handler"
	"namehelp/utils"

	"github.com/kardianos/osext"
	"github.com/kardianos/service"
	"github.com/miekg/dns"
	log "github.com/sirupsen/logrus"
	"gopkg.in/natefinch/lumberjack.v2"
	bloom "github.com/bits-and-blooms/bloom"
	domainutil "github.com/bobesa/go-domain-util/domainutil"
)

var backupHosts = []string{}

var signalChannel chan os.Signal

// Config contains the configuration specifications
type Config struct {
	Name        string
	DisplayName string
	Version     string
	APIURL      string
	BinURL      string
	DiffURL     string
	UpdateDir   string
	Description string
}

// Program of Namehelp
type Program struct {
	clientID        string
	country         string
	oldDNSServers   map[string][]string
	dnsQueryHandler *handler.DNSQueryHandler
	tcpServer       *dns.Server
	udpServer       *dns.Server
	// smartDNSSelector *SmartDNSSelector
	stopHeartBeat chan bool
	shutdownChan  chan bool
	reporter      *reporter.Reporter
}

var appConfig = Config{
	Name:        "namehelp",
	DisplayName: "namehelp",
	Version:     "0.0.2",
	APIURL:      "https://aquarium.aqualab.cs.northwestern.edu/",
	BinURL:      "https://aquarium.aqualab.cs.northwestern.edu/",
	DiffURL:     "https://aquarium.aqualab.cs.northwestern.edu/",
	UpdateDir:   "update/",
	Description: "Namehelp is a background service that improves web performance" +
		" and reliability through better DNS resolution. " +
		"Developed by AquaLab at Northwestern University.",
}

// NewProgram initialize a new namehelp program
func NewProgram() *Program {
	var program *Program = &Program{}
	program.stopHeartBeat = make(chan bool)
	program.shutdownChan = make(chan bool)

	program.initializeReporter()

	// Get client IP info
// 	url := "http://ipinfo.io/json"
// 	resp, err := http.Get(url)
// 	if err != nil {
// 		log.Fatal(err)
// 	}
// 	defer resp.Body.Close()
// 	body, readErr := ioutil.ReadAll(resp.Body)
// 	if readErr != nil {
// 		log.Fatal(readErr)
// 	}
// 	jsonMap := make(map[string]interface{})
//
// 	jsonErr := json.Unmarshal(body, &jsonMap)
// 	if jsonErr != nil {
// 		log.Fatal(jsonErr)
// 	}
//
// 	country, ok := jsonMap["country"].(string)
// 	if ok {
// 		log.WithFields(log.Fields{
// 			"country": jsonMap["country"]}).Info("Namehelp: Country code")
// 	} else {
// 		url := "https://extreme-ip-lookup.com/json"
// 		resp, err := http.Get(url)
// 		if err != nil {
// 			log.Fatal(err)
// 		}
// 		defer resp.Body.Close()
// 		body, readErr := ioutil.ReadAll(resp.Body)
// 		if readErr != nil {
// 			log.Fatal(readErr)
// 		}
// 		jsonMap := make(map[string]interface{})
//
// 		jsonErr := json.Unmarshal(body, &jsonMap)
// 		if jsonErr != nil {
// 			log.Fatal(jsonErr)
// 		}
//
// 		country, ok = jsonMap["countryCode"].(string)
// 		if ok {
// 			log.WithFields(log.Fields{
// 				"country": jsonMap["countryCode"]}).Info("Namehelp: Country code")
// 		} else {
// 			log.Fatal("Failed to get country code")
// 		}
// 	}
// 	program.country = country
//
// 	clientIP := jsonMap["ip"].(string)
    program.country = "US"
    clientIP:=""
	as, err := program.getMacAddr()
	if err != nil {
		log.Fatal(err)
	}
	clientMAC := ""
	for _, a := range as {
		clientMAC = clientMAC + a
	}
	program.clientID = strconv.FormatUint(uint64(hash(clientIP+clientMAC)), 10)

	log.WithFields(log.Fields{
		"client_id": program.clientID}).Info("Client Initialized")

	return program
}

var namehelpProgram *Program
var srcDir string

// init is called before main when starting a program.
// intializes loggers
func init() {
	// Configures the log settings in this function.
	//
	// Optional example: Log as JSON instead of the default ASCII formatter.
	// log.SetFormatter(&log.JSONFormatter{})

	// You can also use lumberjack to set up rollling logs.
	// Can either output logs to stdout or lumberjack. Pick one, comment out the other.
	exe, err := osext.Executable()
	if err != nil {
		panic(err)
	}
	exeDir := path.Dir(exe)
	ljack := &lumberjack.Logger{
		Filename:   filepath.Join(exeDir, appConfig.Name+".log"),
		MaxSize:    1, // In megabytes.
		MaxBackups: 3,
		MaxAge:     3, // In days (0 means keep forever?)
	}
	mw := io.MultiWriter(os.Stdout, ljack)
	log.SetOutput(mw)
	log.SetFormatter(&log.TextFormatter{ForceColors: true})
	// Only log the Info level or above.
	log.SetLevel(log.InfoLevel)

	srcDir = path.Dir(path.Dir(exeDir))
	namehelpProgram = NewProgram()

}

// Start is the Service.Interface method invoked when run with "--service start"
func (program *Program) Start(s service.Service) error {

	log.WithFields(log.Fields{"app": appConfig.Name}).
		Debug("Namehelp: program.Start(service) invoked.")

	// Start() should return immediately. Kick off async execution.
	go program.run()
	return nil
}

// Stop is the Service.Interface method invoked when run with "--service stop"
func (program *Program) Stop(s service.Service) error {

	// Stop should not block. Return with a few seconds.
	log.Debug("Namehelp: program.Stop(service) invoked")
	go func() {
		for signalChannel == nil {
			// Make sure that shutdown channel has been initilized.
		}
		log.Info("Namehelp: Sending SIGINT on signalChannel")
		signalChannel <- syscall.SIGINT
	}()

	return nil
}

// run is the main process running
func (program *Program) run() {
	// Starting the heartbeat
	go program.heartbeat(3600)

	log.Debug("Namehelp: program.run() invoked.")
	rand.Seed(time.Now().UTC().UnixNano())
	log.Info("Namehelp: Starting app.")

	// Capture and handle Ctrl-C signal
	signalChannel = make(chan os.Signal)
	signal.Notify(signalChannel, syscall.SIGINT, syscall.SIGTERM)

	err := program.launchNamehelpDNSServer()
	if err != nil {
		log.WithFields(log.Fields{"error": err.Error()}).Error("Namehelp: Failed to launch namehelp.  Error: [%s]\nShutting down.")
		// TODO shut self down gracefully (including Aquarium)
	}

	// Switch DNS server to 127.0.0.1 (use namehelp as DNS server)
	// save the old configuration for restoration at stopping
	program.oldDNSServers = program.saveCurrentDNSConfiguration()
	networkInterfaces := reflect.ValueOf(program.oldDNSServers).MapKeys()
	// get slice of keys
	program.setDNSServer(utils.LOCALHOST, backupHosts, networkInterfaces)

	// program.smartDNSSelector = NewSmartDNSSelector()
	// going off to the new locally started DNS server for namehelp
	// go program.smartDNSSelector.routine_Do()

	// TODO run aquarium measurements

	log.Info("Namehelp: Waiting for signal from signalChannel (blocking)")

	thisSignal := <-signalChannel

	log.WithFields(log.Fields{
		"signal": thisSignal.String()}).Info("Namehelp: Signal received")

	// restore original DNS settings
	program.restoreOldDNSServers(program.oldDNSServers)
	// save user's top sites to file
	// program.dnsQueryHandler.topSites.SaveUserSites()

	log.Info("Namehelp: Shutdown complete. Exiting.")
	program.shutdownChan <- true
}

func (program *Program) initializeReporter() {
	program.reporter = reporter.NewReporter(appConfig.Version)
}

func (program *Program) initializeDNSServers() {
	// dns library requires a handler function for the ServeMux
	program.dnsQueryHandler = handler.NewHandler(program.oldDNSServers)

	tcpRequestMultiplexer := dns.NewServeMux()
	tcpRequestMultiplexer.HandleFunc(".", program.dnsQueryHandler.DoTCP)

	udpRequestMultiplexer := dns.NewServeMux()
	udpRequestMultiplexer.HandleFunc(".", program.dnsQueryHandler.DoUDP)

	rTimeout := 5 * time.Second
	wTimeout := 5 * time.Second
	dnsServerAddress := utils.LOCALHOST + ":" + strconv.Itoa(utils.PORT)

	program.tcpServer = &dns.Server{
		Addr:         dnsServerAddress,
		Net:          "tcp",
		Handler:      tcpRequestMultiplexer,
		ReadTimeout:  rTimeout,
		WriteTimeout: wTimeout}

	program.udpServer = &dns.Server{
		Addr:         dnsServerAddress,
		Net:          "udp",
		Handler:      udpRequestMultiplexer,
		UDPSize:      65535,
		ReadTimeout:  rTimeout,
		WriteTimeout: wTimeout}
}

func (program *Program) launchNamehelpDNSServer() error {

	testingDir := filepath.Join("analysis", "measurements", program.country)
	for {
		if _, err := os.Stat(filepath.Join(srcDir, testingDir, "publicDNSServers.json")); os.IsNotExist(err) {
			// To ensure proper exit during testing
			select {
			case <-signalChannel:
				os.Exit(0)
				break
			default:
				time.Sleep(time.Second)
				// fmt.Println("Waiting on", filepath.Join(srcDir, testingDir, "publicDNSServers.json"))
				continue
			}
		} else {
			log.Info("Namehelp: publicDNSServers FileFound")
			break
		}
	}
	jsonFile, err := os.Open(filepath.Join(srcDir, testingDir, "publicDNSServers.json"))
	if err != nil {
	    log.WithFields(log.Fields{
	    "error": err,
        "filename": filepath.Join(srcDir, testingDir, "publicDNSServers.json")}).Info("Namehelp: error opening file")
// 		log.Info("Namehelp: error opening file: " + filepath.Join(srcDir, testingDir, "publicDNSServers.json"))
	}
	defer jsonFile.Close()
	byteValue, _ := ioutil.ReadAll(jsonFile)
	var publicDNSServers []string
	json.Unmarshal([]byte(byteValue), &publicDNSServers)
	log.WithFields(log.Fields{
		"publicDNSServers": publicDNSServers}).Info("Namehelp: These are the public DNS servers")
	handler.PDNSServers = publicDNSServers

	program.initializeDNSServers()
//     load top500 sites in bloom filter and top50 to randomly pick from in privacy enabled setting
//     topAlexaSites := filepath.Join(srcDir,"Top500sites.txt")
    filter := bloom.NewWithEstimates(50, 0.0001)
//     _file, err := os.OpenFile(topAlexaSites,os.O_RDONLY,0777)
//     if err != nil {
//         log.Fatal(err)
//
//     }

//     scanner := bufio.NewScanner(_file)
//     count:=0
//     var websites []string
//     for scanner.Scan() {
//         website := scanner.Text()
// //     	filter.Add([]byte(seconded))
//         if count<50{
//             websites = append(websites, website)
//         }
//         count+=1
//     }
//     _file.Close()
    websites:= []string{"google.com", "youtube.com", "tmall.com", "qq.com", "sohu.com", "taobao.com", "baidu.com",
    "360.cn", "jd.com", "amazon.com", "facebook.com", "wikipedia.org", "yahoo.com", "weibo.com", "sina.com.cn",
    "xinhuanet.com", "netflix.com", "live.com", "reddit.com", "alipay.com", "instagram.com", "google.com.hk",
    "zhanqi.tv", "panda.tv", "vk.com", "zoom.us", "microsoft.com", "csdn.net", "twitch.tv", "yahoo.co.jp",
    "myshopify.com", "bongacams.com", "office.com", "okezone.com", "yy.com", "aliexpress.com", "ebay.com",
     "huanqiu.com", "naver.com", "aparat.com", "amazon.in", "tianya.cn", "bing.com", "amazon.co.jp", "twitter.com",
     "adobe.com", "17ok.com", "microsoftonline.com", "chaturbate.com", "ok.ru", "yandex.ru"}

     websites500:=[]string{"google.com", "youtube.com", "tmall.com", "qq.com", "sohu.com", "taobao.com", "baidu.com",
      "360.cn", "jd.com", "amazon.com", "facebook.com", "wikipedia.org", "yahoo.com", "weibo.com", "sina.com.cn", "xinhuanet.com",
       "netflix.com", "live.com", "reddit.com", "alipay.com", "instagram.com", "google.com.hk", "zhanqi.tv", "panda.tv", "vk.com", "zoom.us", "microsoft.com", "csdn.net",
        "twitch.tv", "yahoo.co.jp", "myshopify.com", "bongacams.com", "office.com", "okezone.com", "yy.com", "aliexpress.com", "ebay.com", "huanqiu.com", "naver.com", "aparat.com", "amazon.in",
        "tianya.cn", "bing.com", "amazon.co.jp", "twitter.com", "adobe.com", "17ok.com", "microsoftonline.com", "chaturbate.com", "ok.ru", "yandex.ru", "whatsapp.com", "so.com", "haosou.com",
        "wordpress.com", "fandom.com", "1688.com", "linkedin.com", "mail.ru", "imdb.com", "pornhub.com", "google.com.br", "xvideos.com", "msn.com", "google.co.in", "gome.com.cn", "etsy.com",
        "xhamster.com", "roblox.com", "babytree.com", "udemy.com", "rakuten.co.jp", "hao123.com", "canva.com", "livejasmin.com", "alibaba.com", "tiktok.com", "google.co.jp", "primevideo.com",
        "indeed.com", "dropbox.com", "tribunnews.com", "google.de", "6.cn", "paypal.com", "chase.com", "flipkart.com", "savefrom.net", "espn.com", "kompas.com", "walmart.com", "booking.com", "spotify.com",
        "freepik.com", "bbc.com", "imgur.com", "cnblogs.com", "amazon.de", "163.com", "zillow.com", "telegram.org", "rednet.cn", "stackoverflow.com", "kumparan.com", "amazon.co.uk", "ettoday.net",
        "apple.com", "duckduckgo.com", "google.fr", "google.es", "force.com", "bilibili.com", "google.ru", "amazonaws.com", "nytimes.com", "github.com", "pikiran-rakyat.com", "digikala.com", "salesforce.com", "detik.com", "daum.net", "cnn.com", "slack.com", "grammarly.com", "google.com.sg", "google.it", "nih.gov", "instructure.com", "tumblr.com", "metropoles.com", "indiatimes.com", "godaddy.com", "cowin.gov.in", "soundcloud.com", "pixnet.net", "bbc.co.uk", "51.la", "cnzz.com", "healthline.com", "bet9ja.com", "jiameng.com", "pinterest.com", "youm7.com", "zhihu.com", "researchgate.net", "varzesh3.com", "ilovepdf.com", "amazon.ca", "craigslist.org", "tistory.com", "tokopedia.com", "speedtest.net", "theguardian.com", "bet365.com", "homedepot.com", "hotstar.com", "51yes.com", "stackexchange.com", "wetransfer.com", "pixabay.com", "bestbuy.com", "wix.com", "hulu.com", "ltn.com.tw", "tudou.com", "momoshop.com.tw", "w3schools.com", "soso.com", "notion.so", "archive.org", "xnxx.com", "chess.com", "google.com.tw", "coursera.org", "telewebion.com", "tradingview.com", "coinmarketcap.com", "binance.com", "shutterstock.com", "etoro.com", "mediafire.com", "intuit.com", "avito.ru", "smallpdf.com", "lazada.sg", "steamcommunity.com", "asana.com", "zendesk.com", "iqbroker.com", "asos.com", "manoramaonline.com", "google.co.uk", "wellsfargo.com", "investing.com", "cnet.com", "google.com.tr", "coingecko.com", "y2mate.com", "airbnb.com", "vimeo.com", "disneyplus.com", "americanexpress.com", "liputan6.com", "ebay.de", "suara.com", "yelp.com", "globo.com", "google.ca", "videocampaign.co", "onlinesbi.com", "okta.com", "chouftv.ma", "cnnic.cn", "googlevideo.com", "grid.id", "slideshare.net", "deepl.com", "investopedia.com", "trendyol.com", "sogou.com", "forbes.com", "target.com", "gosuslugi.ru", "google.com.sa", "wikihow.com", "capitalone.com", "amazon.fr", "360.com", "spankbang.com", "get-express-vpn.online", "quizlet.com", "washingtonpost.com", "discord.com", "fc2.com", "manage.wix.com", "fiverr.com", "ikea.com", "proiezionidiborsa.it", "wayfair.com", "namnak.com", "in.gr", "sonhoo.com", "namu.wiki", "gmw.cn", "google.com.mx", "1stepdownload.com", "sindonews.com", "remove.bg", "redfin.com", "hdfcbank.com", "google.com.eg", "exchain.ai", "realtor.com", "evernote.com", "shein.com", "zerodha.com", "google.pl", "sq.cn", "mozilla.org", "icloud.com", "redd.it", "douban.com", "taboola.com", "formula1.com", "japanpost.jp", "thepiratebay.org", "behance.net", "ca.gov", "uol.com.br", "businessinsider.com", "sciencedirect.com", "donya-e-eqtesad.com", "shaparak.ir", "zol.com.cn", "blogger.com", "mercadolibre.com.ar", "wildberries.ru", "amazon.es", "sahibinden.com", "setn.com", "yandex.com", "scribd.com", "academia.edu", "google.co.th", "dailymail.co.uk", "twimg.com", "usps.com", "google.com.ar", "sberbank.ru", "lowes.com", "op.gg", "weather.com", "aliexpress.ru", "dailymotion.com", "t.me", "gismeteo.ru", "skype.com", "agacelebir.com", "rezka.ag", "t.co", "hbomax.com", "crunchyroll.com", "elwatannews.com", "rt.com", "ibicn.com", "foxnews.com", "1337x.to", "marca.com", "ebay.co.uk", "bukalapak.com", "coinbase.com", "allegro.pl", "qoo10.sg", "patreon.com", "samsung.com", "fast.com", "pinimg.com", "mercadolivre.com.br", "worldometers.info", "nike.com", "merdeka.com", "aol.com", "liansuo.com", "padlet.com", "linktr.ee", "shippingchina.com", "dribbble.com", "ih5.cn", "icicibank.com", "reverso.net", "yts.mx", "tutorialspoint.com", "rakuten.com", "ladbible.com", "orange.fr", "livescore.com", "tripadvisor.com", "genius.com", "namasha.com", "hp.com", "ask.com", "alwafd.news", "cnbc.com", "idntimes.com", "chegg.com", "ozon.ru", "shopee.tw", "ny.gov", "babyschool.com.cn", "costco.com", "ouedkniss.com", "iyiou.com", "fedex.com", "thestartmagazine.com", "cloudfront.net", "moneycontrol.com", "softonic.com", "squarespace.com", "google.co.id", "xfinity.com", "nba.com", "goodreads.com", "biobiochile.cl", "medium.com", "onlyfans.com", "dbs.com.sg", "wikimedia.org", "eghtesadnews.com", "rctiplus.com", "ninisite.com", "ria.ru", "rambler.ru", "ikco.ir", "thesaurus.com", "dspultra.com", "blackboard.com", "hotmart.com", "kompas.tv", "cambridge.org", "gmx.net", "wholeactualjournal.com", "divar.ir", "clickpost.jp", "360doc.com", "akamaized.net", "kakao.com", "dcard.tw", "crowdworks.jp", "cnbeta.com", "ameblo.jp", "quora.com", "prothomalo.com", "crunchbase.com", "google.co.kr", "dell.com", "stripchat.com", "uniswap.org", "shopee.co.id", "line.me", "ebay-kleinanzeigen.de", "eee114.com", "irs.gov", "premierleague.com", "atlassian.com", "teachable.com", "meituan.com", "citi.com", "bankofamerica.com", "cnnindonesia.com", "gogoanime.ai", "amazon.it", "laodong.vn", "springer.com", "zhibo8.cc", "bp.blogspot.com", "epicgames.com", "eluniverso.com", "google.com.au", "flashscore.com", "9gag.com", "trustpilot.com", "58.com", "coursehero.com", "albawabhnews.com", "infobae.com", "yt1s.com", "rutracker.org", "mlb.com", "nicovideo.jp", "uptodown.com", "web.de", "shopee.com.my", "eatthis.com", "breitbart.com", "wish.com", "eghtesadonline.com", "coupang.com", "258.com", "indiamart.com", "brilio.net", "gusuwang.com", "ai.marketing", "filimo.com", "9384.com", "ebc.net.tw", "alodokter.com", "google.ro", "nextdoor.com", "baixarfilmetorrent.net", "naukri.com", "elpais.com", "iqiyi.com", "google.gr", "outbrain.com", "runoob.com", "weebly.com", "kundelik.kz", "jpnn.com", "macys.com", "google.co.ve", "canada.ca", "11st.co.kr", "glassdoor.com", "chaduo.com", "ensonhaber.com", "sourceforge.net", "vnexpress.net", "kooora.com", "oschina.net", "viva.co.id", "matchesfashion.com", "clickfunnels.com", "tinyurl.is", "eksisozluk.com", "91jm.com", "reuters.com", "as.com", "creditkarma.com", "google.com.ua", "wiley.com", "kontan.co.id", "google.com.vn", "chinanetrank.com", "dostor.org", "khanacademy.org", "expedia.com", "fidelity.com", "onizatop.net", "t66y.com", "lenta.ru", "creditchina.gov.cn", "att.com", "patch.com", "wordpress.org", "webmd.com", "kakaku.com", "oracle.com", "onet.pl", "britannica.com", "trello.com", "cdc.gov"}


    for _, website := range websites500 {
        secondld:=domainutil.DomainPrefix(website)
        filter.Add([]byte(secondld))
    }
    handler.Top50Websites = websites
    handler.Filter=*filter
    log.WithFields(log.Fields{
            "bloomfilter": *filter,
            "top50Sites": websites}).Info("Namehelp: These are the top 50 sites")

	// start DNS servers for UDP and TCP requests
	go program.startDNSServer(program.udpServer)
	go program.startDNSServer(program.tcpServer)
	// this go func does the testing as soon as SubRosa is started
	// TODO: change this to per-trigger base

	//run SubRosa with No Privacy Enabled,but Racing enabled(SubRosaNP) until measurements start
	handler.DNSDistribution=make(map[string][]int64)
	handler.DNSDistributionPerformance=make(map[string][]string)

	handler.DNSTime=0
	handler.DoHEnabled = true
	handler.Experiment = false
	handler.Decentralized = true
	utils.FlushLocalDnsCache()
	handler.ResolverMapping=make(map[string][]string)
	handler.PrivacyEnabled = false
	handler.Racing = true
	program.dnsQueryHandler.EnableDirectResolution()
	handler.Proxy = false
	handler.DoHServersToTest = []string{"127.0.0.1"}

	//convert client id to string
// 	go program.doMeasurement(testingDir, program.clientID) //uncomment this for the experiment with individual resolvers
	return nil
}

func (program *Program) runTests(resolverName string, ip string, dir string, testingDir string) {
	utils.FlushLocalDnsCache()

	log.WithFields(log.Fields{
		"resolver name": resolverName,
		"ip":            ip,
		"dir":           dir,
		"testing dir":   testingDir}).Info("Namehelp: Namehelp run tests")
	if !handler.Experiment {
		handler.DoHServersToTest = []string{"127.0.0.1"}
	}
	if handler.DoHEnabled && handler.Experiment {
		handler.DoHServersToTest = []string{resolverName}
	} else if !handler.DoHEnabled && handler.Experiment {
		handler.DNSServersToTest = []string{ip}
	}

	//this for loop ensures that ServersToTest is resolverName till we collect all measurements with this resolverName
	//and file filepath.Join(srcDir, testingDir)+"/lighthouseTTBresolverName.json" is made in the directory
	utils.FlushLocalDnsCache()
	log.WithFields(log.Fields{
		"dir": filepath.Join(dir, "lighthouseTTB"+resolverName+"_.json")}).Info("Namehelp: Confirming Directory")

	for {
		if _, err := os.Stat(filepath.Join(dir, "lighthouseTTB"+resolverName+"_.json")); os.IsNotExist(err) {
			time.Sleep(time.Second)
			continue
		} else {
			log.Info("Namehelp: FileFound")
			break
		}
	}
	log.Info("Namehelp: Done Testing " + resolverName)

}

// func (program *Program) MeasureDnsLatencies(resolverName string, ip string, dir string, dict1 map[string]map[string]map[string]interface{}, dnsLatencyFile []string, iterations int, testingDir string) {
func (program *Program) MeasureDnsLatencies(resolverName string, ip string, dir string, dict1 map[string]interface{}, dnsLatencyFile []string, iterations int, testingDir string) {
	utils.FlushLocalDnsCache()
	log.WithFields(log.Fields{"resolver": resolverName}).Info("Namehelp: Measuring DNS latency")
	var err error
	if !handler.Experiment {
		handler.DoHServersToTest = []string{"127.0.0.1"}
	}
	if handler.DoHEnabled && handler.Experiment {
		handler.DoHServersToTest = []string{resolverName}
	} else if !handler.DoHEnabled && handler.Experiment {
		handler.DNSServersToTest = []string{ip}
	}
	handler.DNSDistribution=make(map[string][]int64)
	handler.DNSDistributionPerformance=make(map[string][]string)

	handler.DNSTime=0
	dict1, err = program.dnsQueryHandler.MeasureDnsLatencies(0, dnsLatencyFile, 0, handler.DoHEnabled, handler.Experiment, iterations, dict1, resolverName)
	file, _ := json.MarshalIndent(handler.DNSDistributionPerformance, "", " ")
	_ = ioutil.WriteFile(filepath.Join(dir, "DNSDistributionPerformance2.json"), file, 0644)

	file, _ = json.MarshalIndent(handler.DNSDistribution, "", " ")
	_ = ioutil.WriteFile(filepath.Join(dir, "DNSDistribution2.json"), file, 0644)

	if err != nil {
		log.WithFields(log.Fields{
			"error": err}).Info("Namehelp: DNS Latency Command produced error")
	}
	log.WithFields(log.Fields{
		"dnsLatencyFile: ": filepath.Join(dir, "dnsLatencies.json")}).Info("Namehelp: Write DNS latency result to file")
}

func (program *Program) DnsLatenciesSettings(dir string, testingDir string, publicDNSServers []string, client_id string,dict1 map[string]interface{},websites []string,feature string) {
	log.WithFields(log.Fields{"dir": dir, "testing dir": testingDir}).Info("Namehelp: Setting up for DNS latency testing")

	// dict1 := make(map[string]map[string]map[string]interface{})
	// dict1 := make(map[string]interface{})

	iterations := 3
	if feature=="SubRosa"{
		handler.DoHEnabled = true
		handler.Experiment = false
		handler.Decentralized = true
		handler.PrivacyEnabled=true
		handler.Racing=true
		program.dnsQueryHandler.EnableDirectResolution()
		handler.Proxy=false
		handler.DoHServersToTest=[]string{"127.0.0.1"}
		utils.FlushLocalDnsCache()
		handler.ResolverMapping=make(map[string][]string)
		// program.MeasureDnsLatencies("SubRosa", "", filepath.Join(srcDir, testingDir), dict1,websites, iterations, testingDir)

		return
	}

	handler.Experiment = true
	program.dnsQueryHandler.EnableExperiment()
	handler.Proxy = false
	program.dnsQueryHandler.DisableProxy()

	program.dnsQueryHandler.DisableDirectResolution()

	handler.PrivacyEnabled = false
	program.dnsQueryHandler.DisablePrivacy()
	handler.Racing = false
	program.dnsQueryHandler.DisableRacing()
	handler.Decentralized = false
	program.dnsQueryHandler.DisableDecentralization()
	handler.DoHEnabled = true
	// program.MeasureDnsLatencies("Google", "", filepath.Join(srcDir, testingDir), dict1, websites, iterations, testingDir)
	// program.MeasureDnsLatencies("Cloudflare", "", filepath.Join(srcDir, testingDir), dict1, websites, iterations, testingDir)
	// program.MeasureDnsLatencies("Quad9", "", filepath.Join(srcDir, testingDir), dict1, websites, iterations, testingDir)
	handler.DoHEnabled = false
	program.dnsQueryHandler.DisableDoH()

	for i := 0; i < len(publicDNSServers); i++ {
		// program.MeasureDnsLatencies(publicDNSServers[i], publicDNSServers[i], filepath.Join(srcDir, testingDir), dict1, websites, iterations, testingDir)
	}
	handler.PDNSServers = publicDNSServers

	handler.DoHEnabled = true
	program.dnsQueryHandler.EnableDoH()
	handler.Experiment = false
	program.dnsQueryHandler.DisableExperiment()
	handler.Decentralized = true
	program.dnsQueryHandler.EnableDecentralization()

	program.dnsQueryHandler.DisableDirectResolution()

	handler.Proxy = true
	program.dnsQueryHandler.EnableProxy()
	handler.PrivacyEnabled = false
	program.dnsQueryHandler.DisablePrivacy()
	handler.Racing = false
	program.dnsQueryHandler.DisableRacing()

	utils.FlushLocalDnsCache()
	handler.DoHServersToTest = []string{"127.0.0.1"}
	// program.MeasureDnsLatencies("DoHProxyNP", "", filepath.Join(srcDir, testingDir), dict1, websites, iterations, testingDir)

	// handler.PrivacyEnabled=true
	// handler.Racing=true
	// utils.FlushLocalDnsCache()
	// program.dnsQueryHandler.EnableDirectResolution()
	// handler.Proxy=false
	// handler.DoHServersToTest=[]string{"127.0.0.1"}
	// handler.ResolverMapping=make(map[string][]string)
	// program.MeasureDnsLatencies("SubRosa", "", filepath.Join(srcDir, testingDir), dict1,websites, iterations, testingDir)

	utils.FlushLocalDnsCache()

	handler.PrivacyEnabled = false
	program.dnsQueryHandler.DisablePrivacy()
	handler.Racing = false
	program.dnsQueryHandler.DisableRacing()

	program.dnsQueryHandler.EnableDirectResolution()

	handler.Proxy = false
	program.dnsQueryHandler.DisableProxy()

	handler.DoHServersToTest = []string{"127.0.0.1"}
	// program.MeasureDnsLatencies("SubRosaNPR", "", filepath.Join(srcDir, testingDir), dict1, websites, iterations, testingDir)

	utils.FlushLocalDnsCache()

	handler.PrivacyEnabled = false
	program.dnsQueryHandler.DisablePrivacy()
	handler.Racing = true
	program.dnsQueryHandler.EnableRacing()

	program.dnsQueryHandler.EnableDirectResolution()

	handler.Proxy = false
	program.dnsQueryHandler.DisableProxy()

	handler.DoHServersToTest = []string{"127.0.0.1"}
	program.MeasureDnsLatencies("SubRosaNP", "", filepath.Join(srcDir, testingDir), dict1, websites, iterations, testingDir)

	dict1["country"] = program.country
	dict1["clientID"] = program.clientID
	program.reporter.PushToMongoDB("SubRosa-Test", "dnsLatencies_"+program.country, dict1)
}

func (program *Program) getMacAddr() ([]string, error) {
	ifas, err := net.Interfaces()
	if err != nil {
		return nil, err
	}
	var as []string
	for _, ifa := range ifas {
		a := ifa.HardwareAddr.String()
		if a != "" {
			as = append(as, a)
		}
	}
	return as, nil
}

func hash(s string) uint32 {
	h := fnv.New32a()
	h.Write([]byte(s))
	return h.Sum32()
}

func (program *Program) doMeasurement(testingDir string, client_id string) error {

	handler.DNSDistribution=make(map[string][]int64)
	handler.DNSTime=0
	for {
		if _, err := os.Stat(filepath.Join(srcDir, "dat")); os.IsNotExist(err) {
			time.Sleep(time.Second)
			continue
		} else {
			log.Info("FileFound")
			break
		}
	}

	log.WithFields(log.Fields{"testing dir": testingDir}).Info("Namehelp: Namehelp start measurement")

	publicDNSServers := handler.PDNSServers

	//Measuring Pings to Resolvers
	dict2 := make(map[string]interface{})
	// dohresolvers := []string{"8.8.8.8", "9.9.9.9", "1.1.1.1"}
	// iterations := 3
	// resolverList := append(publicDNSServers, dohresolvers...)
	// dict2 = program.dnsQueryHandler.PingServers(handler.DoHEnabled, handler.Experiment, iterations, dict2, resolverList)
	// file, _ := json.MarshalIndent(dict2, "", " ")
	// _ = ioutil.WriteFile(filepath.Join(srcDir, testingDir, "pingServers.json"), file, 0644)

	// Measuring DNSLatencies and Pings to Replicas
	dnsLatencyFile := filepath.Join(srcDir, testingDir, "AlexaUniqueResources.txt")
	websiteFile:=dnsLatencyFile
	log.WithFields(log.Fields{"dir": websiteFile}).Info("Handler: Loading website file")
	_file, err := os.Open(websiteFile)
	if err != nil {
		log.Fatal(err)
	}

	scanner := bufio.NewScanner(_file)
	count:=0
	var websites []string
	for scanner.Scan() {
		// measure latencies of 100 resources
		// if len(websites)==50{
		if count==100{
			break

		}
		count+=1
		website := scanner.Text()
		u, err := url.Parse(website)
		if err != nil {
			log.Fatal("Handler: Error Parsing website", err)
		}
		if err := scanner.Err(); err != nil {
			log.Fatal("Handler: Error while scanning for website", err)
		}
		found := 0
		for _, ele := range websites {
			if ele == u.Hostname() {
			// if ele == u.String(){
				found = 1
			}
		}
		if found == 0 {
			websites = append(websites, u.Hostname())
			// websites = append(websites, u.String())
		}
	}
	_file.Close()
	handler.ResolverMapping = make(map[string][]string)
	dict1:=make(map[string]interface{})
	program.DnsLatenciesSettings(srcDir, testingDir, publicDNSServers,client_id,dict1,websites,"")


	d1 := []byte("start Lighthouse Measurements\n")
	err = ioutil.WriteFile(filepath.Join(srcDir, "dat1"), d1, 0644)
	if err != nil {
		log.WithFields(log.Fields{
			"error": err}).Info("Namehelp: couldn't start measurements")
		panic(err)
	}

	//handler.Proxy is true when testing DoHProxy
	//handler.Racing is true when testing racing in SubRosa
	//handler.PrivacyEnabled is true when testing SubRosa and DoHProxy with privacy enabled, and all same 2lds go to the same resolver
	//EnableDirectResolution allows SubRosa to do DR, we disable with other approaches

	// //for testing individual resolvers it's true, for testing DoHProxy and SubRosa it's false
	handler.Experiment = true
	program.dnsQueryHandler.EnableExperiment()
	// //for testing DoH resolvers

	// //resolver mapping dict for privacy setting
	handler.ResolverMapping = make(map[string][]string)

	// //stores all measurements
	outPath := filepath.Join(srcDir, testingDir)
	if _, err := os.Stat(outPath); os.IsNotExist(err) {
		os.Mkdir(outPath, 0755)
	}
	if err != nil {
		log.Info("Namehelp: Error getting current working directory")
	}

	handler.Proxy = false
	program.dnsQueryHandler.DisableProxy()

	program.dnsQueryHandler.DisableDirectResolution()

	handler.PrivacyEnabled = false
	program.dnsQueryHandler.DisablePrivacy()
	handler.Racing = false
	program.dnsQueryHandler.DisableRacing()
	handler.Decentralized = false
	program.dnsQueryHandler.DisableDecentralization()
	handler.DoHEnabled = true
	program.dnsQueryHandler.EnableDoH()

	program.runTests("Google", "", filepath.Join(srcDir, testingDir), testingDir)
	log.Info("Namehelp: Namehelp finish Google")
	program.runTests("Cloudflare", "", filepath.Join(srcDir, testingDir), testingDir)
	log.Info("Namehelp: Namehelp finish Cloudflare")
	program.runTests("Quad9", "", filepath.Join(srcDir, testingDir), testingDir)
	log.Info("Namehelp: Namehelp finish Quad9")

	handler.DoHEnabled = false
	program.dnsQueryHandler.DisableDoH()

	///testing publicDns servers
	//publicDNSServers.json file should have ips of public DNS servers of a country to test
	for i := 0; i < len(publicDNSServers); i++ {
		program.runTests(publicDNSServers[i], publicDNSServers[i], filepath.Join(srcDir, testingDir), testingDir)
	}
	handler.PDNSServers = publicDNSServers
	log.Info("Namehelp: Namehelp finished publicDNSServers")
	// Done testing them
	//////////////////

	handler.DoHEnabled = true
	program.dnsQueryHandler.EnableDoH()
	handler.Experiment = false
	program.dnsQueryHandler.DisableExperiment()
	handler.Decentralized = true
	program.dnsQueryHandler.EnableDecentralization()

	program.dnsQueryHandler.DisableDirectResolution()

	handler.Proxy = true
	program.dnsQueryHandler.EnableProxy()

	// //testing DoHProxy with Privacy Enabled
	// handler.PrivacyEnabled=true
	// handler.Proxy=true
	// utils.FlushLocalDnsCache()
	// handler.DoHServersToTest=[]string{"127.0.0.1"}
	// dict1, err = program.dnsQueryHandler.MeasureDnsLatencies(0,dnsLatencyFile,0,handler.DoHEnabled,handler.Experiment,iterations,dict1,"DoHProxy")
	// file,_=json.MarshalIndent(dict1, "", " ")
	// _ = ioutil.WriteFile(filepath.Join(srcDir, testingDir)+"/dnsLatencies.json", file, 0644)

	// //these for loops ensure that DoHServersToTest is DoHProxy with Privacy enabled (but new resolver mapping dict btw each run)
	// // till we collect all measurements with this resolver
	// //and file filepath.Join(srcDir, testingDir)+"/lighthouseTTBDoHProxy.json" is made in the directory
	// utils.FlushLocalDnsCache()
	// for{
	// 	if _, err := os.Stat(filepath.Join(srcDir, testingDir)+"/lighthouseTTBDoHProxy0.json"); os.IsNotExist(err) {
	// 		continue
	// 	}else{
	// 		break
	// 	}
	// }

	// handler.ResolverMapping=make(map[string][]string)
	// for{
	// 	if _, err := os.Stat(filepath.Join(srcDir, testingDir)+"/lighthouseTTBDoHProxy1.json"); os.IsNotExist(err) {
	// 		continue
	// 	}else{
	// 		break
	// 	}
	// }
	// handler.ResolverMapping=make(map[string][]string)
	// for{
	// 	if _, err := os.Stat(filepath.Join(srcDir, testingDir)+"/lighthouseTTBDoHProxy.json"); os.IsNotExist(err) {
	// 		continue
	// 	}else{
	// 		break
	// 	}
	// }
	// log.Info("Done Testing DoHProxy")

	//testing DoHProxy with No Privacy Enabled(DoHProxyNP)
	handler.PrivacyEnabled = false
	program.dnsQueryHandler.DisablePrivacy()
	handler.Racing = false
	program.dnsQueryHandler.DisableRacing()

	utils.FlushLocalDnsCache()
	handler.DoHServersToTest = []string{"127.0.0.1"}
	program.runTests("DoHProxyNP", "", filepath.Join(srcDir, testingDir), testingDir)

	//select best resolvers stored
	jsonFile, err := os.Open(filepath.Join(srcDir, testingDir, "bestResolvers.json"))
	if err != nil {
		log.Info("error opening file: " + filepath.Join(srcDir, testingDir, "bestResolvers.json"))
	}
	defer jsonFile.Close()
	byteValue, _ := ioutil.ReadAll(jsonFile)
	var bestResolvers []string
	json.Unmarshal([]byte(byteValue), &bestResolvers)
	log.WithFields(log.Fields{
		"bestResolvers": bestResolvers}).Info("These are the best public DNS resolvers")
	handler.BestResolvers = bestResolvers


	// //testing SubRosa with Privacy Enabled and Racing
	handler.PrivacyEnabled=true
	handler.Racing=true
	utils.FlushLocalDnsCache()
	program.dnsQueryHandler.EnableDirectResolution()
	handler.Proxy=false
	handler.DoHServersToTest=[]string{"127.0.0.1"}

	// program.DnsLatenciesSettings(srcDir, testingDir, publicDNSServers,client_id,dict1,websites,"SubRosa")
	handler.ResolverMapping=make(map[string][]string)
	utils.FlushLocalDnsCache()


	// // //these for loops ensure that DoHServersToTest is SubRosa with Privacy enabled & Racing (but new resolver mapping dict btw each run)
	// // // till we collect all measurements with this resolver
	// // //and file filepath.Join(srcDir, testingDir)+"/lighthouseTTBSubRosa.json" is made in the directory
	// // utils.FlushLocalDnsCache()
	for{
		if _, err := os.Stat(filepath.Join(srcDir, testingDir)+"/lighthouseTTBSubRosa0.json"); os.IsNotExist(err) {
			continue
		}else{
			break
		}
	}
	handler.ResolverMapping=make(map[string][]string)
	for{
		if _, err := os.Stat(filepath.Join(srcDir, testingDir)+"/lighthouseTTBSubRosa1.json"); os.IsNotExist(err) {
			continue
		}else{
			break
		}
	}
	handler.ResolverMapping=make(map[string][]string)
	for{
		if _, err := os.Stat(filepath.Join(srcDir, testingDir)+"/lighthouseTTBSubRosa_.json"); os.IsNotExist(err) {
			continue
		}else{
			break
		}
	}
	log.Info("Done Testing SubRosa")

	//testing SubRosa with No Privacy Enabled and No Racing Enabled(SubRosaNPR)
	utils.FlushLocalDnsCache()

	handler.PrivacyEnabled = false
	program.dnsQueryHandler.DisablePrivacy()
	handler.Racing = false
	program.dnsQueryHandler.DisableRacing()

	program.dnsQueryHandler.EnableDirectResolution()

	handler.Proxy = false
	program.dnsQueryHandler.DisableProxy()

	handler.DoHServersToTest = []string{"127.0.0.1"}
	program.runTests("SubRosaNPR", "", filepath.Join(srcDir, testingDir), testingDir)

	//testing SubRosa with No Privacy Enabled,but Racing enabled(SubRosaNP)
	utils.FlushLocalDnsCache()

	handler.PrivacyEnabled = false
	program.dnsQueryHandler.DisablePrivacy()
	handler.Racing = true
	program.dnsQueryHandler.EnableRacing()

	program.dnsQueryHandler.EnableDirectResolution()

	handler.Proxy = false
	program.dnsQueryHandler.DisableProxy()

	handler.DoHServersToTest = []string{"127.0.0.1"}
	program.runTests("SubRosaNP", "", filepath.Join(srcDir, testingDir), testingDir)


	dict2["country"] = program.country
	dict2["clientID"] = program.clientID
	program.reporter.PushToMongoDB("SubRosa-Test", "PingServers_"+program.country, dict2)

	// push resourcesttbbyCDNLighthouse.json to server
	jsonFile, err = os.Open(filepath.Join(srcDir, testingDir, "resourcesttbbyCDNLighthouse.json"))
	if err != nil {
		log.Info("Namehelp: error opening file: " + filepath.Join(srcDir, testingDir, "resourcesttbbyCDNLighthouse.json"))
	}
	defer jsonFile.Close()
	byteValue, _ = ioutil.ReadAll(jsonFile)
	// jsonMap := make(map[string]map[string]map[string]interface{})
	jsonMap := make(map[string]interface{})
	json.Unmarshal([]byte(byteValue), &jsonMap)

	jsonMap["country"] = program.country
	jsonMap["clientID"] = program.clientID
	program.reporter.PushToMongoDB("SubRosa-Test", "resourcesttbbyCDNLighthouse_"+program.country, jsonMap)


	log.Info("Namehelp: Namehelp finish measurement")

	return err
}

// Saves the current system configuration for future restoration
// Returns a map of {networkinterface: <list of old dns servers>}
func (program *Program) saveCurrentDNSConfiguration() (oldDNSServers map[string][]string) {
	log.Info("Namehelp: Saving original DNS configuration.")
	oldDNSServers = make(map[string][]string)

	command := exec.Command("")

	// Command to get network interfaces
	if runtime.GOOS == "darwin" {
		// for MacOS
		command = exec.Command("networksetup", "-listallnetworkservices")
	} else if runtime.GOOS == "linux" {
		// for Linux
		command = exec.Command("iwconfig")
	} else if runtime.GOOS == "windows" {
		// for Windows
		// command = exec.Command(`cmd`, `/C`, "wmic nic get NetConnectionID")
		command = exec.Command(`cmd`, `/C`, "netsh interface show interface")
	}

	output, err := command.Output()
	if err != nil {
		log.WithFields(log.Fields{
			"path":     command.Path,
			"argument": command.Args,
			"error":    err.Error()}).Error("Namehelp: Command produced error.  Returning.")
		return oldDNSServers
	}

	// only for windows
	// since the output of windows is special, we have to convert
	// Admin State    State          Type             Interface Name
	// -------------------------------------------------------------------------
	// Enabled        Disconnected   Dedicated        Ethernet 2
	// Enabled        Connected      Dedicated        Wi-Fi 2
	// To only care connected and remain only “Wi-Fi 2” in this case

	// Detect connected network interfaces for windows
	if runtime.GOOS == "windows" {
		var tmpOutput []byte
		networkInterfaces := strings.Split(string(output), "\n")
		for _, networkInterface := range networkInterfaces {
			strippedString := strings.ToLower(strings.Replace(networkInterface, "-", "", -1))

			//only for windows to check disconnected interface
			if strings.Contains(strippedString, "connected") {
				if strings.Contains(strippedString, "disconnected") {
					continue
				}
				tmp := strings.Split(networkInterface, "    ")
				tmp[5] = strings.Split(tmp[5], "\r")[0]
				tmpInter := []byte(tmp[5])
				tmpOutput = append(tmpOutput, tmpInter...)
				tmpOutput = append(tmpOutput, []byte("\n")...)
			} else {
				continue
			}
		}
		output = tmpOutput
	}

	networkInterfaces := strings.Split(strings.TrimSpace(string(output)), "\n")
	log.WithFields(log.Fields{
		"interface": networkInterfaces}).Info("Namehelp: Network interfaces found")

	// Only focus on wifi and ethernet
	interfaceKeywords := []string{"", ""}
	interfacesToChange := make([]string, len(networkInterfaces))
	if runtime.GOOS == "darwin" {
		// For mac
		interfaceKeywords[0] = "wifi"
		interfaceKeywords[1] = "ethernet"
	} else if runtime.GOOS == "linux" {
		// For linux, enable for now
		// keywords need to be adapted
		interfaceKeywords[0] = "wlp2s0"
		interfaceKeywords[1] = "enp2s0"
		// For linux, enable for now
	} else if runtime.GOOS == "windows" {
		// For windows
		interfaceKeywords[0] = "ethernet"
		interfaceKeywords[1] = "wifi" // Wi-Fi or wi-fi or wifi
		// interfaceKeywords[1] = "wifi 2"// Wi-Fi or wi-fi or wifi
		// interfaceKeywords[2] = "Ethernet"
		// interfaceKeywords[3] = "Wi-Fi"
	}

	// Traverse each interface to get DNS setting for each of them
	counter := 0
	for _, networkInterface := range networkInterfaces {
		log.WithFields(log.Fields{
			"interface": networkInterface,
		}).Debug("Namehelp: traversing interfaces")

		for _, keyword := range interfaceKeywords {
			strippedString := strings.ToLower(strings.Replace(networkInterface, "-", "", -1))

			if strings.Contains(strippedString, keyword) {
				interfacesToChange[counter] = networkInterface
				counter++
			}
		}
	}

	log.WithFields(log.Fields{
		"interface": interfacesToChange}).Debug("Namehelp: These network interfaces will have DNS settings changed")

	for _, networkInterface := range interfacesToChange {
		if networkInterface == "" {
			continue
		}
		command := exec.Command("")
		output := ""
		if runtime.GOOS == "darwin" {
			// For mac, disable for now
			command = exec.Command("networksetup", "-getdnsservers", networkInterface)
			tmp, err := command.Output()
			output = string(tmp)
			if err != nil {
				log.Fatal(err)
			}
		} else if runtime.GOOS == "linux" {
			// For linux, enable for Now
			output = "127.0.0.1"
		} else if runtime.GOOS == "windows" {
			// For windows enable for now
			output = "127.0.0.1"
		}

		var oldServers []string
		if strings.Contains(strings.ToLower(string(output)), "there aren't any dns servers") {
			log.WithFields(log.Fields{
				"interface": networkInterface,
			}).Debug("Namehelp: No DNS servers configured")
			oldServers = []string{"empty"}
		} else {
			oldServers = strings.Split(string(output), "\n")
		}

		oldDNSServers[networkInterface] = make([]string, len(oldServers))
		i := 0
		for _, oldServer := range oldServers {
			oldServer = strings.Replace(oldServer, " ", "", -1)
			if oldServer == "127.0.0.1" || oldServer == "LOCALHOST" || oldServer == "" {
				// don't add localhost to list of oldServers
				log.WithFields(log.Fields{
					"old server": oldServer}).Debug("Namehelp: Skipping oldServer")
				continue
			}
			log.WithFields(log.Fields{
				"old server": oldServer,
				"interface":  networkInterface}).Debug("Namehelp: Saving DNS server for interface.")
			oldDNSServers[networkInterface][i] = oldServer
			i++
		}

		// slice off empty strings
		oldDNSServers[networkInterface] = oldDNSServers[networkInterface][:i]

		// if all else fails, at least save "empty"
		if len(oldDNSServers[networkInterface]) == 0 {
			log.WithFields(log.Fields{
				"interface": networkInterface}).Info("Namehelp: No DNS servers to save.  Saving {'empty'}")
			oldDNSServers[networkInterface] = []string{"empty"}
		}
	}

	log.WithFields(log.Fields{
		"old DNS server": oldDNSServers}).Info("Namehelp: old DNS server saved")
	fmt.Printf("oldDNSServers: %v Length [%d]\n", oldDNSServers, len(oldDNSServers))

	return oldDNSServers
}

// Set DNS servers for wifi and ethernet interfaces
func (program *Program) setDNSServer(primaryDNS string, backupDNSList []string, networkInterfaces []reflect.Value) {
	for _, networkInterface := range networkInterfaces {
		log.WithFields(log.Fields{
			"interface":   networkInterface,
			"primary DNS": primaryDNS,
			"backup DNS":  backupDNSList,
			"OS":          runtime.GOOS,
		}).Info("Namehelp: changing DNS server for interface to primary and backup")

		// "..." flattens the list to use each element as separate argument
		if runtime.GOOS == "darwin" {
			//for mac
			argumentList := append([]string{"-setdnsservers", networkInterface.String(), primaryDNS}, backupDNSList...)
			command := exec.Command("networksetup", argumentList...)

			output, err := command.Output()
			if err != nil {
				log.Fatal(err)
			}

			log.Debug(output)

		} else if runtime.GOOS == "linux" {
			b, err := ioutil.ReadFile("/etc/resolv.conf") // just pass the file name
			if err != nil {
				fmt.Print(err)
			}
			str := string(b)

			var newData = "nameserver 127.0.0.1\n#\n" + str

			d1 := []byte(newData)
			err1 := ioutil.WriteFile("/etc/resolv.conf", d1, 0644)
			if err1 != nil {
				fmt.Println(err)
			}
		} else if runtime.GOOS == "windows" {
			command := exec.Command("cmd", "/C", fmt.Sprintf(" netsh interface ipv4 add dnsservers %q address=127.0.0.1 index=1", networkInterface.String()))
			output, err := command.Output()
			if err != nil {
				log.Fatal(err)
				return
			}
			log.WithFields(log.Fields{"output": output}).Info("Namehelp: Windows IPv4 DNS setting finished")
			command = exec.Command("cmd", "/C", fmt.Sprintf(" netsh interface ipv6 add dnsservers %q address=::1 index=1", networkInterface.String()))
			output, err = command.Output()
			if err != nil {
				log.Fatal(err)
				return
			}
			log.WithFields(log.Fields{"output": output}).Info("Namehelp: Windows IPv6 DNS setting finished")
		}
	}
}

// Restore the DNS settings to previously saved DNS resolvers
func (program *Program) restoreOldDNSServers(oldDNSServers map[string][]string) (err error) {
	err = nil

	if runtime.GOOS == "darwin" {
		for networkInterface, dnsServerList := range oldDNSServers {
			fmt.Printf("dnsServerList [%v] length [%d]\n", dnsServerList, len(dnsServerList))
			argumentList := append([]string{"-setdnsservers", networkInterface}, dnsServerList...)

			fmt.Printf("Running networksetup %v\n", argumentList)
			output, thisError := utils.RunCommand("networksetup", argumentList...)
			if thisError != nil {
				fmt.Printf("output [%s] error [%s]\n", output, thisError.Error())
				err = thisError
			}
		}
	} else if runtime.GOOS == "linux" {
		b, err := ioutil.ReadFile("/etc/resolv.conf") // just pass the file name
		if err != nil {
			fmt.Print(err)
		}
		str := string(b) // convert content to a 'string'

		var newData = ""

		var start = false
		for _, i := range str {
			if start {
				newData += string(i)
			} else if i == '\n' {
				start = true
			}
		}

		d1 := []byte(newData)
		err1 := ioutil.WriteFile("/etc/resolv.conf", d1, 0644)
		if err1 != nil {
			fmt.Println(err)
		}
	} else if runtime.GOOS == "windows" {
		for networkInterface := range oldDNSServers {
			fmt.Println("enter windows restoreDNS")
			command := exec.Command("cmd", "/C", fmt.Sprintf(" netsh interface ipv4 set dnsservers %q dhcp", networkInterface))
			output, err1 := command.Output()
			if err1 != nil {
				log.Fatal(err)
				return err1
			}
			log.Println(output)
		}
	}

	log.Info("Namehelp: DNS setting restored.")
	return err
}

// start the DNS proxy
func (program *Program) startDNSServer(dnsServer *dns.Server) {
	err := dnsServer.ListenAndServe()
	if err != nil {
		log.WithFields(log.Fields{
			"DNS server selected": dnsServer.Net,
			"server address":      dnsServer.Addr,
			"error":               err}).Fatal("Namehelp: Failed to start listener on server")
	}
}

// heatbeat keeps pinging a remote server every given period of interval
func (program *Program) heartbeat(interval int) {
	filter := []interface{}{map[string]interface{}{
		"clientID": program.clientID,
	}}
	ticker := time.NewTicker(time.Duration(interval) * time.Second)
	for {
		select {
		case <-program.stopHeartBeat:
			log.Info("Namehelp: Stopping heartbeat")
			break
		case t := <-ticker.C:
			doc := []interface{}{map[string]interface{}{
				"timeStamp": time.Now().Unix(),
				"country":   program.country,
			}}
			program.reporter.UpdateToMongoDB("SubRosa-Test", "Heartbeats", filter, doc)
			log.WithFields(log.Fields{"time stamp": t}).Info("Namehelp: Sending heartbeat to server")
			break
		}
	}
}

// CleanNamehelp clean up the program
func CleanNamehelp() {
	configFilename := getAbsolutePath("config.json")
	os.Remove(configFilename)
}

// Takes relative path to executable
// Returns the absolute path of the executable
func getAbsolutePath(pathRelativeToExecutable string) string {
	executable, err := osext.Executable()
	if err != nil {
		panic(err)
	}

	path := filepath.Join(path.Dir(executable), pathRelativeToExecutable)
	return path
}

var config service.Config = service.Config{
	Name:        appConfig.Name,
	DisplayName: appConfig.DisplayName,
	Description: appConfig.Description,
}

// normally the program should be started with service flag
func main() {
	// NOTE: before executing main(), namehelpProgram is created at the top of this file.

	// do command-line flag parsing
	serviceFlag := flag.String("service", "", "Control the system service")
	cleanFlag := flag.Bool("cleanup", false, "Clean namehelp config files")
	flag.Parse()

	log.Info("Namehelp: Instantiating service")
	namehelpService, err := service.New(namehelpProgram, &config)
	if err != nil {
		log.WithFields(log.Fields{
			"error": err.Error()}).Fatal("Namehelp: Failed to instantiate service")
	}
	log.Info("Namehelp: Namehelp service instantiated")

	// if service flag specified
	// execute the specific operation
	if len(*serviceFlag) != 0 {
		log.WithFields(log.Fields{
			"flag": *serviceFlag}).Info("Namehelp: Calling service.Control with flag")
		err := service.Control(namehelpService, *serviceFlag)
		log.Info("Namehelp: Returned from service.Control()")

		if err != nil {
			log.WithFields(log.Fields{
				"action": service.ControlAction,
				"error":  err.Error()}).Error("Namehelp: Valid actions with Error")
			log.Fatal(err)
		}
		log.Debug("Namehelp: Calling return")
		return
	}
	if *cleanFlag {
		CleanNamehelp()
		return
	}

	// running without service flag
	// try install the program first
	*serviceFlag = "install"
	err = service.Control(namehelpService, *serviceFlag)
	if err != nil {
		log.WithFields(log.Fields{
			"error": err.Error()}).Error("Namehelp: Namehelp has already been installed")
	}

	// directly executing the program
	err = namehelpService.Run()
	if err != nil {
		log.WithFields(log.Fields{
			"error": err.Error()}).Error("Namehelp: Problem running service")
	}

	// wait for signal from run until shut down completed
	<-namehelpProgram.shutdownChan
	e := os.Remove(filepath.Join(srcDir, "dat"))
	if e != nil {
		log.Info("error removing dat file")
	}
	e = os.Remove(filepath.Join(srcDir, "dat1"))
	if e != nil {
		log.Info("error removing dat1 file")

	}

	*serviceFlag = "uninstall"
	err = service.Control(namehelpService, *serviceFlag)
	if err != nil {
		log.WithFields(log.Fields{
			"error": err.Error()}).Error("Namehelp: Namehelp uninstall failed")
	}

	log.Info("Namehelp: Main exiting...")
}
