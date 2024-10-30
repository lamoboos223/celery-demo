from flask import Flask, request, jsonify
from werkzeug.utils import secure_filename
import os
from tasks import process_image
from celery.result import AsyncResult

app = Flask(__name__)

# Configuration
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Ensure upload directory exists
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/upload', methods=['POST'])
def upload_file():
    # Check if file was uploaded
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    
    file = request.files['file']
    
    # Check if file was selected
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
    
    if file and allowed_file(file.filename):
        # Secure the filename
        filename = secure_filename(file.filename)
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        
        # Save the uploaded file
        file.save(file_path)
        
        # Get processing parameters from request
        resize = request.form.get('resize', '800,600')
        width, height = map(int, resize.split(','))
        quality = int(request.form.get('quality', '85'))
        
        # Start async processing task
        task = process_image.delay(
            file_path,
            resize=(width, height),
            quality=quality
        )
        
        return jsonify({
            'message': 'Processing started',
            'task_id': task.id,
            'status': 'processing'
        }), 202

@app.route('/status/<task_id>')
def get_status(task_id):
    """Check the status of a processing task"""
    task_result = AsyncResult(task_id)
    
    if task_result.ready():
        if task_result.successful():
            result = task_result.get()
            return jsonify({
                'status': 'completed',
                'result': result
            })
        else:
            return jsonify({
                'status': 'failed',
                'error': str(task_result.result)
            }), 500
    
    return jsonify({
        'status': task_result.state
    })

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0') 