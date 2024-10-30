## USAGE

```sh
docker-compose down

# start celery with workers
docker-compose up --build --scale celery_default=3 --scale celery_high_priority=2
# upload image
curl -X POST \
  -F "file=@./app/image.jpeg" \
  -F "resize=1024,768" \
  -F "quality=90" \
  http://localhost:5000/upload

# check task status
curl http://localhost:5000/task/<task_id>
```
