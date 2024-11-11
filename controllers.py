import logging
import os
import time

from datetime import datetime

import serial
import cv2


class MultimediaController:

    def __init__(self, camera_index=0):
        self.logger = logging.getLogger('QualityControl.Multimedia')
        self.camera_index = camera_index

        try:
            self.cap = cv2.VideoCapture(self.camera_index)
            if not self.cap.isOpened():
                raise Exception("Could not open video device")
            self.logger.info(f"Webcam {camera_index} initialized successfully")
        except Exception as e:
            self.logger.error(f"Failed to initialize webcam: {e}")
            raise

    def capture_images(self, save_folder='captured_images'):
        images = []
        try:
            if not os.path.exists(save_folder):
                os.makedirs(save_folder)
                self.logger.info(f"Created image save folder: {save_folder}")

            for i in range(4):
                ret, frame = self.cap.read()
                if not ret:
                    self.logger.error(f"Failed to capture image {i+1}")
                    continue

                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                filename = os.path.join(save_folder, f'image_{timestamp}.png')
                cv2.imwrite(filename, frame)
                images.append(filename)
                self.logger.info(f"Captured and saved image: {filename}")
                time.sleep(8)

            return images
        except Exception as e:
            self.logger.error(f"Error during image capture: {e}")
            return []

    def __del__(self):
        if hasattr(self, 'cap') and self.cap.isOpened():
            self.cap.release()
            self.logger.info("Webcam released")


class SerialComsController:

    def __init__(self, port='COM8', baudrate=9600, timeout=1):
        self.logger = logging.getLogger('QualityControl.Serial')
        self.ser = None
        try:
            self.ser = serial.Serial(port, baudrate, timeout=timeout)
            time.sleep(2)
            self.logger.info(f"Serial connection established on {port}")
        except serial.SerialException as e:
            self.logger.error(f"Error opening serial port {port}: {e}")
            raise

    def send_command(self, command):
        try:
            if self.ser and self.ser.is_open:
                self.ser.write(f"{command}\n".encode())
                self.logger.info(f"Sent command: {command}")
            else:
                self.logger.error("Serial port is not open")
        except Exception as e:
            self.logger.error(f"Error sending command {command}: {e}")

    def start_process(self):
        self.send_command("START")

    def handle_defect(self):
        self.send_command("DEFECT")

    def handle_normal(self):
        self.send_command("NORMAL")

    def reset_all_devices(self):
        self.send_command("RESET")

    def __del__(self):
        if hasattr(self, 'ser') and self.ser and self.ser.is_open:
            self.ser.close()
            self.logger.info("Serial connection closed")
