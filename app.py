import random
from flask import Flask, jsonify, redirect, render_template, request, url_for
import os
import librosa
import numpy as np
import soundfile as sf  # Ensure this is imported
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import or_
from werkzeug.security import generate_password_hash, check_password_hash
from flask_migrate import Migrate
from sklearn.metrics.pairwise import cosine_similarity
from cryptography.fernet import Fernet
from email_app import send_email

app = Flask(__name__)

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///voice.db'
db = SQLAlchemy(app)
app.app_context().push()

migrate = Migrate(app, db)

# Generate a key (only needs to be done once)
# encryption_key = Fernet.generate_key()
# Load the encryption key (e.g., from environment variables)
encryption_key = b'PEz6usKtc_0-fKOfoovncqLud0QBDTAaSbzBbCTvopg='

# Initialize the encryption mechanism
cipher = Fernet(encryption_key)

# Store this key securely (e.g., environment variables or a KMS)
# print(encryption_key)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(120), nullable=False)
    audio_features = db.Column(db.BLOB, nullable=True)
    email = db.Column(db.String(120), unique=True, nullable=True)

    def __repr__(self):
        return f"<User {self.username}>"
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

# Set the upload folder
UPLOAD_FOLDER = './uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)  # Ensure the folder exists

def extract_features(audio_path):
    # Load the audio file
    audio, sample_rate = librosa.load(audio_path, sr=None)
    
    # Extract MFCCs
    mfccs = librosa.feature.mfcc(y=audio, sr=sample_rate, n_mfcc=13)
    mfccs = np.mean(mfccs, axis=1)  # Average MFCCs over time
    print("------------------MFCCs------------------")
    print("MFCCs:", mfccs)  # Print MFCCs
    
    # Extract Spectral Contrast
    spectral_contrast = librosa.feature.spectral_contrast(y=audio, sr=sample_rate)
    spectral_contrast = np.mean(spectral_contrast, axis=1)  # Average over time
    print("------------------SPECTRAL CONTRAST------------------")
    print("Spectral Contrast:", spectral_contrast)  # Print Spectral Contrast
    
    # Combine MFCC and Spectral Contrast
    features = np.hstack((mfccs, spectral_contrast))
    print("------------------COMBINED FEATURES------------------")
    print("Combined Features:", features)  # Print the combined features
    
    return features

def preprocess_audio(input_path, output_path):
    # Load the audio file
    audio, sample_rate = librosa.load(input_path, sr=16000)  # Downsample to 16kHz
    print(f"Loaded audio: {input_path}")

    # Trim silence
    trimmed_audio, _ = librosa.effects.trim(audio, top_db=20)
    print(f"Trimmed silence from audio: {input_path}")

    # Save the preprocessed audio
    sf.write(output_path, trimmed_audio, sample_rate)
    print(f"Preprocessed audio saved to {output_path}")


@app.route('/')
def index():
    return render_template('index.html', signup_r_word='hello')


@app.route('/signup')
def signup():
    return render_template('signup.html')


@app.route('/submit_signup', methods=['POST'])
def submit_signup():
    try:
        print("------------------NEW USER SIGNUP------------------")
        # Get form data
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        # audio_file = request.files.get('file') # the file is initially a BLOB on the client site, but here it gets converted into a FileStorage object. This object makes it easy for flask to deal with a file. Its not MP3 or WAV.

        # Validate input
        if not username or not password or not email:
            return jsonify({'error': 'Missing required fields'}), 400

        # Check if username or email already exists
        user_username = User.query.filter_by(username=username).first()
        user_email = User.query.filter_by(email=email).first()
        if user_username or user_email:
            return jsonify({'error': 'User already exists!'}), 400


        words = ['apple', 'banana', 'orange', 'laptop', 'boba', 'princess', 'desk', 'pencil']
        signup_r_word = random.choice(words)
        # Send confirmation email to user
        subject = "Signup Code"
        body = f"Hello {username},\n\nPlease complete your registration by recording the word '{signup_r_word}'."
        send_email(email, subject, body)

        return redirect(url_for('signup_auth', username=username, email=email, password=generate_password_hash(password), signup_r_word=signup_r_word))

        # # Create new user
        # new_user = User(username=username)
        # new_user.set_password(password)
        # db.session.add(new_user)
        # db.session.commit()

        # Save audio file
        file_path = os.path.join(UPLOAD_FOLDER, audio_file.filename)
        audio_file.save(file_path)

        # Preprocess and extract features
        preprocessed_file_path = os.path.join(UPLOAD_FOLDER, 'preprocessed.wav')
        preprocess_audio(file_path, preprocessed_file_path)

        features = extract_features(preprocessed_file_path)

        # Encrypt before storing in the database ------------------------------

        # check the original dtype
        dtype = features.dtype
        print(f"----------dtype is : {dtype}")
        serialized_features = features.tobytes()
        print("Serialised Features:", serialized_features)
        # Encrypt the serialized features
        encrypted_features = cipher.encrypt(serialized_features)
        print(encrypted_features)

        # Store features in the database

        # Create new user
        new_user = User(username=username, email=email)
        new_user.set_password(password)
        db.session.add(new_user)
        db.session.commit()

        new_user.audio_features = encrypted_features  # Convert numpy array to list
        db.session.commit()

        # Respond with success
        return jsonify({'success': True, 'message': 'User registered successfully!'}), 200
        # return redirect(url_for('login'))

    except Exception as e:
        # Log the exception for debugging
        print(f"Error in /submit_signup: {e}")
        return jsonify({'error': 'Internal server error', 'details': str(e)}), 500
  

