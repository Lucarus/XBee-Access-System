#!/bin/bash
#start instances of Python
python3 XBeeReceiver.py "/dev/ttyUSB0" "2" &
receiverPID=$!
python3 accessAPI.py 192.168.2.45 &
accessPID=$!
#python3 accessWebsocket.py &
#socketPID=$!

echo "PIDs"
echo $receiverPID
echo $accessPID
#echo $socketPID

# now monitor logfile
tail -f log

# cleanup
kill receiverPID
kill accessPID
#kill socketPID

#end
