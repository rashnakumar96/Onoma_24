import time
import json
import os
import sys
import threading
import urllib.request
import getpass
import traceback
import urllib.parse
import atexit
from pathlib import Path

"""
python py.py [2_letter_country_code] [VPN auth file] [VPN config file]
"""

def get_config(key=None, defval=None, blankOK=False):
    cf = {}

    file = get_path('config/config.json')
    if os.path.exists(file):
        with open(file) as inf:
            cf = json.load(inf)

    if key:
        val = cf.get(key, defval)

        if blankOK:
            return val
        else:
            if val is None or len(val) is 0:
                return defval
            else:
                return val
    else:
        return cf


def sys_ipinfo():
    s = urllib.request.urlopen("http://ipinfo.io/json").read()
    return json.loads(s)

def connect_vpn():
    if not auto_vpn():
        return

    print("Killing any existing OpenVPN...")
    kill_vpn()

    current_ip = sys_ipinfo()['ip']
    print("Current IP %s" % current_ip)
    print("Connecting OpenVPN (on mac sudo required!)...")
    print("If you did not already, quit now and prefix command with sudo, to avoid keep getting prompted for password")

    launch_vpn()

    time.sleep(3)

    ok = False

    for k in range(0, 3):
        time.sleep(3)
        ip = sys_ipinfo()['ip']
        if current_ip != ip:
            ok = True
            print("Connection established as IP %s" % ip)
            break

    if not ok:
        print("Failed to connect to VPN. Check nohup log. Did you sudo? Aborting!")
        raise Exception("Failed to connect to VPN. Check nohup log. Did you sudo? Aborting!")


def sudo(s):
    os.system("sudo %s" % s)


def auto_vpn():
    return len(sys.argv) >= 3

def kill_vpn():
    if not auto_vpn():
        return

    sudo("killall openvpn")
    time.sleep(2)


def launch_vpn():
    """ Note that on mac, need to 'brew install openvpn' and 'brew cask install tuntap' and allow in Sec Pref. """
    # openvpn command binary path
    bin = "/usr/local/sbin/openvpn"
    config = sys.argv[3]
    auth = sys.argv[2]

    sudo("nohup %s --remap-usr1 SIGHUP --resolv-retry 3 --config %s --auth-user-pass %s &" % (bin, config, auth))


def main():
    ok = False
    tries = 3
    ts = time.time()

    do_crawl()
    te = time.time() - ts

    print("Finished")


def do_crawl():
    nation = sys.argv[1]

    if auto_vpn():
        connect_vpn()
    else:
        input("Ensure VPN connected for location '%s', then press enter to continue..." % (nation))

    start_time = time.time()

    # Code to be executed during VPN

    duration = time.time() - start_time

    kill_vpn()
    return 


def write_json(obj, fn):
    with open(fn, 'w') as outfile:
        json.dump(obj, outfile, indent=2)


def get_path(sub):
    return os.path.join(Path(os.path.dirname(os.path.realpath(__file__))).parent, sub)

if __name__ == "__main__":
    main()