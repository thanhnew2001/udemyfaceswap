import os
from flask import Flask, render_template, request, jsonify, send_from_directory, redirect, url_for
from werkzeug.utils import secure_filename
import replicate
import requests
import uuid


app = Flask(__name__)

# Configure upload and result folders
PHOTO_FOLDER = 'static'
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
    for album_name in os.listdir(PHOTO_FOLDER):
        album_path = os.path.join(PHOTO_FOLDER, album_name)
        if os.path.isdir(album_path):
            album_images = [
                f"{album_name}/{f}" for f in os.listdir(album_path) if allowed_file(f)
            ]
            albums[album_name] = album_images

    return render_template('index.html', albums=albums)

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

        # Get target image URL from the form
        target_image_url = request.form.get('target_image')

        input_data = {
            "local_source": f"{request.host_url}{file_path}",
            "local_target": target_image_url
        }

        try:
            output = replicate.run(
                "xiankgx/face-swap:cff87316e31787df12002c9e20a78a017a36cb31fde9862d8dedd15ab29b7288",
                input=input_data
            )
            print(output)

            # Assuming 'image' is the URL of the processed image
            swapped_image_url = output['image']
            response = requests.get(swapped_image_url)

            if response.status_code == 200:
                # Save the swapped image on the server
                unique_id = uuid.uuid4()
                generated_filename = f"swapped_{unique_id}.png"
                generated_file_path = os.path.join(app.config['RESULT_FOLDER'], generated_filename)
                with open(generated_file_path, 'wb') as f:
                    f.write(response.content)

                # Return the path of the saved image
                return jsonify({
                    'swapped_image_url': f"{request.host_url}{generated_file_path}"
                })
            else:
                return jsonify({'error': 'Failed to download the generated image'}), 500
        except Exception as e:
            print("Error calling Replicate API:", e)
            return jsonify({'error': 'An error occurred while processing the request'}), 500

    return jsonify({'error': 'File type not allowed'}), 400

# API to serve processed files for download
@app.route('/results/<filename>')
def download_file(filename):
    return send_from_directory(app.config['RESULT_FOLDER'], filename)

if __name__ == '__main__':
    app.run(debug=True, port=7000)
