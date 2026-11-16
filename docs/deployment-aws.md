# Deployment on one AWS EC2 instance (AWS Academy)

The server only **serves** precomputed results: ingestion and analysis run
offline on a laptop, and the database is shipped as a `pg_dump`. This keeps
the instance small and avoids downloading 226 MB of OSM data on it.

## 0. What you need

- An AWS Academy Learner Lab session (credentials are temporary; the lab
  stops after a few hours, but the instance and its EBS volume persist).
- The GitHub repository with the `Build images` workflow enabled. Images are
  pushed to `ghcr.io/<owner>/<repo>-{api,frontend}`. Make the packages public
  (GitHub → Packages → Settings), or log in to GHCR on the server with a token.

## 1. Launch the instance

| Setting | Value |
|---|---|
| AMI | Ubuntu Server 24.04 LTS (x86_64). Our images are built for `linux/amd64` |
| Type | `t3.medium` (2 vCPU, 4 GB). `t3.small` works if you skip on-demand optimisation |
| Storage | 20 GB gp3 |
| Key pair | `vockey` (Learner Lab) or your own |
| Security group | inbound **22** from your IP, **80** from 0.0.0.0/0. Do **not** open 5432 |

Allocate an **Elastic IP** and associate it, so the address survives lab restarts.

## 2. Install Docker

```bash
ssh -i labsuser.pem ubuntu@<ELASTIC_IP>
sudo apt-get update && sudo apt-get install -y ca-certificates curl
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker ubuntu && exit   # log in again so the group applies
```

## 3. Configure

```bash
git clone https://github.com/<owner>/<repo>.git accessastana && cd accessastana
cp .env.example .env
nano .env
```

Set at least:

```
POSTGRES_USER=accessastana
POSTGRES_PASSWORD=<long random string>
POSTGRES_DB=accessastana
IMAGE_PREFIX=ghcr.io/<owner>/<repo>
IMAGE_TAG=latest            # or a commit SHA for a pinned release
PUBLIC_ORIGIN=http://<ELASTIC_IP>
```

## 4. Produce the data (on your laptop)

```bash
docker compose up -d db
uv run accessastana db-upgrade
uv run --extra ingest accessastana pipeline --city astana   # ~5 min
./scripts/export_db.sh                                      # → backups/accessastana-YYYYMMDD.dump
scp -i labsuser.pem backups/accessastana-*.dump ubuntu@<ELASTIC_IP>:accessastana/backups/
```

## 5. Start and restore

```bash
docker compose -f docker-compose.prod.yml --env-file .env pull
docker compose -f docker-compose.prod.yml --env-file .env up -d   # api runs `alembic upgrade head` on start
./scripts/restore_db.sh backups/accessastana-YYYYMMDD.dump
curl http://localhost/api/health                                 # {"status":"ok","db":"ok"}
```

Open `http://<ELASTIC_IP>/` in a browser. The first `/api/reports/astana.pdf`
request builds the PDF (a few seconds) and caches it in the `reports` volume.

## 6. Update

```bash
git pull
docker compose -f docker-compose.prod.yml --env-file .env pull
docker compose -f docker-compose.prod.yml --env-file .env up -d
# new data: repeat step 4 and ./scripts/restore_db.sh <new dump>
```

## 7. Operations

- **Logs:** `docker compose -f docker-compose.prod.yml logs -f api` (rotated, 3 × 10 MB per service).
- **Backups:** the DB can be rebuilt from the offline pipeline, so the dump
  file is the backup. Keep the latest dump in S3 or on the laptop.
- **Memory:** about 1.2 GB in total (PostGIS ≈ 300 MB, API ≈ 500 MB with the
  Astana graph loaded, nginx ≈ 20 MB).
- **HTTPS (optional):** put Caddy in front, or use an AWS ALB with an ACM
  certificate. Learner Lab often restricts Route 53/ACM, so HTTP on the Elastic
  IP is acceptable for the course demo.
- **Cost control:** stop the instance when not presenting. An Elastic IP
  attached to a running instance is free, but a detached one is billed.
