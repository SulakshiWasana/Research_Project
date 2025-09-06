from flask import Flask, render_template, request, jsonify, session, redirect, url_for
import cv2, numpy as np, base64, os, json, time
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'student-monitoring-system-2024'

# --- Users ---
users = {
    'student1': {'password': 'password1', 'name': 'John Doe', 'role': 'student'},
    'student2': {'password': 'password2', 'name': 'Jane Smith', 'role': 'student'},
    'admin':    {'password': 'admin123',  'name': 'Administrator', 'role': 'admin'}
}

# --- Persistent data stores ---
detection_history = {}
exams_data = {}
exam_sessions = {}

def load_data():
    global detection_history, exams_data, exam_sessions
    try:
        if os.path.exists('detection_data.json'):
            with open('detection_data.json', 'r') as f:
                detection_history = json.load(f)
        if os.path.exists('exams_data.json'):
            with open('exams_data.json', 'r') as f:
                exams_data = json.load(f)
        if os.path.exists('exam_sessions.json'):
            with open('exam_sessions.json', 'r') as f:
                exam_sessions = json.load(f)
    except Exception:
        detection_history = {}
        exams_data = {}
        exam_sessions = {}

def save_detection_data():
    try:
        with open('detection_data.json', 'w') as f:
            json.dump(detection_history, f, indent=2)
    except Exception:
        pass

def save_exams_data():
    try:
        with open('exams_data.json', 'w') as f:
            json.dump(exams_data, f, indent=2)
    except Exception:
        pass

def save_exam_sessions():
    try:
        with open('exam_sessions.json', 'w') as f:
            json.dump(exam_sessions, f, indent=2)
    except Exception:
        pass

load_data()

def ensure_bucket(username: str):
    if username not in detection_history:
        detection_history[username] = {
            'looking_away': 0,
            'multiple_people': 0,
            'no_face': 0,
            'blur_screen': 0,
            'tab_switching': 0,
            'alert_history': []
        }

# --- Always land on Login first ---
@app.route('/')
def index():
    return redirect(url_for('login'))

# --- Auth ---
@app.route('/login', methods=['GET','POST'])
def login():
    if request.method == 'POST':
        u = request.form.get('username','').strip()
        p = request.form.get('password','')
        if u in users and users[u]['password'] == p:
            session['username'] = u
            if users[u]['role'] == 'student':
                ensure_bucket(u)
                save_detection_data()
            return redirect(url_for('admin_dashboard' if users[u]['role']=='admin' else 'dashboard'))
        return render_template('login.html', error='Invalid username or password')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('username', None)
    return redirect(url_for('login'))

# --- Student dashboard ---
@app.route('/dashboard')
def dashboard():
    if 'username' not in session or users[session['username']]['role'] != 'student':
        return redirect(url_for('login'))
    u = session['username']
    ensure_bucket(u)
    counts = {k:v for k,v in detection_history[u].items() if k!='alert_history'}
    return render_template('dashboard.html', name=users[u]['name'], counts=counts, username=u)

# --- Enhanced Admin dashboard ---
@app.route('/admin')
def admin_dashboard():
    if 'username' not in session or users[session['username']]['role'] != 'admin':
        return redirect(url_for('login'))
    
    # Calculate statistics
    total_users = len(users)
    total_exams = len(exams_data)
    active_sessions = len([s for s in exam_sessions.values() if s.get('status') == 'active'])
    total_detections = sum(
        sum(data.get(k, 0) for k in ['looking_away', 'multiple_people', 'no_face', 'blur_screen', 'tab_switching'])
        for data in detection_history.values()
    )
    
    stats = {
        'total_users': total_users,
        'total_exams': total_exams,
        'active_sessions': active_sessions,
        'total_detections': total_detections
    }
    
    return render_template('admin_dashboard.html', 
                         users=users, 
                         detection_history=detection_history,
                         exams_data=exams_data,
                         exam_sessions=exam_sessions,
                         stats=stats)


