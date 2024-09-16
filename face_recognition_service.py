from flask import Flask, request, jsonify
import base64
import face_recognition
import numpy as np
from PIL import Image
import io
import os
import psycopg2

app = Flask(__name__)

UPLOAD_DIR = 'uploads'
# PostgreSQL credentials
DB_NAME = "kivymmd_face_login"
DB_USER = "postgres"
DB_PASSWORD = "admin"
DB_HOST = "localhost"
DB_PORT = "5432"



def load_known_faces():
    known_face_encodings = []
    known_faces = []
    
    for filename in os.listdir(UPLOAD_DIR):
        if filename.endswith('.jpg') or filename.endswith('.png'):
            image_path = os.path.join(UPLOAD_DIR, filename)
            image = face_recognition.load_image_file(image_path)
            encoding = face_recognition.face_encodings(image)
            if encoding:
                known_face_encodings.append(encoding[0])
                known_faces.append(image_path)
                
    return known_face_encodings, known_faces



def load_known_faces():
    known_face_encodings = []
    known_faces = []

    for filename in os.listdir(UPLOAD_DIR):
        if filename.endswith('.jpg') or filename.endswith('.png'):
            image_path = os.path.join(UPLOAD_DIR, filename)
            image = face_recognition.load_image_file(image_path)
            encoding = face_recognition.face_encodings(image)
            if encoding:
                known_face_encodings.append(encoding[0])
                known_faces.append(image_path)
                
    return known_face_encodings, known_faces

def get_user_profile_from_db(image_filename):
    try:
        conn = psycopg2.connect(
				dbname=DB_NAME,
				user=DB_USER,
				password=DB_PASSWORD,
				host=DB_HOST,
				port=DB_PORT
			)
        cursor = conn.cursor()

        # Extract the base filename
        base_filename = os.path.basename(image_filename)

        # Query to find the profile information based on the profile picture path
        query = "SELECT * FROM users WHERE profile_picture LIKE %s"
        cursor.execute(query, (f'%{base_filename}%',))
        user_profile = cursor.fetchone()

        cursor.close()
        conn.close()
        
        return user_profile

    except Exception as e:
        print(f"Error: {e}")
        return None

@app.route('/recognize_face', methods=['POST'])
def recognize_face():
    data = request.json
    image_data = base64.b64decode(data['image'])

    # Convert image data to a PIL Image object
    image = Image.open(io.BytesIO(image_data))
    
    # Convert PIL Image to NumPy array
    np_image = np.array(image)
    
    # Load known faces and associated image paths
    known_face_encodings, known_faces = load_known_faces()

    # Encode the received image
    unknown_face_encodings = face_recognition.face_encodings(np_image)

    if unknown_face_encodings:
        matches = face_recognition.compare_faces(known_face_encodings, unknown_face_encodings[0])
        if True in matches:
            matched_index = matches.index(True)
            matched_image_path = known_faces[matched_index]

            # Lookup user profile in the database
            user_profile = get_user_profile_from_db(matched_image_path)
            if user_profile:
                # Convert the user profile to a dictionary or suitable format
                profile_info = {
                    'email': user_profile[2],  # Assuming email is the second column
                    'name': user_profile[1],   # Assuming name is the third column
                    # Add other profile details if needed
                }
                print(profile_info)
                return jsonify({'match': True, 'profile': profile_info})

    return jsonify({'match': False})


    return jsonify({'match': False})



if __name__ == '__main__':
    app.run(debug=True)
