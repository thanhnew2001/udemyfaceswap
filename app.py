import os
import uuid
from flask import Flask, render_template, request, jsonify, send_from_directory, redirect, url_for, session
from werkzeug.utils import secure_filename
import replicate
import requests


app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Replace with a secure secret key

# Configure upload and result folders
PHOTO_FOLDER = 'static'
UPLOAD_FOLDER = 'static'
RESULT_FOLDER = 'static/results'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'webp', 'gif'}

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
                   # Force HTTPS in the response URL
                    # if request.is_secure:
                    #     protocol = 'https://'
                    # else:
                    #     protocol = 'https://'  # Force https even if the request is HTTP
                    
                    # Construct the full URL of the generated image
                    swapped_image_url = f"https://{request.host}{generated_file_path}"

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


@app.route('/create_album', methods=['POST'])
def create_album():
    album_name = request.form.get('album_name')
    if not album_name:
        return jsonify({'error': 'Album name is required'}), 400

    album_path = os.path.join(app.config['UPLOAD_FOLDER'], album_name)
    os.makedirs(album_path, exist_ok=True)

    return jsonify({'success': 'Album created successfully', 'album_name': album_name}), 200

@app.route('/upload_to_album/<album_name>', methods=['POST'])
def upload_to_album(album_name):
    album_path = os.path.join(app.config['UPLOAD_FOLDER'], album_name)
    if not os.path.exists(album_path):
        return jsonify({'error': 'Album does not exist'}), 404

    if 'files[]' not in request.files:
        return jsonify({'error': 'No file part'}), 400

    files = request.files.getlist('files[]')
    if not files:
        return jsonify({'error': 'No selected file'}), 400

    for file in files:
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file_path = os.path.join(album_path, filename)
            file.save(file_path)

    return jsonify({'success': 'Files uploaded successfully'}), 200

@app.route('/delete_photo/<album_name>/<filename>', methods=['DELETE'])
def delete_photo(album_name, filename):
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], album_name, filename)
    if os.path.exists(file_path):
        os.remove(file_path)
        return jsonify({'success': 'File deleted successfully'}), 200
    else:
        return jsonify({'error': 'File not found'}), 404

# API to serve processed files for download
@app.route('/results/<filename>')
def download_file(filename):
    return send_from_directory(app.config['RESULT_FOLDER'], filename)

@app.route('/passphrase', methods=['GET', 'POST'])
def passphrase():
    if request.method == 'POST':
        if request.form.get('passphrase') == 'sou':
            session['authenticated'] = True
            return redirect(url_for('manage_albums'))
        else:
            return render_template('passphrase.html', error='Invalid passphrase')
    return render_template('passphrase.html')

@app.route('/manage_albums')
def manage_albums():
    if not session.get('authenticated'):
        return redirect(url_for('passphrase'))
    session.pop('authenticated', None)  # Clear the session variable after access
    albums = [d for d in os.listdir(app.config['UPLOAD_FOLDER']) if os.path.isdir(os.path.join(app.config['UPLOAD_FOLDER'], d))]
    return render_template('manage_albums.html', albums=albums)

@app.route('/get_album_images/<album_name>', methods=['GET'])
def get_album_images(album_name):
    album_path = os.path.join(app.config['UPLOAD_FOLDER'], album_name)
    if not os.path.exists(album_path):
        return jsonify({'error': 'Album does not exist'}), 404

    images = [f for f in os.listdir(album_path) if allowed_file(f)]
    return jsonify({'images': images}), 200

@app.route('/rename_album', methods=['POST'])
def rename_album():
    old_name = request.form.get('old_name')
    new_name = request.form.get('new_name')
    old_path = os.path.join(app.config['UPLOAD_FOLDER'], old_name)
    new_path = os.path.join(app.config['UPLOAD_FOLDER'], new_name)

    if not os.path.exists(old_path):
        return jsonify({'error': 'Album does not exist'}), 404

    if os.path.exists(new_path):
        return jsonify({'error': 'New album name already exists'}), 400

    os.rename(old_path, new_path)
    return jsonify({'success': 'Album renamed successfully'}), 200

if __name__ == '__main__':
    app.run(debug=True, port=7000)
