#!/usr/bin/env bash
# Move Docker's large system storage onto the DATA disk, preserving the originals.
set -euo pipefail
if [ "${EUID}" -ne 0 ]; then
  echo "Run with sudo: sudo bash backend/scripts/setup-storage.sh" >&2
  exit 1
fi
PROJECT_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)"
DATA_MOUNT=/run/media/long/DATA
mountpoint -q "$DATA_MOUNT" || { echo 'Mount DATA before continuing.' >&2; exit 1; }
case "$PROJECT_ROOT/" in "$DATA_MOUNT/"*) ;; *) echo 'Project must reside on DATA.' >&2; exit 1;; esac
command -v rsync >/dev/null || { echo 'Install rsync first: sudo apt install rsync' >&2; exit 1; }
STORAGE="$PROJECT_ROOT/data"
mkdir -p "$STORAGE/runtime"/{mysql/identity,mysql/recruitment,mysql/interview,uploads,interview-huggingface,interview-output,postgres/cvmatch,cvmatch-huggingface}
DOCKER_TARGET="$STORAGE/docker-engine"
CONTAINERD_TARGET="$STORAGE/containerd"
DOCKER_SOURCE="$(python3 - <<'PY'
import json
from pathlib import Path
p=Path('/etc/docker/daemon.json')
print(json.loads(p.read_text()).get('data-root','/var/lib/docker') if p.exists() else '/var/lib/docker')
PY
)"
CONTAINERD_SOURCE="$(python3 - <<'PY'
import re
from pathlib import Path
p=Path('/etc/containerd/config.toml')
s=p.read_text() if p.exists() else ''
top=s.split('[',1)[0]
m=re.search(r'''(?m)^\s*root\s*=\s*["']([^"']+)["']''',top)
print(m.group(1) if m else '/var/lib/containerd')
PY
)"
# Refuse an ambiguous merge, before stopping any services.
for kind in docker containerd; do
  if [ "$kind" = docker ]; then src="$DOCKER_SOURCE"; dst="$DOCKER_TARGET"; else src="$CONTAINERD_SOURCE"; dst="$CONTAINERD_TARGET"; fi
  if [ "$src" != "$dst" ] && [ -d "$dst" ] && [ -n "$(find "$dst" -mindepth 1 -maxdepth 1 -print -quit)" ]; then
    echo "Destination already contains data: $dst. Review it before migrating." >&2; exit 1
  fi
done
# Stop only units that exist. No old source directory is deleted.
for unit in docker.socket docker.service containerd.service; do
  if systemctl cat "$unit" >/dev/null 2>&1; then systemctl stop "$unit"; fi
done
for kind in docker containerd; do
  if [ "$kind" = docker ]; then src="$DOCKER_SOURCE"; dst="$DOCKER_TARGET"; else src="$CONTAINERD_SOURCE"; dst="$CONTAINERD_TARGET"; fi
  mkdir -p "$dst"
  if [ "$src" != "$dst" ] && [ -d "$src" ]; then rsync -aHAX --numeric-ids "$src/" "$dst/"; fi
done
python3 - "$DOCKER_TARGET" "$CONTAINERD_TARGET" <<'PY'
import json,re,sys,shutil
from pathlib import Path
p=Path('/etc/docker/daemon.json');p.parent.mkdir(parents=True,exist_ok=True)
config=json.loads(p.read_text()) if p.exists() else {}
if p.exists() and not p.with_suffix('.json.before-data').exists():shutil.copy2(p,p.with_suffix('.json.before-data'))
config['data-root']=sys.argv[1];p.write_text(json.dumps(config,indent=2)+'\n')
p=Path('/etc/containerd/config.toml');p.parent.mkdir(parents=True,exist_ok=True)
s=p.read_text() if p.exists() else 'version = 2\n'
if p.exists() and not p.with_suffix('.toml.before-data').exists():shutil.copy2(p,p.with_suffix('.toml.before-data'))
parts=s.split('[',1);top=re.sub(r'(?m)^\s*root\s*=.*\n?', '', parts[0])
s='root = '+json.dumps(sys.argv[2])+'\n'+top+('['+parts[1] if len(parts)>1 else '')
p.write_text(s)
PY
for unit in docker.service containerd.service; do
  mkdir -p "/etc/systemd/system/$unit.d"
  printf '[Unit]\nRequiresMountsFor=%s\n' "$STORAGE" > "/etc/systemd/system/$unit.d/data-storage.conf"
done
systemctl daemon-reload
for unit in containerd.service docker.service; do
  if systemctl cat "$unit" >/dev/null 2>&1; then systemctl start "$unit"; fi
done
echo "Docker images/build cache: $DOCKER_TARGET"
echo "Containerd images: $CONTAINERD_TARGET"
echo "Project databases/uploads/model cache: $STORAGE/runtime"
echo 'Original storage was preserved; inspect the running stack before cleaning old copies.'
