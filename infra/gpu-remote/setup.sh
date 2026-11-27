#!/usr/bin/env bash
# Dung lai 3 service AI (interview-ai, cv-extraction-ai, cvmatch-ai) tren may GPU thue.
# Chay tu may local, o bat ky thu muc nao. Xem docs/GPU_REMOTE_HOSTING.md.
# Chi day ai-service len may GPU. DB cua cvmatch (cvmatch-db) chay o may local,
# cvmatch-ai noi ve qua reverse SSH tunnel (db-tunnel.sh) -> may local phai bat khi dung.
#
#   ./infra/gpu-remote/setup.sh <host> <ssh-port> [tuy chon]
#
# Tuy chon:
#   --user U          tai khoan SSH (mac dinh: root)
#   --port-base N     cong public dau tien cua dai cong rieng (mac dinh: 42000)
#                     interview = N, extraction = N+1, cvmatch = N+3
#   --cuda-arch N     compute capability GPU (mac dinh: 86 = RTX 3090/A4000/A10)
#   --keys-only       chi cai SSH key trong infra/gpu-remote/team_keys/ roi thoat
#   --no-build        khong build lai image (chi sync + up)
#   --no-wait         khong cho /health
set -euo pipefail

usage() { sed -n '2,18p' "$0" | sed 's/^# \{0,1\}//'; exit 1; }
[[ $# -ge 2 ]] || usage

HOST=$1; SSH_PORT=$2; shift 2
USER_NAME=root; PORT_BASE=42000; CUDA_ARCH=86
KEYS_ONLY=0; BUILD=1; WAIT=1
while [[ $# -gt 0 ]]; do
  case $1 in
    --user) USER_NAME=$2; shift 2 ;;
    --port-base) PORT_BASE=$2; shift 2 ;;
    --cuda-arch) CUDA_ARCH=$2; shift 2 ;;
    --keys-only) KEYS_ONLY=1; shift ;;
    --no-build) BUILD=0; shift ;;
    --no-wait) WAIT=0; shift ;;
    *) echo "Tuy chon khong hop le: $1"; usage ;;
  esac
done

REPO=$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)
HERE="$REPO/infra/gpu-remote"
REMOTE_DIR=/root/recruit_system
TARGET="$USER_NAME@$HOST"
SSH_OPTS=(-p "$SSH_PORT" -o StrictHostKeyChecking=accept-new -o ServerAliveInterval=30)
rssh() { ssh "${SSH_OPTS[@]}" -o BatchMode=yes "$TARGET" "$@"; }
RSYNC_SSH="ssh -p $SSH_PORT -o StrictHostKeyChecking=accept-new -o BatchMode=yes"

P_INTERVIEW=$PORT_BASE
P_EXTRACTION=$((PORT_BASE + 1))
P_CVMATCH=$((PORT_BASE + 3))

step() { printf '\n\033[1;36m==> %s\033[0m\n' "$*"; }
die() { printf '\033[1;31mLOI: %s\033[0m\n' "$*" >&2; exit 1; }

# ---------- 1. Ket noi SSH ----------
step "Ket noi $TARGET:$SSH_PORT"
# May thue lai co host key moi -> xoa khoa cu de SSH khong bao loi.
ssh-keygen -R "[$HOST]:$SSH_PORT" >/dev/null 2>&1 || true
if ! rssh true 2>/dev/null; then
  echo "Chua dang nhap duoc bang key. Cai key cua ban (nhap mat khau root tren trang quan ly):"
  ssh-copy-id "${SSH_OPTS[@]}" "$TARGET"
  rssh true || die "Van khong SSH duoc bang key."
fi

