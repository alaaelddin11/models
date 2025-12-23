#!/usr/bin/env python3
"""
Servo Motor Gate Controller
Subscribes to camera result events and controls gate based on access status
"""

import time
import json
from datetime import datetime
import paho.mqtt.client as mqtt
import RPi.GPIO as GPIO
import config

class ServoGateController:
    def __init__(self):
        """Initialize servo motor and MQTT client"""
        # Setup GPIO
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(config.SERVO_PIN, GPIO.OUT)

        # Initialize PWM on servo pin (50Hz for standard servo)
        self.pwm = GPIO.PWM(config.SERVO_PIN, 50)
        self.pwm.start(0)

        # Initialize MQTT client
        self.client = mqtt.Client("ServoGateController")
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

        self.is_running = True
        self.gate_open = False

        # Initialize gate to closed position
        self.close_gate()

    def on_connect(self, client, userdata, flags, rc):
        """Callback when connected to MQTT broker"""
        if rc == 0:
            print("✓ Servo Gate Controller connected to MQTT broker")
            # Subscribe to camera result topic
            client.subscribe(config.TOPIC_CAMERA_RESULT, qos=1)
            print(f"✓ Subscribed to: {config.TOPIC_CAMERA_RESULT}")
        else:
            print(f"✗ Failed to connect to MQTT broker. Return code: {rc}")

    def on_disconnect(self, client, userdata, rc):
        """Callback when disconnected from MQTT broker"""
        print(f"Disconnected from MQTT broker. Return code: {rc}")

    def on_message(self, client, userdata, msg):
        """Callback when message received from MQTT"""
        try:
            # Parse camera result message
            result_data = json.loads(msg.payload.decode())
            print(f"\n📡 Received camera result: {result_data}")

            access_granted = result_data.get('access_granted', False)
            plate_number = result_data.get('plate_number', 'UNKNOWN')
            remaining_passes = result_data.get('remaining_passes', 0)

            print(f"Vehicle: {plate_number}")
            print(f"Access: {'GRANTED ✓' if access_granted else 'DENIED ✗'}")
            if access_granted:
                print(f"Remaining passes: {remaining_passes}")

            # Control gate based on access status
            if access_granted:
                self.open_gate()
                time.sleep(config.GATE_OPEN_TIME_SECONDS)
                self.close_gate()
            else:
                print("🚫 Gate remains closed - Access denied")
                # Ensure gate is closed
                self.close_gate()

        except Exception as e:
            print(f"Error processing message: {e}")

    def set_servo_angle(self, angle):
        """
        Set servo to specific angle
        Args:
            angle: Angle in degrees (0-180)
        """
        # Convert angle to duty cycle
        # Duty cycle = (angle / 18) + 2
        # For 0°: 2% duty cycle
        # For 90°: 7% duty cycle
        # For 180°: 12% duty cycle
        duty = (angle / 18) + 2
        self.pwm.ChangeDutyCycle(duty)
        time.sleep(0.5)  # Allow time for servo to move
        self.pwm.ChangeDutyCycle(0)  # Stop sending signal to prevent jitter

    def open_gate(self):
        """Open the gate"""
        if not self.gate_open:
            print(f"🚪 Opening gate to {config.SERVO_OPEN_ANGLE}°...")
            self.set_servo_angle(config.SERVO_OPEN_ANGLE)
            self.gate_open = True
            print(f"✓ Gate opened for {config.GATE_OPEN_TIME_SECONDS} seconds")
        else:
            print("Gate already open")

    def close_gate(self):
        """Close the gate"""
        if self.gate_open or not hasattr(self, 'gate_initialized'):
            print(f"🚪 Closing gate to {config.SERVO_CLOSE_ANGLE}°...")
            self.set_servo_angle(config.SERVO_CLOSE_ANGLE)
            self.gate_open = False
            self.gate_initialized = True
            print("✓ Gate closed")

    def run(self):
        """Main loop to keep the program running"""
        print("Starting Servo Gate Controller...")
        print(f"Subscribed to: {config.TOPIC_CAMERA_RESULT}")
        print(f"Gate open angle: {config.SERVO_OPEN_ANGLE}°")
        print(f"Gate close angle: {config.SERVO_CLOSE_ANGLE}°")
        print(f"Gate open duration: {config.GATE_OPEN_TIME_SECONDS} seconds")
        print("-" * 60)
        print("Waiting for camera result events...")
        print("-" * 60)

        try:
            while self.is_running:
                time.sleep(1)

        except KeyboardInterrupt:
            print("\n\nStopping Servo Gate Controller...")
        finally:
            self.cleanup()

    def cleanup(self):
        """Clean up resources"""
        print("Cleaning up resources...")
        self.is_running = False

        # Ensure gate is closed before exiting
        if self.gate_open:
            self.close_gate()

        self.pwm.stop()
        self.client.loop_stop()
        self.client.disconnect()
        GPIO.cleanup()
        print("✓ Cleanup complete")

def main():
    """Main entry point"""
    try:
        controller = ServoGateController()
        controller.run()
    except Exception as e:
        print(f"Error: {e}")
        GPIO.cleanup()

if __name__ == "__main__":
    main()
