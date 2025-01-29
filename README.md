# Two-Factor Authentication System Using Voice Recognition
This project is for the Information Systems Security Course at Princess Sumaya University for Technology. We created a 2FA system that uses voice recognition to authenticate users upon logging in to the system.

## How It Works
### Signup
When users sign up, they are prompted to enter their username, email, and password. After validating that this is a new user considering it's a signup process, the user is then prompted to record a randomly chosen word shown on the screen (note that this code also sends this word to the email that was used to sign up).

After receiving the voice recording of the user, it undergoes preprocessing and feature extraction.

- Preprocessing: The voice recording undergoes silence trimming at the beginning and end of the recording, as well as downsampling the recording to 16kHz.
- Feature extraction: Two audio features, MFCCs and spectral contrast, are extracted from the preprocessed voice recording.
After the features are extracted, they are combined together, then encrypted using AES, and stored in the database with the credentials of the corresponding user.

### Login
When a user tries logging in, the user credentials are first validated. If the user exists, the user is prompted to record another word. This voice recording undergoes the same preprocessing and feature extraction processes. However, the extracted features are not stored in the database; they are compared with the features stored in the database for the user that the login attempt is for. The comparison is done using cosine similarity. If the similarity passes a certain threshold, in our case 96.5%, the user is authenticated and redirected to the homepage. If the similarity is less than the threshold, the user is not authenticated.

## How To Use The System
1. Clone the project
2. Import the required python libraries
3. Generate a new key for encryption and decryption in [key-gen.py](/.key-gen.py) by running the file. Insert key in [app.py](./app.py) inside:
```
   encryption_key = b'your-generated-key'
```
4. Run the flask app using the following command:
```
   flask run
```
