# -*- coding: utf-8 -*-
import time
import sys
import os.path
import json
from datetime import datetime, timezone
from passlib.hash import sha256_crypt
from bottle import run, get, post, put, request, template, delete, auth_basic, route
from XBeeDBAccessControler import XBeeDBAccessControler, Benutzer, Gruppe, Karte

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
    groupNames = request.json.get('Gruppen')

    if (vorname == None) or (nachname == None) or (access == None):
        return {'status': "error", 'message': "Kein Benutzer übergeben", 'code': "e010"}
    if (groupNames != None):
        # überprüfen, ob gruppen vorhanden sind !!!! wichtig
        for gruppe in groupNames:
            try:
                dbAccessControler.getGroup(dbAccessControler.generateKey(gruppe));
            except LookupError as error:
                return {'status': "error", 'message': str(error), 'code': "e040", 'group': gruppe}
    else:
        groupNames = ""

    #print(groupNames)

    try:
        user = dbAccessControler.createUser(vorname, nachname, access, groupNames)
    except LookupError as error:
        return {'status': "error", 'message': str(error), 'code': "e600"}
    return {'status': "ok", 'benutzer': user.toJSON(), 'code': "o200"}

@delete('/benutzer')
@auth_basic(checkAuth)
def deleteUser():
    vorname = request.json.get('Vorname')
    nachname = request.json.get('Nachname')
    if (vorname == None) or (nachname == None):
        return {'status': "error", 'message': "Kein Benutzer übergeben", 'code': "e010"}

    try:
        deletedUser = dbAccessControler.removeUser(dbAccessControler.generateKey(vorname, nachname))
    except LookupError as error:
        return {'status': "error", 'message': str(error), 'code': "e404"}
    return {'status': "ok", 'benutzer': deletedUser.toJSON(), 'code': "o100"}


# Karten werden überarbeitet

@post('/cards')
@auth_basic(checkAuth)
def addKarte():
    vorname = request.json.get('Vorname')
    nachname = request.json.get('Nachname')
    cardName = request.json.get('Kartenname')
    groupNames = request.json.get('Gruppen')

    if (vorname == None) or (nachname == None):
        return {'status': "error", 'message': "Kein Benutzer übergeben", 'code': "e010"}
    if cardName == None:
        return {'status': "error", 'message': "Kein Kartenname übergeben", 'code': "e020"}

    # Kartenname abfragen
    foundCard = None
    try:
        foundCard = dbAccessControler.getCard(cardName)
    except LookupError as error:
        None
        # Fehler bedeutet, alles is in Ordnung ^^

    if foundCard != None:
        return {'status': "error", 'message':"Karte bereits vorhanden", 'code': "e700"}

    # Gruppen abfragen
    if groupNames != None:
        for gruppe in groupNames:
            try:
                dbAccessControler.getGroup(dbAccessControler.generateKey(gruppe));
            except LookupError as error:
                return {'status': "error", 'message': str(error), 'code': "e040", 'group': gruppe}
    else:
        groupNames = ""

    #überprüfen, ob der nutzer vorhanden ist
    #Gruppe auch testn
    try:
        dbAccessControler.getUser(vorname, nachname)
        #dbAccessControler.getGroup(gruppenKey)
    except LookupError as error:
        return {'status': "error", 'message': str(error), 'code': "e404"}

    # action für XBeeReceiver erstellen
    action = open("action.json", mode='w', encoding="UTF_8")
    action.write('''{"action":"addCard","parameter":{"vorname":"%(vorname)s","nachname":"%(nachname)s","kartenname": "%(kartenname)s", "gruppen": "%(gruppen)s"}}''' % {"vorname": vorname, "nachname": nachname, "kartenname": cardName, "gruppen": groupNames})
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
    return {'status': "ok", 'message': "Karte hinzugefügt", 'code': "o500", 'karte': responseJSON['karte']}

@delete('/cards')
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

@get('/cards')
@auth_basic(checkAuth)
def getUserCards():
    raise NotImplementedError()

@get('/groups')
@auth_basic(checkAuth)
def getGroups():
    groupDictionary = []
    for group in dbAccessControler.getAllGroups():
        groupDictionary.append(group.toJSON())
    return {'gruppen' : groupDictionary}

@post('/groups')
@auth_basic(checkAuth)
def createGroup():
    name = request.json.get('Name')

    if (name == None):
        return {'status': "error", 'message': "Kein Gruppenname übergeben", 'code': "e030"}

    try:
        group = dbAccessControler.createGroup(name)
    except LookupError as error:
        return {'status': "error", 'message': str(error), 'code': "e500"}
    return {'status': "ok", 'gruppe': group.toJSON(), "code": "o400"}

@delete('/groups')
@auth_basic(checkAuth)
def deleteGroup():
    name = request.json.get('Name')

    if (name == None):
        return {'status': "error", 'message': "Kein Gruppenname übergeben", 'code': "e030"}

    try:
        deletedGroup = dbAccessControler.removeGroup(dbAccessControler.generateKey(name))
    except LookupError as error:
        return {'status': "error", 'message': str(error), 'code': "e504"}
    return {'status': "ok", 'gruppe': deletedGroup.toJSON(), 'code': "o300"}

@put('/benutzer')
@auth_basic(checkAuth)
def getAllAccesstimes():
    vorname = request.json.get('Vorname')
    nachname = request.json.get('Nachname')
    access = request.json.get('Access')
    groupNames = request.json.get('Gruppen')

    if (vorname == None) or (nachname == None) or (access == None):
        return {'status': "error", 'message': "Kein Benutzer übergeben", 'code': "e010"}
    if (groupNames != None):
        # überprüfen, ob gruppen vorhanden sind !!!! wichtig
        for gruppe in groupNames:
            try:
                dbAccessControler.getGroup(dbAccessControler.generateKey(gruppe));
            except LookupError as error:
                return {'status': "error", 'message': str(error), 'code': "e040", 'group': gruppe}
    else:
        groupNames = ""

    #print(groupNames)

    try:
        user = dbAccessControler.updateUser(vorname, nachname, access, groupNames)
    except LookupError as error:
        return {'status': "error", 'message': str(error), 'code': "e404"}
    return {'status': "ok", 'benutzer': user.toJSON(), 'code': "o202"}

@put('/card')
@auth_basic(checkAuth)
def createAccesstime():
    raise NotImplementedError()

@put('/accesstimes')
@auth_basic(checkAuth)
def getAllAccesstimes():
    raise NotImplementedError()

@get('/accesstimes')
@auth_basic(checkAuth)
def getAllAccesstimes():
    raise NotImplementedError()

@post('/accesstimes')
@auth_basic(checkAuth)
def createAccesstime():
    raise NotImplementedError()

@delete('/accesstimes')
@auth_basic(checkAuth)
def removeAccesstime():
    raise NotImplementedError()

host = 'localhost'
#check for IP
if (len(sys.argv) == 2):
    host = sys.argv[1]

run(host=host, port=80, reloader=True)
