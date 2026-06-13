#!/bin/sh
# Certbot renewal automation script
echo "Starting SSL certificate renewal scan..."
certbot renew --webroot -w /var/www/certbot --quiet
echo "Hot-reloading Nginx web server..."
nginx -s reload
