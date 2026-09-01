# Uptime Kuma Domain API

Eine schlanke REST-API, mit der überwachte Domains (HTTP/HTTPS-Monitore) in
[Uptime Kuma](https://github.com/louislam/uptime-kuma) angelegt, geändert und
gelöscht werden können — z. B. direkt aus einem CRM heraus.

Uptime Kuma selbst bietet keine offizielle REST-API zur Monitor-Verwaltung,
sondern nur eine Socket.IO-Schnittstelle. Dieser Dienst verbindet sich als
Client mit deiner laufenden Uptime-Kuma-Instanz und stellt die
Monitor-Verwaltung als einfache, per API-Key geschützte REST-API bereit.

> Schritt-für-Schritt-Installation auf einem frischen Debian-Server:
> siehe [DEPLOYMENT.md](DEPLOYMENT.md).

## Endpunkte

Alle Endpunkte (außer `/health`) erwarten den Header `X-API-Key: <dein-key>`.

| Methode | Pfad                 | Beschreibung                                   |
|---------|----------------------|-------------------------------------------------|
| GET     | `/domains`           | Alle überwachten Domains auflisten              |
| GET     | `/domains/{id}`      | Eine Domain abrufen                             |
| POST    | `/domains`           | Neue Domain anlegen                             |
| PUT     | `/domains/{id}`      | Domain aktualisieren (nur gesetzte Felder)      |
| DELETE  | `/domains/{id}`      | Domain löschen                                  |
| GET     | `/health`            | Health-Check (kein API-Key nötig)               |

Nach dem Start stehen zwei Arten von Dokumentation zur Verfügung:

- **`/reference`** – kuratierte API-Referenz mit Beispielen (diese Seite; die
  Basis-URL/den API-Key oben auf der Seite eintragen, dann sind alle
  Code-Beispiele direkt kopierbar).
- **`/docs`** (Swagger UI) bzw. **`/redoc`** – automatisch aus dem Code
  generierte, interaktive OpenAPI-Dokumentation.

### Beispiel: Domain anlegen

```bash
curl -X POST http://localhost:8000/domains \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"domain": "example.com", "interval": 60}'
```

Antwort:

```json
{
  "id": 3,
  "domain": "example.com",
  "name": "example.com",
  "url": "https://example.com",
  "active": true,
  "interval": 60,
  "retry_interval": 60,
  "max_retries": 0,
  "resend_interval": 0,
  "upside_down": false,
  "ignore_tls": false,
  "accepted_statuscodes": ["200-299"],
  "notification_ids": []
}
```

### Beispiel: Domain löschen

```bash
curl -X DELETE http://localhost:8000/domains/3 -H "X-API-Key: $API_KEY"
```

### Beispiel: Domain pausieren / Intervall ändern

```bash
curl -X PUT http://localhost:8000/domains/3 \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"active": false, "interval": 300}'
```

## Konfiguration

Konfiguration erfolgt über Umgebungsvariablen bzw. eine `.env`-Datei (siehe
`.env.example`):

| Variable                 | Pflicht | Beschreibung                                            |
|---------------------------|---------|----------------------------------------------------------|
| `UPTIME_KUMA_URL`          | ja      | Basis-URL deiner Uptime-Kuma-Instanz                     |
| `UPTIME_KUMA_USERNAME`     | ja      | Login eines Uptime-Kuma-Benutzers                        |
| `UPTIME_KUMA_PASSWORD`     | ja      | Passwort dieses Benutzers                                |
| `API_KEY`                  | ja      | API-Key, den Clients (z. B. dein CRM) mitschicken müssen  |
| `DEFAULT_SCHEME`           | nein    | Standard-Schema für neue Domains (`https`)                |
| `DEFAULT_INTERVAL`         | nein    | Standard-Check-Intervall in Sekunden (`60`)               |
| `UPTIME_KUMA_TIMEOUT`      | nein    | Timeout für die Socket.IO-Verbindung in Sekunden (`15`)   |

API-Key erzeugen:

```bash
python3 -c "import secrets; print(secrets.token_urlsafe(32))"
```

## Lokal starten

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # Werte anpassen
uvicorn app.main:app --reload
```

## Deployment auf einem separaten Server (Docker)

Dieser Dienst ist eigenständig und muss nicht auf demselben Server wie
Uptime Kuma laufen. Er verbindet sich per Netzwerk (Socket.IO über HTTP/HTTPS)
mit der URL aus `UPTIME_KUMA_URL` — das kann eine andere Maschine, ein anderes
Docker-Netz oder eine andere Cloud-Instanz sein.

1. Projekt auf den Ziel-Server kopieren (z. B. per `git clone` oder `scp`):

   ```bash
   git clone https://github.com/MeinholC/UptimeKuma-API.git
   cd UptimeKuma-API
   ```

2. `.env` anlegen und auf die **bestehende, extern erreichbare**
   Uptime-Kuma-Instanz zeigen lassen:

   ```bash
   cp .env.example .env
   ```

   ```env
   UPTIME_KUMA_URL=https://kuma.deine-domain.tld
   UPTIME_KUMA_USERNAME=admin
   UPTIME_KUMA_PASSWORD=...
   API_KEY=...
   ```

3. Starten:

   ```bash
   docker compose up --build -d
   ```

   Das startet ausschließlich diesen API-Dienst (siehe `docker-compose.yml`)
   auf Port `8000`. Uptime Kuma selbst muss bereits laufen und von diesem
   Server aus erreichbar sein (Firewall/Security-Group beachten — Port 3001
   bzw. dein konfigurierter Kuma-Port muss offen sein).

   Alternativ ohne Compose:

   ```bash
   docker build -t uptime-kuma-domain-api .
   docker run --env-file .env -p 8000:8000 --restart unless-stopped uptime-kuma-domain-api
   ```

4. Optional: einen Reverse Proxy (nginx, Caddy, Traefik) mit TLS vor Port
   `8000` schalten, bevor die API vom CRM aus dem Internet erreichbar ist —
   der API-Key ersetzt kein TLS.

### Alles auf einem Host testen (Uptime Kuma + API zusammen)

Für lokale Tests, bei denen Uptime Kuma noch nicht existiert, gibt es
`docker-compose.with-uptime-kuma.yml`, das beide Dienste zusammen startet:

```bash
cp .env.example .env   # UPTIME_KUMA_URL wird von der Compose-Datei überschrieben
docker compose -f docker-compose.with-uptime-kuma.yml up --build -d
```

## Tests

```bash
pip install -r requirements-dev.txt
pytest
```

Die Tests laufen gegen eine In-Memory-Fake-Implementierung der Uptime-Kuma-API
und benötigen keine echte Uptime-Kuma-Instanz.

## Architektur

- **FastAPI** stellt die REST-Endpunkte bereit.
- **[`uptime-kuma-api`](https://pypi.org/project/uptime-kuma-api/)** (Python-Client) spricht per Socket.IO mit Uptime Kuma.
- Pro Request wird eine kurzlebige Socket.IO-Verbindung auf- und wieder
  abgebaut (`app/kuma_client.py`), damit eine instabile Verbindung zu Uptime
  Kuma nie zu einem dauerhaft kaputten Zustand des API-Dienstes führt.
- Domains werden als HTTP(S)-Monitore in Uptime Kuma angelegt
  (`type=http`, `url=https://<domain>`).
