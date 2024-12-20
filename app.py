import os
from flask import Flask, render_template, request, jsonify, send_from_directory, redirect, url_for
from werkzeug.utils import secure_filename
import replicate
import requests

app = Flask(__name__)

# Configure upload and result folders
UPLOAD_FOLDER = 'static/uploads'
RESULT_FOLDER = 'static/results'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'webp'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['RESULT_FOLDER'] = RESULT_FOLDER

# Ensure directories exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(RESULT_FOLDER, exist_ok=True)

# Function to check allowed file extensions
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Route to render the main page
@app.route('/')
def index():
    # List albums and images for display
    albums = {}
    for album_name in os.listdir(UPLOAD_FOLDER):
        album_path = os.path.join(UPLOAD_FOLDER, album_name)
        if os.path.isdir(album_path):
            album_images = [
                f"{album_name}/{f}" for f in os.listdir(album_path) if allowed_file(f)
            ]
            albums[album_name] = album_images

    return render_template('index.html', albums=albums)

# API to upload image and perform face swap
@app.route('/upload', methods=['POST'])
def upload():
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)

        # Get target image URL from form
        target_image_url = request.form.get('target_image')
        if not target_image_url:
            return jsonify({'error': 'No target image provided'}), 400

        # Call Replicate API for face swap
        input_data = {
            "local_source": f"http://localhost:7000/{file_path}",
            "local_target": target_image_url,
        }

        try:
            output = replicate.run(
                "xiankgx/face-swap:cff87316e31787df12002c9e20a78a017a36cb31fde9862d8dedd15ab29b7288",
                input=input_data
            )
        except Exception as e:
            return jsonify({'error': str(e)}), 500

        # Download the processed image to the server
        swapped_image_url = output['image']['url']
        swapped_image_path = os.path.join(app.config['RESULT_FOLDER'], filename)

        try:
            response = requests.get(swapped_image_url, stream=True)
            if response.status_code == 200:
                with open(swapped_image_path, 'wb') as f:
                    for chunk in response.iter_content(1024):
                        f.write(chunk)
            else:
                return jsonify({'error': 'Failed to download processed image'}), 500
        except Exception as e:
            return jsonify({'error': str(e)}), 500

        # Return the URL of the locally saved result image
        result_url = url_for('download_file', filename=filename)
        return jsonify({'swapped_image_url': result_url})

    return jsonify({'error': 'Invalid file'}), 400

# API to serve processed files for download
@app.route('/results/<filename>')
def download_file(filename):
    return send_from_directory(app.config['RESULT_FOLDER'], filename)

if __name__ == '__main__':
    app.run(debug=True, port=7000)