# ---------- 2. SSH key cua thanh vien ----------
step "Cai SSH key trong infra/gpu-remote/team_keys/"
shopt -s nullglob
KEY_FILES=("$HERE"/team_keys/*.pub)
if [[ ${#KEY_FILES[@]} -gt 0 ]]; then
  cat "${KEY_FILES[@]}" | rssh 'mkdir -p ~/.ssh && chmod 700 ~/.ssh && touch ~/.ssh/authorized_keys &&
    while IFS= read -r k; do [ -n "$k" ] && { grep -qxF "$k" ~/.ssh/authorized_keys || echo "$k" >> ~/.ssh/authorized_keys; }; done &&
    chmod 600 ~/.ssh/authorized_keys && echo "authorized_keys: $(wc -l < ~/.ssh/authorized_keys) key"'
else
  echo "Khong co file .pub nao, bo qua."
fi
[[ $KEYS_ONLY -eq 1 ]] && { echo "Xong (--keys-only)."; exit 0; }

# ---------- 3. Kiem tra dau vao local ----------
step "Kiem tra file can thiet tren may local"
ENV_FILE="$REPO/.env"
[[ -f $ENV_FILE ]] || die "Thieu $ENV_FILE (can SERVICE_TOKEN, CVMATCH_HMAC_KEY)."
getenv() { grep -E "^$1=" "$ENV_FILE" | tail -1 | cut -d= -f2- || true; }
SERVICE_TOKEN=$(getenv SERVICE_TOKEN)
CVMATCH_HMAC_KEY=$(getenv CVMATCH_HMAC_KEY)
CVMATCH_DB_PASSWORD=$(getenv CVMATCH_DB_PASSWORD)
CV_MODEL_VERSION=$(getenv CV_MODEL_VERSION); CV_MODEL_VERSION=${CV_MODEL_VERSION:-v4}
[[ -n $SERVICE_TOKEN ]] || die "SERVICE_TOKEN trong .env dang trong."
[[ -n $CVMATCH_HMAC_KEY ]] || die "CVMATCH_HMAC_KEY trong .env dang trong (tao: openssl rand -hex 32)."

GGUF_NAME="model-$CV_MODEL_VERSION-q4_k_m.gguf"
GGUF=""
for c in "$REPO/ai-service/models/cv-extraction/$GGUF_NAME" "$REPO/ai-service/extraction/merged_model/$GGUF_NAME"; do
  [[ -f $c ]] && { GGUF=$c; break; }
done
[[ -n $GGUF ]] || die "Khong tim thay $GGUF_NAME trong ai-service/models/cv-extraction/ hoac ai-service/extraction/merged_model/."
[[ -d $REPO/ai-service/matching/kb-builder/out/snapshot ]] || die "Thieu KB snapshot ai-service/matching/kb-builder/out/snapshot/."
echo "Model: ${GGUF#$REPO/}"

# ---------- 3b. cvmatch-db o may local ----------
step "Bat cvmatch-db (Postgres + pgvector) o may local"
LOCAL_STORAGE=$(getenv STORAGE_ROOT)
[[ -n $LOCAL_STORAGE ]] || die "STORAGE_ROOT trong .env dang trong (thu muc luu du lieu local)."
DB_PORT=$(getenv CVMATCH_DB_PORT); DB_PORT=${DB_PORT:-5433}
TUNNEL_PORT=15433
mkdir -p "$LOCAL_STORAGE/postgres/cvmatch"
(cd "$REPO" && docker compose --profile match up -d cvmatch-db)
for _ in $(seq 1 30); do
  (cd "$REPO" && docker compose exec -T cvmatch-db pg_isready -U cvmatch -d cvmatch >/dev/null 2>&1) && break
  sleep 2
done
(cd "$REPO" && docker compose exec -T cvmatch-db pg_isready -U cvmatch -d cvmatch) || die "cvmatch-db local chua san sang."

# ---------- 4. Kiem tra may GPU ----------
step "Kiem tra GPU, Docker, NVIDIA runtime"
rssh 'set -e
  nvidia-smi --query-gpu=name,driver_version,memory.total --format=csv,noheader
  command -v rsync >/dev/null || { apt-get update -qq && apt-get install -y -qq rsync >/dev/null; }
  command -v docker >/dev/null || { echo "Cai Docker..."; curl -fsSL https://get.docker.com | sh >/dev/null; }
  if ! docker info 2>/dev/null | grep -q "Runtimes:.*nvidia"; then
    echo "Cai nvidia-container-toolkit..."
    curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | gpg --dearmor --yes -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg
    curl -fsSL https://nvidia.github.io/libnvidia-container/stable/deb/nvidia-container-toolkit.list \
      | sed "s#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g" \
      > /etc/apt/sources.list.d/nvidia-container-toolkit.list
    apt-get update -qq && apt-get install -y -qq nvidia-container-toolkit >/dev/null
    nvidia-ctk runtime configure --runtime=docker >/dev/null && systemctl restart docker
  fi
  docker --version
  # Cho phep reverse tunnel bind tren IP docker0 (db-tunnel.sh), khong mo ra Internet.
  if ! sshd -T 2>/dev/null | grep -qi "^gatewayports clientspecified"; then
    echo "GatewayPorts clientspecified" > /etc/ssh/sshd_config.d/90-hirelens-tunnel.conf
    systemctl reload ssh 2>/dev/null || systemctl reload sshd
  fi'

# ---------- 5. Dong bo code + model ----------
step "Dong bo code, compose va model len $REMOTE_DIR"
rssh "mkdir -p $REMOTE_DIR/ai-service/models/cv-extraction $REMOTE_DIR/infra/gpu-remote"
rsync -az -e "$RSYNC_SSH" "$REPO/docker-compose.yml" "$REPO/docker-compose.gpu.yml" "$TARGET:$REMOTE_DIR/"
rsync -az -e "$RSYNC_SSH" "$HERE/docker-compose.remote.yml" "$TARGET:$REMOTE_DIR/infra/gpu-remote/"
rsync -az --delete -e "$RSYNC_SSH" \
  --exclude .venv --exclude __pycache__ --exclude .pytest_cache --exclude 'checkpoint-*' \
  --exclude extraction/data --exclude extraction/training --exclude extraction/merged_model \
  --exclude '*.docx' --exclude notebooks --exclude models/cv-extraction \
  "$REPO/ai-service/" "$TARGET:$REMOTE_DIR/ai-service/"
rsync -az --partial --chmod=F644 --info=progress2 -e "$RSYNC_SSH" "$GGUF" "$TARGET:$REMOTE_DIR/ai-service/models/cv-extraction/"

# ---------- 6. .env tren may GPU ----------
step "Ghi $REMOTE_DIR/.env"
{
  echo "SERVICE_TOKEN=$SERVICE_TOKEN"
  echo "CVMATCH_HMAC_KEY=$CVMATCH_HMAC_KEY"
  [[ -n $CVMATCH_DB_PASSWORD ]] && echo "CVMATCH_DB_PASSWORD=$CVMATCH_DB_PASSWORD"
  cat <<EOF
STORAGE_ROOT=/root/data
CV_MODEL_VERSION=$CV_MODEL_VERSION
CV_CUDA_ARCH=$CUDA_ARCH
INTERVIEW_SCORING_MODE=bertscore
CVMATCH_DEVICE=cuda
GPU_INTERVIEW_PORT=$P_INTERVIEW
GPU_EXTRACTION_PORT=$P_EXTRACTION
GPU_CVMATCH_PORT=$P_CVMATCH
GPU_DB_TUNNEL_PORT=$TUNNEL_PORT
# De go ngan "docker compose ps/logs" tren may GPU ma khong can -f/--profile
COMPOSE_FILE=docker-compose.yml:docker-compose.gpu.yml:infra/gpu-remote/docker-compose.remote.yml
COMPOSE_PROFILES=ai,cv-ai,match
EOF
} | rssh "cat > $REMOTE_DIR/.env && chmod 600 $REMOTE_DIR/.env &&
  mkdir -p /root/data/interview-huggingface /root/data/interview-output /root/data/cvmatch-huggingface"

# ---------- 7. Build + chay ----------
COMPOSE="docker compose -f docker-compose.yml -f docker-compose.gpu.yml -f infra/gpu-remote/docker-compose.remote.yml --profile ai --profile cv-ai --profile match"
SERVICES="interview-ai cv-extraction-ai cvmatch-ai"
if [[ $BUILD -eq 1 ]]; then
  step "Build image (lan dau 10-20 phut, log: /root/build.log tren may GPU)"
  rssh "cd $REMOTE_DIR && $COMPOSE build $SERVICES > /root/build.log 2>&1 || { tail -30 /root/build.log; exit 1; }"
fi
step "Bat reverse tunnel DB: may GPU :$TUNNEL_PORT -> local 127.0.0.1:$DB_PORT"
SSH_USER=$USER_NAME GPU_DB_TUNNEL_PORT=$TUNNEL_PORT CVMATCH_DB_PORT=$DB_PORT \
  "$HERE/db-tunnel.sh" "$HOST" "$SSH_PORT" start
ok=0
for _ in $(seq 1 20); do
  rssh "ss -ltn | grep -q ':$TUNNEL_PORT '" && { ok=1; break; }
  sleep 2
done
[[ $ok -eq 1 ]] || die "Tunnel DB chua len. Xem: $HERE/db-tunnel.sh $HOST $SSH_PORT status"

step "Khoi dong service (khong chay cvmatch-db tren may GPU)"
rssh "cd $REMOTE_DIR && $COMPOSE rm -sf cvmatch-db >/dev/null 2>&1; $COMPOSE up -d --no-deps $SERVICES && $COMPOSE ps --format 'table {{.Name}}\t{{.Status}}'"

# ---------- 8. Cho /health ----------
URL_INTERVIEW="http://$HOST:$P_INTERVIEW"
URL_EXTRACTION="http://$HOST:$P_EXTRACTION"
URL_CVMATCH="http://$HOST:$P_CVMATCH"
if [[ $WAIT -eq 1 ]]; then
  step "Cho /health (lan dau tai model bge-m3/BERT co the mat toi 10 phut)"
  for pair in "interview-ai $URL_INTERVIEW" "cv-extraction-ai $URL_EXTRACTION" "cvmatch-ai $URL_CVMATCH"; do
    set -- $pair
    printf '%-18s ' "$1"
    ok=0
    for _ in $(seq 1 80); do
      if curl -fsS --max-time 5 "$2/health" >/dev/null 2>&1; then ok=1; break; fi
      printf '.'; sleep 10
    done
    [[ $ok -eq 1 ]] && echo " OK" || echo " CHUA SAN SANG (xem: ssh -p $SSH_PORT $TARGET 'cd $REMOTE_DIR && $COMPOSE logs --tail 50 $1')"
  done
fi

cat <<EOF

$(printf '\033[1;32m')Xong. Dan cac dong sau vao .env cua backend local:$(printf '\033[0m')

AI_URL=$URL_INTERVIEW
CV_EXTRACTION_URL=$URL_EXTRACTION
CVMATCH_URL=$URL_CVMATCH

DB cvmatch o may local, tunnel phai luon chay khi dung cvmatch-ai:
  $HERE/db-tunnel.sh $HOST $SSH_PORT status|start|stop

SSH tunnel (neu khong muon dung URL public):
  ssh -p $SSH_PORT -N -L 8000:127.0.0.1:8000 -L 8001:127.0.0.1:8001 -L 8003:127.0.0.1:8003 $TARGET
EOF