@app.route('/signup_auth', methods=['GET', 'POST'])
def signup_auth():
    print("------------------SHOW EMAIL WITH CODE------------------")
    username = request.args.get('username')
    email = request.args.get('email')
    password = request.args.get('password')
    signup_r_word = request.args.get('signup_r_word')
    # Generate a random word (you can customize this as per your needs)
    
    return render_template('signup_auth.html', username=username, email=email, password=password, signup_r_word=signup_r_word)

@app.route('/submit_authenticate_signup', methods=['POST'])
def submit_authenticate_signup():
    print("-----------LISTEN TO RECORDING BEFORE AND AFTER PREPROCESSING-----------")
    username = request.form.get('username')
    email = request.form.get('email')
    password = request.form.get('password')
    # # Create new user
    # new_user = User(username=username)
    # new_user.set_password(password)
    # db.session.add(new_user)
    # db.session.commit()
    audio_file = request.files.get('file')
    # Save audio file
    file_path = os.path.join(UPLOAD_FOLDER, audio_file.filename)
    audio_file.save(file_path)

    # Preprocess and extract features
    preprocessed_file_path = os.path.join(UPLOAD_FOLDER, 'preprocessed.wav')
    preprocess_audio(file_path, preprocessed_file_path)

    features = extract_features(preprocessed_file_path)

    # Encrypt before storing in the database ------------------------------

    # check the original dtype
    dtype = features.dtype
    print(f"----------dtype is : {dtype}")
    serialized_features = features.tobytes()
    print("------------------SERIALISED FEATURES------------------")
    print("Serialised Features:", serialized_features)
    # Encrypt the serialized features
    encrypted_features = cipher.encrypt(serialized_features)
    print("------------------ENCRYPTED FEATURES------------------")
    print(encrypted_features)
    print("------------------SHOW KEY GENERATION------------------")

    # Store features in the database

    # Create new user
    new_user = User(username=username, email=email, password_hash=password)
    # new_user.set_password(password)
    db.session.add(new_user)
    db.session.commit()

    new_user.audio_features = encrypted_features  # Convert numpy array to list
    db.session.commit()

    print("------------------SHOW USER IN DATABASE------------------")
    # Respond with success
    return jsonify({'success': True, 'message': 'User registered successfully!'}), 200
    # return redirect(url_for('login'))

@app.route('/login')
def login():
    return render_template('login.html')


@app.route('/submit_login', methods=['POST'])
def submit_login():
    try:
        print("------------------VALIDATE USER IN DATABASE------------------")
        # Get form data
        username = request.form.get('username')
        password = request.form.get('password')
        print(f"Username received: {username}")

        # Validate input
        if not username or not password:
            return jsonify({'error': 'Missing required fields'}), 400

        # Query the database for the user
        user = User.query.filter(or_(
            User.username == username,
            User.email == username
        )
        ).first()
        print(f"User found: {user}")

        print("------------------SHOW EMAIL WITH CODE FOR LOGIN------------------")
        # Check if the user exists and the password is correct
        if user and check_password_hash(user.password_hash, password):
            subject = "Login Code"
            body = f"Hello {username},\n\nPlease complete your registration by recording the word 'hello'."
            send_email(user.email, subject, body)
            # Credentials are correct; redirect to authenticate page
            return redirect(url_for('authenticate', username=username))
        else:
            # Invalid credentials
            return jsonify({'error': 'Invalid username or password'}), 401

    except Exception as e:
        print(f"Error in /submit_login: {e}")
        return jsonify({'error': 'Internal server error', 'details': str(e)}), 500


