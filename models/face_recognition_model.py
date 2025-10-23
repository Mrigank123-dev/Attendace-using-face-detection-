import cv2
import numpy as np
import face_recognition
from config import config

# --- File Validation ---

def allowed_file(filename: str) -> bool:
    """Checks if a filename has an allowed image extension."""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in config.ALLOWED_EXTENSIONS

# --- Image and Face Processing ---

def load_image_file(path: str):
    """
    Loads an image file from a path and converts it from BGR (OpenCV default)
    to RGB (face_recognition default).
    """
    img = cv2.imread(str(path))
    if img is None:
        raise ValueError(f"Could not read image from path: {path}")
    
    # Convert from BGR color (which OpenCV uses) to RGB color (which face_recognition uses)
    img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    return img

def encode_face_from_image(image):
    """
    Given an image (as a numpy array), find the first face and
    return its 128-dimension face encoding.
    
    Returns None if no face is found.
    """
    # Find all face locations in the image
    face_locations = face_recognition.face_locations(image)
    
    # Get face encodings
    # This returns a list, even if there's only one face
    face_encodings = face_recognition.face_encodings(image, face_locations)

    if len(face_encodings) == 0:
        # No faces found in the image
        return None
    
    # Return the encoding for the first face found
    return face_encodings[0]

# --- Face Comparison ---

def compare_face(known_encodings: list, face_encoding, tolerance=0.5):
    """
    Compare a list of known face encodings against one new encoding.
    
    Args:
        known_encodings: A list of 128d encodings from the database.
        face_encoding: A single 128d encoding from the webcam.
        tolerance: How strict the match is. Lower is stricter. 0.5 is a good value.
                   
    Returns:
        A tuple (match_index, confidence)
        - match_index: The index of the best match in known_encodings. None if no match.
        - confidence: A percentage-like score (1.0 - distance).
    """
    if len(known_encodings) == 0:
        return (None, 1.0) # Return 1.0 for distance (0.0 confidence) if no known faces

    # Calculate the "distance" between the new face and all known faces
    # The lower the distance, the more similar the faces are.
    distances = face_recognition.face_distance(known_encodings, face_encoding)

    # Find the index (position) of the best match (smallest distance)
    best_match_index = np.argmin(distances)
    best_distance = float(distances[best_match_index])

    # Invert distance to get a "confidence" score (0.0 dist = 1.0 confidence)
    confidence = 1.0 - best_distance

    # Check if the best match is within our tolerance
    if best_distance <= tolerance:
        # We have a match!
        return (best_match_index, confidence)
    else:
        # No match found
        return (None, confidence)