# --- Student history (admin only) ---
@app.route('/student_history/<username>')
def student_history(username):
    if 'username' not in session or users[session['username']]['role'] != 'admin':
        return redirect(url_for('login'))
    if username not in detection_history:
        return render_template('student_history.html',
                               user={'name':'Unknown','username':username},
                               error='No data available for this student')
    return render_template('student_history.html',
                           user={'name': users.get(username,{}).get('name','Unknown'),
                                 'username': username},
                           history=detection_history[username])

# --- Lightweight CV detectors (heuristics only; no random) ---
face_cascade    = cv2.CascadeClassifier(cv2.data.haarcascades+'haarcascade_frontalface_default.xml')
profile_cascade = cv2.CascadeClassifier(cv2.data.haarcascades+'haarcascade_profileface.xml')
eye_cascade     = cv2.CascadeClassifier(cv2.data.haarcascades+'haarcascade_eye.xml')

def laplacian_variance(gray):
    return float(cv2.Laplacian(gray, cv2.CV_64F).var())

# Global variables for movement and absence detection
prev_frame = None
last_face_detected = None
absence_start_time = None

# Alert cooldown system to prevent spam
last_alert_time = {}
alert_cooldown_seconds = 5  # 5 seconds cooldown per alert type

def analyze_frame(image_bgr):
    """
    Returns one of: 'multiple_people', 'no_face', 'looking_away', 'blur_screen', 'none'
    """
    global prev_frame, last_face_detected, absence_start_time
    import time
    
    if image_bgr is None or image_bgr.size == 0:
        return 'no_face'

    h, w = image_bgr.shape[:2]
    if max(w, h) > 640:
        scale = 640 / max(w, h)
        image_bgr = cv2.resize(image_bgr, (int(w*scale), int(h*scale)))
    gray = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY)
    
    # Store current frame for next comparison
    prev_frame = gray.copy()

    blur = laplacian_variance(gray)
    
    # STRICT face detection for multiple people - only use frontal faces for multiple detection
    # Use very strict parameters to avoid false positives
    faces = face_cascade.detectMultiScale(gray, 1.3, 8, minSize=(80, 80), maxSize=(300, 300))
    
    # For multiple people detection, ONLY use frontal faces (no profiles)
    # Profiles will only be used later for "looking away" detection
    allf = list(faces)
    filtered_faces = []
    
    # VERY STRICT overlap filtering - remove any faces that are even slightly overlapping
    for i, face1 in enumerate(allf):
        is_duplicate = False
        for face2 in filtered_faces:
            x1, y1, w1, h1 = face1
            x2, y2, w2, h2 = face2
            
            # Calculate overlap
            overlap_x = max(0, min(x1 + w1, x2 + w2) - max(x1, x2))
            overlap_y = max(0, min(y1 + h1, y2 + h2) - max(y1, y2))
            overlap_area = overlap_x * overlap_y
            face1_area = w1 * h1
            face2_area = w2 * h2
            
            # Much stricter overlap threshold - remove if any overlap > 10%
            if overlap_area > 0.1 * min(face1_area, face2_area):
                is_duplicate = True
                break
            
            # Also check distance between centers - faces must be well separated
            center1_x, center1_y = x1 + w1//2, y1 + h1//2
            center2_x, center2_y = x2 + w2//2, y2 + h2//2
            distance = ((center1_x - center2_x)**2 + (center1_y - center2_y)**2)**0.5
            min_distance = max(w1, h1, w2, h2) * 1.2  # Faces must be at least 1.2x face size apart
            
            if distance < min_distance:
                is_duplicate = True
                break
        
        if not is_duplicate:
            # Additional quality check - reject faces that are too small, too large, or near edges
            x, y, w, h = face1
            if (w < 80 or h < 80 or w > 300 or h > 300 or 
                x < 20 or y < 20 or x + w > gray.shape[1] - 20 or y + h > gray.shape[0] - 20):
                continue
            filtered_faces.append(face1)
    
    fcnt = len(filtered_faces)
    current_time = time.time()

    if fcnt == 0:
        # Track absence duration
        if absence_start_time is None:
            absence_start_time = current_time
        
        # When no face is detected, analyze image to determine if person is absent or looking away
        mean_brightness = np.mean(gray)
        std_brightness = np.std(gray)
        
        # Check for movement/change from previous frame to detect if person moved away
        movement_detected = False
        if prev_frame is not None:
            diff = cv2.absdiff(gray, prev_frame)
            movement_score = np.mean(diff)
            movement_detected = movement_score > 10  # Threshold for significant movement
        
        # Time-based analysis
        absence_duration = current_time - absence_start_time if absence_start_time else 0
        
        # More sophisticated absence detection:
        # 1. Very dark image (person turned off lights) -> no_face
        # 2. Very low contrast (blurry/empty room) -> no_face  
        # 3. High brightness + low contrast (empty bright room) -> no_face
        # 4. Absent for more than 5 seconds -> no_face (likely left)
        # 5. Recent movement detected -> looking_away (person moved out of frame)
        # 6. Otherwise -> looking_away (person might be partially visible)
        
        is_very_dark = mean_brightness < 30
        is_low_contrast = std_brightness < 15
        is_empty_bright_room = mean_brightness > 100 and std_brightness < 25
        is_long_absence = absence_duration > 5.0  # 5 seconds
        
        if is_very_dark or is_low_contrast or is_empty_bright_room or is_long_absence:
            decision = 'no_face'
            print(f"No face detected - person absent: brightness={mean_brightness:.1f}, contrast={std_brightness:.1f}, duration={absence_duration:.1f}s")
        elif movement_detected:
            # Check if we can detect profile faces (for looking away detection)
            profs = profile_cascade.detectMultiScale(gray, 1.1, 3, minSize=(30, 30))
            if len(profs) > 0:
                decision = 'looking_away'
                print(f"No face but profile detected (looking away): brightness={mean_brightness:.1f}, movement={movement_score:.1f}")
            else:
                decision = 'looking_away'
                print(f"No face but person moved away: brightness={mean_brightness:.1f}, movement={movement_score:.1f}")
        else:
            # Check if we can detect profile faces (for looking away detection)
            profs = profile_cascade.detectMultiScale(gray, 1.1, 3, minSize=(30, 30))
            if len(profs) > 0:
                decision = 'looking_away'
                print(f"No frontal face but profile detected (looking away): brightness={mean_brightness:.1f}, contrast={std_brightness:.1f}")
            else:
                decision = 'looking_away'
                print(f"No face but looking away detected: brightness={mean_brightness:.1f}, contrast={std_brightness:.1f}")
    elif fcnt >= 2:
        # Face detected - reset absence tracking
        last_face_detected = current_time
        absence_start_time = None
        decision = 'multiple_people'
        print(f"Multiple people detected: {fcnt} faces")
    else:
        # Face detected - reset absence tracking
        last_face_detected = current_time
        absence_start_time = None
        
        # one face → check eyes/aspect (looking away)
        x, y, wf, hf = max(filtered_faces, key=lambda r: r[2]*r[3])
        aspect = (wf/float(hf)) if hf else 0.0
        roi = gray[y:y+hf, x:x+wf]
        # Try multiple eye detection methods for better sensitivity
        eyes = eye_cascade.detectMultiScale(roi, 1.05, 2)  # Even more lenient
        eyes_alt = eye_cascade.detectMultiScale(roi, 1.1, 1)  # Alternative detection
        
        # Use the detection that finds more eyes
        eyes_count = max(len(eyes), len(eyes_alt))
        
        # More sensitive looking away detection
        face_area = wf * hf
        image_area = gray.shape[0] * gray.shape[1]
        face_ratio = face_area / image_area
        
        # More sensitive triggers for looking away:
        # 1. Face is wide (side profile) - lowered threshold
        # 2. Face is small (partial face) - increased threshold  
        # 3. No eyes detected (most important indicator)
        # 4. Face positioned off-center (looking to side)
        face_center_x = x + wf/2
        image_center_x = gray.shape[1] / 2
        face_offset = abs(face_center_x - image_center_x) / image_center_x
        
        is_side_profile = aspect > 1.1  # Lowered from 1.2
        is_partial_face = face_ratio < 0.08  # Increased from 0.05 (8% instead of 5%)
        is_off_center = face_offset > 0.3  # Face is more than 30% off center
        no_eyes = eyes_count == 0
        
        # Trigger looking away if any of these conditions are met:
        # - Side profile OR partial face OR off-center face, AND no eyes detected
        # - OR just no eyes detected (most sensitive)
        decision = 'looking_away' if ((is_side_profile or is_partial_face or is_off_center) and no_eyes) or no_eyes else 'none'
        if decision == 'looking_away':
            print(f"Looking away detected: aspect={aspect:.2f}, eyes={eyes_count}, face_ratio={face_ratio:.3f}, offset={face_offset:.2f}")

    # blur detection - only trigger for very blurry images (much more lenient threshold)
    # Normal laptop webcams typically have blur values between 50-200
    if blur < 15.0 and decision in ('none','looking_away'):
        decision = 'blur_screen'
        print(f"Blur detected: {blur:.2f} (threshold: 15.0)")

    return decision

