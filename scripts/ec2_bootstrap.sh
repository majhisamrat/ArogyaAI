#!/usr/bin/env bash
set -euo pipefail

if [ $# -lt 1 ]; then
  echo "Usage: $0 <git-repo-url> [branch]"
  exit 1
fi

REPO="$1"
BRANCH="${2:-main}"
APP_DIR="/home/ubuntu/health_assistant"

echo "Installing Docker and dependencies..."
sudo apt-get update
sudo apt-get install -y ca-certificates curl gnupg lsb-release
sudo mkdir -p /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
  $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin git

echo "Cloning application into $APP_DIR"
sudo rm -rf "$APP_DIR"
sudo mkdir -p "$APP_DIR"
sudo chown $USER:$USER "$APP_DIR"
git clone --depth 1 --branch "$BRANCH" "$REPO" "$APP_DIR"

cd "$APP_DIR"
echo "Copy .env.example to .env and edit values before continuing"
cp .env.example .env || true

echo "Starting application with docker compose"
docker compose up -d --build

echo "Bootstrap complete."
echo "If you need SSL, run: ./scripts/obtain_certs.sh yourdomain.com youremail@example.com"
