# Deploying to the Raspberry Pi (bot + Alexa + stable tunnel)

Guided deploy of the SQLite build to the Pi, with a **stable Cloudflare named tunnel**
so the Alexa endpoint survives reboots. Run these on the Pi (over SSH or directly).

Placeholders: `<pi-user>` = your Pi login, `<subdomain>` = e.g. `rocky.yourdomain.com`,
`<tunnel-name>` = e.g. `rocky`.

---

## 1. Pull the new code

```bash
cd ~/<path-to>/telegram-alexa-planner
git pull
```

If `git pull` complains about local changes (the Pi ran the old Sheets version):
```bash
git stash         # or: git checkout -- .
git pull
```

## 2. Dependencies

The old version already had `python-telegram-bot`, `fastapi`, `uvicorn`. The SQLite build
adds **no new runtime deps** (`sqlite3` is stdlib). Only install if you hit an ImportError:
```bash
pip3 install -r requirements.txt        # add --break-system-packages on Debian 12+ if needed
```

## 3. Create the database

The Pi starts with an empty SQLite file (`data/planner.db`). Seed the reference data so the
bot's `/add` has categories/types (you'll add real tasks yourself later):
```bash
python3 -m core.seed         # creates default types + categories
```
> To instead pull your real tasks from Google Sheets: `python3 -m scripts.migrate_from_sheets`
> (needs `SPREADSHEET_ID` + `GOOGLE_CREDS_JSON` in `.env`, which the old version already had).

## 4. Restart the bot service

The unit already exists (`telegram-alexa-planner.service`). Pick it back up:
```bash
sudo systemctl enable --now telegram-alexa-planner.service
systemctl status telegram-alexa-planner.service     # want: active (running)
```
Confirm the Alexa server is listening locally:
```bash
curl -s -X POST localhost:8001/alexa -H 'Content-Type: application/json' \
  -d '{"request":{"type":"LaunchRequest"},"session":{"attributes":{}}}'
```
You should get back the welcome SSML.

## 5. Stable Cloudflare named tunnel

Prereq: your domain is active on Cloudflare (buying via **Cloudflare Registrar** puts it on
Cloudflare automatically; a GoDaddy domain needs its nameservers pointed at Cloudflare first).

```bash
# install cloudflared (Debian/RPi)
curl -L https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-arm64 \
  -o /usr/local/bin/cloudflared && sudo chmod +x /usr/local/bin/cloudflared

cloudflared tunnel login                              # browser: authorize your zone
cloudflared tunnel create <tunnel-name>               # prints a UUID + writes a .json cred file
cloudflared tunnel route dns <tunnel-name> <subdomain>
```
Put `deploy/cloudflared-config.yml` at `~/.cloudflared/config.yml` and fill in the placeholders
(`<tunnel-id>` is the UUID from `create`). Then run it as a service so it survives reboots:
```bash
sudo cloudflared service install
sudo systemctl enable --now cloudflared
```
Test the public URL:
```bash
curl -s -X POST https://<subdomain>/alexa -H 'Content-Type: application/json' \
  -d '{"request":{"type":"IntentRequest","intent":{"name":"GetMajorTasksIntent","slots":{}}},"session":{"attributes":{}}}'
```

## 6. Point Alexa at the stable URL (one time, permanent)

Alexa Developer Console → your skill → **Build → Endpoint → HTTPS**:
- Default Region: `https://<subdomain>/alexa`
- Cert: **"My development endpoint has a certificate from a trusted certificate authority"**
- **Save Endpoints**

Also make sure the **interaction model** is the one from `alexa/interaction_model.json`
(invocation `captain rocky`) — Build → JSON Editor → paste → Save → Build Model.

Done. `https://<subdomain>/alexa` is now permanent — reboots and restarts no longer change it.

---

## Notes / hardening
- ⚠️ The `/alexa` endpoint does **not** yet verify Amazon's request signature. Fine for a
  personal skill, but add signature verification before treating it as production.
- Only `main.py` (bot + Alexa on :8001) is deployed here. The web app (`api/app.py` on :8000 +
  `frontend/dist`) is a separate add-on for later (#7) — uncomment its hostname in the tunnel
  config when you deploy it.