# The authenticate page route
@app.route('/authenticate')
def authenticate():
    username = request.args.get('username')
    return render_template('authenticate.html', username=username)


@app.route('/submit_authenticate', methods=['POST'])
def submit_authenticate():
    try:
        print("submit_authenticate method")

        # Get the username from the form data
        username = request.form.get('username')  # This retrieves the 'username' field from the form
        file = request.files.get('file')

        # Validate input
        if not username or not file:
            return jsonify({'error': 'Missing required fields'}), 400
    
        print("------------------SHOW RECORDING BEFORE AND AFTER------------------")
        # Save the file directly to the uploads folder
        file_path = os.path.join(UPLOAD_FOLDER, file.filename)
        file.save(file_path)

        # Call preprocessing functiong
        preprocessed_file_path = os.path.join(UPLOAD_FOLDER, 'preprocessed.wav')
        preprocess_audio(file_path, preprocessed_file_path)

        features = extract_features(preprocessed_file_path)
        print("------------------EXTRACTED FEATURES------------------")
        print("Extracted Features:", features)

        # You can now use the 'username' variable here to compare features with the database, etc.

        # For example, find the user in the database (assuming you have a User model)
        # user = User.query.filter_by(username=username).first()
        user = User.query.filter(or_(
            User.username == username,
            User.email == username
        )
        ).first()

        if user:
            encrypted_features = user.audio_features  # Fetch encrypted data from DB
            decrypted_features = cipher.decrypt(encrypted_features)
            print("------------------DECRYPTED FEATURES------------------")
            print(decrypted_features)

            # Get the stored features from the user
            # stored_features = np.array(user.audio_features) 

            # Convert the decrypted bytes back into a numpy array
            stored_features = np.frombuffer(decrypted_features, dtype=np.float64)  # Adjust dtype as needed 
            print("------------------DESERIALISED FEATURES------------------")
            print("Stored Features:", stored_features)

            print("------------------CHECK COSINE SIMILARITY------------------")
            similarity = cosine_similarity([features], [stored_features])  # Compare features using cosine similarity
            print(f"SIMILARITY: {similarity}")
            # You can now check the similarity result and return an appropriate response
            print("------------------SHOW THRESHOLD------------------")
            if similarity > 0.95:  # Example threshold
                # return redirect(url_for('homepage', username=username))
                return jsonify({'success': True, 'message': 'User authenticated successfully!', "username": username}), 200
                # return jsonify({'username': username}), 200
            else:
                return jsonify({"success": False, "message": "Authentication failed: Features don't match."})
        else:
            return jsonify({"success": False, "message": "User not found."})
    
    except Exception as e:
        print(f"Error during authentication: {e}")
        return jsonify({'error': 'Internal server error', 'details': str(e)}), 500


@app.route('/homepage')
def homepage():
    username = request.args.get('username')
    return render_template('homepage.html', username=username)

# @app.route('/upload', methods=['POST'])
# def upload_audio(file):
#     # Check if the file is part of the request
#     if 'file' not in request.files:
#         return "No file part", 400

#     file = request.files['file']
#     if file.filename == '':
#         return "No selected file", 400

#     # Save the file directly to the uploads folder
#     file_path = os.path.join(UPLOAD_FOLDER, file.filename)
#     file.save(file_path)
#     # Check if the file exists
#     if not os.path.exists(file_path):
#         return "Error saving file", 400
#     print(f"Audio file saved as {file.filename}")

#     # Call preprocessing functiong
#     preprocessed_file_path = os.path.join(UPLOAD_FOLDER, 'preprocessed.wav')
#     preprocess_audio(file_path, preprocessed_file_path)

#     return f"File saved and preprocessed as preprocessed.wav", 200

with app.app_context():
    # Run this once to initialize migration scripts
    migrate.init_app(app, db)
    # Run migrations
    db.create_all()

if __name__ == '__main__':
    app.run(debug=True)

