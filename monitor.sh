#!/bin/bash

# Simple script to deploy a resource manager 

# Define paths and names
LOG_DIR="/var/log/system_stats"
LOG_FILE="$LOG_DIR/usage.log"
SCRIPT_PATH="/usr/local/bin/log_system_stats.sh"
SERVICE_NAME="log_system_stats"
SERVICE_FILE="/etc/systemd/system/$SERVICE_NAME.service"
TIMER_FILE="/etc/systemd/system/$SERVICE_NAME.timer"

# Create logging directory
sudo mkdir -p $LOG_DIR

# Create the monitoring script
sudo tee $SCRIPT_PATH > /dev/null <<EOF
#!/bin/bash
# Log current CPU and memory usage to the log file
echo "CPU and Memory usage at \$(date):" >> $LOG_FILE
ps -eo pid,ppid,cmd,%cpu,%mem --sort=%mem | head >> $LOG_FILE
EOF

# Make the script executable
sudo chmod +x $SCRIPT_PATH

# Create the Systemd service file
sudo tee $SERVICE_FILE > /dev/null <<EOF
[Unit]
Description=Log System CPU and Memory Usage

[Service]
Type=oneshot
ExecStart=$SCRIPT_PATH
EOF

# Create the Systemd timer file
sudo tee $TIMER_FILE > /dev/null <<EOF
[Unit]
Description=Run $SERVICE_NAME every hour

[Timer]
OnCalendar=hourly

[Install]
WantedBy=timers.target
EOF

# Reload Systemd, enable, and start the timer
sudo systemctl daemon-reload
sudo systemctl enable $SERVICE_NAME.timer
sudo systemctl start $SERVICE_NAME.timer

echo "System monitoring script setup complete. CPU and memory usage will be logged every hour to $LOG_FILE"
