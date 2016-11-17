#!/bin/bash


ips=`ip -4 addr | grep -Eo '([0-9]{1,3}\.){3}[0-9]{1,3}' | grep -v -E '255|^127'`
echo "Freifunk-VM-Passwort: `cat ~/.config/freifunk-vm/password.txt` Ips: $ips" > /etc/issue

cd "`dirname \"$0\"`"

base=/opt/freifunk-vm

mkdir -p "$base"

log="$base/app.log"
echo "---------------------------------------------------" >> "$log"

( python3 app.py 1>>"$log" 2>>"$log" ) & 
echo "$!" > "$base/app.pid"
