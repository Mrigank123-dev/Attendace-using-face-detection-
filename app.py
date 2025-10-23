import os
from flask import Flask
from config import config
from database import db
from routes.student_routes import bp as student_bp
from routes.attendance_routes import bp as attendance_bp

def create_app():
    app = Flask(__name__)
    app.config.from_object(config)

    # Ensure upload and data directories exist
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    os.makedirs(os.path.dirname(app.config['SQLALCHEMY_DATABASE_URI'].replace('sqlite:///', '')), exist_ok=True)

    # Initialize extensions
    db.init_app(app)

    # Create database tables if they don't exist
    with app.app_context():
        db.create_all()

    # Register blueprints
    app.register_blueprint(student_bp, url_prefix='/students')
    app.register_blueprint(attendance_bp, url_prefix='/')

    return app

app = create_app()

if __name__ == '__main__':
    app.run(debug=True, ssl_context='adhoc') # 'adhoc' for HTTPS, required by some browsers for webcam