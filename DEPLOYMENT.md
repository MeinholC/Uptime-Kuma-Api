# Installation auf einem frischen Debian-Server

Diese Anleitung geht von einem leeren Debian-Server (Debian 12 „bookworm“)
mit SSH- und Root-/sudo-Zugriff aus und bringt die API mittels Docker zum
Laufen. Eine bereits laufende, extern erreichbare Uptime-Kuma-Instanz wird
vorausgesetzt (muss nicht auf diesem Server laufen).

## 1. System aktualisieren

```bash
sudo apt update && sudo apt upgrade -y
```

## 2. Docker installieren

```bash
sudo apt install -y ca-certificates curl gnupg
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/debian/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
sudo chmod a+r /etc/apt/keyrings/docker.gpg

echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/debian \
  $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
```

Prüfen, ob es funktioniert:

```bash
sudo docker run hello-world
```

Optional, damit `docker`-Befehle ohne `sudo` laufen (danach einmal neu
einloggen):

```bash
sudo usermod -aG docker $USER
```

## 3. Projektdateien auf den Server bringen

Zielverzeichnis anlegen:

```bash
sudo mkdir -p /opt/uptime-kuma-domain-api
sudo chown $USER:$USER /opt/uptime-kuma-domain-api
```

**Variante A — ZIP hochladen** (von deinem lokalen Rechner aus ausführen,
nicht auf dem Server):

```bash
scp uptime-kuma-domain-api.zip DEIN_USER@DEIN_SERVER:/opt/uptime-kuma-domain-api/
```

Auf dem Server entpacken:

```bash
cd /opt/uptime-kuma-domain-api
sudo apt install -y unzip
unzip uptime-kuma-domain-api.zip
# falls die ZIP einen Unterordner enthält (z. B. UptimeKuma-API-main),
# dessen Inhalt eine Ebene nach oben verschieben:
# mv UptimeKuma-API-*/* UptimeKuma-API-*/.* . 2>/dev/null; rmdir UptimeKuma-API-*
rm uptime-kuma-domain-api.zip
```

**Variante B — Git-Repository klonen** (empfohlen, da Updates dann per
`git pull` möglich sind):

```bash
sudo apt install -y git
cd /opt
sudo git clone https://github.com/MeinholC/UptimeKuma-API.git uptime-kuma-domain-api
sudo chown -R $USER:$USER uptime-kuma-domain-api
cd uptime-kuma-domain-api
```

Am Ende muss im Verzeichnis `/opt/uptime-kuma-domain-api` u. a. `Dockerfile`,
`docker-compose.yml` und der Ordner `app/` liegen.

## 4. Konfiguration (`.env`)

```bash
cp .env.example .env
nano .env
```

Mindestens diese Werte anpassen:

```env
UPTIME_KUMA_URL=https://kuma.deine-domain.tld
UPTIME_KUMA_USERNAME=admin
UPTIME_KUMA_PASSWORD=dein-kuma-passwort
API_KEY=dein-generierter-api-key
```

API-Key generieren (z. B. lokal oder mit `python3` auf dem Server):

```bash
python3 -c "import secrets; print(secrets.token_urlsafe(32))"
```

## 5. Firewall (empfohlen: `ufw`)

Die API soll normalerweise **nicht** direkt aus dem Internet auf Port 8000
erreichbar sein, sondern nur über einen Reverse Proxy mit TLS (siehe
Schritt 7). Deshalb Port 8000 nicht öffentlich freigeben:

```bash
sudo apt install -y ufw
sudo ufw allow OpenSSH
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable
sudo ufw status
```

## 6. Starten

```bash
cd /opt/uptime-kuma-domain-api
docker compose up --build -d
docker compose logs -f
```

Test lokal auf dem Server:

```bash
curl http://localhost:8000/health
# {"status":"ok"}

curl -H "X-API-Key: dein-generierter-api-key" http://localhost:8000/domains
```

Der Container ist mit `restart: unless-stopped` konfiguriert und startet
damit automatisch nach einem Server-Neustart mit, solange der
Docker-Dienst läuft (das ist nach der Installation aus Schritt 2 bereits
standardmäßig der Fall — prüfbar mit `systemctl is-enabled docker`).

## 7. Reverse Proxy mit TLS (empfohlen für Zugriff aus dem Internet)

Bevor dein CRM die API über das Internet anspricht, sollte HTTPS davor
geschaltet sein. Am einfachsten mit [Caddy](https://caddyserver.com/), das
Zertifikate automatisch besorgt und erneuert:

```bash
sudo apt install -y debian-keyring debian-archive-keyring apt-transport-https curl
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' | \
  sudo gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' | \
  sudo tee /etc/apt/sources.list.d/caddy-stable.list
sudo apt update
sudo apt install -y caddy
```

Voraussetzung: Ein DNS-A-Record (z. B. `api.deine-domain.tld`) zeigt bereits
auf die IP dieses Servers.

`/etc/caddy/Caddyfile` anpassen:

```
api.deine-domain.tld {
    reverse_proxy localhost:8000
}
```

Neu laden:

```bash
sudo systemctl reload caddy
```

Danach ist die API unter `https://api.deine-domain.tld` erreichbar, dein
CRM sollte diese URL statt `http://server-ip:8000` verwenden.

## 8. Updates einspielen

Bei Variante B (Git):

```bash
cd /opt/uptime-kuma-domain-api
git pull
docker compose up --build -d
```

Bei Variante A (ZIP): neue ZIP hochladen, altes Verzeichnis ersetzen (`.env`
vorher sichern), dann wieder `docker compose up --build -d`.

## Kurzübersicht

| Was | Wo |
|---|---|
| Projektdateien | `/opt/uptime-kuma-domain-api` |
| Konfiguration | `/opt/uptime-kuma-domain-api/.env` (nicht ins Git/Zip-Backup, enthält Passwörter) |
| API lokal auf dem Server | `http://localhost:8000` |
| API von außen (nach Schritt 7) | `https://api.deine-domain.tld` |
| Logs | `docker compose logs -f` im Projektverzeichnis |
