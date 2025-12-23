#!/usr/bin/env python3
"""
Ultrasonic Sensor Module for Vehicle Detection
Continuously monitors for objects and publishes detection events to MQTT
"""

import time
import RPi.GPIO as GPIO
import paho.mqtt.client as mqtt
import json
from datetime import datetime
import config

class UltrasonicSensor:
    def __init__(self):
        """Initialize ultrasonic sensor and MQTT client"""
        # Setup GPIO
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(config.ULTRASONIC_TRIGGER_PIN, GPIO.OUT)
        GPIO.setup(config.ULTRASONIC_ECHO_PIN, GPIO.IN)

        # Initialize MQTT client
        self.client = mqtt.Client("UltrasonicSensor")
        self.client.on_connect = self.on_connect
        self.client.on_disconnect = self.on_disconnect

        # Connect to MQTT broker
        try:
            self.client.connect(config.MQTT_BROKER, config.MQTT_PORT, config.MQTT_KEEPALIVE)
            self.client.loop_start()
        except Exception as e:
            print(f"Failed to connect to MQTT broker: {e}")
            raise

        self.is_running = True
        self.last_detection_time = 0
        self.detection_cooldown = 5  # Prevent multiple detections within 5 seconds

    def on_connect(self, client, userdata, flags, rc):
        """Callback when connected to MQTT broker"""
        if rc == 0:
            print("✓ Ultrasonic Sensor connected to MQTT broker")
        else:
            print(f"✗ Failed to connect to MQTT broker. Return code: {rc}")

    def on_disconnect(self, client, userdata, rc):
        """Callback when disconnected from MQTT broker"""
        print(f"Disconnected from MQTT broker. Return code: {rc}")

    def get_distance(self):
        """
        Measure distance using ultrasonic sensor
        Returns distance in centimeters
        """
        # Send trigger pulse
        GPIO.output(config.ULTRASONIC_TRIGGER_PIN, True)
        time.sleep(0.00001)  # 10 microseconds
        GPIO.output(config.ULTRASONIC_TRIGGER_PIN, False)

        # Wait for echo
        pulse_start = time.time()
        pulse_end = time.time()
        timeout = time.time() + 1  # 1 second timeout

        # Record start time
        while GPIO.input(config.ULTRASONIC_ECHO_PIN) == 0:
            pulse_start = time.time()
            if pulse_start > timeout:
                return -1  # Timeout

        # Record end time
        while GPIO.input(config.ULTRASONIC_ECHO_PIN) == 1:
            pulse_end = time.time()
            if pulse_end > timeout:
                return -1  # Timeout

        # Calculate distance
        pulse_duration = pulse_end - pulse_start
        distance = pulse_duration * 17150  # Speed of sound = 34300 cm/s (divide by 2 for round trip)
        distance = round(distance, 2)

        return distance

    def publish_detection(self, distance):
        """Publish detection event to MQTT"""
        current_time = time.time()

        # Check cooldown period to avoid multiple rapid detections
        if current_time - self.last_detection_time < self.detection_cooldown:
            return

        detection_data = {
            "timestamp": datetime.now().isoformat(),
            "distance_cm": distance,
            "status": "object_detected"
        }

        # Publish to MQTT
        result = self.client.publish(
            config.TOPIC_ULTRASONIC_DETECTION,
            json.dumps(detection_data),
            qos=1
        )

        if result.rc == mqtt.MQTT_ERR_SUCCESS:
            print(f"🚗 Object detected at {distance} cm - Published to MQTT")
            self.last_detection_time = current_time
        else:
            print(f"✗ Failed to publish detection event")

    def run(self):
        """Main loop to continuously monitor for objects"""
        print("Starting Ultrasonic Sensor monitoring...")
        print(f"Detection threshold: {config.DETECTION_DISTANCE_CM} cm")
        print(f"Publishing to topic: {config.TOPIC_ULTRASONIC_DETECTION}")
        print("-" * 50)

        try:
            while self.is_running:
                distance = self.get_distance()

                if distance > 0:  # Valid measurement
                    # Print distance for debugging
                    print(f"Distance: {distance} cm", end='\r')

                    # Check if object is within detection range
                    if distance <= config.DETECTION_DISTANCE_CM:
                        self.publish_detection(distance)

                time.sleep(config.SENSOR_CHECK_INTERVAL)

        except KeyboardInterrupt:
            print("\n\nStopping Ultrasonic Sensor...")
        finally:
            self.cleanup()

    def cleanup(self):
        """Clean up resources"""
        print("Cleaning up resources...")
        self.is_running = False
        self.client.loop_stop()
        self.client.disconnect()
        GPIO.cleanup()
        print("✓ Cleanup complete")

def main():
    """Main entry point"""
    try:
        sensor = UltrasonicSensor()
        sensor.run()
    except Exception as e:
        print(f"Error: {e}")
        GPIO.cleanup()

if __name__ == "__main__":
    main()
