// based heavily upon github.com/kenshinx/godns/hosts.go

package hosts

import (
	"bufio"
	"net"
	"os"
	"regexp"
	"strings"
	"sync"
	"time"

	"namehelp/settings"
	"namehelp/utils"
)

// Hosts defines object for file host
type Hosts struct {
	fileHosts       *FileHosts
	refreshInterval time.Duration
}

// NewHosts initializes and returns a new Hosts object
func NewHosts(hs settings.HostsSettings) Hosts {
	fileHosts := &FileHosts{
		file:  hs.HostsFile,
		hosts: make(map[string]string),
	}

	hosts := Hosts{fileHosts, time.Second * time.Duration(hs.RefreshInterval)}
	hosts.refresh()
	return hosts
}

// Get matches local /etc/hosts file first, remote redis records second
func (h *Hosts) Get(domain string, family int) ([]net.IP, bool) {

	var sips []string
	var ip net.IP
	var ips []net.IP

	sips, _ = h.fileHosts.Get(domain)

	if sips == nil {
		return nil, false
	}

	for _, sip := range sips {
		switch family {
		case utils.IP4Query:
			ip = net.ParseIP(sip).To4()
		case utils.IP6Query:
			ip = net.ParseIP(sip).To16()
		default:
			continue
		}
		if ip != nil {
			ips = append(ips, ip)
		}
	}

	return ips, (ips != nil)
}

// refresh updates hosts records from /etc/hosts file and redis per minute
func (h *Hosts) refresh() {
	ticker := time.NewTicker(h.refreshInterval)
	go func() {
		for {
			h.fileHosts.Refresh()

			<-ticker.C
		}
	}()
}

// FileHosts object represents the relation between host and file
type FileHosts struct {
	file  string
	hosts map[string]string
	mu    sync.RWMutex
}

// Get return the hosts of the provided file domain
func (f *FileHosts) Get(domain string) ([]string, bool) {
	domain = strings.ToLower(domain)
	f.mu.RLock()
	ip, ok := f.hosts[domain]
	f.mu.RUnlock()
	if !ok {
		return nil, false
	}
	return []string{ip}, true
}

// Refresh updates hosts records
func (f *FileHosts) Refresh() {
	buf, err := os.Open(f.file)
	if err != nil {
		//logger.Warningf("Update hosts records from file failed %s", err)
		return
	}
	defer buf.Close()

	f.mu.Lock()
	defer f.mu.Unlock()

	f.clear()

	scanner := bufio.NewScanner(buf)
	for scanner.Scan() {

		line := scanner.Text()
		line = strings.TrimSpace(line)

		if strings.HasPrefix(line, "#") || line == "" {
			continue
		}

		sli := strings.Split(line, " ")
		if len(sli) == 1 {
			sli = strings.Split(line, "\t")
		}

		if len(sli) < 2 {
			continue
		}

		domain := sli[len(sli)-1]
		ip := sli[0]
		if !f.isDomain(domain) || !f.isIP(ip) {
			continue
		}

		f.hosts[strings.ToLower(domain)] = ip
	}
	//logger.Infof("update hosts records from %s", f.file)
}

// clear clean up the file hosts
func (f *FileHosts) clear() {
	f.hosts = make(map[string]string)
}

// isDomain checkes whether the given domain is a valid domain
func (f *FileHosts) isDomain(domain string) bool {
	if f.isIP(domain) {
		return false
	}
	match, _ := regexp.MatchString(`^([a-zA-Z0-9\*]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,6}$`, domain)
	return match
}

// isIP checks whether the given ip is a valid ip
func (f *FileHosts) isIP(ip string) bool {
	return (net.ParseIP(ip) != nil)
}
