#!/usr/bin/env python3
import os
import cv2
import logging

logger = logging.getLogger("stash_face_cropper")

CASCADE_FILE = os.path.join(os.path.dirname(cv2.__file__), "data", "haarcascade_frontalface_default.xml")
if not os.path.exists(CASCADE_FILE):
    logger.error("OpenCV Haar Cascade file not found. Face cropping disabled.")
    CASCADE_FILE = None

face_cascade = cv2.CascadeClassifier(CASCADE_FILE) if CASCADE_FILE else None

def crop_and_save_performer_image(image_path, output_path=None, target_size=(500, 500)):
    if not os.path.exists(image_path):
        return image_path

    final_path = image_path
    
    if not output_path:
        dir_name = os.path.dirname(image_path)
        base_name = os.path.splitext(os.path.basename(image_path))[0]
        output_path = os.path.join(dir_name, f"{base_name}_plex.jpg")

    try:
        img = cv2.imread(image_path)
        if img is None:
            return image_path

        h, w, _ = img.shape
        aspect_ratio = h / w

        if aspect_ratio < 1.2:
            return image_path

        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        faces = face_cascade.detectMultiScale(gray, 1.1, 4)

        if len(faces) > 0:
            x, y, w_face, h_face = max(faces, key=lambda f: f[2]*f[3])
            cx = x + (w_face // 2)
            cy = y + (h_face // 2)
            square_size = int(max(w_face, h_face) * 2.5)
            crop_x = max(0, cx - (square_size // 2))
            crop_y = max(0, cy - (square_size // 2))
            crop_w = min(square_size, w - crop_x)
            crop_h = min(square_size, h - crop_y)
            cropped_img = img[crop_y:crop_y+crop_h, crop_x:crop_x+crop_w]
            resized = cv2.resize(cropped_img, target_size)
            cv2.imwrite(output_path, resized)
            logger.info(f"✅ Face cropped: {image_path} -> {output_path}")
            return output_path
        else:
            logger.info(f"ℹ️ No face found in {image_path}, center-cropping.")
            center_x = w // 2
            center_y = h // 2
            crop_size = min(w, h)
            start_x = center_x - (crop_size // 2)
            start_y = center_y - (crop_size // 2)
            center_crop = img[start_y:start_y+crop_size, start_x:start_x+crop_size]
            resized = cv2.resize(center_crop, target_size)
            cv2.imwrite(output_path, resized)
            logger.info(f"✅ Center cropped: {image_path} -> {output_path}")
            return output_path

    except Exception as e:
        logger.error(f"❌ Failed to crop image {image_path}: {e}")
        return image_path