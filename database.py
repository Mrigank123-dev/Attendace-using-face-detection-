from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, date

# Initialize the SQLAlchemy database object
db = SQLAlchemy()

class Student(db.Model):
    """
    Model for storing student information.
    """
    __tablename__ = 'students'
    
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.String(64), unique=True, nullable=False, index=True)
    name = db.Column(db.String(128), nullable=False)
    email = db.Column(db.String(128), unique=True, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # --- Relationships ---
    # One-to-Many: One student can have multiple face encodings
    faces = db.relationship('Face', backref='student', lazy=True, cascade='all, delete-orphan')
    
    # One-to-Many: One student can have many attendance records
    attendances = db.relationship('Attendance', backref='student', lazy=True, cascade='all, delete-orphan')

    def __repr__(self):
        return f'<Student {self.name} ({self.student_id})>'

    def to_dict(self):
        """Returns a dictionary representation of the student."""
        return {
            'id': self.id,
            'student_id': self.student_id,
            'name': self.name,
            'email': self.email,
            'created_at': self.created_at.isoformat()
        }

class Face(db.Model):
    """
    Model for storing individual face encodings for each student.
    """
    __tablename__ = 'faces'
    
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(256), nullable=False)
    # PickleType is used to store the numpy array (face encoding)
    encoding = db.Column(db.PickleType, nullable=False)
    
    # --- Foreign Key ---
    student_id = db.Column(db.Integer, db.ForeignKey('students.id'), nullable=False)

    def __repr__(self):
        return f'<Face {self.filename} for Student ID {self.student_id}>'

class Attendance(db.Model):
    """
    Model for storing attendance records.
    """
    __tablename__ = 'attendances'
    
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    date = db.Column(db.Date, default=date.today, nullable=False, index=True)
    status = db.Column(db.String(16), default='present', nullable=False)
    
    # --- Foreign Key ---
    student_id = db.Column(db.Integer, db.ForeignKey('students.id'), nullable=False)
    
    # --- Constraints ---
    # Ensures a student can only be marked present once per day
    __table_args__ = (db.UniqueConstraint('date', 'student_id', name='_date_student_uc'),)

    def __repr__(self):
        return f'<Attendance {self.student.name} on {self.date}>'

    def to_dict(self):
        """Returns a dictionary representation of the attendance record."""
        return {
            'id': self.id,
            'student_id': self.student_id,
            'name': self.student.name if self.student else None,
            'timestamp': self.timestamp.isoformat(),
            'date': self.date.isoformat(),
            'status': self.status
        }