# --- Analyze endpoint (alert only when detection happens) ---
@app.route('/analyze', methods=['POST'])
def analyze():
    if 'username' not in session or users[session['username']]['role'] != 'student':
        return jsonify({'error': 'Not authenticated'}), 401

    u = session['username']
    ensure_bucket(u)

    payload = request.get_json(silent=True) or {}
    img_b64 = payload.get('image')
    if not img_b64:
        return jsonify({'error':'No image data provided'}), 400

    # decode dataURL (base64)
    b64 = img_b64.split(',', 1)[-1]
    img = cv2.imdecode(np.frombuffer(base64.b64decode(b64), np.uint8), cv2.IMREAD_COLOR)
    decision = analyze_frame(img)

    ts = datetime.now().isoformat()
    resp = {
        'alert': False,
        'message': 'Everything looks good. Keep focusing on your exam!',
        'sound_type': None,
        'screen_blurred': False
    }
    
    # Reset cooldowns only when face is properly detected (student is focused)
    # This means alerts won't repeat until student actually fixes the issue
    face_detected = decision == 'none'  # 'none' means face detected and everything is good
    if face_detected:
        # Clear cooldowns for this user to allow immediate alerts if issues return
        keys_to_remove = [key for key in last_alert_time.keys() if key.startswith(f"{u}_")]
        if keys_to_remove:
            print(f"RESET: Face detected for {u}, clearing {len(keys_to_remove)} cooldowns")
            for key in keys_to_remove:
                del last_alert_time[key]

    if decision in ('looking_away','multiple_people','no_face','blur_screen'):
        # Check cooldown to prevent spam alerts
        current_time = time.time()
        alert_key = f"{u}_{decision}"
        
        # Only alert if this type hasn't been alerted recently
        # Alert will not repeat until face is properly detected (cooldown is reset)
        should_alert = alert_key not in last_alert_time
        
        # Always increment detection count
        detection_history[u][decision] += 1
        
        if should_alert:
            # Update last alert time
            last_alert_time[alert_key] = current_time
            print(f"ALERT: {decision} - First time, sending alert to {u}")
            
            msg_map = {
                'looking_away': 'Looking away from screen detected!',
                'multiple_people': 'Multiple people detected!',
                'no_face': 'No face detected!',
                'blur_screen': 'Screen blur detected!'
            }
            detection_history[u]['alert_history'].append({
                'timestamp': ts, 'type': decision, 'message': msg_map[decision]
            })
            save_detection_data()

            resp.update(alert=True,
                        message=msg_map[decision],
                        sound_type=decision,
                        screen_blurred=(decision=='blur_screen'))
        else:
            # If in cooldown, don't send alert but still count the detection
            print(f"COOLDOWN: {decision} - Suppressing repeat alert for {u}")

    return jsonify(resp)

