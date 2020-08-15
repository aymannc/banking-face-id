import os
import time
from pathlib import Path

import numpy as np
import tensorflow as tf
from flask import Flask
from flask import request, send_from_directory
from flask_cors import CORS
from flask_mysqldb import MySQL
from tensorflow.python.keras.backend import set_session
from tensorflow.python.keras.models import load_model

from _facenet import calculate_embeddings
from mysql_queries import insert_encodings, create_encodings_table, get_user_id, calculate_distance_mysql, \
    get_user_encoding

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}
dataset_path = "data/images/"
public_url = 'http://127.0.0.1:5000/'
app = Flask(__name__)
CORS(app)

app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = ''
app.config['MYSQL_DB'] = 'adria'
mysql = MySQL(app)

model_path = 'facenet_keras.h5'

print('[INFO] loading model')
tf_config = None
sess = tf.Session(config=tf_config)
graph = tf.get_default_graph()

set_session(sess)
model = load_model(model_path)
print('[INFO] Done !')


@app.route('/uploads/<path:path>')
def download_file(path):
    return send_from_directory(dataset_path, path)


def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route('/creating_encodings_table', methods=['GET'])
def creating_encodings_table():
    return create_encodings_table(mysql)


@app.route('/upload_images', methods=['GET', 'POST'])
def upload_file():
    if request.method == 'POST' and 'files' in request.files:
        username = request.form.get('username') or None
        print("username", username)

        user_id = get_user_id(username, mysql)
        if user_id:
            public_paths = []
            local_paths = []
            try:
                for file in request.files.getlist('files'):
                    if file and allowed_file(file.filename):
                        base_path = os.path.join(dataset_path, username)
                        file_name = f"{username}_{time.time()}{file.filename}"
                        Path(base_path).mkdir(parents=True, exist_ok=True)
                        full_path = os.path.join(base_path, file_name)
                        file.save(full_path)
                        local_paths.append(full_path)
                        public_paths.append(f"{public_url}uploads/{username}/{file_name}")
                print(local_paths)
                error_message = encode_images(username, user_id=user_id)
                if error_message:
                    raise Exception(error_message)
            except Exception as e:
                print(e)
                return {"error": str(e)}, 500
            return {"file_path": public_paths}, 201
        else:
            return {"error": "Didn't found the user "}, 404
    return '''
    <!doctype html>
    <title>Upload</title>
    <h1>Upload a picture !</h1>
    <form method="POST" enctype="multipart/form-data">
      <input type="text" id="username" name="username"><br>
      <input type="file" id="files" name="files" multiple>
      <input type="submit" value="Upload">
    </form>
    '''


def encode_images(username, user_id=None):
    try:
        path = os.path.join(dataset_path, username)
        images = [os.path.join(path, f) for f in os.listdir(path) if os.path.isfile(os.path.join(path, f))]
        encodings = calculate_embeddings(images, model, sess, graph)
        print('[INFO] Calculating the mean')
        mean = np.mean(encodings, axis=0)
        error = insert_encodings(mean, username, mysql, user_id)
        if error:
            return error
        return None
    except Exception as e:
        print(e)
        return e


@app.route('/encode_user_images', methods=['POST'])
def encode_user_images(username=None):
    start_time = time.time()
    status_code = 201

    request_data = request.get_json()
    username = username or request_data.get('username')
    if username:
        error_message = encode_images(username)
        status_code = 500 if error_message else status_code
    else:
        error_message = "Username not provided/found"
        status_code = 404
    successful = not error_message
    response = {
        "successful": successful,
        "error_message": str(error_message),
        "time_to_complete": time.time() - start_time
    }
    return response, status_code


@app.route('/encode_all_images', methods=['GET', 'POST'])
def encode_all_images():
    successful = True
    error_message = None
    start_time = time.time()
    try:
        usernames = [directory for directory in os.listdir(dataset_path) if os.path.isdir(dataset_path + directory)]
        print(usernames)
        for username in usernames:
            error_message = encode_images(username)
            if error_message:
                return
    except Exception as e:
        successful = False
        error_message = e
        print(e)
    finally:
        response = {
            "successful": successful and not error_message,
            "error_message": str(error_message if not True else None),
            "time_to_complete": time.time() - start_time
        }

        return response, 500 if error_message else 201


@app.route('/compare_users_encodings', methods=['GET'])
def compare_users_encodings():
    encodings = get_user_encoding(mysql, 'ouftou')
    results = calculate_distance_mysql(encodings, mysql, distance=0.55)
    return str(results)


# @app.route('/facial_recognition', methods=['GET', 'POST'])
# def upload_image():
#     if request.method == 'POST':
#         if 'file' not in request.files:
#             return Response(
#                 "No image uploaded!",
#                 status=404
#             )
#
#         file = request.files['file']
#
#         if file.filename == '':
#             return Response("Image error!", status=415)
#
#         if file and allowed_file(file.filename): pass
#         # The image file seems valid! Detect faces and return the result.
#         # return detect_faces_in_image(file)
#
#     # If no valid image file was uploaded, show the file upload form:
#     return '''
#     <!doctype html>
#     <title>Is this a picture of X?</title>
#     <h1>Upload a picture !</h1>
#     <form method="POST" enctype="multipart/form-data">
#       <input type="file" name="file">
#       <input type="submit" value="Upload">
#     </form>
#     '''


if __name__ == "__main__":
    app.run()
