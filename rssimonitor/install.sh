python -m pip install -r requirements.txt

SERVICE_DEF="[Unit]
Description=RSSI Monitor
After=network.target

[Service]
Type=simple
Restart=always
User=$USER
WorkingDirectory=$PWD
ExecStart=python -m gunicorn -b 0.0.0,0:8133 app:app

[Install]
WantedBy=multi-user.target
"

echo "$SERVICE_DEF" | sudo tee /etc/systemd/system/rssimonitor.service > /dev/null

sudo systemctl enable rssimonitor.service --now

