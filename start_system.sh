#!/bin/bash
# Vehicle Access Control System - Startup Script

echo "=========================================="
echo " Vehicle Access Control System Startup"
echo "=========================================="
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo "⚠ Warning: Some GPIO operations may require sudo"
    echo "Consider running: sudo ./start_system.sh"
    echo ""
fi

# Create log directory
LOG_DIR="./logs"
mkdir -p $LOG_DIR

# Get timestamp for log files
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

echo "Starting all components..."
echo ""

# Start ultrasonic sensor
echo "1. Starting Ultrasonic Sensor..."
python3 ultrasonic_sensor.py > "$LOG_DIR/ultrasonic_$TIMESTAMP.log" 2>&1 &
ULTRASONIC_PID=$!
echo "   PID: $ULTRASONIC_PID"
sleep 2

# Start camera plate reader
echo "2. Starting Camera Plate Reader..."
python3 camera_plate_reader.py > "$LOG_DIR/camera_$TIMESTAMP.log" 2>&1 &
CAMERA_PID=$!
echo "   PID: $CAMERA_PID"
sleep 2

# Start servo motor controller
echo "3. Starting Servo Motor Controller..."
python3 servo_motor.py > "$LOG_DIR/servo_$TIMESTAMP.log" 2>&1 &
SERVO_PID=$!
echo "   PID: $SERVO_PID"
sleep 2

echo ""
echo "=========================================="
echo " ✓ All components started successfully"
echo "=========================================="
echo ""
echo "Process IDs:"
echo "  Ultrasonic Sensor: $ULTRASONIC_PID"
echo "  Camera Reader:     $CAMERA_PID"
echo "  Servo Controller:  $SERVO_PID"
echo ""
echo "Log files:"
echo "  $LOG_DIR/ultrasonic_$TIMESTAMP.log"
echo "  $LOG_DIR/camera_$TIMESTAMP.log"
echo "  $LOG_DIR/servo_$TIMESTAMP.log"
echo ""
echo "To monitor logs in real-time:"
echo "  tail -f $LOG_DIR/ultrasonic_$TIMESTAMP.log"
echo "  tail -f $LOG_DIR/camera_$TIMESTAMP.log"
echo "  tail -f $LOG_DIR/servo_$TIMESTAMP.log"
echo ""
echo "To stop all components:"
echo "  ./stop_system.sh"
echo "  Or: kill $ULTRASONIC_PID $CAMERA_PID $SERVO_PID"
echo ""

# Save PIDs to file for stop script
echo "$ULTRASONIC_PID" > /tmp/vehicle_system_pids.txt
echo "$CAMERA_PID" >> /tmp/vehicle_system_pids.txt
echo "$SERVO_PID" >> /tmp/vehicle_system_pids.txt

echo "System is running. Press Ctrl+C to stop monitoring."
echo ""

# Wait for user interrupt
wait
