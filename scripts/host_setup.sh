#!/usr/bin/env bash
# ACUSEEK host setup: Ubuntu Server 22.04 + Docker + NVIDIA
set -e

echo "=== ACUSEEK Host Setup ==="

# 1. Update system
sudo apt-get update
sudo apt-get upgrade -y

# 2. Install prerequisites
sudo apt-get install -y curl ca-certificates gnupg lsb-release

# 3. Install Docker Engine
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

# Add current user to docker group
sudo usermod -aG docker "$USER"

# 4. Install NVIDIA Drivers + Container Toolkit
echo "=== Installing NVIDIA Driver + Container Toolkit ==="
sudo apt-get install -y nvidia-driver-535 nvidia-utils-535

# NVIDIA Container Toolkit
curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | sudo gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg
curl -s -L https://nvidia.github.io/libnvidia-container/stable/deb/nvidia-container-toolkit.list | \
  sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' | \
  sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list

sudo apt-get update
sudo apt-get install -y nvidia-container-toolkit
sudo nvidia-ctk runtime configure --runtime=docker
sudo systemctl restart docker

# 5. Create media directory
sudo mkdir -p /data/media
sudo chown -R "$USER":"$USER" /data

echo "=== Creating env file ==="
if [ ! -f .env ]; then
  cp .env.example .env
  echo "Copied .env.example to .env — EDIT .env with your secrets!"
fi

echo ""
echo "=== DONE ==="
echo "1. Reboot: sudo reboot"
echo "2. Verify GPU: nvidia-smi"
echo "3. Edit .env with your passwords + Cloudflare tunnel token"
echo "4. Run: make up"
