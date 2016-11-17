#!/usr/bin/python3
from bottle import post, get, run, request, static_file, redirect, route, auth_basic, \
                   response, abort
import os
import sys
import shutil
import base64
import subprocess
import re
import threading

APPLICATION = "freifunk-vm"
HERE = os.path.dirname(__file__) or os.getcwd()
CONFIGURATION_FILES = os.path.join(os.environ.get("HOME", "~"), ".config", APPLICATION)
HTTPS_SOURCE = "https://github.com/niccokunzmann/freifunk-vm.git"
WIFI_NAME = "tinyurl.com/freifunk-vm"

os.makedirs(CONFIGURATION_FILES, exist_ok=True)
# ------------------- Passwords -------------------

PASSWORDS = []
PASSWORD_BYTES = 5
PASSWORD_FILE = os.path.join(CONFIGURATION_FILES, "password.txt")
AUTH_REALM = "Freifunk-VM-Passwort:"
AUTHENTICATIONS_LEFT = 10

def create_password():
    """Return a new password."""
    new_password = os.urandom(PASSWORD_BYTES)
    new_password = base64.b64encode(new_password)
    new_password = new_password.decode("UTF-8")
    return new_password

def update_passwords():
    """Update passwords."""
    global PASSWORDS
    new_password = create_password()
    PASSWORDS = [new_password]
    if os.path.exists(PASSWORD_FILE):
        with open(PASSWORD_FILE) as f:
            old_password = f.read()
        PASSWORDS.append(old_password)
    os.makedirs(os.path.dirname(PASSWORD_FILE), exist_ok=True)
    with open(PASSWORD_FILE, "w") as f:
        f.write(new_password)

class Versuche(object):
    def __str__(self):
        return "{} Versuche verbleiben.".format(AUTHENTICATIONS_LEFT)


def authenticate(function):
    """Function wrapper for basic authenticaion"""
    def check(user, password):
        global AUTHENTICATIONS_LEFT
        if AUTHENTICATIONS_LEFT <= 0:
            return False
        authenticated = password in PASSWORDS
        if not authenticated:
            AUTHENTICATIONS_LEFT -= 1
        return authenticated
    return auth_basic(check, realm=AUTH_REALM,
                      text=Versuche())(function)


# ------------------- Routes -------------------

#                     WIFI

CURRENTLY_RUNNING_WIFI = None

@get("/restart-wifi")
@authenticate
def get_restart_wifi():
    try:
        restart_wifi()
    except ValueError as e:
        abort(500, e)
    redirect(CONFIG)

def interfaces(command="link"):
    links = subprocess.check_output(["ip", "-o", command])
    links = links.decode()
    return re.findall("^\\d+:\\s+(\\S+?)(?::|\\s)", links, re.MULTILINE)

def restart_wifi():
    global CURRENTLY_RUNNING_WIFI
    subprocess.call(["killall", "create_ap"])
    if CURRENTLY_RUNNING_WIFI:
        CURRENTLY_RUNNING_WIFI.terminate()
        CURRENTLY_RUNNING_WIFI.wait(1)
    wifi_name = WIFI_NAME
    ifaces = interfaces()
    print("ifaces: {}".format(ifaces))
    tunnel = [i for i in ifaces if i.startswith("tun")]
    if not tunnel:
        raise ValueError("No VPN tunnel found.")
    tunnel = tunnel[0]
    wifi = [i for i in ifaces if i.startswith("w")]
    if not wifi:
        raise ValueError("Keinen WLAN-Adapter gefunden. Bitte schalte ihn ein!")
    wifi = wifi[0]
    print("wifi: {} tunnel: {}".format(wifi, tunnel))
    CURRENTLY_RUNNING_VPN = subprocess.Popen(["create_ap", wifi, tunnel, wifi_name],
                                             cwd=VPN_CONFIGURATION_FILES)

