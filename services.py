import logging

import cv2
import SimpleITK as sitk
import numpy as np

from skimage import measure


class ImageProcessingService:

    def __init__(self):
        self.logger = logging.getLogger('QualityControl.ImageProcessing')

    def process_image_for_defects(self, image_path):
        try:
            self.logger.info(f"Processing image for defects: {image_path}")

            # Read and process image
            image = sitk.ReadImage(image_path)
            image_array = sitk.GetArrayFromImage(image)
            image_gray = np.mean(image_array, axis=2)

            # Threshold and mask
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

            # Convert to RGB for annotation
            result_rgb = cv2.cvtColor(result_image.astype(np.uint8),
                                      cv2.COLOR_GRAY2RGB)

            # Draw bounding box
            cv2.rectangle(result_rgb, (int(min_col), int(min_row)),
                          (int(max_col), int(max_row)), (255, 0, 0), 2)

            # Add rectangularity score
            text = f"         {rectangularity:.3f}"
            cv2.putText(result_rgb, text, (10, 30), cv2.FONT_HERSHEY_SIMPLEX,
                        1, (0, 255, 255), 2)

            self.logger.info("Image processing complete. Rectangularity: " +
                             f"{rectangularity:.4f}")

            # Determine if there are defects
            has_defects = rectangularity < 0.7 or rectangularity > 0.95

            return result_rgb, has_defects

        except Exception as e:
            self.logger.error(f"Error processing image: {e}")
            return None, False
        except Exception as e:
            self.logger.error(f"Error processing image: {e}")
            return None, True