# --- Tab switching (counts + admin visibility) ---
@app.route('/tab_switch', methods=['POST'])
def tab_switch():
    if 'username' not in session or users[session['username']]['role'] != 'student':
        return jsonify({'error':'Not authenticated'}), 401
    u = session['username']
    ensure_bucket(u)
    
    # Check cooldown to prevent spam alerts
    current_time = time.time()
    alert_key = f"{u}_tab_switching"
    
    # Only alert if this type hasn't been alerted recently
    # Alert will not repeat until face is properly detected (cooldown is reset)
    should_alert = alert_key not in last_alert_time
    
    # Always increment detection count
    detection_history[u]['tab_switching'] += 1
    
    if should_alert:
        # Update last alert time
        last_alert_time[alert_key] = current_time
        print(f"ALERT: tab_switching - First time, sending alert to {u}")
        
        detection_history[u]['alert_history'].append({
            'timestamp': datetime.now().isoformat(),
            'type': 'tab_switching',
            'message': 'Tab switching detected!'
        })
        save_detection_data()
        
        return jsonify({'alert': True,
                        'message': 'Please stay on the exam page. Tab switching detected!',
                        'sound_type': 'tab_switching'})
    else:
        # In cooldown, don't send alert but still count the detection
        print(f"COOLDOWN: tab_switching - Suppressing repeat alert for {u}")
        return jsonify({'alert': False})

