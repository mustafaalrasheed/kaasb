#!/bin/bash
# ============================================
# Kaasb Server Security Hardening Script
# Run ONCE after setting up the Hetzner server
# Usage: bash server-setup.sh
# ============================================

set -e

echo "============================================"
echo "  Kaasb Server Setup & Security Hardening"
echo "============================================"

# 1. Update system
echo "[1/8] Updating system packages..."
apt update && apt upgrade -y

# 2. Install essentials
echo "[2/8] Installing essentials..."
apt install -y curl git nano ufw fail2ban htop

# 3. Install Docker
echo "[3/8] Installing Docker..."
curl -fsSL https://get.docker.com | sh
apt install -y docker-compose-plugin

# 4. Configure firewall
echo "[4/8] Configuring firewall (UFW)..."
ufw default deny incoming
ufw default allow outgoing
ufw allow ssh        # Port 22
ufw allow http       # Port 80
ufw allow https      # Port 443
ufw --force enable
echo "Firewall enabled: only SSH, HTTP, HTTPS allowed"

# 5. Configure fail2ban (blocks IPs after failed SSH attempts)
echo "[5/8] Configuring fail2ban..."
cat > /etc/fail2ban/jail.local << 'FAIL2BAN'
[sshd]
enabled = true
port = ssh
filter = sshd
logpath = /var/log/auth.log
maxretry = 5
bantime = 3600
findtime = 600
FAIL2BAN
systemctl restart fail2ban
echo "fail2ban active: IPs banned after 5 failed SSH attempts"

# 6. Disable root password login (SSH key only)
echo "[6/8] Securing SSH..."
sed -i 's/#PasswordAuthentication yes/PasswordAuthentication no/' /etc/ssh/sshd_config
sed -i 's/PasswordAuthentication yes/PasswordAuthentication no/' /etc/ssh/sshd_config
systemctl restart sshd
echo "SSH hardened: password login disabled, key-only access"

# 7. Set up automatic security updates
echo "[7/8] Enabling automatic security updates..."
apt install -y unattended-upgrades
dpkg-reconfigure -plow unattended-upgrades

# 8. Create swap file (useful for 4GB RAM servers)
echo "[8/8] Creating 2GB swap file..."
if [ ! -f /swapfile ]; then
    fallocate -l 2G /swapfile
    chmod 600 /swapfile
    mkswap /swapfile
    swapon /swapfile
    echo '/swapfile none swap sw 0 0' >> /etc/fstab
    echo "2GB swap file created"
else
    echo "Swap file already exists"
fi

echo ""
echo "============================================"
echo "  Server setup complete!"
echo "============================================"
echo ""
echo "  Firewall:    SSH + HTTP + HTTPS only"
echo "  fail2ban:    Blocks brute-force SSH"
echo "  SSH:         Key-only (no passwords)"
echo "  Updates:     Automatic security patches"
echo "  Swap:        2GB (prevents OOM kills)"
echo "  Docker:      $(docker --version)"
echo ""
echo "  Next: clone your repo and run deploy.sh"
echo "============================================"
