#!/usr/bin/env python3
"""
Camera Plate Reader Module
Subscribes to ultrasonic detection events, captures vehicle image,
reads license plate, and validates against AWS DynamoDB
"""

import time
import json
from datetime import datetime
from threading import Thread, Event
import paho.mqtt.client as mqtt
import boto3
from botocore.exceptions import ClientError
import cv2
import pytesseract
import re
import config

class CameraPlateReader:
    def __init__(self):
        """Initialize camera, MQTT client, and AWS DynamoDB"""
        # Initialize MQTT client
        self.client = mqtt.Client("CameraPlateReader")
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        self.client.on_disconnect = self.on_disconnect

        # Connect to MQTT broker
        try:
            self.client.connect(config.MQTT_BROKER, config.MQTT_PORT, config.MQTT_KEEPALIVE)
            self.client.loop_start()
        except Exception as e:
            print(f"Failed to connect to MQTT broker: {e}")
            raise

        # Initialize AWS DynamoDB
        try:
            self.dynamodb = boto3.resource('dynamodb', region_name=config.AWS_REGION)
            self.table = self.dynamodb.Table(config.DYNAMODB_TABLE_NAME)
            print(f"✓ Connected to DynamoDB table: {config.DYNAMODB_TABLE_NAME}")
        except Exception as e:
            print(f"Failed to connect to DynamoDB: {e}")
            raise

        # Camera active flag and event
        self.camera_active_event = Event()
        self.is_running = True
        self.processing = False

    def on_connect(self, client, userdata, flags, rc):
        """Callback when connected to MQTT broker"""
        if rc == 0:
            print("✓ Camera Plate Reader connected to MQTT broker")
            # Subscribe to ultrasonic detection topic
            client.subscribe(config.TOPIC_ULTRASONIC_DETECTION, qos=1)
            print(f"✓ Subscribed to: {config.TOPIC_ULTRASONIC_DETECTION}")
        else:
            print(f"✗ Failed to connect to MQTT broker. Return code: {rc}")

    def on_disconnect(self, client, userdata, rc):
        """Callback when disconnected from MQTT broker"""
        print(f"Disconnected from MQTT broker. Return code: {rc}")

    def on_message(self, client, userdata, msg):
        """Callback when message received from MQTT"""
        try:
            # Parse detection message
            detection_data = json.loads(msg.payload.decode())
            print(f"\n📡 Received detection event: {detection_data}")

            # Check if already processing
            if self.processing:
                print("⚠ Already processing a vehicle, ignoring detection")
                return

            # Start camera processing in separate thread
            self.processing = True
            thread = Thread(target=self.process_vehicle)
            thread.daemon = True
            thread.start()

        except Exception as e:
            print(f"Error processing message: {e}")

    def capture_image(self):
        """
        Capture image using camera
        Returns path to captured image or None if failed
        """
        try:
            print(f"📷 Waiting {config.CAMERA_DELAY_SECONDS} seconds before capturing image...")
            time.sleep(config.CAMERA_DELAY_SECONDS)

            # Open camera
            cap = cv2.VideoCapture(0)
            if not cap.isOpened():
                print("✗ Failed to open camera")
                return None

            # Allow camera to warm up
            time.sleep(1)

            # Capture frame
            print("📸 Capturing image...")
            ret, frame = cap.read()
            cap.release()

            if not ret:
                print("✗ Failed to capture image")
                return None

            # Save image
            cv2.imwrite(config.IMAGE_PATH, frame)
            print(f"✓ Image saved to: {config.IMAGE_PATH}")
            return config.IMAGE_PATH

        except Exception as e:
            print(f"Error capturing image: {e}")
            return None

    def read_plate_number(self, image_path):
        """
        Read license plate number from image using OCR
        Returns plate number string or None if not found
        """
        try:
            # Read image
            img = cv2.imread(image_path)
            if img is None:
                print("✗ Failed to read image")
                return None

            # Convert to grayscale
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

            # Apply CLAHE (Contrast Limited Adaptive Histogram Equalization)
            clahe = cv2.createCLAHE(3.0, (8, 8))
            gray = clahe.apply(gray)

            # Apply Otsu's thresholding
            _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

            # Use pytesseract to extract text - read everything in the image
            print("🔍 Reading text from image...")

            # Try OCR on preprocessed image - PSM 6 reads any text block
            text = pytesseract.image_to_string(thresh, config='--psm 6 --oem 3')

            print(f"📝 Raw OCR result: '{text.strip()}'")

            # Clean up the text - keep only letters, numbers, and spaces, convert to uppercase
            cleaned_text = re.sub(r'[^A-Z0-9\s]', '', text.upper())
            # Remove extra whitespace and normalize to single space
            cleaned_text = ' '.join(cleaned_text.split())

            print(f"🧹 Cleaned text: '{cleaned_text}'")

            # Validate plate format: 3 letters + space + 4 numbers (e.g., ABC 1234)
            # Space is optional in case OCR doesn't detect it
            match = re.match(config.PLATE_FORMAT_PATTERN, cleaned_text)

            if match:
                plate_number = cleaned_text
                print(f"✓ Detected valid plate number: {plate_number}")
                return plate_number
            else:
                print(f"✗ Invalid plate format detected: '{cleaned_text}'")
                print(f"   Expected format: 3 letters + 4 numbers (e.g., ABC 1234)")
                return None

        except Exception as e:
            print(f"Error reading plate number: {e}")
            return None

    def check_vehicle_access(self, plate_number):
        """
        Check if vehicle has access and update DynamoDB
        Returns tuple (has_access: bool, remaining_passes: int)
        """
        try:
            print(f"🔍 Checking database for plate: {plate_number}")

            # Get item from DynamoDB
            response = self.table.get_item(
                Key={'plate_number': plate_number}
            )

            # Check if plate exists in database
            if 'Item' not in response:
                print(f"✗ Plate {plate_number} not found in database")
                return False, 0

            item = response['Item']
            remaining_passes = item.get('remaining_passes', 0)

            print(f"✓ Plate found. Remaining passes: {remaining_passes}")

            # Check if vehicle has remaining passes
            if remaining_passes <= 0:
                print(f"✗ No remaining passes for plate {plate_number}")
                return False, 0

            # Decrease remaining_passes by 1
            new_remaining_passes = remaining_passes - 1

            self.table.update_item(
                Key={'plate_number': plate_number},
                UpdateExpression='SET remaining_passes = :val',
                ExpressionAttributeValues={':val': new_remaining_passes}
            )

            print(f"✓ Access granted! Remaining passes updated: {remaining_passes} → {new_remaining_passes}")
            return True, new_remaining_passes

        except ClientError as e:
            print(f"DynamoDB error: {e.response['Error']['Message']}")
            return False, 0
        except Exception as e:
            print(f"Error checking vehicle access: {e}")
            return False, 0

    def publish_result(self, has_access, plate_number=None, remaining_passes=0):
        """Publish access result to MQTT"""
        result_data = {
            "timestamp": datetime.now().isoformat(),
            "access_granted": has_access,
            "plate_number": plate_number,
            "remaining_passes": remaining_passes
        }

        # Publish to MQTT
        result = self.client.publish(
            config.TOPIC_CAMERA_RESULT,
            json.dumps(result_data),
            qos=1
        )

        if result.rc == mqtt.MQTT_ERR_SUCCESS:
            status = "✓ GRANTED" if has_access else "✗ DENIED"
            print(f"{status} - Published result to MQTT: {result_data}")
        else:
            print(f"✗ Failed to publish result")

    def process_vehicle(self):
        """Main processing pipeline for vehicle detection"""
        try:
            print("\n" + "=" * 60)
            print("🚗 VEHICLE DETECTED - Starting processing pipeline")
            print("=" * 60)

            # Step 1: Capture image
            image_path = self.capture_image()
            if not image_path:
                print("✗ Failed to capture image, denying access")
                self.publish_result(False)
                return

            # Step 2: Read plate number
            plate_number = self.read_plate_number(image_path)
            if not plate_number:
                print("✗ Failed to read plate number, denying access")
                self.publish_result(False)
                return

            # Step 3: Check database and update
            has_access, remaining_passes = self.check_vehicle_access(plate_number)

            # Step 4: Publish result
            self.publish_result(has_access, plate_number, remaining_passes)

            print("=" * 60)
            print("✓ Processing complete")
            print("=" * 60 + "\n")

        except Exception as e:
            print(f"Error in processing pipeline: {e}")
            self.publish_result(False)
        finally:
            # Reset processing flag after a delay to prevent rapid re-triggers
            time.sleep(5)
            self.processing = False

    def run(self):
        """Main loop to keep the program running"""
        print("Starting Camera Plate Reader...")
        print(f"Subscribed to: {config.TOPIC_ULTRASONIC_DETECTION}")
        print(f"Publishing to: {config.TOPIC_CAMERA_RESULT}")
        print("-" * 60)
        print("Waiting for vehicle detection events...")
        print("-" * 60)

        try:
            while self.is_running:
                time.sleep(1)

        except KeyboardInterrupt:
            print("\n\nStopping Camera Plate Reader...")
        finally:
            self.cleanup()

    def cleanup(self):
        """Clean up resources"""
        print("Cleaning up resources...")
        self.is_running = False
        self.client.loop_stop()
        self.client.disconnect()
        print("✓ Cleanup complete")

def main():
    """Main entry point"""
    try:
        reader = CameraPlateReader()
        reader.run()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
