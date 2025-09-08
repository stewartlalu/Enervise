#!/usr/bin/env python3
"""
Roboflow API Processor - Use the working Roboflow model via API
"""

import requests
import base64
import cv2
import pandas as pd
import argparse
import os
import time

class RoboflowAPIProcessor:
    def __init__(self, api_key, project_id, model_version):
        """Initialize the Roboflow API processor."""
        self.api_key = api_key
        self.project_id = project_id
        self.model_version = model_version
        self.base_url = f"https://detect.roboflow.com/{project_id}/{model_version}"
        
        print(f"✅ Initialized Roboflow API processor")
        print(f"   Project ID: {project_id}")
        print(f"   Model Version: {model_version}")

    def encode_image(self, image_path):
        """Encode image to base64 for API."""
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode('utf-8')

    def detect_with_api(self, image_path, confidence=0.3):
        """Detect digits using Roboflow API."""
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
                print(f"❌ API Error: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            print(f"❌ Error calling API: {e}")
            return None

    def extract_ten_frames_equal_gap(self, video_path):
        """Extract exactly 10 frames with equal time gaps from start to end."""
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            raise ValueError(f"Could not open video: {video_path}")
        
        fps = cap.get(cv2.CAP_PROP_FPS)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        duration = total_frames / fps
        
        print(f"🎬 Video Info:")
        print(f"   FPS: {fps:.2f}")
        print(f"   Total frames: {total_frames}")
        print(f"   Duration: {duration:.2f}s")
        
        # Calculate equal time gaps for 10 frames
        time_gap = duration / 9
        frame_gap = int(fps * time_gap)
        
        print(f"   Time gap between frames: {time_gap:.2f}s")
        print(f"   Frame gap: {frame_gap}")
        
        frames = []
        
        for i in range(10):
            frame_number = i * frame_gap
            if frame_number >= total_frames:
                frame_number = total_frames - 1
            
            # Seek to the specific frame
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame_number)
            ret, frame = cap.read()
            
            if ret:
                timestamp_ms = cap.get(cv2.CAP_PROP_POS_MSEC)
                frames.append((frame_number, timestamp_ms, frame.copy()))
                print(f"   Frame {i+1}: frame #{frame_number}, time {timestamp_ms/1000:.2f}s")
            else:
                print(f"   ❌ Failed to read frame {i+1}")
        
        cap.release()
        print(f"📸 Extracted {len(frames)} frames for processing")
        return frames

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

    def process_video(self, video_path, output_csv="roboflow_api_results.csv", confidence=0.3):
        """Process the video using Roboflow API."""
        print(f"\n🚀 Starting video processing with Roboflow API...")
        print(f"   Video: {video_path}")
        print(f"   Output: {output_csv}")
        print(f"   Confidence: {confidence}")
        
        # Extract exactly 10 frames with equal time gaps
        frames = self.extract_ten_frames_equal_gap(video_path)
        
        results = []
        
        for i, (frame_num, timestamp_ms, frame) in enumerate(frames):
            print(f"\n📸 Processing frame {i+1}/10 (frame #{frame_num})")
            print(f"   Timestamp: {timestamp_ms/1000:.2f}s")
            
            # Save frame temporarily
            temp_image_path = f"temp_frame_{i+1}.jpg"
            cv2.imwrite(temp_image_path, frame)
            
            # Detect digits using API
            detections = self.detect_with_api(temp_image_path, confidence)
            
            # Clean up temp file
            os.remove(temp_image_path)
            
            if detections and 'predictions' in detections:
                print(f"   Detected {len(detections['predictions'])} objects")
                
                # Show detection details
                for det in detections['predictions']:
                    print(f"     {det['class']}: {det['confidence']:.3f}")
                
                # Group digits into reading
                reading = self.group_digits_to_reading(detections)
                
                if reading:
                    print(f"   ✅ Reading: {reading}")
                    
                    results.append({
                        'frame_number': i + 1,
                        'video_frame': frame_num,
                        'timestamp_s': timestamp_ms / 1000.0,
                        'reading': reading,
                        'num_detections': len(detections['predictions']),
                        'avg_confidence': sum(d['confidence'] for d in detections['predictions']) / len(detections['predictions'])
                    })
                else:
                    print(f"   ❌ No valid reading detected")
            else:
                print(f"   ❌ No detections from API")
            
            # Add delay to avoid rate limiting
            time.sleep(0.5)
        
        # Save results
        if results:
            df = pd.DataFrame(results)
            df.to_csv(output_csv, index=False)
            print(f"\n✅ Processing complete!")
            print(f"   📊 Total frames processed: {len(frames)}")
            print(f"   📈 Valid readings found: {len(results)}")
            print(f"   💾 Results saved to: {output_csv}")
            
            # Show summary
            print(f"\n📋 Final Reading Summary:")
            for i, result in enumerate(results):
                print(f"   Frame {result['frame_number']}: {result['reading']} (at {result['timestamp_s']:.1f}s)")
                
            # Compare with expected readings
            expected_readings = ['1564', '1580', '1602', '1643', '1652', '1690', '1724', '1739', '1745']
            print(f"\n🎯 Comparison with Expected Readings:")
            for i, result in enumerate(results):
                expected = expected_readings[i] if i < len(expected_readings) else "N/A"
                match = "✅" if result['reading'] == expected else "❌"
                print(f"   Frame {result['frame_number']}: {result['reading']} vs {expected} {match}")
        else:
            print(f"\n❌ No readings found!")
            
        return pd.DataFrame(results) if results else pd.DataFrame()

def main():
    parser = argparse.ArgumentParser(description="Process video using Roboflow API")
    parser.add_argument("--api_key", required=True, help="Roboflow API key")
    parser.add_argument("--project_id", required=True, help="Roboflow project ID")
    parser.add_argument("--model_version", required=True, help="Model version")
    parser.add_argument("--video", required=True, help="Path to input video")
    parser.add_argument("--conf", type=float, default=0.3, help="Confidence threshold")
    parser.add_argument("--output", default="roboflow_api_results.csv", help="Output CSV file")
    
    args = parser.parse_args()
    
    # Validate inputs
    if not os.path.exists(args.video):
        print(f"❌ Video file not found: {args.video}")
        return
    
    # Initialize processor
    processor = RoboflowAPIProcessor(args.api_key, args.project_id, args.model_version)
    
    # Process video
    results = processor.process_video(args.video, args.output, args.conf)
    
    if not results.empty:
        print(f"\n🎉 Successfully processed video!")
        print(f"   Found {len(results)} meter readings")
    else:
        print(f"\n⚠️  No readings detected.")

if __name__ == "__main__":
    main()
