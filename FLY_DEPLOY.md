# Fly.io Deployment Guide — AI Navi Auditor Gate Service (T-12)

**Operator task**: Deploy the Auditor HTTP service to Fly.io and configure n8n cloud to call it.

---

## Prerequisites

- Fly.io account: https://fly.io — pricing: verify current Fly.io pricing before deploy
- Fly CLI installed locally: `brew install flyctl` (macOS) or https://fly.io/docs/getting-started/installing-flyctl/
- Git repository cloned and committed (this repo)

---

## Step 1: Fly.io CLI Setup

```bash
flyctl auth login
# Opens browser for OAuth login
# Login with your Fly.io account
```

Verify:
```bash
flyctl version
flyctl auth whoami
```

---

## Step 2: Create Fly App

```bash
cd /path/to/ai-solution-
flyctl apps create ainavi-auditor-gate
```

Output will show:
```
Created app ainavi-auditor-gate in organization <your-org>
```

The app name is `ainavi-auditor-gate` (renamed from `claim-auditor` to avoid confusion with the Claim-Auditor repository). The hostname will be `ainavi-auditor-gate.fly.dev`.

Verify `fly.toml` exists in the repo root (already committed).

---

## Step 3: Create Persistent Volume

Auditor service requires `data/memory.db` to persist across deployments (§23: 30-day ratchet).

```bash
flyctl volumes create data --size 1 --app ainavi-auditor-gate --region nrt
# Adjust region: nrt (Tokyo), syd (Sydney), iad (Washington DC), etc.
```

Output:
```
        ID: vol_mq2z...
      Name: data
    Status: created
      Size: 1 GB
    Region: nrt
```

---

## Step 4: Set Secrets

Store `AINAVI_GATE_TOKEN` as a Fly secret (read from `$AINAVI_GATE_TOKEN` env var locally):

```bash
# Option A: if you have the token value ready
flyctl secrets set AINAVI_GATE_TOKEN=your-bearer-token-value --app ainavi-auditor-gate

# Option B: interactive input (more secure)
echo -n "Enter AINAVI_GATE_TOKEN: "
read -s token
flyctl secrets set AINAVI_GATE_TOKEN="$token" --app ainavi-auditor-gate
```

Verify:
```bash
flyctl secrets list --app ainavi-auditor-gate
# Shows: AINAVI_GATE_TOKEN (value hidden)
```

---

## Step 5: Deploy

```bash
flyctl deploy -c fly.toml --app ainavi-auditor-gate
```

Note: `[http_service]` in `fly.toml` exposes the app on 443 with `force_https` — no `[[services]]` port block is
needed (that config was replaced; see §28-3).

**First deployment takes 2–3 minutes**. Output shows:
```
...
==> Pushing image to registry
image size: 123 MB
Successfully pushed...

==> Monitoring deployment
v0 deployed successfully

App 'ainavi-auditor-gate' is live!
https://ainavi-auditor-gate.fly.dev
```

**Save the hostname**: `https://ainavi-auditor-gate.fly.dev` (yours will be different).

---

## Step 6: Test Health Endpoint

```bash
curl -s https://ainavi-auditor-gate.fly.dev/health | jq .
```

**Expected output**:
```json
{
  "status": "ok",
  "service": "ainavi-auditor-gate",
  "memory_db": true,
  "auth": true
}
```

**Pass condition**: `"auth": true` **and** `"memory_db": true`.

If `"auth": false`, token not set or invalid. Re-run Step 4.

If `"memory_db": false`, the volume is mounted root-owned while the container runs as user `auditor`.
Remediation:
```bash
flyctl ssh console -a ainavi-auditor-gate -C "chown -R auditor /app/data"
flyctl restart --app ainavi-auditor-gate
```
Then re-check `/health`.

---

## Step 7: Record Hostname

Update `docs/requirements.md` §28-3 with the actual hostname:

```markdown
### 28-3. 配置 (Updated T-12)

| 環境 | 配置 | n8n 側設定 |
|---|---|---|
| 本番（n8n cloud） | **Fly.io** — ホスト: `https://ainavi-auditor-gate.fly.dev` (決定日: 2026-09-13, デプロイ完了: YYYY-MM-DD) | ... |
```

---

## Step 8: Configure n8n Cloud Variables (T-13)

**Do NOT complete this step yet** — it is operator task T-13.

Once the hostname is confirmed, log into n8n.cloud and set Variables:

```
AINAVI_GATE_URL  = https://ainavi-auditor-gate.fly.dev
AINAVI_GATE_MODE = report_only
AINAVI_GATE_TOKEN = <same value as Step 4>
```

(Details in SETUP_GUIDE Step 2–3)

---

## Troubleshooting

### Deployment fails: "Pulled image not found"
- Ensure `Dockerfile` exists and is valid
- Check `docker build .` locally first

### /health returns 502 Bad Gateway
- SSH into the container: `flyctl ssh console -a ainavi-auditor-gate`
- Check logs: `docker logs <container_id>`
- Restart: `flyctl restart --app ainavi-auditor-gate`

### AINAVI_GATE_TOKEN not read
- Verify: `flyctl secrets list --app ainavi-auditor-gate`
- Re-run Step 4 if missing
- Redeploy: `flyctl deploy --app ainavi-auditor-gate`

### memory.db keeps resetting
- Volume mount failed: `flyctl volumes list -a ainavi-auditor-gate`
- Ensure the `data` volume exists and `fly.toml` has `[[mounts]] source = "data", destination = "/app/data"`
  (matching `AINAVI_GATE_MEMORY_DB=/app/data/memory.db` in `[env]`)
- If `/health` shows `"memory_db": false`, the volume mounted root-owned while the container runs as user
  `auditor`: `flyctl ssh console -a ainavi-auditor-gate -C "chown -R auditor /app/data"`, then
  `flyctl restart --app ainavi-auditor-gate` and re-check `/health`

### Network: cannot reach from n8n cloud
- Check firewall: `flyctl status -a ainavi-auditor-gate` → "Healthy" status
- Test from a different network: `curl https://ainavi-auditor-gate.fly.dev/health`
- If only n8n cloud can't reach: n8n outbound network policy issue (contact n8n support)

---

## Rollback

If deployment breaks:

```bash
# View releases
flyctl releases -a ainavi-auditor-gate

# Rollback to previous version
flyctl releases rollback --app ainavi-auditor-gate
```

---

## Cost Estimate (unverified estimate — confirm against current Fly.io pricing before relying on it)

- **Compute**: 3 shared-cpu-1x 256MB VMs included at no cost under Fly.io's current plan (verify before relying on it)
- **Volume**: $0.15 / GB-month (1 GB → ~$1.50/month)
- **Bandwidth**: $0.02 / GB (typical: <100MB/month → <$2/month)

**Total**: ~$2–5/month for small-scale deployment.

---

## Cleanup (if needed)

Destroy the app and volume:

```bash
flyctl apps destroy ainavi-auditor-gate
```

(Fly will prompt for confirmation before deletion.)
