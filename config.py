"""
Configuration file for Vehicle Access Control System
Update these settings according to your setup
"""

# MQTT Broker Settings
MQTT_BROKER = "localhost"  # Change to your MQTT broker IP (e.g., "192.168.1.100")
MQTT_PORT = 1883
MQTT_KEEPALIVE = 60

# MQTT Topics
TOPIC_ULTRASONIC_DETECTION = "vehicle/ultrasonic/detection"
TOPIC_CAMERA_RESULT = "vehicle/camera/result"

# AWS DynamoDB Settings
AWS_REGION = "us-east-1"  # Change to your AWS region
DYNAMODB_TABLE_NAME = "VehiclePassRegistrations"

# GPIO Pin Configuration (BCM numbering)
# Ultrasonic Sensor
ULTRASONIC_TRIGGER_PIN = 23
ULTRASONIC_ECHO_PIN = 24

# Servo Motor
SERVO_PIN = 18

# Camera Settings
CAMERA_DELAY_SECONDS = 10  # Wait 10 seconds before taking picture
CAMERA_RUNTIME_SECONDS = 60  # Keep camera active for 1 minute
IMAGE_PATH = "/tmp/plate_image.jpg"

# License Plate Format Validation
# Expected format: 3 letters followed by 4 numbers (e.g., ABC1234)
PLATE_FORMAT_PATTERN = r'^[A-Z]{3}[0-9]{4}$'

# Servo Motor Settings
GATE_OPEN_TIME_SECONDS = 20  # Keep gate open for 20 seconds
SERVO_OPEN_ANGLE = 90  # Angle to open gate
SERVO_CLOSE_ANGLE = 0  # Angle to close gate

# Ultrasonic Sensor Settings
DETECTION_DISTANCE_CM = 50  # Trigger when object is within 50 cm
SENSOR_CHECK_INTERVAL = 0.5  # Check sensor every 0.5 seconds
