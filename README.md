# Vehicle Access Control System with MQTT and AWS

An IoT-based vehicle access control system using Raspberry Pi, ultrasonic sensor, camera, servo motor, MQTT messaging, and AWS DynamoDB for vehicle registration management.

## System Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                    VEHICLE ACCESS CONTROL SYSTEM                │
└─────────────────────────────────────────────────────────────────┘

[Ultrasonic Sensor] ──┐
                      │
                      ├──> [MQTT Broker] <──> [AWS DynamoDB]
                      │           ↑
[Camera Module]   ────┤           │
                      │           ↓
[Servo Motor]     ────┘      [All Components]
```

## How It Works

1. **Ultrasonic Sensor**: Continuously monitors for approaching vehicles
   - When object detected within 50cm → publishes to MQTT topic `vehicle/ultrasonic/detection`

2. **Camera Module**: Subscribes to ultrasonic detection events
   - Waits 10 seconds after detection
   - Captures vehicle image
   - Reads license plate using OCR
   - Checks AWS DynamoDB for plate registration
   - If registered and has remaining passes → decreases count by 1
   - Publishes result (true/false) to MQTT topic `vehicle/camera/result`

3. **Servo Motor**: Subscribes to camera result events
   - If access granted (true) → opens gate for 20 seconds
   - If access denied (false) → keeps gate closed

## Components Required

### Hardware
- Raspberry Pi (3/4/Zero W) with Raspbian OS
- HC-SR04 Ultrasonic Sensor
- Raspberry Pi Camera Module or USB Camera
- SG90 or MG90S Servo Motor (or similar)
- Jumper wires
- Breadboard (optional)
- Power supply for Raspberry Pi
- External power for servo (recommended 5V 2A)

### Software
- Python 3.7+
- MQTT Broker (Mosquitto)
- AWS Account with DynamoDB access
- Tesseract OCR

## Pin Connections

### Ultrasonic Sensor (HC-SR04)
```
HC-SR04          Raspberry Pi
---------        ------------
VCC       ────>  5V (Pin 2 or 4)
TRIG      ────>  GPIO 23 (Pin 16)
ECHO      ────>  GPIO 24 (Pin 18)
GND       ────>  GND (Pin 6)
```

### Servo Motor
```
Servo Motor      Raspberry Pi
-----------      ------------
Red (VCC)  ────>  5V (External power recommended)
Brown/Black ───>  GND (Pin 14)
Orange     ────>  GPIO 18 (Pin 12) - PWM capable
```

**Important**: For reliable servo operation, use external 5V power supply. Connect:
- Servo VCC → External 5V+
- Servo GND → External GND + Raspberry Pi GND (common ground)
- Servo Signal → GPIO 18

### Camera Module
```
Raspberry Pi Camera Module
- Connect to CSI port on Raspberry Pi
- Or use USB camera (plug into USB port)
```

## Wiring Diagram

```
                    ┌─────────────────────┐
                    │   Raspberry Pi      │
                    │                     │
    ┌───────────────┤ GPIO 23 (Trig)      │
    │   ┌───────────┤ GPIO 24 (Echo)      │
    │   │   ┌───────┤ GPIO 18 (Servo)     │
    │   │   │       │                     │
    │   │   │       │ Camera CSI Port ────┼──> [Camera Module]
    │   │   │       │                     │
    │   │   │       │ 5V ─────────────────┼──> [Ultrasonic VCC]
    │   │   │       │ GND ────────────────┼──> [Ultrasonic GND]
    │   │   │       │                     │    [Servo GND]
    │   │   │       └─────────────────────┘
    │   │   │
    │   │   └──> Servo Signal Wire (Orange)
    │   │
    │   └──> Ultrasonic ECHO
    │
    └──> Ultrasonic TRIG

External 5V Power Supply
    (+) ──> Servo VCC (Red)
    (-) ──> Servo GND (Black) + Raspberry Pi GND (common ground)
```

## Installation Steps

### 1. Prepare Raspberry Pi

```bash
# Update system
sudo apt-get update
sudo apt-get upgrade -y

