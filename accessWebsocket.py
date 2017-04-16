import asyncio
import websockets
import os.path
import sys

async def time(websocket, path):
    while True:
        if os.path.exists("scanned.json"):
            scanned = open("scanned.json")
            scannedFile = scanned.readline()
            scanned.close()
            os.remove("scanned.json")
            await websocket.send(scannedFile)
        await asyncio.sleep(1)

host = '127.0.0.1'
#check for IP
if (len(sys.argv) == 2):
    host = sys.argv[1]

start_server = websockets.serve(time, host, 5678)

asyncio.get_event_loop().run_until_complete(start_server)
asyncio.get_event_loop().run_forever()