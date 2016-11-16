#!/bin/bash

last=""
current_pid=""

while true
do
  current="`cat app.py`"
  sleep 0.1
  if [ "$last" != "$current" ]
  then
    sudo killall app.py
    if [ -n "$current_pid" ]
    then
      echo "Restarting PID: $current_pid."
      wait "$current_pid"
    else
      echo "Starting server."
    fi
    sudo ./app.py &
    current_pid="$!"
    echo "Current PID: $current_pid "
    last="$current"
  fi
done