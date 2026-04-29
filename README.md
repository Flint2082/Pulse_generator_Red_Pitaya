# Red Pitaya Pulse Generator 
A browser-controlled pulse generator for the Red Pitaya platform.  
The system provides deterministic FPGA-timed pulse generation for laboratory and optics experiments through a FastAPI backend and web GUI.

## Features

- FPGA-timed pulse generation
- 3 configurable output channels
- Browser-based control GUI
- CSV import/export of pulse configurations
- Python client library for scripting and automation

## Architecture

The project consists of three layers:

1. FPGA bitstream
   - Generates deterministic output timing

2. Python backend (FastAPI)
   - Controls FPGA registers
   - Exposes REST API endpoints

3. Browser GUI
   - Provides visualization and control interface
   - Displays pulse timing and system state

## Quick Start
1. Power on your Red Pitaya 
2. Connect your computer to the red pitaya network (e.g. via Ethernet)
3. Access the web GUI at `http://rp-f0XXXX.local:8000` (replace `XXXX' with the last 4 digits of your Red Pitaya's MAC address)
4. Use the GUI to configure pulse parameters and start/stop the generator


<br>

## SETUP INSTRUCTIONS
Instructions for setting up your new Red Pitaya.


### 1. Create Service File

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

ExecStart=/root/Pulse_generator_Red_Pitaya/.venv/bin/python -m uvicorn server:app --host 0.0.0.0 --port 8000

Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

### 2. Enable and Start Service

```bash
sudo systemctl daemon-reload
sudo systemctl enable pulsegen.service
sudo systemctl start pulsegen.service
```

### 3. Useful Commands

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

