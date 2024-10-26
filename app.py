"""
This is the main file containing the code for the GUI application. The
application is a simple quality control system that uses an Arduino Mega
for controlling motors, LCD displays, buzzers and Webcam
"""

# pip install ttkbootstrap pillow simpleitk numpy scikit-image opencv-python

import ttkbootstrap as ttk
from ttkbootstrap.constants import LEFT, RIGHT, BOTTOM, Y, X, BOTH, TOP
from ttkbootstrap.dialogs import MessageDialog
from PIL import Image, ImageTk

import SimpleITK as sitk
import numpy as np
from skimage import measure
import cv2
import time
from threading import Thread
from datetime import datetime
import json
import os
import serial
import logging
from logging.handlers import RotatingFileHandler


# Configure logging
def setup_logging():
    log_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    log_file = 'quality_control.log'

    # Create handlers
    file_handler = RotatingFileHandler(log_file,
                                       maxBytes=5 * 1024 * 1024,
                                       backupCount=5)
    file_handler.setFormatter(log_formatter)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(log_formatter)

    # Create logger
    logger = logging.getLogger('QualityControl')
    logger.setLevel(logging.INFO)
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logger


LOGGER = setup_logging()
TITLE = "Automatic Quality Control System"


class MultimediaController:

    def __init__(self):
        self.logger = logging.getLogger('QualityControl.Multimedia')
        try:
            self.cap = cv2.VideoCapture(0)
            if not self.cap.isOpened():
                raise Exception("Could not open video device")
            self.logger.info("Webcam initialized successfully")
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

    def __init__(self, port='COM9', baudrate=9600, timeout=1):
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


class ImageProcessingService:

    def __init__(self):
        self.logger = logging.getLogger('QualityControl.ImageProcessing')

    def process_image_for_defects(self, image_path):
        try:
            self.logger.info(f"Processing image for defects: {image_path}")

            image = sitk.ReadImage(image_path)
            image_array = sitk.GetArrayFromImage(image)
            image_gray = np.mean(image_array, axis=2)

            image_gray_sitk = sitk.GetImageFromArray(image_gray)
            otsu_filter = sitk.OtsuThresholdImageFilter()
            gray_image = sitk.Cast(
                sitk.IntensityWindowing(image_gray_sitk,
                                        windowMinimum=0,
                                        windowMaximum=255), sitk.sitkFloat32)
            mask = otsu_filter.Execute(gray_image)
            mask = sitk.Cast(mask == 0, sitk.sitkUInt8)
            masked_image = sitk.Mask(image_gray_sitk, mask)
            result_image = sitk.GetArrayFromImage(masked_image)

            contours = measure.find_contours(result_image, level=0.5)
            if not contours:
                self.logger.warning("No contours found in the image")
                return result_image, False

            largest_contour = max(contours, key=lambda x: len(x))

            # Calculate metrics
            mask_array = sitk.GetArrayFromImage(mask)
            object_area = np.sum(mask_array)

            min_row, min_col = np.min(largest_contour, axis=0)
            max_row, max_col = np.max(largest_contour, axis=0)
            width = max_col - min_col
            height = max_row - min_row
            bounding_box_area = width * height

            rectangularity = object_area / bounding_box_area
            self.logger.info(
                f"Image processing complete. Rectangularity: {rectangularity:.4f}"
            )

            # Determine if there are defects (you may need to adjust these thresholds)
            has_defects = rectangularity < 0.7 or rectangularity > 0.95

            return result_image, has_defects
        except Exception as e:
            self.logger.error(f"Error processing image: {e}")
            return None, True


