#!/usr/bin/env bash
# Reverse SSH tunnel: cho cvmatch-ai tren may GPU dung Postgres (cvmatch-db) chay o may local.
#   may GPU  <docker0-ip>:REMOTE_PORT  --ssh -R-->  may local 127.0.0.1:LOCAL_PORT
# Chi bind tren bridge docker0 cua may GPU (khong public Internet). Tu ket noi lai khi rot.
#
#   ./infra/gpu-remote/db-tunnel.sh <host> <ssh-port> [start|stop|status|run]
#     start  (mac dinh) chay nen, log o $STATE_DIR
#     run    chay foreground (Ctrl+C de dung)
#
# Bien moi truong: GPU_DB_TUNNEL_PORT (mac dinh 15433), CVMATCH_DB_PORT (mac dinh 5433), SSH_USER (root)
set -euo pipefail

[[ $# -ge 2 ]] || { sed -n '2,11p' "$0" | sed 's/^# \{0,1\}//'; exit 1; }
HOST=$1; SSH_PORT=$2; ACTION=${3:-start}
USER_NAME=${SSH_USER:-root}
REMOTE_PORT=${GPU_DB_TUNNEL_PORT:-15433}
LOCAL_PORT=${CVMATCH_DB_PORT:-5433}
STATE_DIR=${XDG_RUNTIME_DIR:-/tmp}/hirelens-gpu
PID_FILE="$STATE_DIR/db-tunnel-$HOST-$SSH_PORT.pid"
LOG_FILE="$STATE_DIR/db-tunnel-$HOST-$SSH_PORT.log"
mkdir -p "$STATE_DIR"

SSH=(ssh -p "$SSH_PORT" -o BatchMode=yes -o StrictHostKeyChecking=accept-new
     -o ServerAliveInterval=15 -o ServerAliveCountMax=3 -o ExitOnForwardFailure=yes)

running() { [[ -f $PID_FILE ]] && kill -0 "$(cat "$PID_FILE")" 2>/dev/null; }

loop() {
  while true; do
    bridge=$("${SSH[@]}" "$USER_NAME@$HOST" "ip -4 -o addr show docker0 | awk '{print \$4}' | cut -d/ -f1" 2>/dev/null || true)
    if [[ -n $bridge ]]; then
      echo "$(date '+%F %T') tunnel $bridge:$REMOTE_PORT -> 127.0.0.1:$LOCAL_PORT"
      "${SSH[@]}" -N -R "$bridge:$REMOTE_PORT:127.0.0.1:$LOCAL_PORT" "$USER_NAME@$HOST" || true
      echo "$(date '+%F %T') tunnel rot, ket noi lai sau 5s"
    else
      echo "$(date '+%F %T') chua SSH duoc, thu lai sau 5s"
    fi
    sleep 5
  done
}

case $ACTION in
  run) loop ;;
  start)
    if running; then echo "Tunnel dang chay (pid $(cat "$PID_FILE"))."; exit 0; fi
    nohup "$0" "$HOST" "$SSH_PORT" run >>"$LOG_FILE" 2>&1 &
    echo $! >"$PID_FILE"
    echo "Da bat tunnel (pid $!), log: $LOG_FILE" ;;
  stop)
    if running; then
      pid=$(cat "$PID_FILE")
      pkill -P "$pid" 2>/dev/null || true; kill "$pid" 2>/dev/null || true
      echo "Da tat tunnel."
    else
      echo "Tunnel khong chay."
    fi
    rm -f "$PID_FILE" ;;
  status)
    if running; then echo "Dang chay (pid $(cat "$PID_FILE")). Log: $LOG_FILE"; tail -3 "$LOG_FILE"; else echo "Khong chay."; exit 1; fi ;;
  *) echo "Hanh dong khong hop le: $ACTION"; exit 1 ;;
esac
