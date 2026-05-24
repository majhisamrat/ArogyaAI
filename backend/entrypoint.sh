#!/usr/bin/env sh
set -e

# Wait for a TCP host:port to become available. Defaults to redis:6379
WAIT_HOST=${WAIT_HOST:-redis}
WAIT_PORT=${WAIT_PORT:-6379}
RETRIES=${RETRIES:-60}
SLEEP=${SLEEP:-2}

echo "Waiting for $WAIT_HOST:$WAIT_PORT to be available..."

python - <<PY
import os, socket, sys, time
host=os.environ.get('WAIT_HOST','redis')
port=int(os.environ.get('WAIT_PORT','6379'))
retries=int(os.environ.get('RETRIES','60'))
sleep=float(os.environ.get('SLEEP','2'))
for i in range(retries):
    try:
        s=socket.create_connection((host,port), timeout=5)
        s.close()
        print(f"Connected to {host}:{port}")
        sys.exit(0)
    except Exception as e:
        print(f"Waiting for {host}:{port}... ({i+1}/{retries})")
        time.sleep(sleep)
print('Timed out waiting for service')
sys.exit(1)
PY

echo "Starting application: $@"
exec "$@"