# --- User Management Routes ---

# User management page
@app.route('/admin/users')
def manage_users():
    if 'username' not in session or users[session['username']]['role'] != 'admin':
        return redirect(url_for('login'))
    
    return render_template('admin_users.html', users=users)

# Add new user
@app.route('/admin/users/add', methods=['GET', 'POST'])
def add_user():
    if 'username' not in session or users[session['username']]['role'] != 'admin':
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        data = request.get_json()
        username = data.get('username', '').strip()
        password = data.get('password', '').strip()
        name = data.get('name', '').strip()
        role = data.get('role', 'student')
        
        if not username or not password or not name:
            return jsonify({'error': 'All fields are required'}), 400
        
        if username in users:
            return jsonify({'error': 'Username already exists'}), 400
        
        users[username] = {
            'password': password,
            'name': name,
            'role': role
        }
        
        return jsonify({'success': True, 'message': 'User added successfully'})
    
    return render_template('add_user.html')

# Edit user
@app.route('/admin/users/edit/<username>', methods=['GET', 'POST'])
def edit_user(username):
    if 'username' not in session or users[session['username']]['role'] != 'admin':
        return redirect(url_for('login'))
    
    if username not in users:
        return render_template('error.html', message='User not found')
    
    if request.method == 'POST':
        data = request.get_json()
        password = data.get('password', '').strip()
        name = data.get('name', '').strip()
        role = data.get('role', 'student')
        
        if not name:
            return jsonify({'error': 'Name is required'}), 400
        
        users[username]['name'] = name
        users[username]['role'] = role
        
        if password:  # Only update password if provided
            users[username]['password'] = password
        
        return jsonify({'success': True, 'message': 'User updated successfully'})
    
    return render_template('edit_user.html', user=users[username], username=username)

# Delete user
@app.route('/admin/users/delete/<username>', methods=['POST'])
def delete_user(username):
    if 'username' not in session or users[session['username']]['role'] != 'admin':
        return jsonify({'error': 'Not authenticated'}), 401
    
    if username not in users:
        return jsonify({'error': 'User not found'}), 404
    
    if username == session['username']:
        return jsonify({'error': 'Cannot delete your own account'}), 400
    
    # Remove user data
    del users[username]
    if username in detection_history:
        del detection_history[username]
    
    return jsonify({'success': True, 'message': 'User deleted successfully'})

# --- Exam Management Routes ---

# Create new exam
@app.route('/admin/create_exam', methods=['GET', 'POST'])
def create_exam():
    if 'username' not in session or users[session['username']]['role'] != 'admin':
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        data = request.get_json()
        exam_id = f"exam_{int(datetime.now().timestamp())}"
        exams_data[exam_id] = {
            'title': data['title'],
            'description': data['description'],
            'duration_minutes': int(data['duration_minutes']),
            'questions': data['questions'],
            'created_at': datetime.now().isoformat(),
            'created_by': session['username'],
            'status': 'draft'  # draft, active, completed
        }
        save_exams_data()
        return jsonify({'success': True, 'exam_id': exam_id})
    
    return render_template('create_exam.html')

# List all exams
@app.route('/admin/exams')
def list_exams():
    if 'username' not in session or users[session['username']]['role'] != 'admin':
        return redirect(url_for('login'))
    
    return render_template('admin_exams.html', exams=exams_data)

