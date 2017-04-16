@echo off

start cmd.exe /k "python accessAPI.py"
start cmd.exe /k "python accessWebsocket.py"
start cmd.exe /k "python XBeeReceiver.py COM8"