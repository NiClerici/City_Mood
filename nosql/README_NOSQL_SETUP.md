# NoSQL Setup – MongoDB auf Windows VM (HSLU)

Dieses Dokument beschreibt, wie du den MongoDB-Teil des City Mood Projekts auf der Windows VM einrichtest und ausführst.

---

## Voraussetzungen

- MySQL läuft bereits und enthält Daten (aggregator.py wurde mindestens einmal gestartet)
- Python 3.8+ ist installiert
- Internetverbindung auf der VM

---

## Schritt 1 – MongoDB installieren

1. Geh auf [mongodb.com/try/download/community](https://www.mongodb.com/try/download/community)
2. Wähle:
   - Version: **7.0 (current)**
   - Platform: **Windows**
   - Package: **msi**
3. Installer starten → **Complete** Installation wählen
4. Haken bei **"Install MongoDB as a Service"** lassen
5. **mongosh** (MongoDB Shell) wird automatisch mitinstalliert

Nach der Installation prüfen ob MongoDB läuft:
```powershell
# In PowerShell (als Admin)
Get-Service MongoDB
# Sollte "Running" anzeigen

# Falls nicht:
Start-Service MongoDB
```

---

## Schritt 2 – MongoDB Database Tools installieren

`mongoimport` ist ein separates Paket:

1. Geh auf [mongodb.com/try/download/database-tools](https://www.mongodb.com/try/download/database-tools)
2. Wähle **Windows ZIP** → entpacken
3. Die `.exe`-Dateien (mongoimport.exe, etc.) in einen Ordner kopieren der im PATH ist, z.B.:
   ```
   C:\Program Files\MongoDB\Tools\bin\
   ```
4. Diesen Ordner zu den **System Environment Variables → PATH** hinzufügen

Prüfen:
```powershell
mongoimport --version
mongosh --version
```

---

## Schritt 3 – Python-Abhängigkeiten installieren

```powershell
# Im City_Mood Projektordner
pip install -r requirements.txt
```

Die bestehende `requirements.txt` reicht — das Export-Script braucht nur `mysql-connector-python` und `python-dotenv`, die bereits drin sind.

---

## Schritt 4 – .env Datei prüfen

Öffne die `.env` Datei und stelle sicher dass diese MongoDB-Zeilen vorhanden sind:

```env
MONGO_HOST=localhost
MONGO_PORT=27017
MONGO_DB=city_mood
MONGO_USER=
MONGO_PASS=
```

Ohne Benutzername/Passwort läuft MongoDB standardmässig ohne Authentifizierung — das ist für die HSLU VM in Ordnung.

---

## Schritt 5 – MySQL-Daten nach JSON exportieren

```powershell
# Im nosql/ Ordner
cd nosql
python export_mysql_to_json.py
```

Erwartete Ausgabe:
```
Connecting to MySQL...
Exporting tables:
  Exported     10 documents → cities.json
  Exported    480 documents → weather.json
  Exported    480 documents → sbb.json
  Exported    480 documents → traffic.json
  Exported    420 documents → mood_scores.json

Done. Run mongoimport.sh next.
```

---

## Schritt 6 – Daten in MongoDB importieren

Da `mongoimport.sh` ein Bash-Script ist, auf Windows direkt die Befehle in PowerShell ausführen:

```powershell
# Im nosql/ Ordner ausführen (Pfade anpassen falls nötig)

mongoimport --host localhost --port 27017 --db city_mood --collection cities      --jsonArray --drop --file cities.json
mongoimport --host localhost --port 27017 --db city_mood --collection weather     --jsonArray --drop --file weather.json
mongoimport --host localhost --port 27017 --db city_mood --collection sbb         --jsonArray --drop --file sbb.json
mongoimport --host localhost --port 27017 --db city_mood --collection traffic     --jsonArray --drop --file traffic.json
mongoimport --host localhost --port 27017 --db city_mood --collection mood_scores --jsonArray --drop --file mood_scores.json
```

Jede Zeile sollte ausgeben:
```
connected to: mongodb://localhost/
X document(s) imported successfully.
```

---

## Schritt 7 – ELT Transformation ausführen

```powershell
# Im nosql/ Ordner
mongosh city_mood mongo_transform_pipeline.js
```

Erwartete Ausgabe:
```
=== ELT Transform: building mood_snapshots ===
mood_snapshots collection created.
Documents: 420
Building mv_daily_mood...
mv_daily_mood collection created.
Documents: 70
Transformation complete.
```

---

## Schritt 8 – Analytics Query ausführen

```powershell
mongosh city_mood mongo_analytics_query.js
```

Gibt die Städte-Rangliste mit Mood-Scores und Empfehlungen aus.

---

## Schritt 9 – Performance-Optimierung ausführen

```powershell
mongosh city_mood mongo_performance.js
```

Gibt Ausführungszeiten vor/nach Indexierung aus.

---

## Schritt 10 – Metabase mit MongoDB verbinden

1. Metabase öffnen (Standard: http://localhost:3000)
2. **Settings → Admin → Databases → Add database**
3. Einstellungen:
   - Database type: **MongoDB**
   - Display name: `City Mood MongoDB`
   - Host: `localhost`
   - Port: `27017`
   - Database name: `city_mood`
   - Username/Password: leer lassen
4. **Save** klicken

---

## Collections Übersicht

| Collection | Inhalt | Typ |
|---|---|---|
| `cities` | 10 Schweizer Städte | Raw (aus MySQL) |
| `weather` | Wetterdaten pro Stadt/Zeitstempel | Raw (aus MySQL) |
| `sbb` | Zugverspätungen pro Stadt/Zeitstempel | Raw (aus MySQL) |
| `traffic` | Verkehrsdaten pro Stadt/Zeitstempel | Raw (aus MySQL) |
| `mood_scores` | Berechnete Scores (MySQL normalized) | Raw (aus MySQL) |
| `mood_snapshots` | **Denormalisiert**: city + weather + sbb + traffic + scores in einem Dokument | Transformiert |
| `mv_daily_mood` | Tägliche Durchschnittswerte pro Stadt | Materialized View |

---

## Reihenfolge zusammengefasst

```
1. MongoDB installieren + starten
2. python export_mysql_to_json.py
3. mongoimport (5x Befehle oben)
4. mongosh city_mood mongo_transform_pipeline.js
5. mongosh city_mood mongo_analytics_query.js
6. mongosh city_mood mongo_performance.js
7. Metabase verbinden
```

---

## Häufige Fehler

**`mongoimport` nicht gefunden**
→ Database Tools separat installieren und PATH setzen (siehe Schritt 2)

**`Connection refused` bei MongoDB**
→ `Start-Service MongoDB` in PowerShell als Admin ausführen

**`Export failed: Connection failed`**
→ MySQL läuft nicht oder `.env` Credentials falsch — `python init_db.py` nochmal ausführen

**`mood_snapshots` leer nach Transform**
→ Wahrscheinlich haben nicht alle Snapshots Daten in allen 3 Tabellen (weather, sbb, traffic). Prüfen ob `aggregator.py` mindestens einmal komplett durchgelaufen ist.
