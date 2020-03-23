// based heavily upon github.com/kenshinx/godns/settings.go

package settings

//"flag"
//"fmt"
//"os"
//
//"github.com/BurntSushi/toml"
//
//"path"
//"path/filepath"
//"github.com/kardianos/osext"

var (
	// NamehelpSettings is the global setting variable
	NamehelpSettings Settings
)

// Settings specifies program setups
type Settings struct {
	Version      string
	Debug        bool
	Server       DNSServerSettings `toml:"server"`
	ResolvConfig ResolvSettings    `toml:"resolv"`
	Log          LogSettings       `toml:"log"`
	Cache        CacheSettings     `toml:"cache"`
	Hosts        HostsSettings     `toml:"hosts"`
}

// ResolvSettings specifies settings for resolution
type ResolvSettings struct {
	ResolvFile string `toml:"resolv-file"`
	Timeout    int
	Interval   int // must be strictly greater than 0
}

// LogSettings specifies settings for logger
type LogSettings struct {
	Stdout bool
	Level  string
}

// DNSServerSettings specifies settings for DNS server
type DNSServerSettings struct {
	Host string
	Port int
}

// CacheSettings specifies settings for cache
type CacheSettings struct {
	Backend  string
	Expire   int
	Maxcount int
}

// HostsSettings specifies settings for hosts
type HostsSettings struct {
	Enable          bool
	HostsFile       string `toml:"host-file"`
	RedisEnable     bool   `toml:"redis-enable"`
	RedisKey        string `toml:"redis-key"`
	TTL             uint32 `toml:"ttl"`
	RefreshInterval uint32 `toml:"refresh-interval"`
}

func init() {

	//executable, err := osext.Executable()
	//if err != nil {
	//	panic(err)
	//}
	//
	//var configFile string = filepath.Join(path.Dir(executable), "namehelp.conf")
	//
	////flag.StringVar(&configFile, "c", "namehelp.conf", "Look for namehelp toml-formatting config file in this directory")
	////flag.Parse()
	//
	//if _, err := toml.DecodeFile(configFile, &NamehelpSettings); err != nil {
	//	fmt.Printf("%s is not a valid toml config file\n", configFile)
	//	fmt.Println(err)
	//	os.Exit(1)
	//}

	NamehelpSettings.Version = "2.0.0"
	NamehelpSettings.Debug = false
	NamehelpSettings.Server = DNSServerSettings{
		"127.0.0.1",
		53,
	}
	NamehelpSettings.ResolvConfig = ResolvSettings{
		"/etc/resolv.conf",
		5,
		1, // delay in ms between asking multiple DNS servers for the same query, TODO hard-code this?
	}

	NamehelpSettings.Log = LogSettings{
		Stdout: false,
		Level:  "DEBUG",
	}
	NamehelpSettings.Cache = CacheSettings{
		"memory",
		600,
		0,
	}
	NamehelpSettings.Hosts = HostsSettings{
		true,
		"/etc/hosts",
		false,
		"",
		600,
		5,
	}

}
