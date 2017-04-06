import sqlite3
import serial
import time
import hashlib

class XBeeDBAccessControler:
    dbName = "accessControl.db"

    def whoIs(self, bindata):
        conn = sqlite3.connect(self.dbName)
        cur = conn.cursor()
        cur.execute("SELECT * FROM karten WHERE kartenID=:kartenID",{"kartenID": bindata})
        karte = cur.fetchone()
        if (karte == None):
            conn.close()
            raise LookupError("Karte nicht gefunden")

        cur.execute("SELECT * FROM benutzer WHERE userKey=:userKey", {"userKey": karte[1]})

        benutzer = cur.fetchone()
        if (benutzer == None):
            conn.close()
            raise LookupError("Kein Benutzer zur Karte gefunden")

        conn.close()
        return Benutzer(benutzer[0], benutzer[1], benutzer[2], benutzer[3], benutzer[4])

    def getUser(self, vorname, nachname):
        conn = sqlite3.connect(self.dbName)
        cur = conn.cursor()
        cur.execute("SELECT * FROM benutzer WHERE userKey=:userKey", {"userKey": self.generateKey(vorname, nachname)})
        user = cur.fetchone()
        if (user == None):
            raise LookupError("Benutzer nicht vorhanden")

        return Benutzer(user[0], user[1], user[2], user[3])

    def getUserCards(self, userKey):
        conn = sqlite3.connect(self.dbName)
        cur = conn.cursor()
        cur.execute("SELECT * FROM karten WHERE userKey=:userKey",{"userKey": userKey})
        karten = []
        for (kartenID, wayne) in cur.fetchall():
            karten.append(kartenID)
        return karten

    def removeUser(self, userKey):
        conn = sqlite3.connect(self.dbName)
        cur = conn.cursor()
        # del all card
        cur.execute("DELETE FROM karten WHERE userKey=:userKey", {"userKey": userKey})
        cur.execute("SELECT * FROM benutzer WHERE userKey=:userKey", {"userKey": userKey})
        foundUser = cur.fetchone()
        if foundUser != None:
            cur.execute("DELETE FROM benutzer WHERE userKey=:userKey", {"userKey": userKey})
            conn.commit()
            conn.close()
            return Benutzer(foundUser[0], foundUser[1], foundUser[2], foundUser[3], foundUser[4])
        conn.close()
        raise LookupError("Benutzer nicht gefunden")

    def removeCard(self, cardID):
        conn = sqlite3.connect(self.dbName)
        cur = conn.cursor()
        cur.execute("DELETE FROM karten WHERE kartenID=:kartenID", {"kartenID": cardID})
        conn.commit()
        conn.close()

    def getAllUsers(self):
        conn = sqlite3.connect(self.dbName)
        cur = conn.cursor()
        cur.execute("SELECT * FROM benutzer")
        benutzerList = []
        for (vorname, nachname, access, userKey, gruppen) in cur.fetchall():
            benutzerList.append(Benutzer(vorname, nachname, access, userKey, gruppen))
        return benutzerList

    def addTimestamp(self, bindata):
        conn = sqlite3.connect(self.dbName)
        cur = conn.cursor()
        cur.execute("SELECT userKey from karten WHERE kartenID=:kartenID", {"kartenID": bindata})
        userKey = cur.fetchone()
        print(userKey)
        cur.execute("INSERT INTO accessLog VALUES (?, ?, ?)", (bindata, time.time(), userKey))
        conn.commit()
        conn.close()

    def createUser(self, vorname, nachname, access, gruppen=""):
        conn = sqlite3.connect(self.dbName)
        cur = conn.cursor()
        userKey = self.generateKey(vorname, nachname)
        cur.execute("SELECT * FROM benutzer WHERE userKey=:userKey",{"userKey": userKey})
        benutzer = cur.fetchone()

        if (benutzer == None):
            cur.execute("INSERT INTO benutzer VALUES (?, ?, ?, ?, ?)", (vorname, nachname, access, userKey, str(gruppen)))
            conn.commit()
            conn.close()
            return Benutzer(vorname, nachname, access, userKey, gruppen)

        conn.close()
        raise LookupError("Benutzer bereits vorhanden")

    def createGroup(self, name):
        gruppenKey = self.generateKey(name)

        conn = sqlite3.connect(self.dbName)
        cur = conn.cursor()
        cur.execute("SELECT * FROM gruppen WHERE gruppenKey=:gruppenKey", {"gruppenKey": gruppenKey})
        if cur.fetchone() != None:
            conn.close()
            raise LookupError("Gruppe bereits vorhanden")
        cur.execute("INSERT INTO gruppen VALUES (?, ?)", (name, gruppenKey))
        conn.commit()
        conn.close()
        return Gruppe(name, gruppenKey)

    def removeGroup(self, gruppenKey):
        conn = sqlite3.connect(self.dbName)
        cur = conn.cursor()
        cur.execute("SELECT name FROM gruppen WHERE gruppenKey=:gruppenKey", {"gruppenKey": gruppenKey})
        name = cur.fetchone()
        if name == None:
            conn.close()
            raise LookupError("Gruppe nicht gefunden")
        name = name[0]
        cur.execute("DELETE FROM gruppen WHERE gruppenKey=:gruppenKey", {"gruppenKey": gruppenKey})
        conn.commit()
        conn.close()
        return Gruppe(name, gruppenKey)

    # da es eh immer nur einen namen geben kann
    def getGroup(self, gruppenKey):
        conn = sqlite3.connect(self.dbName)
        cur = conn.cursor()
        cur.execute("SELECT * FROM gruppen WHERE gruppenKey=:gruppenKey", {"gruppenKey": gruppenKey})
        foundGroup = cur.fetchone()
        if foundGroup == None:
            conn.close()
            raise LookupError("Gruppe nicht gefunden")
        conn.commit()
        conn.close()
        return Gruppe(foundGroup[0], gruppenKey)

    def getAllGroups(self):
        conn = sqlite3.connect(self.dbName)
        cur = conn.cursor()
        cur.execute("SELECT * FROM gruppen")
        foundGroups = cur.fetchall()

        gefundeneGruppen = []
        for (name, gruppenKey) in foundGroups:
            gefundeneGruppen.append(Gruppe(name, gruppenKey))

        conn.commit()
        conn.close()
        return gefundeneGruppen

    def updateUser(self):
        raise NotImplementedError

    def updateCard(self):
        raise NotImplementedError

    def updateGroup(self):
        raise NotImplementedError

    def addCardToUser(self, userKey, bindata, name):
        conn = sqlite3.connect(self.dbName)
        cur = conn.cursor()
        cur.execute("SELECT * FROM karten WHERE kartenID=:kartenID", {"kartenID": bindata})
        karte = cur.fetchone()
        if (karte == None):
            cur.execute("SELECT * FROM benutzer WHERE userKey=:userKey", {"userKey": userKey})
            if (cur.fetchone() == None):
                conn.close()
                raise LookupError("Benutzer nicht vorhanden")
            cur.execute("INSERT INTO karten VALUES (?, ?, ?, ?)", (bindata, userKey, name, ""))
            conn.commit()
            conn.close()
            return None

        conn.close()
        raise LookupError("Karte bereits registriert")

    def generateKey(self, vorname, nachname=""):
        hashKey = hashlib.md5(bytes((vorname + "" + nachname).encode()))
        return hashKey.digest()

    def createDB(self):
        conn = sqlite3.connect(self.dbName)
        cur = conn.cursor()
        cur.execute("DROP TABLE IF EXISTS benutzer")
        cur.execute("DROP TABLE IF EXISTS accessLog")
        cur.execute("DROP TABLE IF EXISTS karten")
        cur.execute("DROP TABLE IF EXISTS gruppen")
        cur.execute("DROP TABLE IF EXISTS zugriffsZeiten")
        cur.execute("CREATE TABLE benutzer (vorname TEXT, nachname TEXT, accessGranted INTEGER, userKey BLOB, gruppen TEXT, PRIMARY KEY (userKey))")
        cur.execute("CREATE TABLE karten (kartenID BLOB, userKey BLOB, name TEXT, gruppen TEXT, PRIMARY KEY (kartenID))")
        cur.execute("CREATE TABLE accessLog (kartenID BLOB, timestamp REAL, userKey BLOB)")
        cur.execute("CREATE TABLE gruppen (name TEXT, gruppenKey BLOB, PRIMARY KEY (gruppenKey))")
        cur.execute("CREATE TABLE zugriffsZeiten (name TEXT, gruppenKey BLOB, startTime TEXT, stopTime TEXT)")
        conn.commit()
        conn.close()

    def __init__(self, dbName):
        self.dbName = dbName

class Benutzer:
    vorname = ""
    nachname = ""
    access = 0
    userKey = b''
    gruppen = ""
    def __str__(self):
        return (self.vorname + " " + self.nachname)
    def __init__(self, vorname, nachname, access, userKey, gruppen):
        self.vorname = vorname
        self.nachname = nachname
        self.userKey = userKey
        self.access = access
        self.gruppen = gruppen
    def toJSON(self):
        return {"vorname": self.vorname, "nachname": self.nachname, "access": self.access, "userKey": self.userKey.hex(), "gruppen": self.gruppen}

class Gruppe:
    name = ""
    gruppenKey = b''

    def __init__(self, name, gruppenKey):
        self.name = name
        self.gruppenKey = gruppenKey

    def toJSON(self):
        return {"name": self.name, "gruppenKey": self.gruppenKey.hex()}
