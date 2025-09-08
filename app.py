import sqlite3
import cv2
import threading
import time
import os
import glob
import numpy as np
from flask import Flask, Response, render_template, jsonify, request, redirect, url_for, flash
from datetime import datetime, timedelta
# Removed Gemini API dependency - using Roboflow API instead
from roboflow_integration import initialize_roboflow_detector
from database import init_db, save_reading, get_readings, clear_all_readings
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-here'  # Change this to a secure secret key

# Add cache-busting headers to prevent browser caching issues
@app.after_request
def after_request(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response

# Initialize database
def init_extended_db():
    conn = sqlite3.connect('readings.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS user_settings
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  user_id TEXT,
                  daily_cost_limit REAL)''')
    
    # Create alerts table
    c.execute('''CREATE TABLE IF NOT EXISTS alerts
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  user_id TEXT,
                  message TEXT,
                  type TEXT,
                  timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                  is_read INTEGER DEFAULT 0)''')
    conn.commit()
    conn.close()

init_db()
init_extended_db()

# Clear all readings on startup to ensure fresh start
clear_all_readings()

# Initialize Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# User class for Flask-Login
class User(UserMixin):
    def __init__(self, id):
        self.id = id

@login_manager.user_loader
def load_user(user_id):
    return User(user_id)

# Hardcoded credentials as per requirement
VALID_EMAIL = "admin"
VALID_PASSWORD = "1234"

# Global variables
last_reading = "No reading yet"
last_reading_time = None
last_bill_amount = 0  # Holds the latest bill amount from Selenium
daily_cost_limit = 0  # Default cost limit
debug_info = "Not started"
initial_reading_value = None  # Holds the first valid reading
current_phase = "single"      # "single" or "three" based on the HTML selection
process_started = False         # To ensure we only start once
detection_active = False        # To track if detection is actively running
video_current_time = 0         # Track current video time
last_detection_time = 0        # Track last detection time
processing_lock = False        # Lock to prevent concurrent processing

def get_bill_from_site(consumption, phase):
    """
    Use Selenium (like bill calc.py) to get the bill amount 
    from https://bills.kseb.in based on consumption and meter phase.
    """
    from selenium import webdriver
    from selenium.webdriver.chrome.service import Service
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.common.by import By
    from selenium.webdriver.common.keys import Keys
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from webdriver_manager.chrome import ChromeDriverManager
    
    chrome_options = Options()
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    
    # Use webdriver-manager to automatically get the correct ChromeDriver version
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    
    try:
        driver.get("https://bills.kseb.in")
        if phase != 1:
            phase_element = driver.find_element(By.ID, "phase3")
            phase_element.click()
        reading_str = str(int(consumption))
        input_element = driver.find_element(By.ID, "unit")
        input_element.clear()
        input_element.send_keys(reading_str + Keys.ENTER)
        wait = WebDriverWait(driver, 10)
        element = wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, ".total.blue-tail")))
        text_value = element.text.strip()
        clean_value = ''.join(filter(str.isdigit, text_value))
        val = int(clean_value) if clean_value else 0
        amount = val / 100
        time.sleep(2)
        return amount
    except Exception as e:
        print("Error in get_bill_from_site:", e)
        return None
    finally:
        driver.quit()

@app.route('/get_status')
def get_status():
    """Return status for Roboflow video processing."""
    global process_started, debug_info
    
    if process_started:
        return jsonify({
            'next_capture_in': "N/A",
            'next_capture_time': "N/A",
            'is_initial_delay': False,
            'status': 'Roboflow Detection Active'
        })
    else:
        return jsonify({
            'next_capture_in': "N/A",
            'next_capture_time': "N/A",
            'is_initial_delay': False,
            'status': 'Roboflow Detection Stopped'
        })

@app.route('/start_process', methods=['POST'])
def start_process():
    """Start Roboflow video processing for meter reading detection."""
    global process_started, debug_info, initial_reading_value, detection_active
    if not process_started:
        # Reset initial reading when starting afresh
        initial_reading_value = None
        process_started = True
        detection_active = True
        debug_info = "Roboflow detection started - ready to detect meter readings"
        return "Process started", 200
    else:
        return "Process already running", 200

@app.route('/stop_process', methods=['POST'])
def stop_process():
    """Stop Roboflow video processing."""
    global process_started, debug_info, detection_active
    process_started = False
    detection_active = False
    debug_info = "Roboflow detection stopped"
    return "Process stopped", 200

@app.route('/get_reading')
def get_reading():
    """Return current reading, bill amount and debug info."""
    return jsonify({
        'reading': last_reading,
        'timestamp': last_reading_time,
        'bill_amount': last_bill_amount,
        'debug_info': debug_info,
        'initial_reading': initial_reading_value
    })

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Handle login with hardcoded credentials"""
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        if email == VALID_EMAIL and password == VALID_PASSWORD:
            user = User(email)
            login_user(user)
            return redirect(url_for('camera'))
        else:
            flash('Invalid email or password')
    
    return render_template('Login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Logged out successfully')
    return redirect(url_for('login'))

@app.route('/')
def index():
    """Always redirect to login page first"""
    # Force redirect to login page
    return redirect(url_for('login'))

@app.route('/camera')
@login_required
def camera():
    """Render camera feed page (requires authentication)"""
    return render_template('index.html', 
                         last_reading=last_reading, 
                         last_reading_time=last_reading_time,
                         debug_info=debug_info)

@app.route('/dashboard')
@login_required
def dashboard():
    """Render main dashboard page"""
    return render_template('dashboard.html')

@app.route('/profile')
@login_required
def profile():
    """Render main dashboard page"""
    return render_template('profile.html')

@app.route('/alerts')
@login_required
def alerts():
    """Render main dashboard page"""
    return render_template('alerts.html')

@app.route('/get_readings')
def get_readings_route():
    """Get all readings from the database"""
    readings = get_readings()
    return jsonify([{
        'reading': r[0],
        'timestamp': r[1],
        'image_path': r[2],
        'fixed_charge': r[3],
        'energy_charge': r[4],
        'tod_charge': r[5],
        'duty': r[6],
        'subsidy': r[7],
        'total_amount': r[8]
    } for r in readings])

@app.route('/clear_readings', methods=['POST'])
def clear_readings():
    """Clear all readings from the database but keep the cost limit."""
    global initial_reading_value, last_reading, last_reading_time, last_bill_amount, debug_info
    try:
        conn = sqlite3.connect('readings.db')
        c = conn.cursor()
        # Clear only readings, not user settings
        c.execute('DELETE FROM readings')
        conn.commit()
        conn.close()

        # Reset global variables
        initial_reading_value = None
        last_reading = "No reading yet"
        last_reading_time = None
        last_bill_amount = 0
        debug_info = "All readings cleared"

        return jsonify({
            "success": True,
            "message": "All readings cleared successfully"
        })
    except Exception as e:
        print(f"Error clearing readings: {e}")
        return jsonify({
            "success": False,
            "message": f"Failed to clear readings: {str(e)}"
        })

@app.route('/update_phase', methods=['POST'])
def update_phase():
    """Update meter phase based on user selection from the webpage."""
    global current_phase
    data = request.get_json()
    phase = data.get('phase', 'single')
    current_phase = phase  # "single" or "three"
    return "Phase updated", 200

@app.route('/update_video_time', methods=['POST'])
def update_video_time():
    """Update current video time for continuous detection."""
    global video_current_time, last_detection_time, detection_active
    
    if not detection_active:
        return jsonify({'success': False, 'message': 'Detection not active'})
    
    data = request.get_json()
    video_time = data.get('video_time', 0)
    video_current_time = video_time
    
    # Check if we should detect (every 5 seconds)
    if video_time > last_detection_time + 4.5:
        last_detection_time = video_time
        # Trigger detection
        try:
            result = process_meter_reading_internal(video_time)
            return jsonify(result)
        except Exception as e:
            return jsonify({'success': False, 'message': str(e)})
    
    return jsonify({'success': True, 'message': 'Video time updated'})

def process_meter_reading_internal(video_time):
    """Internal function to process meter reading at specific video time."""
    global last_reading, last_reading_time, debug_info, initial_reading_value, current_phase, last_bill_amount, processing_lock
    
    # Prevent concurrent processing
    if processing_lock:
        print(f"PROCESSING LOCKED: Another process is already running, skipping video time {video_time}")
        return {'success': True, 'message': 'Processing locked - skipping', 'reading': None, 'skip_toast': True}
    
    processing_lock = True
    print(f"PROCESSING LOCK ACQUIRED: Starting processing for video time {video_time}")
    
    try:
        print(f"Processing meter reading at video time: {video_time}")
        
        # Initialize Roboflow detector
        detector = initialize_roboflow_detector()
        
        # Process video frame using Roboflow API with faster processing
        result = detector.process_video_frame('static/sample.mp4', video_time, confidence=0.05)
        
        if not result['success']:
            debug_info = f"Roboflow detection failed at {video_time:.1f}s: {result.get('error', 'Unknown error')}"
            return {'success': False, 'message': result.get('error', 'Detection failed')}
        
        # Extract reading from Roboflow result
        reading_value = result['reading']
        current_units = float(reading_value)
        
        print(f"Roboflow detected meter reading: {current_units} at video time: {video_time}")
        
        # Set initial reading if this is the first valid reading
        if initial_reading_value is None:
            initial_reading_value = current_units
            debug_info = f"Initial reading set: {initial_reading_value} KWh"
            print(f"INITIAL READING SET: {initial_reading_value} KWh - No calculation needed")
            return {'success': True, 'message': 'Initial reading set', 'reading': current_units}
        
        # Calculate difference from initial reading
        difference_units = current_units - initial_reading_value
        
        # Skip if difference is 0 or negative (should not happen after initial reading is set)
        if difference_units <= 0:
            debug_info = f"Initial reading: {initial_reading_value} KWh | Current reading: {current_units} KWh"
            print(f"SKIPPING SAME READING: Current reading same as initial reading")
            return {'success': True, 'message': 'Same reading as initial - skipping', 'reading': current_units, 'skip_toast': True}
        
        # Check if this is a duplicate reading by checking database
        conn = sqlite3.connect('readings.db')
        c = conn.cursor()
        c.execute('SELECT reading FROM readings ORDER BY timestamp DESC LIMIT 10')
        recent_readings = c.fetchall()
        conn.close()
        
        print(f"Checking for duplicates. Current difference: {difference_units:.1f} KWh")
        print(f"Recent readings from DB: {[r[0] for r in recent_readings]}")
        
        # Check if this difference already exists in recent readings
        is_duplicate = False
        for (reading_str,) in recent_readings:
            try:
                existing_diff = float(reading_str.replace(' KWh (Δ)', ''))
                print(f"Comparing {difference_units:.1f} with existing {existing_diff:.1f}")
                if abs(difference_units - existing_diff) < 0.1:
                    is_duplicate = True
                    print(f"DUPLICATE DETECTED: {difference_units:.1f} KWh matches existing {existing_diff:.1f} KWh")
                    break
            except ValueError:
                continue
        
        if is_duplicate:
            debug_info = f"Current: {current_units} KWh | Initial: {initial_reading_value} KWh | Difference: {difference_units:.1f} KWh | Duplicate reading; skipping"
            print(f"SKIPPING DUPLICATE: {debug_info}")
            return {'success': True, 'message': 'Duplicate reading skipped', 'reading': current_units}
        
        new_reading = f"{difference_units:.0f} KWh (Δ)"
        
        print(f"NEW READING DETECTED: {new_reading} - Saving to database")
        
        # Calculate bill amount using Selenium
        phase_num = 1 if current_phase == "single" else 3
        bill_amount = get_bill_from_site(difference_units, phase_num)
        if bill_amount is None:
            debug_info = f"Current: {current_units} KWh | Initial: {initial_reading_value} KWh | Difference: {difference_units:.1f} KWh | Error obtaining bill amount"
            bill_amount = 0
        
        last_bill_amount = round(bill_amount, 2)
        print(f"Bill amount: Rs.{last_bill_amount}")
        
        # Update global variables
        last_reading = new_reading
        last_reading_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        debug_info = f"Current: {current_units} KWh | Initial: {initial_reading_value} KWh | Difference: {difference_units:.1f} KWh | Bill: ₹{last_bill_amount}"
        
        # Save to database
        bill_details = {
            'final': last_bill_amount,
            'fixed_charge': 0,
            'energy_charge': 0,
            'tod_charge': 0,
            'duty': 0,
            'subsidy': 0
        }
        
        # Use a descriptive image path for Roboflow detection
        image_path = f"roboflow_frame_{video_time:.1f}s.jpg"
        save_reading(last_reading, image_path, bill_details)
        
        print(f"SUCCESSFULLY SAVED TO DATABASE: {last_reading} at {last_reading_time}")
        
        return {
            'success': True, 
            'message': 'Reading processed successfully',
            'reading': current_units,
            'difference': difference_units,
            'bill_amount': last_bill_amount
        }
        
    finally:
        # Always release the lock
        processing_lock = False
        print(f"PROCESSING LOCK RELEASED: Finished processing for video time {video_time}")

@app.route('/process_meter_reading', methods=['POST'])
def process_meter_reading():
    """Process meter reading from video frame detection using Roboflow API."""
    try:
        data = request.get_json()
        video_time = data.get('video_time')
        
        if not video_time:
            return jsonify({'success': False, 'message': 'No video time provided'}), 400
        
        result = process_meter_reading_internal(video_time)
        return jsonify(result)
        
    except Exception as e:
        print(f"Error processing meter reading: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/set_cost_limit', methods=['POST'])
@login_required
def set_cost_limit():
    """Set daily cost limit for the user"""
    try:
        # Get the cost limit from form data
        limit = request.form.get('cost_limit')
        if not limit:
            return jsonify({
                "success": False,
                "message": "No cost limit provided"
            })
            
        # Convert to float and validate
        limit = float(limit)
        if limit <= 0:
            return jsonify({
                "success": False,
                "message": "Please enter a valid cost limit greater than 0"
            })

        # Use admin as the user_id since we're using hardcoded login
        user_id = "admin"
        
        conn = sqlite3.connect('readings.db')
        c = conn.cursor()
        
        try:
            # First delete any existing limit for this user
            c.execute('DELETE FROM user_settings WHERE user_id = ?', (user_id,))
            
            # Insert new limit
            c.execute('INSERT INTO user_settings (user_id, daily_cost_limit) VALUES (?, ?)',
                     (user_id, limit))
            
            conn.commit()
            
            # Verify the limit was set
            c.execute('SELECT daily_cost_limit FROM user_settings WHERE user_id = ?', (user_id,))
            result = c.fetchone()
            
            if not result or result[0] != limit:
                raise Exception("Failed to verify cost limit was set correctly")
                
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()
            
        return jsonify({
            "success": True,
            "message": "Cost limit updated successfully",
            "cost_limit": limit
        })
    except ValueError:
        return jsonify({
            "success": False,
            "message": "Invalid cost limit value"
        })
    except Exception as e:
        print(f"Error setting cost limit: {str(e)}")
        return jsonify({
            "success": False,
            "message": f"Error setting cost limit: {str(e)}"
        })

@app.route('/clear_cost_limit', methods=['POST'])
@login_required
def clear_cost_limit():
    """Clear only the cost limit setting"""
    try:
        # Use admin as the user_id since we're using hardcoded login
        user_id = "admin"
        
        conn = sqlite3.connect('readings.db')
        c = conn.cursor()
        # Only clear user settings (cost limit)
        c.execute('DELETE FROM user_settings WHERE user_id = ?', (user_id,))
        conn.commit()
        conn.close()
        
        return jsonify({
            "success": True,
            "message": "Cost limit cleared successfully"
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"Error clearing cost limit: {str(e)}"
        })

@app.route('/clear_all', methods=['POST'])
@login_required
def clear_all():
    """Clear all readings only (preserve user settings like daily limit)"""
    global initial_reading_value, last_reading, last_reading_time, last_bill_amount, debug_info, detection_active, video_current_time, last_detection_time, processing_lock
    try:
        conn = sqlite3.connect('readings.db')
        c = conn.cursor()
        # Clear readings only (preserve user settings like daily limit)
        c.execute('DELETE FROM readings')
        conn.commit()
        conn.close()
        
        # Reset ALL global variables for fresh start
        initial_reading_value = None
        last_reading = "No reading yet"
        last_reading_time = None
        last_bill_amount = 0
        debug_info = "Not started"
        detection_active = False
        video_current_time = 0
        last_detection_time = 0
        processing_lock = False
        
        print("CLEAR ALL: All global variables reset for fresh start")
        
        return jsonify({
            "success": True,
            "message": "All data cleared successfully"
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"Error clearing data: {str(e)}"
        })

@app.route('/get_dashboard_data')
@login_required
def get_dashboard_data():
    """Get all dashboard data including current reading, average, and limits"""
    try:
        # Get all readings from history
        readings = get_readings()
        
        # Use admin as the user_id since we're using hardcoded login
        user_id = "admin"
        
        # Get user's cost limit first
        conn = sqlite3.connect('readings.db')
        c = conn.cursor()
        c.execute('SELECT daily_cost_limit FROM user_settings WHERE user_id = ?', (user_id,))
        result = c.fetchone()
        cost_limit = float(result[0]) if result else 0
        conn.close()
        
        print(f"Retrieved cost limit: {cost_limit}")  # Debug print
        
        if readings:
            # Get the latest reading for current consumption
            latest_reading = readings[0]  # First reading since we order by DESC
            # Extract numeric value from reading (remove 'KWh' and '(Δ)')
            reading_value = latest_reading[0].split()[0]
            current_reading = latest_reading[0]  # Use the full reading text
            current_bill = float(latest_reading[8])  # Total amount from the last reading
            
            # Calculate average daily usage from all readings
            total_units = sum(float(r[0].split()[0]) for r in readings if r[0].split()[0].replace('.','').isdigit())
            avg_daily = total_units / len(readings)
            
            # Get consumption trend data
            trend_readings = readings[-30:]  # Get last 30 readings for trend
            consumption_data = []
            consumption_labels = []
            
            # Initialize peak hours data
            peak_hours_data = [0] * 8  # 8 time slots (12AM, 3AM, 6AM, 9AM, 12PM, 3PM, 6PM, 9PM)
            peak_hours_counts = [0] * 8  # Count readings in each slot for averaging
            
            for reading in trend_readings:
                try:
                    value = float(reading[0].split()[0])  # Extract numeric value from reading
                    consumption_data.append(value)
                    # Format timestamp for label
                    time_str = reading[1]  # Timestamp from reading
                    dt = datetime.strptime(time_str, '%Y-%m-%d %H:%M:%S')
                    consumption_labels.append(dt.strftime('%d/%m %H:%M'))
                    
                    # Calculate peak hours data
                    hour = dt.hour
                    slot = hour // 3  # Divide day into 8 3-hour slots
                    peak_hours_data[slot] += value
                    peak_hours_counts[slot] += 1
                    
                except (ValueError, IndexError) as e:
                    print(f"Error processing reading: {e}")
                    continue
            
            # Calculate averages for peak hours
            peak_hours_data = [
                round(peak_hours_data[i] / peak_hours_counts[i], 2) if peak_hours_counts[i] > 0 else 0 
                for i in range(8)
            ]
            
        else:
            # No readings in history
            current_reading = "0 KWh"
            current_bill = 0
            avg_daily = 0
            consumption_data = []
            consumption_labels = []
            peak_hours_data = [0] * 8

        # Calculate limit usage percentage based on latest bill amount
        limit_used_percent = (current_bill / cost_limit * 100) if cost_limit > 0 else 0
        limit_remaining_percent = max(0, 100 - limit_used_percent)

        # Generate alerts based on latest bill amount
        if cost_limit > 0 and readings:
            save_limit_alert(user_id, current_bill, cost_limit, limit_used_percent)

        response_data = {
            "current_reading": current_reading,
            "average_daily": f"{avg_daily:.1f}",
            "current_bill": current_bill,
            "cost_limit": cost_limit,
            "limit_used_percent": limit_used_percent,
            "limit_remaining_percent": limit_remaining_percent,
            "has_readings": bool(readings),
            "consumption_data": consumption_data,
            "consumption_labels": consumption_labels,
            "peak_hours_data": peak_hours_data
        }
        print(f"Sending dashboard data: {response_data}")  # Debug print
        return jsonify(response_data)
        
    except Exception as e:
        print(f"Error in get_dashboard_data: {str(e)}")
        return jsonify({"error": str(e)})

def cleanup():
    """Clean up resources and logout users"""
    global process_started
    process_started = False
    try:
        pass  # No camera to release in video mode
    except Exception as e:
        print("Error in cleanup:", e)
    
    # Clear user sessions only (not readings)
    try:
        conn = sqlite3.connect('readings.db')
        c = conn.cursor()
        c.execute('DELETE FROM user_settings')  # Clear user settings
        conn.commit()
        conn.close()
        print("🧹 User sessions cleared")
    except Exception as e:
        print("Error clearing user sessions:", e)

def save_alert(user_id, message, alert_type):
    """Save an alert to the database"""
    try:
        conn = sqlite3.connect('readings.db')
        c = conn.cursor()
        c.execute('INSERT INTO alerts (user_id, message, type) VALUES (?, ?, ?)',
                 (user_id, message, alert_type))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Error saving alert: {e}")

@app.route('/get_alerts')
@login_required
def get_alerts():
    """Get all alerts for the current user"""
    try:
        conn = sqlite3.connect('readings.db')
        c = conn.cursor()
        c.execute('SELECT id, message, type, timestamp, is_read FROM alerts WHERE user_id = ? ORDER BY timestamp DESC',
                 (current_user.id,))
        alerts = c.fetchall()
        conn.close()
        
        return jsonify([{
            'id': alert[0],
            'message': alert[1],
            'type': alert[2],
            'timestamp': alert[3],
            'is_read': alert[4]
        } for alert in alerts])
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/mark_alert_read/<int:alert_id>', methods=['POST'])
@login_required
def mark_alert_read(alert_id):
    """Mark an alert as read"""
    try:
        conn = sqlite3.connect('readings.db')
        c = conn.cursor()
        c.execute('UPDATE alerts SET is_read = 1 WHERE id = ? AND user_id = ?',
                 (alert_id, current_user.id))
        conn.commit()
        conn.close()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/clear_alerts', methods=['POST'])
@login_required
def clear_alerts():
    """Clear all alerts for the current user"""
    try:
        conn = sqlite3.connect('readings.db')
        c = conn.cursor()
        c.execute('DELETE FROM alerts WHERE user_id = ?', (current_user.id,))
        conn.commit()
        conn.close()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Modify the updateDashboard function to save alerts
def save_limit_alert(user_id, current_bill, cost_limit, limit_used_percent):
    if limit_used_percent >= 100:
        message = f"Alert: Daily cost limit exceeded! Current bill: ₹{current_bill:.2f}, Limit: ₹{cost_limit}"
        save_alert(user_id, message, "danger")
    elif limit_used_percent >= 90:
        remaining = cost_limit - current_bill
        message = f"Warning: Approaching daily limit! Used: {limit_used_percent:.1f}%, Remaining: ₹{remaining:.2f}"
        save_alert(user_id, message, "warning")

@app.teardown_appcontext
def cleanup_on_shutdown(error):
    """Called when the application context is torn down."""
    if error:
        print(f"Error during cleanup: {error}")
    # Only cleanup process state, not readings
    global process_started
    process_started = False

if __name__ == '__main__':
    # Clear all user sessions on startup to force login
    print("🧹 Clearing all user sessions on startup...")
    try:
        conn = sqlite3.connect('readings.db')
        c = conn.cursor()
        c.execute('DELETE FROM user_settings')  # Clear user settings
        conn.commit()
        conn.close()
        print("✅ All user sessions cleared - users will need to login")
    except Exception as e:
        print(f"Error clearing sessions: {e}")
    
    # Force clear Flask session data
    import shutil
    import tempfile
    try:
        # Clear Flask session files if they exist
        session_dir = tempfile.gettempdir()
        for file in os.listdir(session_dir):
            if file.startswith('flask_session_'):
                os.remove(os.path.join(session_dir, file))
        print("✅ Flask session files cleared")
    except Exception as e:
        print(f"Error clearing Flask sessions: {e}")
    
    os.makedirs('input', exist_ok=True)
    try:
        app.run(host='0.0.0.0', port=5000, debug=False)
    except KeyboardInterrupt:
        print("KeyboardInterrupt received.")
    except Exception as e:
        print(f"Error occurred: {e}")
    finally:
        print("Cleaning up and logging out all users...")
        cleanup()
        print("Cleanup complete. All users logged out.")
