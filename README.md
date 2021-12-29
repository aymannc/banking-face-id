# Banking FaceId

A facial recognition system allowing user identification during authentication and signing of banking transactions 

## Model used
facenet with pretrained Keras model (trained by MS-Celeb-1M dataset).
- Download model from [here](https://drive.google.com/open?id=1pwQ3H4aJ8a6yyJHZkTwtjcL4wYWQb7bn) and save it in model/keras/

# Steps to running the Backends
```bash
docker build  -t faceidapi:latest .
docker-compose up --build -d
```
