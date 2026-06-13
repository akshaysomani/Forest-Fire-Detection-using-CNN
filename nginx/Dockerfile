FROM nginx:1.25-alpine

# Remove default configuration files
RUN rm /etc/nginx/conf.d/default.conf

# Copy custom configurations
COPY nginx.conf /etc/nginx/nginx.conf

# Copy certification renew scripts
COPY certbot-renew.sh /usr/local/bin/certbot-renew.sh
RUN chmod +x /usr/local/bin/certbot-renew.sh

EXPOSE 80 443

CMD ["nginx", "-g", "daemon off;"]
