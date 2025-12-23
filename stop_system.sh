#!/bin/bash
# Vehicle Access Control System - Shutdown Script

echo "=========================================="
echo " Vehicle Access Control System Shutdown"
echo "=========================================="
echo ""

# Check if PID file exists
if [ ! -f /tmp/vehicle_system_pids.txt ]; then
    echo "⚠ No PID file found. System may not be running."
    echo "Attempting to find and kill processes..."
    echo ""

    # Try to find processes by name
    pkill -f ultrasonic_sensor.py
    pkill -f camera_plate_reader.py
    pkill -f servo_motor.py

    echo "✓ Attempted to stop all processes"
    exit 0
fi

# Read PIDs from file
PIDS=$(cat /tmp/vehicle_system_pids.txt)

echo "Stopping processes..."
for PID in $PIDS; do
    if ps -p $PID > /dev/null 2>&1; then
        echo "  Stopping PID $PID..."
        kill $PID
    else
        echo "  Process $PID not found (may have already stopped)"
    fi
done

# Wait a moment for graceful shutdown
sleep 2

# Force kill if still running
for PID in $PIDS; do
    if ps -p $PID > /dev/null 2>&1; then
        echo "  Force stopping PID $PID..."
        kill -9 $PID
    fi
done

# Remove PID file
rm -f /tmp/vehicle_system_pids.txt

echo ""
echo "✓ All components stopped"
echo "=========================================="
