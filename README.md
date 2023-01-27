# co2watcher
Small Utility for reading and publishing TFA Dostmann CO2 Monitor Data

## Installation

```bash
sudo cp 90-co2watcher.rules /etc/udev/rules.d/
sudo udevadm control --reload-rules
```

## Service

```bash
nano /etc/systemd/system/co2monitor.service
```

```ini
[Unit]
Description=Co2Monitor
After=syslog.target network.target
[Service]
Type=simple
ExecStart=/bin/bash /home/pi/bin/co2watcher/start-co2monitor.sh
User=pi
LimitMEMLOCK=33554432
[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl start co2monitor.service
sudo systemctl enable co2monitor.service
```