class GUI(ttk.Window):

    def __init__(self):
        super().__init__(themename="cyborg")
        self.logger = logging.getLogger('QualityControl.GUI')
        self.logger.info("Initializing Quality Control Application")

        self.title("Quality Control")
        self.geometry("800x600")

        try:
            self.multimedia_controller = MultimediaController()
            self.serial_controller = SerialComsController(port='COM9')
            self.image_processor = ImageProcessingService()
            self.logger.info("All controllers initialized successfully")
        except Exception as e:
            self.logger.error(f"Failed to initialize controllers: {e}")
            self.show_error_dialog(
                "Initialization Error",
                "Failed to initialize system components. Check the log for details."
            )
            return

        self.processing_active = False
        self.current_display = "images"
        self.history_data = self.load_history()

        self.setup_gui()
        self.logger.info("GUI setup complete")

    def setup_gui(self):
        # Create main container
        self.main_container = ttk.Frame(self)
        self.main_container.pack(fill=BOTH, expand=True)

        # Create notebook for tabs
        self.notebook = ttk.Notebook(self.main_container)
        self.notebook.pack(fill=BOTH, expand=True)

        # Create tabs
        self.processing_tab = ttk.Frame(self.notebook)
        self.history_tab = ttk.Frame(self.notebook)

        self.notebook.add(self.processing_tab, text="Processing")
        self.notebook.add(self.history_tab, text="History")

        self.setup_processing_tab()
        self.setup_history_tab()

    def setup_processing_tab(self):
        self.create_menu_panel()
        self.create_image_display()
        self.create_quality_indicator()

    def setup_history_tab(self):
        # Create controls frame
        controls_frame = ttk.Frame(self.history_tab)
        controls_frame.pack(fill=X, padx=10, pady=5)

        # Add refresh button
        refresh_btn = ttk.Button(controls_frame,
                                 text="Refresh History",
                                 bootstyle="info",
                                 command=self.refresh_history)
        refresh_btn.pack(side=LEFT, padx=5)

        # Add clear history button
        clear_btn = ttk.Button(controls_frame,
                               text="Clear History",
                               bootstyle="danger",
                               command=self.clear_history)
        clear_btn.pack(side=LEFT, padx=5)

        # Create treeview for history
        columns = ("Date", "Time", "Status", "Processing Duration",
                   "Images Processed")
        self.history_tree = ttk.Treeview(self.history_tab,
                                         columns=columns,
                                         show="headings",
                                         bootstyle="primary")

        # Configure columns
        for col in columns:
            self.history_tree.heading(col, text=col)
            self.history_tree.column(col, width=150)

        # Add scrollbar
        scrollbar = ttk.Scrollbar(self.history_tab,
                                  orient="vertical",
                                  command=self.history_tree.yview)
        self.history_tree.configure(yscrollcommand=scrollbar.set)

        # Pack treeview and scrollbar
        self.history_tree.pack(fill=BOTH, expand=True, padx=10, pady=5)
        scrollbar.pack(side=RIGHT, fill=Y)

        # Load initial history data
        self.refresh_history()

    def refresh_history(self):
        # Clear existing items
        for item in self.history_tree.get_children():
            self.history_tree.delete(item)

        # Add history entries
        for entry in self.history_data:
            self.history_tree.insert(
                "",
                "end",
                values=(entry["date"], entry["time"], entry["status"],
                        entry["duration"], entry["images_processed"]))

    def show_completion_dialog(self, duration):

        def handle_result(button_pressed=None
                          ):  # Make argument optional with default value
            if button_pressed == "View History":
                self.notebook.select(self.history_tab)

        dialog = MessageDialog(
            title="Processing Complete",
            message=
            f"Image processing completed successfully!\n\nProcessing Time: {duration:.1f} seconds",
            buttons=["View History", "OK"],
            command=handle_result)
        dialog.show()

    def processing_sequence(self):
        start_time = time.time()
        self.processing_active = True
        self.start_button.configure(state="disabled")

        try:
            # Start the process on Arduino
            self.serial_controller.start_process()
            self.logger.info("Processing sequence started")

            # Capture images
            self.update_progress(25, "Capturing Images", "warning")
            captured_images = self.multimedia_controller.capture_images()
            if not captured_images:
                raise Exception("Failed to capture images")

            # Process each image
            defects_found = False
            for i, image_path in enumerate(captured_images):
                if not self.processing_active:
                    break

                self.update_progress(50 + i * 10, f"Processing Image {i+1}/4",
                                     "warning")

                # Display original image
                self.load_and_display_image(self.frames[i], image_path)

                # Process image
                result_image, has_defects = self.image_processor.process_image_for_defects(
                    image_path)
                if has_defects:
                    defects_found = True
                    self.logger.warning(f"Defects found in image {i+1}")

            # Handle results
            if defects_found:
                self.serial_controller.handle_defect()
                status = "Defects Detected"
                status_style = "danger"

            else:
                self.serial_controller.handle_normal()
                status = "No Defects Found"
                status_style = "success"

            duration = time.time() - start_time
            self.update_progress(100, status, status_style)
            self.show_completion_dialog(duration)
            self.add_history_entry(duration, status, len(captured_images))

        except Exception as e:
            self.logger.error(f"Error during processing sequence: {e}")
            self.update_progress(0, "Error Occurred", "danger")
            self.show_error_dialog(
                "Processing Error",
                f"An error occurred during processing: {str(e)}")
        finally:
            self.serial_controller.reset_all_devices()
            self.start_button.configure(state="disabled")

            time.sleep(5)
            self.start_button.configure(state="normal")
            self.start_button.configure(state="normal")
            self.processing_active = False

    def show_error_dialog(self, title, message):
        dialog = MessageDialog(title=title, message=message, buttons=["OK"])
        dialog.show()

    def load_history(self):
        try:
            if os.path.exists('processing_history.json'):
                with open('processing_history.json', 'r') as f:
                    return json.load(f)
            return []
        except Exception as e:
            print(f"Error loading history: {e}")
            return []

    def add_history_entry(self, duration, status, images_processed):
        now = datetime.now()
        entry = {
            "date": now.strftime("%Y-%m-%d"),
            "time": now.strftime("%H:%M:%S"),
            "status": status,
            "duration": f"{duration:.1f}s",
            "images_processed": images_processed
        }
        self.history_data.append(entry)
        self.save_history()
        self.refresh_history()

    def save_history(self):
        try:
            with open('processing_history.json', 'w') as f:
                json.dump(self.history_data, f)
        except Exception as e:
            print(f"Error saving history: {e}")

    def clear_history(self):

        def handle_result(button_pressed=None
                          ):  # Make argument optional with default value
            if button_pressed == "Yes":
                self._perform_clear_history()

        confirm = MessageDialog(
            title="Clear History",
            message="Are you sure you want to clear all history?",
            buttons=["No", "Yes"],
            command=handle_result)
        confirm.show()

    def _perform_clear_history(self):
        self.history_data = []
        self.save_history()
        self.refresh_history()

    def create_menu_panel(self):
        menu_frame = ttk.Frame(self.processing_tab, bootstyle="light")
        menu_frame.pack(side=LEFT, fill=Y, padx=10, pady=10)

        self.start_button = ttk.Button(menu_frame,
                                       text="START",
                                       bootstyle="danger",
                                       width=20,
                                       command=self.start_processing)
        self.start_button.pack(fill=X, pady=5)

        self.reset_button = ttk.Button(menu_frame,
                                       text="RESET",
                                       bootstyle="success",
                                       width=20,
                                       command=self.reset_display)
        self.reset_button.pack(fill=X, pady=5)

    def create_image_display(self):
        self.display_frame = ttk.Frame(self.processing_tab, bootstyle="dark")
        self.display_frame.pack(side=RIGHT,
                                expand=True,
                                fill=BOTH,
                                padx=10,
                                pady=10)

        self.title_label = ttk.Label(self.display_frame,
                                     text=TITLE,
                                     wraplength=400,
                                     bootstyle="inverse-dark",
                                     font=("Helvetica", 12, "bold"))
        self.title_label.pack(pady=(0, 10))

        self.grid_frame = ttk.Frame(self.display_frame)
        self.grid_frame.pack(expand=True, fill=BOTH)

        for i in range(2):
            self.grid_frame.columnconfigure(i, weight=1)
            self.grid_frame.rowconfigure(i, weight=1)

        self.frames = []
        for i in range(2):
            for j in range(2):
                frame = ttk.Labelframe(self.grid_frame,
                                       text=f"Frame {i*2+j+1}",
                                       bootstyle="primary")
                frame.grid(row=i, column=j, padx=5, pady=5, sticky="nsew")
                self.frames.append(frame)

    def create_quality_indicator(self):
        quality_frame = ttk.Frame(self.processing_tab)
        quality_frame.pack(side=BOTTOM, fill=X, padx=10, pady=10)

        self.quality_progress = ttk.Progressbar(quality_frame,
                                                bootstyle="success-striped",
                                                length=200,
                                                mode='determinate')
        self.quality_progress.pack(side=LEFT, padx=10)

        status_frame = ttk.Frame(quality_frame)
        status_frame.pack(side=LEFT, padx=10)

        self.quality_label = ttk.Label(status_frame,
                                       text="Status:",
                                       bootstyle="primary",
                                       font=("Helvetica", 12))
        self.quality_label.pack(side=TOP, pady=2)

        self.status_value = ttk.Label(status_frame,
                                      text="Ready",
                                      bootstyle="success",
                                      font=("Helvetica", 12, "bold"))
        self.status_value.pack(side=TOP, pady=2)

    def load_and_display_image(self, frame, image_path):
        try:
            image = Image.open(image_path)
            aspect_ratio = image.width / image.height
            max_size = 300
            if image.width > image.height:
                new_width, new_height = max_size, int(max_size / aspect_ratio)
            else:
                new_height, new_width = max_size, int(max_size * aspect_ratio)
            image = image.resize((new_width, new_height), Image.LANCZOS)
            photo = ImageTk.PhotoImage(image)
            label = ttk.Label(frame, image=photo)
            label.image = photo
            label.pack(expand=True, fill=BOTH)
        except Exception as e:
            print(f"Error loading image: {e}")
            error_label = ttk.Label(frame,
                                    text="Error loading image",
                                    bootstyle="danger")
            error_label.pack(expand=True, fill=BOTH)

    def update_progress(self, value, status_text, status_style="success"):
        self.quality_progress['value'] = value
        self.status_value.configure(text=status_text, bootstyle=status_style)

    def clear_frame(self, frame):
        for widget in frame.winfo_children():
            widget.destroy()

    def start_processing(self):
        if not self.processing_active:
            Thread(target=self.processing_sequence, daemon=True).start()

    def reset_display(self):
        for frame in self.frames:
            self.clear_frame(frame)

        self.serial_controller.reset_all_devices()
        self.start_button.configure(state="disabled")

        time.sleep(5)

        self.start_button.configure(state="normal")
        self.start_button.configure(state="normal")

        self.processing_active = False

        self.update_progress(0, "Ready", "success")
        self.title_label.config(text=TITLE)


if __name__ == "__main__":
    gui = GUI()
    gui.mainloop()
