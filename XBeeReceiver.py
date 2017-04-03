import serial, time, sys, os.path, json
from xbee import ZigBee
from XBeeDBAccessControler import XBeeDBAccessControler, Benutzer

# Instanz eines DB Controlers erstellen
dbAccessControler = XBeeDBAccessControler("accessControl.db")

# Variabeln für das arbeiten mit dem Thread
nextInstruction = {"action": "justStarted", "parameter": {"vorname": "", "nachname": ""}}
cardReceiver = {"vorname": "test", "nachname": ""}
cardResponse = {"responce": "NIX"}

def dataReceived(data):
    recData = data['rf_data'] 
    if (recData[0] == 0x11):
        # Karte wurde gelesen
        # karten ID aus den übergebenen Bytes extrahieren (an 1. Stelle steht die Art des Pakets)
        cardID = recData[1:]
        if nextInstruction['action'] == 'addCard':
            # Karte zu einem Benutzer hinzufügen
            try:
                # Karten ID in der Datenbank speichern
                dbAccessControler.addCardToUser(dbAccessControler.generateUserKey(nextInstruction['parameter']['vorname'], nextInstruction['parameter']['nachname']),cardID)
                # response erstellen
                cardResponse['responce'] = '''{"status": "ok"}'''
            except LookupError as error:
                # fehler erstellen falls fehler aufgetreten
                cardResponse['responce'] = '''{"status": "error", "message": "%(message)s"}''' %{"message": str(error)}

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
                print(user)
                # timestap wenn karte gesannt wurde
                dbAccessControler.addTimestamp(cardID)

                # Datei erstellen um im websocket anzuzeigen
                scanned = open("scanned.json", mode='w')
                scanned.write('''{"benutzer": %(userInfo)s}''' %{"userInfo": str(user.toJSON()).replace("'", '"')})
                scanned.close()

                # is access granted ?
                # check_for_access()
            except LookupError as error:
                print(str(error))

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

        # Soll eine vorherige instruktion abgebrochen werden (Timeout)
        if nextInstruction['action'] == "stopAddCard" or nextInstruction['action'] == "stopRemoveCard":
            nextInstruction['action'] = "NIXformStopping"

        print("Next instruction: ")
        print(nextInstruction)

def writeResponse():
    # wurde eine Instruktion durchgeführt wird die response in eine Datei geschrieben um dem Fronted die änderung mitzuteilen
    if cardResponse['responce'] != "NIX":
        myResponse = open("response.json", mode='w')
        myResponse.write(cardResponse['responce'])
        myResponse.close()
        cardResponse['responce'] = "NIX"

# XBee initialisieren
serialConn = serial.Serial("COM8", 9600)
xbee = ZigBee(serialConn, callback=dataReceived)

while True:
    try:
        # Auf action.json warten
        time.sleep(0.01)
        checkForData()
        writeResponse()
    except KeyboardInterrupt:
        # Ctl + C beendet programm
        break

# WICHTIG ! um die Asynchronen Threads zu beenden
xbee.halt()
# Serial port wieder freigeben
serialConn.close()