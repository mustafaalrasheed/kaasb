#!/usr/bin/env bash
# =============================================================================
# Kaasb Server Initial Setup & Security Hardening
# Run ONCE on a fresh Hetzner CX22 (Ubuntu 22.04 LTS)
# Usage:  bash server-setup.sh
# =============================================================================

set -euo pipefail

# Non-interactive mode for apt and dpkg
export DEBIAN_FRONTEND=noninteractive

DEPLOY_DIR="/opt/kaasb"
BACKUP_DIR="/opt/kaasb/backups"
LOG_DIR="/var/log/kaasb"

echo "============================================================"
echo "  Kaasb Server Setup — $(date)"
echo "============================================================"

# ---------------------------------------------------------------------------
# 1. Update system
# ---------------------------------------------------------------------------
echo "[1/10] Updating system packages..."
apt-get update -qq
apt-get upgrade -y -qq

# ---------------------------------------------------------------------------
# 2. Install essentials
# ---------------------------------------------------------------------------
echo "[2/10] Installing essentials..."
apt-get install -y -qq \
    curl git nano ufw fail2ban htop \
    unattended-upgrades apt-listchanges \
    logrotate cron \
    ca-certificates gnupg lsb-release

# ---------------------------------------------------------------------------
# 3. Install Docker Engine (official repo)
# ---------------------------------------------------------------------------
echo "[3/10] Installing Docker Engine..."
install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | \
    gpg --dearmor -o /etc/apt/keyrings/docker.gpg
chmod a+r /etc/apt/keyrings/docker.gpg

echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] \
  https://download.docker.com/linux/ubuntu \
  $(lsb_release -cs) stable" | \
  tee /etc/apt/sources.list.d/docker.list > /dev/null

apt-get update -qq
apt-get install -y -qq docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

systemctl enable --now docker
echo "Docker $(docker --version) installed"

# ---------------------------------------------------------------------------
# 4. Install Certbot (Let's Encrypt)
# ---------------------------------------------------------------------------
echo "[4/10] Installing Certbot..."
apt-get install -y -qq snapd
snap install core && snap refresh core
snap install --classic certbot
ln -sf /snap/bin/certbot /usr/bin/certbot

# Create webroot directory for ACME challenges
mkdir -p /var/www/certbot
echo "Certbot $(certbot --version 2>&1) installed"

# ---------------------------------------------------------------------------
# 5. Configure UFW firewall
# ---------------------------------------------------------------------------
echo "[5/10] Configuring UFW firewall..."
ufw --force reset
ufw default deny incoming
ufw default allow outgoing
ufw allow 22/tcp   comment "SSH"
ufw allow 80/tcp   comment "HTTP"
ufw allow 443/tcp  comment "HTTPS"
ufw --force enable
echo "Firewall enabled: SSH + HTTP + HTTPS only"

# ---------------------------------------------------------------------------
# 6. Configure fail2ban
# ---------------------------------------------------------------------------
echo "[6/10] Configuring fail2ban..."
cat > /etc/fail2ban/jail.local << 'FAIL2BAN'
[DEFAULT]
bantime  = 3600
findtime = 600
maxretry = 5
backend  = systemd

[sshd]
enabled  = true
port     = ssh
filter   = sshd
logpath  = /var/log/auth.log
maxretry = 5

[nginx-http-auth]
enabled  = true
filter   = nginx-http-auth
logpath  = /var/log/nginx/kaasb.error.log

[nginx-limit-req]
enabled  = true
filter   = nginx-limit-req
logpath  = /var/log/nginx/kaasb.error.log
maxretry = 10
FAIL2BAN

systemctl enable --now fail2ban
systemctl restart fail2ban
echo "fail2ban active: bans after 5 failed attempts"

# ---------------------------------------------------------------------------
# 7. Harden SSH (key-only, no root login via password)
# ---------------------------------------------------------------------------
echo "[7/10] Hardening SSH..."
sed -i 's/^#\?PasswordAuthentication.*/PasswordAuthentication no/'   /etc/ssh/sshd_config
sed -i 's/^#\?ChallengeResponseAuthentication.*/ChallengeResponseAuthentication no/' /etc/ssh/sshd_config
sed -i 's/^#\?PermitRootLogin.*/PermitRootLogin prohibit-password/' /etc/ssh/sshd_config
systemctl restart sshd
echo "SSH hardened: key-only, no root password login"

# ---------------------------------------------------------------------------
# 8. Automatic security updates
# ---------------------------------------------------------------------------
echo "[8/10] Enabling automatic security updates..."
cat > /etc/apt/apt.conf.d/50unattended-upgrades << 'APT'
Unattended-Upgrade::Allowed-Origins {
    "${distro_id}:${distro_codename}-security";
};
Unattended-Upgrade::Automatic-Reboot "false";
Unattended-Upgrade::Automatic-Reboot-Time "03:00";
APT

