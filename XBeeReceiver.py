# -*- coding: utf-8 -*-
import serial, time, sys, os.path, json
from xbee import ZigBee
from XBeeDBAccessControler import XBeeDBAccessControler, Benutzer, Karte, Gruppe

# Instanz eines DB Controlers erstellen
dbAccessControler = XBeeDBAccessControler("accessControl.db")
nextInstruction = {"action": "justStarted", "parameter": {"vorname": "", "nachname": "", "kartenname": "", "gruppen": ""}}
cardResponse = {"responce": "NIX"}

powerTime = 2

loggingFile = open("log", mode='a+', encoding="UTF_8")

def dataReceived(data):
    recData = data['rf_data']
    if (recData[0] == 0x11):
    # Karte wurde gelesen
    # karten ID aus den übergebenen Bytes extrahieren (an 1. Stelle steht die Art des Pakets)

    cardID = recData[1:]

    if nextInstruction['action'] == 'addCard':
    #print("Adding....")
    # Karte zu einem Benutzer hinzufügen
    try:
    # Karten ID in der Datenbank speichern
    newCard = dbAccessControler.addCardToUser(dbAccessControler.generateKey(nextInstruction['parameter']['vorname'], nextInstruction['parameter']['nachname']),cardID,nextInstruction['parameter']['kartenname'], nextInstruction['parameter']['gruppen'])
    # response erstellen
    cardResponse['responce'] = '''{"status": "ok", "karte": {%(karte)s}}''' %{"karte": newCard.toJSONString()}
    except LookupError as error:
    # fehler erstellen falls fehler aufgetreten
    cardResponse['responce'] = '''{"status": "error", "message": "%(message)s"}''' %{"message": str(error)}
    except:
    #print ("Unexpected error:", sys.exc_info())

    # instruktion wieder zurück setzen
    nextInstruction['action'] = "justAddedCard"

    elif nextInstruction['action'] == 'removeCard':
    # nächste karte löschen
    dbAccessControler.removeCard(cardID)
    # status ist immer OK auch wenn Karte noch garnicht hinzugefügt
    # vielleicht nicht so GUT rüchmeldung über Benutzer dem die Karte gehörte ????
    cardResponse['responce'] = '''{"status": "ok"}'''

    # instruktion wieder zurück setzen
    nextInstruction['action'] = "justRemovedCard"

    else:
    # wenn keine Instruktion einfach nach User zu Karte suchen
    try:
    # anfrage an Datenbank
    user = dbAccessControler.whoIs(cardID)
    #print(user)

    # timestap wenn karte gesannt wurde
    dbAccessControler.addTimestamp(cardID)

    # zugriff abfragem
    access = dbAccessControler.check_for_access(user)

    # Datei erstellen um im websocket anzuzeigen
    scanned = open("scanned.json", mode='w')
    scanned.write('''{"benutzer": %(userInfo)s, "access": %(access)s}''' %{"userInfo": str(user.toJSON()).replace("'", '"'), "access": access})
    scanned.close()

    myLogging.writelines('''%(timestamp)s Scanned: {"benutzer": %(userInfo)s, "access": %(access)s} \n''' %{"userInfo": str(user.toJSON()).replace("'", '"'), "access": access, "timestamp": time.time()})

    # Note: this approach seems to be shit and somtimes the signal seems to flicker the relay
    # is access granted ?
    #print(access)
    if access:
    # send high to digital Pin0 of 3. Xbee
    xbee.remote_at(
    dest_addr=b'\x1E\x40',
    command=b'D0',
    parameter=b'\x05')
    time.sleep(powerTime)
    # put pin low again after some time
    xbee.remote_at(
    dest_addr=b'\x1E\x40',
    command=b'D0',
    parameter=b'\x04')

    except LookupError as error:
    #print(str(error))

def checkForData():
    # Überprüfen ob Instruktion erstellt wurden
    if os.path.exists("action.json"):
    # Instruktionen vorhanden
    # Instruktionne einlesen und als JSON parsen
    action = open("action.json")
    actionJSON = json.loads(action.readline())
    # Datei wieder schließen und löschen, damit sie nicht nocheinmal gefunden wird
    action.close()
    os.remove("action.json")

    # Informationen in instruction einsetzen
    nextInstruction['action'] = actionJSON['action']
    if nextInstruction['action'] == "addCard":
    nextInstruction['parameter']['vorname'] = actionJSON['parameter']['vorname']
    nextInstruction['parameter']['nachname'] = actionJSON['parameter']['nachname']
    nextInstruction['parameter']['kartenname'] = actionJSON['parameter']['kartenname']
    nextInstruction['parameter']['gruppen'] = actionJSON['parameter']['gruppen']

    # Soll eine vorherige instruktion abgebrochen werden (Timeout)
    if nextInstruction['action'] == "stopAddCard" or nextInstruction['action'] == "stopRemoveCard":
    nextInstruction['action'] = "NIXformStopping"

    #print("Next instruction: ")
    #print(nextInstruction)

    myLogging.writelines(time.time() + " Action: " + nextInstruction + "\n")
    myLogging.flush

def writeResponse():
    # wurde eine Instruktion durchgeführt wird die response in eine Datei geschrieben um dem Fronted die änderung mitzuteilen
    if cardResponse['responce'] != "NIX":
    myResponse = open("response.json", mode='w', encoding="UTF_8")
    myResponse.write(cardResponse['responce'])
    myResponse.close()
    # for logging:
    myLogging.writelines(time.time() + " Responce: " + cardResponse['responce']+ "\n")
    myLogging.flush()
    cardResponse['responce'] = "NIX"

# parameter verwenden
port = None
if (len(sys.argv) > 1):
    port = sys.argv[1]
    powerTime = 2
if len(sys.argv) > 2:
    powerTime = int(sys.argv[2])

if len(sys.argv) == 1:
    #print("COM-Port angeben !")
    sys.exit(0)

# XBee initialisieren
serialConn = serial.Serial(port, 9600)
xbee = ZigBee(serialConn, callback=dataReceived)

while True:
    try:
    # Auf action.json warten
    time.sleep(0.05)
    checkForData()
    writeResponse()
    except KeyboardInterrupt:
    # Ctl + C beendet programm
    break

# WICHTIG ! um die Asynchronen Threads zu beenden
xbee.halt()
# Serial port wieder freigeben
serialConn.close()
# Close logging File
myLogging.close()
