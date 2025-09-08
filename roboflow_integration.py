#!/usr/bin/env python3
"""
Roboflow Integration for Flask App - Real-time meter reading detection
"""

import requests
import base64
import cv2
import os
import time
import tempfile
from datetime import datetime

class RoboflowMeterDetector:
    def __init__(self, api_key, project_id, model_version):
        """Initialize the Roboflow meter detector."""
        self.api_key = api_key
        self.project_id = project_id
        self.model_version = model_version
        self.base_url = f"https://detect.roboflow.com/{project_id}/{model_version}"
        
        print(f"✅ Initialized Roboflow Meter Detector")
        print(f"   Project ID: {project_id}")
        print(f"   Model Version: {model_version}")

    def encode_image(self, image_path):
        """Encode image to base64 for API."""
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode('utf-8')

    def detect_meter_reading(self, image_path, confidence=0.1):
        """Detect meter reading using Roboflow API."""
        try:
            # Encode image
            image_data = self.encode_image(image_path)
            
            # Prepare request
            params = {
                "api_key": self.api_key,
                "confidence": confidence,
                "overlap": 0.5
            }
            
            # Make request
            response = requests.post(
                self.base_url,
                params=params,
                data=image_data,
                headers={"Content-Type": "application/x-www-form-urlencoded"}
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                print(f"❌ Roboflow API Error: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            print(f"❌ Error calling Roboflow API: {e}")
            return None

    def group_digits_to_reading(self, detections):
        """Group detected digits into a single meter reading."""
        if not detections or 'predictions' not in detections:
            return None
            
        # Sort detections by x-coordinate (left to right)
        sorted_detections = sorted(detections['predictions'], key=lambda x: x['x'])
        
        # Extract digits
        digits = []
        for det in sorted_detections:
            if det['class'] not in ['.', '-']:
                digits.append(det['class'])
        
        if not digits:
            return None
            
        # Join digits into reading
        reading = ''.join(digits)
        
        # For 4-digit readings
        if len(reading) < 4:
            reading = reading.zfill(4)
        elif len(reading) > 4:
            reading = reading[:4]
            
        return reading

    def extract_frame_from_video(self, video_path, timestamp_seconds):
        """Extract a specific frame from video at given timestamp."""
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            raise ValueError(f"Could not open video: {video_path}")
        
        # Set video position to timestamp
        fps = cap.get(cv2.CAP_PROP_FPS)
        frame_number = int(timestamp_seconds * fps)
        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_number)
        
        ret, frame = cap.read()
        cap.release()
        
        if ret:
            return frame
        else:
            raise ValueError(f"Could not extract frame at {timestamp_seconds}s")

    def process_video_frame(self, video_path, timestamp_seconds, confidence=0.1):
        """Process a single video frame for meter reading detection."""
        try:
            # Extract frame from video
            frame = self.extract_frame_from_video(video_path, timestamp_seconds)
            
            # Save frame temporarily
            with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as temp_file:
                temp_path = temp_file.name
                cv2.imwrite(temp_path, frame)
            
            # Detect meter reading using Roboflow API
            detections = self.detect_meter_reading(temp_path, confidence)
            
            # Clean up temp file
            os.unlink(temp_path)
            
            if detections and 'predictions' in detections:
                print(f"   Detected {len(detections['predictions'])} objects at {timestamp_seconds:.1f}s")
                
                # Show detection details
                for det in detections['predictions']:
                    print(f"     {det['class']}: {det['confidence']:.3f}")
                
                # Group digits into reading
                reading = self.group_digits_to_reading(detections)
                
                if reading:
                    print(f"   ✅ Meter Reading: {reading}")
                    return {
                        'success': True,
                        'reading': reading,
                        'timestamp': timestamp_seconds,
                        'num_detections': len(detections['predictions']),
                        'avg_confidence': sum(d['confidence'] for d in detections['predictions']) / len(detections['predictions'])
                    }
                else:
                    print(f"   ❌ No valid reading detected")
                    return {
                        'success': False,
                        'error': 'No valid reading detected',
                        'timestamp': timestamp_seconds
                    }
            else:
                print(f"   ❌ No detections from Roboflow API")
                return {
                    'success': False,
                    'error': 'No detections from API',
                    'timestamp': timestamp_seconds
                }
                
        except Exception as e:
            print(f"❌ Error processing frame at {timestamp_seconds}s: {e}")
            return {
                'success': False,
                'error': str(e),
                'timestamp': timestamp_seconds
            }

# Global instance
roboflow_detector = None

def initialize_roboflow_detector():
    """Initialize the global Roboflow detector instance."""
    global roboflow_detector
    if roboflow_detector is None:
        roboflow_detector = RoboflowMeterDetector(
            api_key="mwY8QAFFdfiIyLG57bQK",
            project_id="7-segments-custom-hblhp", 
            model_version="6"
        )
    return roboflow_detector
