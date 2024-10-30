## USAGE

```sh
docker-compose down

docker-compose up --build

curl -X POST \
  -F "file=@./app/image.jpeg" \
  -F "resize=1024,768" \
  -F "quality=90" \
  http://localhost:5000/upload
```
