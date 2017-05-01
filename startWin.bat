@echo off

start cmd.exe /k "python accessAPI.py 192.168.2.42"
start cmd.exe /k "python accessWebsocket.py 192.168.2.42"
start cmd.exe /k "python XBeeReceiver.py COM8"
