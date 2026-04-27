#!/usr/bin/env bash
set -e

HOST="nina@fjoven.com"
REMOTE="/var/www/eventor"

echo "==> Copying files..."
scp app.py requirements.txt ecosystem.config.js "$HOST:$REMOTE/"
scp -r cloudflare "$HOST:$REMOTE/"

echo "==> Installing dependencies on server..."
ssh "$HOST" "
  cd $REMOTE
  python3 -m venv venv
  venv/bin/pip install -q -r requirements.txt
"

echo "==> Restarting app with PM2..."
ssh "$HOST" "
  cd $REMOTE
  pm2 restart eventor 2>/dev/null || pm2 start $REMOTE/ecosystem.config.js
  pm2 save
"

echo "==> Done. https://eventor.fjoven.com"
