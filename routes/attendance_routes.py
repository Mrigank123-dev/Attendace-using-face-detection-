import io
import cv2
import csv
import numpy as np
import face_recognition
from flask import (
    Blueprint, request, current_app, jsonify, 
    render_template, send_file, Response
)
from database import db, Student, Face, Attendance
from models.face_recognition_model import compare_face
from datetime import datetime, date

bp = Blueprint('attendance', __name__)

# --- Page Routes ---

@bp.route('/')
def index():
    """Renders the main dashboard page."""
    today = date.today()
    
    # Query for statistics
    total_students = Student.query.count()
    
    # Count unique students present today
    students_present_today = db.session.query(Attendance.student_id).filter(
        Attendance.date == today
    ).distinct().count()

    stats = {
        'total_students': total_students,
        'present_today': students_present_today,
        'absent_today': total_students - students_present_today
    }
    return render_template('index.html', stats=stats)

@bp.route('/attendance')
def attendance_page():
    """Renders the live attendance marking page."""
    # --- THIS IS THE FIX ---
    # Get today's date and pass it to the template
    today = date.today()
    return render_template('attendance.html', today=today)
    # ----------------------

@bp.route('/reports')
def reports_page():
    """Renders the attendance reports page."""
    return render_template('reports.html')

# --- API Routes ---

@bp.route('/api/recognize', methods=['POST'])
def recognize():
    """API endpoint to recognize a face from a webcam frame."""
    file = request.files.get('image')
    if file is None:
        return jsonify({'error': 'no image uploaded'}), 400

    try:
        # Read image from buffer
        in_memory = file.read()
        arr = np.frombuffer(in_memory, np.uint8)
        img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
        if img is None:
            return jsonify({'error': 'could not decode image'}), 400
        
        rgb_img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

        # Find face locations and encodings in the current frame
        face_locations = face_recognition.face_locations(rgb_img)
        live_encodings = face_recognition.face_encodings(rgb_img, face_locations)

        # --- Load known faces from database ---
        known_faces = db.session.query(Face.encoding, Student.id, Student.name).join(Student).all()
        if not known_faces:
            return jsonify({'results': [], 'locations': face_locations})

        known_encodings = [f[0] for f in known_faces]
        known_student_ids = [f[1] for f in known_faces]
        known_names = [f[2] for f in known_faces]
        # ----------------------------------------

        results = []
        today = date.today()

        for (top, right, bottom, left), live_encoding in zip(face_locations, live_encodings):
            match_idx, confidence = compare_face(known_encodings, live_encoding, tolerance=0.5)
            
            name = "Unknown"
            student_pk = None
            
            if match_idx is not None:
                name = known_names[match_idx]
                student_pk = known_student_ids[match_idx]
                
                # --- Mark Attendance ---
                already_marked = Attendance.query.filter(
                    Attendance.student_id == student_pk,
                    Attendance.date == today
                ).first()

                if not already_marked:
                    try:
                        att = Attendance(student_id=student_pk, date=today, timestamp=datetime.utcnow())
                        db.session.add(att)
                        db.session.commit()
                        name = f"{name} (Marked)" # Give feedback
                    except Exception as e:
                        db.session.rollback()
                        current_app.logger.error(f'Error marking attendance: {e}')

            results.append({
                'name': name,
                'confidence': f"{confidence * 100:.2f}%",
                'location': [top, right, bottom, left]
            })

        return jsonify({'results': results})

    except Exception as e:
        current_app.logger.error(f'Recognition error: {e}')
        return jsonify({'error': str(e)}), 500


@bp.route('/api/attendance/today')
def get_today_attendance():
    """API endpoint to get all attendance records for today."""
    today = date.today()
    records = db.session.query(Attendance, Student).join(Student).filter(
        Attendance.date == today
    ).order_by(Attendance.timestamp.desc()).all()
    
    results = [
        {
            'name': student.name,
            'student_id': student.student_id,
            'time': att.timestamp.strftime('%I:%M:%S %p')
        }
        for att, student in records
    ]
    return jsonify(results)


@bp.route('/api/reports')
def get_reports_data():
    """API endpoint to get attendance data for a date range."""
    try:
        start_date_str = request.args.get('start_date')
        end_date_str = request.args.get('end_date')

        start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
        end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()

        # Query all students and their attendance in the range
        students = Student.query.all()
        report_data = []

        for s in students:
            records = Attendance.query.filter(
                Attendance.student_id == s.id,
                Attendance.date >= start_date,
                Attendance.date <= end_date
            ).all()
            
            present_dates = {r.date.isoformat() for r in records}
            report_data.append({
                'id': s.id,
                'student_id': s.student_id,
                'name': s.name,
                'present_count': len(present_dates),
                'present_dates': list(present_dates)
            })
        
        return jsonify(report_data)

    except Exception as e:
        return jsonify({'error': str(e)}), 400

@bp.route('/api/reports/export')
def export_csv():
    """API endpoint to export a CSV report for a date range."""
    try:
        start_date_str = request.args.get('start_date')
        end_date_str = request.args.get('end_date')

        start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
        end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()

        records = db.session.query(Attendance, Student).join(Student).filter(
            Attendance.date >= start_date,
            Attendance.date <= end_date
        ).order_by(Attendance.date, Student.name, Attendance.timestamp).all()

        # Create CSV in memory
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(['Student Name', 'Student ID', 'Date', 'Time', 'Status'])

        for att, student in records:
            writer.writerow([
                student.name,
                student.student_id,
                att.date.isoformat(),
                att.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
                att.status
            ])

        output.seek(0)
        
        return Response(
            output,
            mimetype="text/csv",
            headers={"Content-Disposition": f"attachment;filename=attendance_report_{start_date_str}_to_{end_date_str}.csv"}
        )

    except Exception as e:
        return jsonify({'error': str(e)}), 400