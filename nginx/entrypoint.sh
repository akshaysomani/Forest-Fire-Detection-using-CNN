#!/bin/sh
set -e

SSL_DIR="/etc/nginx/ssl/live/ignisai.platform"
mkdir -p "$SSL_DIR"

if [ ! -f "$SSL_DIR/fullchain.pem" ] || [ ! -f "$SSL_DIR/privkey.pem" ]; then
    echo "========================================================================="
    echo "⚠️ SSL certificates not found in $SSL_DIR."
    echo "Generating temporary self-signed fallback certificate to prevent crash..."
    echo "========================================================================="
    
    openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
        -keyout "$SSL_DIR/privkey.pem" \
        -out "$SSL_DIR/fullchain.pem" \
        -subj "/CN=ignisai.platform/O=IgnisAI/C=US"
        
    echo "Fallback certificates successfully generated."
else
    echo "Production SSL certificates verified in $SSL_DIR."
fi

# Hand execution off to the default cmd
exec "$@"
