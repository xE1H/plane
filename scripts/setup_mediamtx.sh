sudo apt update
sudo apt upgrade -y
sudo apt install -y libcamera0

sudo mkdir /mediamtx
sudo chown "$USER" /mediamtx
cd /mediamtx

wget https://github.com/bluenviron/mediamtx/releases/download/v1.8.4/mediamtx_v1.8.4_linux_arm64v8.tar.gz
tar -xvzf mediamtx_v1.8.4_linux_arm64v8.tar.gz
rm mediamtx_v1.8.4_linux_arm64v8.tar.gz

echo -e "\n  cam:\n" \
"    source: rpiCamera\n" \
"   rpiCameraWidth: 1280\n" \
"   rpiCameraHeight: 720\n" >> mediamtx.yml

curl -fsSL https://tailscale.com/install.sh | sudo sh

SERVICE_CONTENT="[Unit]
Description=MediaMTX
After=network.target

[Service]
Type=simple
Restart=always
User=$USER
WorkingDirectory=/mediamtx
ExecStart=/mediamtx/mediamtx

[Install]
WantedBy=multi-user.target"

echo "$SERVICE_CONTENT" | sudo tee /etc/systemd/system/mediamtx.service > /dev/null
sudo systemctl enable mediamtx.service --now



sudo tailscale up

cd ~