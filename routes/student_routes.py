import os
from flask import (
    Blueprint, request, render_template, jsonify, 
    current_app, redirect, url_for
)
from werkzeug.utils import secure_filename
from database import db, Student, Face
from models.face_recognition_model import allowed_file, load_image_file, encode_face_from_image
from datetime import datetime

bp = Blueprint('student', __name__)

@bp.route('/')
def students_page():
    """Renders the student management page."""
    students = Student.query.order_by(Student.name).all()
    return render_template('students.html', students=students)

@bp.route('/register')
def register_page():
    """Renders the new student registration page."""
    return render_template('register.html')

@bp.route('/api/students', methods=['GET'])
def list_students():
    """API endpoint to get a list of all students."""
    students = Student.query.all()
    return jsonify([s.to_dict() for s in students])

@bp.route('/api/students', methods=['POST'])
def create_student():
    """API endpoint to register a new student and their face images."""
    name = request.form.get('name')
    student_id = request.form.get('student_id')
    email = request.form.get('email')

    if not name or not student_id:
        return redirect(url_for('student.register_page', error='Name and Student ID are required.'))

    # Check for existing student
    existing = Student.query.filter_by(student_id=student_id).first()
    if existing:
        return redirect(url_for('student.register_page', error=f'Student ID {student_id} already exists.'))

    # Create student entry
    s = Student(name=name, student_id=student_id, email=email)
    db.session.add(s)
    db.session.commit() # Commit to get the student's primary key (s.id)

    # Handle image uploads
    files = request.files.getlist('images')
    upload_folder = current_app.config['UPLOAD_FOLDER']
    
    face_encodings_added = 0
    for f in files:
        if f and allowed_file(f.filename):
            # Use student's primary key for a cleaner filename
            filename = secure_filename(f"{s.id}_{student_id}_{datetime.utcnow().timestamp()}_{f.filename}")
            filepath = os.path.join(upload_folder, filename)
            f.save(filepath)
            
            # Encode the face
            try:
                img = load_image_file(filepath)
                enc = encode_face_from_image(img)
                
                if enc is None:
                    # No face found, delete the image
                    os.remove(filepath)
                    current_app.logger.warning(f'No face found in {filename}, file deleted.')
                    continue
                    
                # Save the face encoding to the database
                face = Face(filename=filename, encoding=enc, student=s)
                db.session.add(face)
                face_encodings_added += 1

            except Exception as e:
                current_app.logger.error(f'Error processing image {filename}: {e}')
                if os.path.exists(filepath):
                    os.remove(filepath) # Clean up failed file

    if face_encodings_added == 0:
        # No valid faces were added, roll back student creation
        db.session.delete(s)
        db.session.commit()
        return redirect(url_for('student.register_page', error='Registration failed. No valid faces detected in uploaded images.'))

    db.session.commit()
    return redirect(url_for('student.students_page'))

@bp.route('/api/students/<int:id>', methods=['DELETE'])
def delete_student(id):
    """API endpoint to delete a student and their associated data."""
    s = Student.query.get_or_404(id)
    
    # Delete associated image files
    for face in s.faces:
        try:
            filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], face.filename)
            if os.path.exists(filepath):
                os.remove(filepath)
        except Exception as e:
            current_app.logger.error(f'Could not delete file {face.filename}: {e}')
            
    # Database will cascade delete face encodings and attendance records
    db.session.delete(s)
    db.session.commit()
    
    return jsonify({'success': True, 'message': f'Student {s.name} deleted.'})