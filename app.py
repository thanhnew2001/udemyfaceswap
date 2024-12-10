import os
import replicate
from flask import Flask, render_template, request, jsonify, send_from_directory
from werkzeug.utils import secure_filename

app = Flask(__name__)

# Cấu hình thư mục lưu ảnh upload
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # Giới hạn dung lượng ảnh upload tối đa là 16MB

# Kiểm tra định dạng file
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Route trả về file index.html
@app.route('/')
def index():
    # Lấy danh sách ảnh mẫu từ thư mục 'static/images'
    image_files = os.listdir(os.path.join(app.static_folder, 'images'))
    image_files = [f'/static/images/{file}' for file in image_files if allowed_file(file)]
    
    # Render template index.html và truyền dữ liệu danh sách ảnh mẫu
    return render_template('index.html', image_files=image_files)

# API để xử lý upload ảnh và gọi Replicate API
@app.route('/upload', methods=['POST'])
def upload():
    base_url = request.host_url
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        file_path = os.path.join('static/uploads/', filename)
        file.save(file_path)

        # Lấy ảnh mẫu từ form
        target_image_url = request.form.get('target_image')

        # Gọi API Replicate để thực hiện FaceSwap
        input_data = {
            "local_source": f"{base_url}/{file_path}",
            "local_target": target_image_url
        }
        print(input_data)

        output = replicate.run(
            "xiankgx/face-swap:cff87316e31787df12002c9e20a78a017a36cb31fde9862d8dedd15ab29b7288",
            input=input_data
        )

        print(output)
        # Assuming 'image' is a FileOutput object
        file_output = output['image']

        # Lấy URL của ảnh đã xử lý từ Replicate
        swapped_image_url = file_output.url

        # Trả về URL của ảnh đã swap
        return jsonify({'swapped_image_url': swapped_image_url})

    return jsonify({'error': 'Invalid file'}), 400

# API để trả về ảnh trong thư mục uploads (nếu cần)
@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

if __name__ == '__main__':
    if not os.path.exists(UPLOAD_FOLDER):
        os.makedirs(UPLOAD_FOLDER)
    app.run(debug=True)