# Edit exam
@app.route('/admin/exams/edit/<exam_id>', methods=['GET', 'POST'])
def edit_exam(exam_id):
    if 'username' not in session or users[session['username']]['role'] != 'admin':
        return redirect(url_for('login'))
    
    if exam_id not in exams_data:
        return render_template('error.html', message='Exam not found')
    
    if request.method == 'POST':
        data = request.get_json()
        exams_data[exam_id].update({
            'title': data['title'],
            'description': data['description'],
            'duration_minutes': int(data['duration_minutes']),
            'questions': data['questions'],
            'updated_at': datetime.now().isoformat(),
            'updated_by': session['username']
        })
        save_exams_data()
        return jsonify({'success': True, 'message': 'Exam updated successfully'})
    
    return render_template('edit_exam.html', exam=exams_data[exam_id], exam_id=exam_id)

# Delete exam
@app.route('/admin/exams/delete/<exam_id>', methods=['POST'])
def delete_exam(exam_id):
    if 'username' not in session or users[session['username']]['role'] != 'admin':
        return jsonify({'error': 'Not authenticated'}), 401
    
    if exam_id not in exams_data:
        return jsonify({'error': 'Exam not found'}), 404
    
    # Check if exam is in any active sessions
    active_sessions = [s for s in exam_sessions.values() if s.get('exam_id') == exam_id and s.get('status') == 'active']
    if active_sessions:
        return jsonify({'error': 'Cannot delete exam with active sessions'}), 400
    
    # Remove exam
    del exams_data[exam_id]
    save_exams_data()
    
    return jsonify({'success': True, 'message': 'Exam deleted successfully'})

# Schedule exam (set status to active)
@app.route('/admin/exams/schedule/<exam_id>', methods=['POST'])
def schedule_exam(exam_id):
    if 'username' not in session or users[session['username']]['role'] != 'admin':
        return jsonify({'error': 'Not authenticated'}), 401
    
    if exam_id not in exams_data:
        return jsonify({'error': 'Exam not found'}), 404
    
    exams_data[exam_id]['status'] = 'active'
    exams_data[exam_id]['scheduled_at'] = datetime.now().isoformat()
    exams_data[exam_id]['scheduled_by'] = session['username']
    save_exams_data()
    
    return jsonify({'success': True, 'message': 'Exam scheduled successfully'})

# Unschedule exam (set status to draft)
@app.route('/admin/exams/unschedule/<exam_id>', methods=['POST'])
def unschedule_exam(exam_id):
    if 'username' not in session or users[session['username']]['role'] != 'admin':
        return jsonify({'error': 'Not authenticated'}), 401
    
    if exam_id not in exams_data:
        return jsonify({'error': 'Exam not found'}), 404
    
    exams_data[exam_id]['status'] = 'draft'
    exams_data[exam_id]['unscheduled_at'] = datetime.now().isoformat()
    exams_data[exam_id]['unscheduled_by'] = session['username']
    save_exams_data()
    
    return jsonify({'success': True, 'message': 'Exam unscheduled successfully'})

# Start exam session
@app.route('/admin/start_exam/<exam_id>', methods=['POST'])
def start_exam(exam_id):
    if 'username' not in session or users[session['username']]['role'] != 'admin':
        return jsonify({'error': 'Not authenticated'}), 401
    
    if exam_id not in exams_data:
        return jsonify({'error': 'Exam not found'}), 404
    
    session_id = f"session_{int(datetime.now().timestamp())}"
    exam_sessions[session_id] = {
        'exam_id': exam_id,
        'started_at': datetime.now().isoformat(),
        'status': 'active',  # active, completed
        'students': [],
        'student_answers': {},
        'student_detections': {}
    }
    
    exams_data[exam_id]['status'] = 'active'
    save_exam_sessions()
    save_exams_data()
    
    return jsonify({'success': True, 'session_id': session_id})