# Install system dependencies
sudo apt-get install -y python3-pip python3-dev
sudo apt-get install -y libopencv-dev python3-opencv
sudo apt-get install -y tesseract-ocr libtesseract-dev
sudo apt-get install -y libatlas-base-dev

# Enable camera (if using Raspberry Pi Camera Module)
sudo raspi-config
# Navigate to: Interface Options → Camera → Enable
# Reboot after enabling
```

### 2. Install MQTT Broker (Mosquitto)

```bash
# Install Mosquitto MQTT broker
sudo apt-get install -y mosquitto mosquitto-clients

# Enable and start Mosquitto
sudo systemctl enable mosquitto
sudo systemctl start mosquitto

# Test MQTT broker
mosquitto -v
```

### 3. Configure AWS Credentials

```bash
# Install AWS CLI
sudo apt-get install -y awscli

# Configure AWS credentials
aws configure
# Enter your:
#   - AWS Access Key ID
#   - AWS Secret Access Key
#   - Default region (e.g., us-east-1)
#   - Default output format (json)
```

### 4. Create DynamoDB Table

Create a DynamoDB table with the following structure:

**Table Name**: `VehiclePassRegistrations`

**Partition Key**: `plate_number` (String)

**Attributes**:
- `plate_number` (String) - Primary key
- `remaining_passes` (Number)
- `car_type` (String) - Optional
- `email` (String) - Optional
- `name` (String) - Optional
- `phone_number` (String) - Optional
- `registered_at` (String) - Optional
- `status` (String) - Optional

**Example item**:
```json
{
  "plate_number": "ABC123",
  "remaining_passes": 10,
  "car_type": "sedan",
  "email": "user@example.com",
  "name": "John Doe"
}
```

### 5. Clone and Setup Project

```bash
# Clone the repository
cd ~
git clone <repository-url>
cd models

# Install Python dependencies
pip3 install -r requirements.txt

# Or install globally (recommended)
sudo pip3 install -r requirements.txt
```

### 6. Configure Settings

Edit the `config.py` file to match your setup:

```python
# MQTT Broker - Change to your Raspberry Pi IP if using external broker
MQTT_BROKER = "localhost"  # or "192.168.1.100"

# AWS Region - Match your DynamoDB region
AWS_REGION = "us-east-1"

# GPIO Pins - Change if using different pins
ULTRASONIC_TRIGGER_PIN = 23
ULTRASONIC_ECHO_PIN = 24
SERVO_PIN = 18

# Adjust detection distance, timing, and servo angles as needed
DETECTION_DISTANCE_CM = 50
CAMERA_DELAY_SECONDS = 10
GATE_OPEN_TIME_SECONDS = 20
```

### 7. Test Individual Components

Test each component separately before running the full system:

```bash
# Test ultrasonic sensor
python3 ultrasonic_sensor.py

# In another terminal, subscribe to MQTT to see messages
mosquitto_sub -t "vehicle/ultrasonic/detection" -v

# Test camera (capture test image)
python3 -c "import cv2; cap = cv2.VideoCapture(0); ret, frame = cap.read(); cv2.imwrite('test.jpg', frame); cap.release(); print('Image saved')"

# Test servo motor
python3 servo_motor.py
# Then publish a test message:
mosquitto_pub -t "vehicle/camera/result" -m '{"access_granted": true, "plate_number": "TEST123", "remaining_passes": 5}'
```

## Running the System

### Method 1: Run Each Component in Separate Terminals

```bash
# Terminal 1 - Start ultrasonic sensor
python3 ultrasonic_sensor.py

# Terminal 2 - Start camera plate reader
python3 camera_plate_reader.py

# Terminal 3 - Start servo motor controller
python3 servo_motor.py
```

### Method 2: Run as Background Services (Recommended)

Create systemd service files:

**1. Create ultrasonic service**:
```bash
sudo nano /etc/systemd/system/ultrasonic-sensor.service
```

```ini
[Unit]
Description=Ultrasonic Sensor Service
After=network.target mosquitto.service

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/models
ExecStart=/usr/bin/python3 /home/pi/models/ultrasonic_sensor.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

**2. Create camera service**:
```bash
sudo nano /etc/systemd/system/camera-reader.service
```

