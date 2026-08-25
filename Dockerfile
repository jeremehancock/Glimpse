FROM python:3.13-slim

# Install dependencies
RUN apt-get update && apt-get install -y \
    cron \
    nginx \
    supervisor \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
RUN pip install requests

# Set up directories
RUN mkdir -p /app/web /app/data /app/scripts

# Copy Python scripts.
#
# The whole directory, not a file list. glimpse_config.py was added and the
# per-file COPY silently left it out of the image — the container then refused
# to start, correctly, but only at runtime. A directory copy cannot drift from
# what the entrypoint invokes.
COPY scripts/ /app/scripts/
RUN chmod +x /app/scripts/*.py

# Copy web files
COPY web/ /app/web/

# Remove default Nginx configuration and add our custom one
RUN rm -f /etc/nginx/sites-enabled/default
COPY config/nginx.conf /etc/nginx/conf.d/default.conf
COPY config/supervisord.conf /etc/supervisor/conf.d/supervisord.conf
COPY config/entrypoint.sh /app/
RUN chmod +x /app/entrypoint.sh

# Create empty crontab file
RUN touch /etc/cron.d/media-cron
RUN chmod 0644 /etc/cron.d/media-cron

# Create data directory structure for all three servers
RUN mkdir -p /app/data/plex /app/data/jellyfin /app/data/emby

WORKDIR /app

# Expose port for the web server
EXPOSE 80

# Set entrypoint
ENTRYPOINT ["/app/entrypoint.sh"]