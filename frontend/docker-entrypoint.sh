#!/bin/sh
# Extract hostname from BACKEND_URL for proxy Host header
export BACKEND_HOST=$(echo "$BACKEND_URL" | sed -E 's|https?://([^/:]+).*|\1|')
# Substitute variables in nginx config template, then start nginx
envsubst '$BACKEND_URL $BACKEND_HOST' < /etc/nginx/conf.d/default.conf.template > /etc/nginx/conf.d/default.conf
exec nginx -g 'daemon off;'
