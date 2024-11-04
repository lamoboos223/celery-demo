from celery import Celery
from PIL import Image
import os
from datetime import datetime
import logging
from typing import Optional

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Celery
app = Celery("tasks", broker="redis://broker:6379/0", backend="redis://broker:6379/0")

# Celery Configuration
app.conf.update(
    task_track_started=True,
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    task_routes={
        "tasks.process_image": {"queue": "high_priority"},
        # Add other tasks here with their queue assignments
    },
    task_default_queue="default",
    worker_prefetch_multiplier=1,  # Process one task at a time
    task_acks_late=True,  # Task acknowledgment after completion
    timezone="Asia/Riyadh",  # Set Celery timezone
    enable_utc=True,
)


class ImageProcessingError(Exception):
    pass


# @app.on_after_configure.connect
# def setup_periodic_tasks(sender, **kwargs):
#     print("Celery configured")
#     sender.add_periodic_task(
#         10.0,
#         process_image.s(
#             image_path="/app/app/image.jpeg",
#             resize=(800, 600),
#             quality=85
#         ),
#         name='process-image'
#     )


@app.task(
    bind=True,
    name="tasks.process_image",
    max_retries=3,
    retry_backoff=True,
    queue="high_priority",
)
def process_image(
    self,
    image_path: str,
    resize: tuple[int, int] = (800, 600),
    optimize: bool = True,
    quality: Optional[int] = 85,
) -> dict:
    """
    Process an image with various operations
    """
    try:
        pass

        # time.sleep(10)
        logger.info(f"Starting to process image: {image_path}")

        # Get file info
        filename = os.path.basename(image_path)
        name, ext = os.path.splitext(filename)

        # Create output filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_filename = f"processed_{name}_{timestamp}{ext}"
        output_path = os.path.join("processed", output_filename)

        # Ensure output directory exists
        os.makedirs("processed", exist_ok=True)

        # Open and process image
        with Image.open(image_path) as img:
            # Convert to RGB if necessary
            if img.mode in ("RGBA", "P"):
                img = img.convert("RGB")

            # Resize
            if resize:
                img = img.resize(resize, Image.Resampling.LANCZOS)

            # Save processed image
            img.save(output_path, optimize=optimize, quality=quality)

            # Get file size
            file_size = os.path.getsize(output_path)

            logger.info(f"Successfully processed image: {output_path}")

            return {
                "status": "success",
                "original_path": image_path,
                "processed_path": output_path,
                "size": file_size,
                "dimensions": img.size,
            }

    except Exception as e:
        logger.error(f"Error processing image {image_path}: {str(e)}")
        raise self.retry(exc=e)
