FROM ubuntu:22.04

# Prevent interactive prompts during package installation
ENV DEBIAN_FRONTEND=noninteractive

# Install Python, pip, cron, and other dependencies
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    python3-venv \
    cron \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip3 install --no-cache-dir -r requirements.txt

# Copy application files
COPY __main__.py .
COPY src/ ./src/
COPY .env .env

# Expose HTTP server port
EXPOSE 8000

# Create logs directory
RUN mkdir -p /app/logs

# Create non-root user
RUN useradd -m -u 1000 -s /bin/bash appuser

# Copy cron configuration
COPY crontab /etc/cron.d/trading-alerts
RUN chmod 0644 /etc/cron.d/trading-alerts

# Set up cron for non-root user
RUN crontab -u appuser /etc/cron.d/trading-alerts

# Create the log file to be able to run tail
RUN touch /app/logs/cron.log

# Change ownership of app directory to non-root user
RUN chown -R appuser:appuser /app

# Copy and set up entrypoint script
COPY docker-entrypoint.sh /usr/local/bin/
RUN chmod +x /usr/local/bin/docker-entrypoint.sh

# Note: We stay as root to run cron, but cron executes commands as appuser
# Run the command on container startup
ENTRYPOINT ["/usr/local/bin/docker-entrypoint.sh"]
