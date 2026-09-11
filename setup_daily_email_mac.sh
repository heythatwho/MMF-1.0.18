#!/bin/bash
set -e
cd "$(dirname "$0")"
mkdir -p reports
PY="$PWD/.venv/bin/python"
if [ ! -f "$PY" ]; then python3 -m venv .venv; "$PY" -m pip install --upgrade pip; "$PY" -m pip install -r requirements.txt; fi
PLIST="$HOME/Library/LaunchAgents/com.mmf.dailyemail.plist"
cat > "$PLIST" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "https://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
<key>Label</key><string>com.mmf.dailyemail</string>
<key>ProgramArguments</key><array><string>$PY</string><string>$PWD/scheduler/daily_email_job.py</string></array>
<key>StartCalendarInterval</key><dict><key>Hour</key><integer>16</integer><key>Minute</key><integer>0</integer></dict>
<key>WorkingDirectory</key><string>$PWD</string>
<key>StandardOutPath</key><string>$PWD/reports/daily_email.out.log</string>
<key>StandardErrorPath</key><string>$PWD/reports/daily_email.err.log</string>
</dict></plist>
EOF
launchctl unload "$PLIST" 2>/dev/null || true
launchctl load "$PLIST"
echo "Installed MMF daily email at 4:00 PM local time. Weekends skipped by script."
