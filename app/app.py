from flask import Flask, request, jsonify
from werkzeug.utils import secure_filename
import os
from tasks import process_image, app as celery_app
from celery.result import AsyncResult
from pytz import timezone
import pendulum
import time
app = Flask(__name__)

# Configuration
UPLOAD_FOLDER = "uploads"
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif"}
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
TIMEZONE = timezone("Asia/Riyadh")

# Ensure upload directory exists
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


def allowed_file(filename):
    """Check if file extension is allowed"""
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def save_uploaded_file(file):
    """Save uploaded file and return file path"""
    filename = secure_filename(file.filename)
    file_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
    file.save(file_path)
    return file_path


def get_processing_params(request_form):
    """Extract and validate processing parameters from request form"""
    resize = request_form.get("resize", "800,600")
    width, height = map(int, resize.split(","))
    quality = int(request_form.get("quality", "85"))
    return (width, height), quality


@app.route("/upload", methods=["POST"])
def upload_file():
    """Handle image upload and start processing"""
    if "file" not in request.files:
        return jsonify({"error": "No file part"}), 400

    file = request.files["file"]
    if file.filename == "":
        return jsonify({"error": "No selected file"}), 400

    if not file or not allowed_file(file.filename):
        return jsonify({"error": "Invalid file type"}), 400

    file_path = save_uploaded_file(file)
    resize_dims, quality = get_processing_params(request.form)

    task = process_image.delay(file_path, resize=resize_dims, quality=quality)

    return (
        jsonify(
            {
                "message": "Processing started",
                "task_id": task.id,
                "status": "processing",
            }
        ),
        202,
    )


@app.route("/status/<task_id>")
def get_status(task_id):
    """Check the status of a processing task"""
    task_result = AsyncResult(task_id, app=celery_app)

    if task_result.ready():
        if task_result.successful():
            return jsonify({"status": "completed", "result": task_result.get()})
        return jsonify({"status": "failed", "error": str(task_result.result)}), 500

    return jsonify({"status": task_result.state})


def parse_schedule_time(schedule_time):
    """Parse and validate schedule time"""
    if not schedule_time:
        raise ValueError("schedule_time is required")

    try:
        execution_time = pendulum.parse(schedule_time, tz="Asia/Riyadh")
        return execution_time
    except Exception as e:
        raise ValueError(f"Invalid schedule_time format: {str(e)}")


@app.route("/schedule-future", methods=["POST"])
def schedule_future():
    """Schedule a future image processing task"""
    if "file" not in request.files:
        return jsonify({"error": "No file uploaded"}), 400

    file = request.files["file"]
    if file.filename == "":
        return jsonify({"error": "No file selected"}), 400

    try:
        file_path = save_uploaded_file(file)
        resize_dims, quality = get_processing_params(request.form)
        execution_time = parse_schedule_time(request.form.get("schedule_time"))
        execution_time_utc = execution_time.in_timezone("UTC")

        task = process_image.apply_async(
            kwargs={"image_path": file_path, "resize": resize_dims, "quality": quality},
            eta=execution_time_utc,
        )

        return (
            jsonify(
                {
                    "message": "Task scheduled successfully",
                    "scheduled_time_riyadh": execution_time.isoformat(),
                    "scheduled_time_utc": execution_time_utc.isoformat(),
                    "task_id": task.id,
                }
            ),
            202,
        )

    except ValueError as e:
        return jsonify({"error": str(e)}), 400


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0")