@get("/wifi-status")
def get_wifi_status():
    if any(i.startswith("w") for i in interfaces("addr")):
        redirect("/static/vpn-ok.png", 307)
    redirect("/static/vpn-down.png", 307)


#                     VPN

VPN_CONFIGURATION_FILE = os.path.join(CONFIGURATION_FILES, "freifunk-vpn.tgz")
VPN_CONFIGURATION_FILES = os.path.join(CONFIGURATION_FILES, "vpn")

os.makedirs(VPN_CONFIGURATION_FILES, exist_ok=True)

@post("/update-vpn")
@authenticate
def update_vpn():
    print(request.files.keys())
    configuration = request.files.freifunk_configuration
    if not configuration:
        print(configuration)
        raise ValueError("Error: no configuration given.")
    with open(VPN_CONFIGURATION_FILE, "wb") as f:
        shutil.copyfileobj(configuration.file, f)
    subprocess.check_call(["tar", "zxvf", VPN_CONFIGURATION_FILE],
                          cwd=VPN_CONFIGURATION_FILES)
    restart_vpn()
    return "OK"

CURRENTLY_RUNNING_VPN = None
FILE_ENDING = "udp.ovpn"

@get("/restart-vpn")
@authenticate
def get_restart_vpn():
    try:
        restart_vpn()
    except ValueError as e:
        abort(500, e)
    redirect(CONFIG)

def restart_vpn():
    global CURRENTLY_RUNNING_VPN
    subprocess.call(["killall", "openvpn"])
    if CURRENTLY_RUNNING_VPN:
        CURRENTLY_RUNNING_VPN.terminate()
        CURRENTLY_RUNNING_VPN.wait(1)
    files = os.listdir(VPN_CONFIGURATION_FILES)
    configuration = [f for f in files if f.lower().endswith(FILE_ENDING)]
    if not configuration:
         raise ValueError("Could not find file with ending {} among "
                          "those listed here: {}"\
                          .format(FILE_ENDING, ",".join(files)))
    configuration = configuration[0]
    CURRENTLY_RUNNING_VPN = subprocess.Popen(["openvpn", configuration],
                                             cwd=VPN_CONFIGURATION_FILES)

@get("/vpn-status")
def get_vpn_status():
    if CURRENTLY_RUNNING_VPN and CURRENTLY_RUNNING_VPN.returncode is None:
        redirect("/static/vpn-ok.png", 307)
    redirect("/static/vpn-down.png", 307)

#                     update
@get("/update-sourcecode")
@authenticate
def update_from_github():
    response.content_type = "text/plain"
    return subprocess.check_output(["git", "pull", HTTPS_SOURCE]) + \
           b"\r\nBitte die VM neustarten."

#                     Static
STATIC_FILES = os.path.join(HERE, "static")
HOME = "/static/index.html"
CONFIG = "/static/config.html"

@route('/')
def index():
    return redirect(HOME)

@route('/static/<filename>')
def static(filename):
    return static_file(filename, root=STATIC_FILES)

#                     AGPL
ZIP_PATH = "/" + APPLICATION + ".zip"

@get('/source')
def get_source_redirect():
    """Download the source of this application."""
    redirect(ZIP_PATH)

@get(ZIP_PATH)
def get_source():
    """Download the source of this application."""
    # from http://stackoverflow.com/questions/458436/adding-folders-to-a-zip-file-using-python#6511788
    path = (shutil.make_archive("/tmp/" + APPLICATION, "zip", HERE))
    return static_file(path, root="/")

@get("/License.txt")
def get_license():
    return static_file("LICENSE", root=".", mimetype="text/plain")


# ------------------- main -------------------

def main():
    update_passwords()
    restart_vpn()
    threading.Timer(3, restart_wifi).start()
    print("{} {}".format(AUTH_REALM, " ".join(PASSWORDS)))
    run(host='', port=80, debug=True)

if __name__ == "__main__":
    main()