# Stop exam session
@app.route('/admin/stop_exam/<session_id>', methods=['POST'])
def stop_exam(session_id):
    if 'username' not in session or users[session['username']]['role'] != 'admin':
        return jsonify({'error': 'Not authenticated'}), 401
    
    if session_id not in exam_sessions:
        return jsonify({'error': 'Session not found'}), 404
    
    exam_sessions[session_id]['status'] = 'completed'
    exam_sessions[session_id]['ended_at'] = datetime.now().isoformat()
    
    # Update exam status
    exam_id = exam_sessions[session_id]['exam_id']
    exams_data[exam_id]['status'] = 'completed'
    
    save_exam_sessions()
    save_exams_data()
    
    return jsonify({'success': True})

# Student exam dashboard
@app.route('/student/exams')
def student_exams():
    if 'username' not in session or users[session['username']]['role'] != 'student':
        return redirect(url_for('login'))
    
    # Get active exam sessions
    active_sessions = []
    for session_id, session_data in exam_sessions.items():
        if session_data['status'] == 'active':
            exam = exams_data[session_data['exam_id']]
            active_sessions.append({
                'session_id': session_id,
                'exam': exam,
                'started_at': session_data['started_at']
            })
    
    return render_template('student_exams.html', sessions=active_sessions)

# Direct exam start - show questions and start monitoring
@app.route('/student/start_exam/<session_id>')
def start_exam_direct(session_id):
    if 'username' not in session or users[session['username']]['role'] != 'student':
        return redirect(url_for('login'))
    
    if session_id not in exam_sessions:
        return render_template('error.html', message='Exam session not found')
    
    session_data = exam_sessions[session_id]
    if session_data['status'] != 'active':
        return render_template('error.html', message='Exam session is not active')
    
    exam = exams_data[session_data['exam_id']]
    
    # Add student to session if not already added
    if session['username'] not in session_data['students']:
        session_data['students'].append(session['username'])
        session_data['student_answers'][session['username']] = {}
        session_data['student_detections'][session['username']] = []
        save_exam_sessions()
    
    return render_template('exam_interface.html', 
                         exam=exam, 
                         session_id=session_id,
                         student=session['username'])

# Submit exam answer
@app.route('/student/submit_answer', methods=['POST'])
def submit_answer():
    if 'username' not in session or users[session['username']]['role'] != 'student':
        return jsonify({'error': 'Not authenticated'}), 401
    
    data = request.get_json()
    session_id = data['session_id']
    question_id = data['question_id']
    answer = data['answer']
    
    if session_id not in exam_sessions:
        return jsonify({'error': 'Session not found'}), 404
    
    exam_sessions[session_id]['student_answers'][session['username']][question_id] = answer
    save_exam_sessions()
    
    return jsonify({'success': True})

# Submit detection data during exam
@app.route('/student/exam_detection', methods=['POST'])
def exam_detection():
    if 'username' not in session or users[session['username']]['role'] != 'student':
        return jsonify({'error': 'Not authenticated'}), 401
    
    data = request.get_json()
    session_id = data['session_id']
    detection_type = data['detection_type']
    timestamp = datetime.now().isoformat()
    
    if session_id not in exam_sessions:
        return jsonify({'error': 'Session not found'}), 404
    
    # Add detection to session data
    if session['username'] not in exam_sessions[session_id]['student_detections']:
        exam_sessions[session_id]['student_detections'][session['username']] = []
    
    exam_sessions[session_id]['student_detections'][session['username']].append({
        'type': detection_type,
        'timestamp': timestamp
    })
    
    save_exam_sessions()
    return jsonify({'success': True})

# View exam results
@app.route('/admin/exam_results/<session_id>')
def exam_results(session_id):
    if 'username' not in session or users[session['username']]['role'] != 'admin':
        return redirect(url_for('login'))
    
    if session_id not in exam_sessions:
        return render_template('error.html', message='Session not found')
    
    session_data = exam_sessions[session_id]
    exam = exams_data[session_data['exam_id']]
    
    return render_template('exam_results.html', 
                         exam=exam, 
                         session=session_data,
                         students=session_data['students'])

if __name__ == '__main__':
    print("🎓 Student Behavior Monitoring System — http://127.0.0.1:8080")
    print("Admin: admin/admin123 | Students: student1/password1, student2/password2")
    app.run(debug=True, host='127.0.0.1', port=8080, use_reloader=False)
