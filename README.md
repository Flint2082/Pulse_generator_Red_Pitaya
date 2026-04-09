# Auto-Start Pulse Generator API and Startup Script on Red Pitaya

Configure the Red Pitaya to run both the API server and `tools/startup_rp.sh` automatically on boot.

## 1. Create Service File

```bash
sudo nano /etc/systemd/system/pulsegen.service
```

Add:

```ini
[Unit]
Description=Pulse Generator Startup Service
After=network-online.target multi-user.target
Wants=network-online.target

[Service]
Type=simple
User=root
WorkingDirectory=/root/Pulse_generator_Red_Pitaya

ExecStartPre=/bin/bash /root/Pulse_generator_Red_Pitaya/tools/startup_rp.sh
ExecStart=/root/Pulse_generator_Red_Pitaya/.venv/bin/python -m uvicorn server:app --host 0.0.0.0 --port 8000

Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

## 2. Enable and Start Service

```bash
sudo systemctl daemon-reload
sudo systemctl enable pulsegen.service
sudo systemctl start pulsegen.service
```

## 3. Useful Commands

Check status:

```bash
sudo systemctl status pulsegen.service
```

View logs:

```bash
journalctl -u pulsegen.service -f
```

Stop service:

```bash
sudo systemctl stop pulsegen.service
```

## Result

On boot, the Red Pitaya will:

1. Run `tools/startup_rp.sh`
2. Start the Pulse Generator API server