```ini
[Unit]
Description=Camera Plate Reader Service
After=network.target mosquitto.service

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/models
ExecStart=/usr/bin/python3 /home/pi/models/camera_plate_reader.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

**3. Create servo service**:
```bash
sudo nano /etc/systemd/system/servo-gate.service
```

```ini
[Unit]
Description=Servo Gate Controller Service
After=network.target mosquitto.service

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/models
ExecStart=/usr/bin/python3 /home/pi/models/servo_motor.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

**4. Enable and start services**:
```bash
# Reload systemd
sudo systemctl daemon-reload

# Enable services to start on boot
sudo systemctl enable ultrasonic-sensor.service
sudo systemctl enable camera-reader.service
sudo systemctl enable servo-gate.service

# Start services
sudo systemctl start ultrasonic-sensor.service
sudo systemctl start camera-reader.service
sudo systemctl start servo-gate.service

# Check status
sudo systemctl status ultrasonic-sensor.service
sudo systemctl status camera-reader.service
sudo systemctl status servo-gate.service

# View logs
sudo journalctl -u ultrasonic-sensor.service -f
sudo journalctl -u camera-reader.service -f
sudo journalctl -u servo-gate.service -f
```

## MQTT Topics

| Topic | Publisher | Subscriber | Message Format |
|-------|-----------|------------|----------------|
| `vehicle/ultrasonic/detection` | ultrasonic_sensor.py | camera_plate_reader.py | `{"timestamp": "...", "distance_cm": 45.2, "status": "object_detected"}` |
| `vehicle/camera/result` | camera_plate_reader.py | servo_motor.py | `{"timestamp": "...", "access_granted": true, "plate_number": "ABC123", "remaining_passes": 9}` |

## Troubleshooting

### Camera Issues
```bash
# Test if camera is detected
vcgencmd get_camera

# Test camera capture
raspistill -o test.jpg

# For USB camera, check device
ls -l /dev/video*
```

### MQTT Issues
```bash
# Check if Mosquitto is running
sudo systemctl status mosquitto

# Test MQTT broker
mosquitto_sub -t "#" -v

# Check MQTT logs
sudo tail -f /var/log/mosquitto/mosquitto.log
```

### GPIO Permission Issues
```bash
# Add user to GPIO group
sudo usermod -a -G gpio pi

# Set GPIO permissions
sudo chmod -R 777 /sys/class/gpio
```

### OCR Not Reading Plates Well

1. **Improve lighting** - Ensure good lighting on license plate
2. **Adjust camera angle** - Point camera directly at plate
3. **Increase image quality** - Modify camera settings in code
4. **Use better OCR** - Consider using EasyOCR instead of Tesseract:

```python
# Install EasyOCR
pip3 install easyocr

# Modify camera_plate_reader.py to use EasyOCR
import easyocr
reader = easyocr.Reader(['en'])
result = reader.readtext(image_path)
```

### AWS Connection Issues
```bash
# Test AWS credentials
aws sts get-caller-identity

# Test DynamoDB access
aws dynamodb list-tables --region us-east-1

# Check IAM permissions - ensure your user has:
# - dynamodb:GetItem
# - dynamodb:UpdateItem
# - dynamodb:PutItem
```

## Security Considerations

1. **MQTT Security**: Enable authentication on Mosquitto broker
2. **AWS Credentials**: Use IAM roles instead of hardcoded credentials
3. **Network**: Keep system on private network or use VPN
4. **Rate Limiting**: Add cooldown periods to prevent abuse

## Future Enhancements

- [ ] Add web dashboard for monitoring
- [ ] Send email/SMS notifications for access events
- [ ] Store images in S3 for audit trail
- [ ] Add machine learning for better plate recognition
- [ ] Support multiple gates/entries
- [ ] Add manual override controls
- [ ] Implement visitor registration system

## File Structure

```
models/
├── config.py                  # Configuration settings
├── ultrasonic_sensor.py       # Ultrasonic sensor module
├── camera_plate_reader.py     # Camera and plate reader module
├── servo_motor.py             # Servo motor controller
├── requirements.txt           # Python dependencies
└── README.md                  # This file
```

## License

MIT License

## Support

For issues and questions, please open an issue in the repository.

---

**Built with ❤️ for IoT and Home Automation**