cat > /etc/apt/apt.conf.d/20auto-upgrades << 'APT'
APT::Periodic::Update-Package-Lists "1";
APT::Periodic::Unattended-Upgrade "1";
APT::Periodic::Download-Upgradeable-Packages "1";
APT::Periodic::AutocleanInterval "7";
APT'

systemctl enable --now unattended-upgrades
echo "Automatic security updates enabled"

# ---------------------------------------------------------------------------
# 9. Swap file (prevents OOM kills on 4 GB RAM)
# ---------------------------------------------------------------------------
echo "[9/10] Configuring swap..."
if [ ! -f /swapfile ]; then
    fallocate -l 2G /swapfile
    chmod 600 /swapfile
    mkswap /swapfile
    swapon /swapfile
    echo '/swapfile none swap sw 0 0' >> /etc/fstab
    # Reduce swappiness for server workload
    echo 'vm.swappiness=10' >> /etc/sysctl.conf
    sysctl -p
    echo "2 GB swap created (swappiness=10)"
else
    echo "Swap already exists"
fi

# ---------------------------------------------------------------------------
# 10. Project structure + log rotation + backup cron
# ---------------------------------------------------------------------------
echo "[10/10] Setting up project structure..."

# Deployment directory
mkdir -p "$DEPLOY_DIR" "$BACKUP_DIR" "$LOG_DIR"

# Log rotation for Kaasb containers
cat > /etc/logrotate.d/kaasb << LOGROTATE
${LOG_DIR}/*.log
/var/lib/docker/containers/*/*.log
/var/log/nginx/kaasb*.log {
    daily
    rotate 14
    compress
    delaycompress
    missingok
    notifempty
    sharedscripts
    postrotate
        docker exec kaasb_nginx nginx -s reopen 2>/dev/null || true
    endscript
}
LOGROTATE

# Database backup cron (runs at 2:00 AM daily, keeps 14 days)
cat > /etc/cron.d/kaasb-backup << 'CRON'
# Kaasb daily database backup
0 2 * * * root /opt/kaasb/scripts/backup.sh >> /var/log/kaasb/backup.log 2>&1
CRON

# SSL certificate auto-renewal (Certbot) — runs twice a day per Let's Encrypt recommendation
cat > /etc/cron.d/certbot-renew << 'CRON'
# Certbot SSL renewal + nginx reload
0 3,15 * * * root certbot renew --quiet --webroot --webroot-path /var/www/certbot && docker exec kaasb_nginx nginx -s reload 2>/dev/null || true
CRON

# Backup script
mkdir -p "$DEPLOY_DIR/scripts"
cat > "$DEPLOY_DIR/scripts/backup.sh" << 'BACKUP'
#!/usr/bin/env bash
set -euo pipefail
BACKUP_DIR="/opt/kaasb/backups"
ENV_FILE="/opt/kaasb/.env.production"
KEEP_DAYS=14

[ -f "$ENV_FILE" ] || exit 0
set -a; source "$ENV_FILE"; set +a

TIMESTAMP=$(date +%Y%m%d-%H%M%S)
OUTFILE="${BACKUP_DIR}/kaasb-auto-${TIMESTAMP}.sql.gz"
mkdir -p "$BACKUP_DIR"

docker compose -f /opt/kaasb/docker-compose.prod.yml --env-file "$ENV_FILE" \
    exec -T db pg_dump -U "${DB_USER}" "${DB_NAME}" | gzip > "$OUTFILE"

echo "$(date): Backup saved to $OUTFILE ($(du -sh "$OUTFILE" | cut -f1))"

# Delete backups older than KEEP_DAYS
find "$BACKUP_DIR" -name "kaasb-auto-*.sql.gz" -mtime +${KEEP_DAYS} -delete
echo "$(date): Old backups cleaned (keeping last ${KEEP_DAYS} days)"
BACKUP
chmod +x "$DEPLOY_DIR/scripts/backup.sh"

echo ""
echo "============================================================"
echo "  Server setup complete!"
echo "============================================================"
echo ""
echo "  Firewall:      SSH (22) + HTTP (80) + HTTPS (443)"
echo "  fail2ban:      Brute-force protection on SSH + Nginx"
echo "  SSH:           Key-only, no root password"
echo "  Auto-updates:  Security patches applied nightly"
echo "  Swap:          2 GB (swappiness=10)"
echo "  Certbot:       $(certbot --version 2>&1)"
echo "  Docker:        $(docker --version)"
echo "  Backup cron:   Daily at 02:00 → $BACKUP_DIR"
echo "  SSL renewal:   Twice daily auto-renew cron"
echo "  Log rotation:  Daily, 14-day retention"
echo ""
echo "  Next steps:"
echo "  1. cd $DEPLOY_DIR"
echo "  2. git clone https://github.com/mustafaalrasheed/kaasb.git ."
echo "  3. cp .env.production.example .env.production && nano .env.production"
echo "  4. ./deploy.sh --ssl          # Get SSL certificate"
echo "  5. ./deploy.sh --full         # First deployment"
echo "============================================================"
