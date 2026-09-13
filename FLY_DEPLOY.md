# Fly.io Deployment Guide — Claim Auditor Service (T-12)

**Operator task**: Deploy the Auditor HTTP service to Fly.io and configure n8n cloud to call it.

---

## Prerequisites

- Fly.io account: https://fly.io (free tier available)
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
flyctl apps create claim-auditor
```

Output will show:
```
Created app claim-auditor in organization <your-org>
```

Note the **app name** (e.g. `claim-auditor`). This will become `claim-auditor-<random>.fly.dev`.

Verify `fly.toml` exists in the repo root (already committed).

---

## Step 3: Create Persistent Volume

Auditor service requires `data/memory.db` to persist across deployments (§23: 30-day ratchet).

```bash
flyctl volumes create data --size 1 --app claim-auditor --region nrt
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

Store `CLAIM_AUDITOR_TOKEN` as a Fly secret (read from `$CLAIM_AUDITOR_TOKEN` env var locally):

```bash
# Option A: if you have the token value ready
flyctl secrets set CLAIM_AUDITOR_TOKEN=your-bearer-token-value --app claim-auditor

# Option B: interactive input (more secure)
echo -n "Enter CLAIM_AUDITOR_TOKEN: "
read -s token
flyctl secrets set CLAIM_AUDITOR_TOKEN="$token" --app claim-auditor
```

Verify:
```bash
flyctl secrets list --app claim-auditor
# Shows: CLAIM_AUDITOR_TOKEN (value hidden)
```

---

## Step 5: Deploy

```bash
flyctl deploy -c fly.toml --app claim-auditor
```

**First deployment takes 2–3 minutes**. Output shows:
```
...
==> Pushing image to registry
image size: 123 MB
Successfully pushed...

==> Monitoring deployment
v0 deployed successfully

App 'claim-auditor' is live!
https://claim-auditor-abc123.fly.dev
```

**Save the hostname**: `https://claim-auditor-abc123.fly.dev` (yours will be different).

---

## Step 6: Test Health Endpoint

```bash
curl -s https://claim-auditor-abc123.fly.dev/health | jq .
```

**Expected output**:
```json
{
  "status": "ok",
  "service": "claim-auditor-gate",
  "memory_db": true,
  "auth": true
}
```

If `"auth": true`, the `CLAIM_AUDITOR_TOKEN` was read. ✅

If `"auth": false`, token not set or invalid. Re-run Step 4.

---

## Step 7: Record Hostname

Update `docs/requirements.md` §28-3 with the actual hostname:

```markdown
### 28-3. 配置 (Updated T-12)

| 環境 | 配置 | n8n 側設定 |
|---|---|---|
| 本番（n8n cloud） | **Fly.io** — ホスト: `https://claim-auditor-abc123.fly.dev` (決定日: 2026-09-13, デプロイ完了: YYYY-MM-DD) | ... |
```

---

## Step 8: Configure n8n Cloud Variables (T-13)

**Do NOT complete this step yet** — it is operator task T-13.

Once the hostname is confirmed, log into n8n.cloud and set Variables:

```
CLAIM_AUDITOR_URL  = https://claim-auditor-abc123.fly.dev
CLAIM_AUDITOR_MODE = report_only
CLAIM_AUDITOR_TOKEN = <same value as Step 4>
```

(Details in SETUP_GUIDE Step 2–3)

---

## Troubleshooting

### Deployment fails: "Pulled image not found"
- Ensure `Dockerfile` exists and is valid
- Check `docker build .` locally first

### /health returns 502 Bad Gateway
- SSH into the container: `flyctl ssh console -a claim-auditor`
- Check logs: `docker logs <container_id>`
- Restart: `flyctl restart --app claim-auditor`

### CLAIM_AUDITOR_TOKEN not read
- Verify: `flyctl secrets list --app claim-auditor`
- Re-run Step 4 if missing
- Redeploy: `flyctl deploy --app claim-auditor`

### memory.db keeps resetting
- Volume mount failed: `flyctl volumes list -a claim-auditor`
- Ensure `data` volume exists and is mounted at `/app/data` in `fly.toml`

### Network: cannot reach from n8n cloud
- Check firewall: `flyctl status -a claim-auditor` → "Healthy" status
- Test from a different network: `curl https://claim-auditor-abc123.fly.dev/health`
- If only n8n cloud can't reach: n8n outbound network policy issue (contact n8n support)

---

## Rollback

If deployment breaks:

```bash
# View releases
flyctl releases -a claim-auditor

# Rollback to previous version
flyctl releases rollback --app claim-auditor
```

---

## Cost Estimate

- **Compute**: $0 (free tier: 3 shared-cpu-1x 256MB VMs)
- **Volume**: $0.15 / GB-month (1 GB → ~$1.50/month)
- **Bandwidth**: $0.02 / GB (typical: <100MB/month → <$2/month)

**Total**: ~$2–5/month for small-scale deployment.

---

## Cleanup (if needed)

Destroy the app and volume:

```bash
flyctl apps destroy claim-auditor
```

(Fly will prompt for confirmation before deletion.)
