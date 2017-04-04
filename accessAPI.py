import time
import sys
import os.path
import json
from datetime import datetime, timezone
from passlib.hash import sha256_crypt
from bottle import run, get, post, request, template, delete, auth_basic, route
from XBeeDBAccessControler import XBeeDBAccessControler, Benutzer

# Instanz eines DB Controlers erstellen
dbAccessControler = XBeeDBAccessControler("accessControl.db")

def checkAuth(username, password):
    #benutzer muss sich bei der Schnittstelle anmelden
    # weil ich ein schlauer fuchs bin erstelle ich eine Funktion bei der sich das password jede
    variablePW = "apiMinutePW" + datetime.now(timezone.utc).strftime("%d%m%Y")
    hashed = sha256_crypt.hash(variablePW)
    return sha256_crypt.verify(password, hashed)

@get('/benutzer')
@auth_basic(checkAuth)
def getBenutzer():
    userDictionary = []
    # wandelt Benuter Objekt in ein Dictonary um, damit bottle das ganze als JSON ausgeben kann
    for benutzer in dbAccessControler.getAllUsers():
        userDictionary.append(benutzer.toJSON())
    return {'benutzer' : userDictionary}

@post('/benutzer')
@auth_basic(checkAuth)
def createBenutzer():
    vorname = request.json.get('Vorname')
    nachname = request.json.get('Nachname')
    access = request.json.get('Access')
    if (vorname == None) or (nachname == None) or (access == None):
        return {'status': "error", 'message': "Kein Benutzer übergeben", 'code': "e010"}
    
    try:
        user = dbAccessControler.createUser(vorname, nachname, access)
    except LookupError as error:
        return {'status': "error", 'message': str(error), 'code': "e600"}
    return {'status': "ok", 'benutzer': user.toJSON()}

@delete('/benutzer')
@auth_basic(checkAuth)
def deleteUser():
    vorname = request.json.get('Vorname')
    nachname = request.json.get('Nachname')
    if (vorname == None) or (nachname == None):
        return {'status': "error", 'message': "Kein Benutzer übergeben", 'code': "e010"}

    try:
        deletedUser = dbAccessControler.removeUser(dbAccessControler.generateUserKey(vorname, nachname))
    except LookupError as error:
        return {'status': "error", 'message': str(error), 'code': "e404"}
    return {'status': "ok", 'benutzer': deletedUser.toJSON(), 'code': "o100"}


# Karten werden überarbeitet

@post('/benutzer/card')
@auth_basic(checkAuth)
def addKarte():
    vorname = request.json.get('Vorname')
    nachname = request.json.get('Nachname')

    if (vorname == None) or (nachname == None):
        return {'status': "error", 'message': "Kein Benutzer übergeben", 'code': "e010"}

    #überprüfen, ob der nutzer vorhanden ist
    try:
        dbAccessControler.getUser(vorname, nachname)
    except LookupError as error:
        return {'status': "error", 'message': str(error), 'code': "e404"}
    
    # action für XBeeReceiver erstellen
    action = open("action.json", mode='w')
    action.write('''{"action":"addCard","parameter":{"vorname":"%(vorname)s","nachname":"%(nachname)s"}}''' % {"vorname": vorname, "nachname": nachname})
    action.close()

    # auf antwort warten
    timeout = 3000
    while (not os.path.exists("response.json") and (timeout > 0)):
        time.sleep(0.01)
        timeout -= 1

    if (not os.path.exists("response.json")):
        # time exceeded
        action = open("action.json", mode='w')
        action.write('''{"action":"stopAddCard"}''')
        action.close()
        return {'status': "error", 'message': "Es wurde keine Karte gescannt", 'code': "e300"}

    response = open("response.json")
    responseJSON = json.loads(response.readline())
    response.close()
    os.remove("response.json")

    if responseJSON['status'] == "error":
        return responseJSON
    return {'status': "ok", 'message': "Karte hinzugefügt", 'code': "o500"}

@delete('/benutzer/card')
@auth_basic(checkAuth)
def deleteCard():
    # action für XBeeReceiver erstellen
    action = open("action.json", mode='w')
    action.write('''{"action":"removeCard"}''')
    action.close()

    # auf antwort warten
    timeout = 3000
    while (not os.path.exists("response.json") and (timeout > 0)):
        time.sleep(0.01)
        timeout -= 1

    if (not os.path.exists("response.json")):
        # time exceeded
        action = open("action.json", mode='w')
        action.write('''{"action":"stopRemoveCard"}''')
        action.close()
        return {'status': "error", 'message': "Es wurde keine Karte gescannt", 'code': "e300"}

    os.remove("response.json")
    return {'status': "ok", 'message': "Karte gelöscht", 'code': "o700"}

run(host='localhost', port=80, reloader=True)