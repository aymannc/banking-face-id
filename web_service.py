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
from mysql_queries import insert_encodings, create_encodings_table, get_user_id, calculate_distance_from_mysql, \
    get_user_encoding

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}
images_path = 'data/'
dataset_path = os.path.join(images_path, "images/")
requests_path = os.path.join(images_path, "requests/")
public_url = 'http://127.0.0.1:5000/'
app = Flask(__name__)
CORS(app)

app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = ''
app.config['MYSQL_DB'] = 'adria'
mysql = MySQL(app)

print('[INFO] loading model')
tf_config = None
sess = tf.Session(config=tf_config)
graph = tf.get_default_graph()
set_session(sess)
model = load_model('facenet_keras.h5')
print('[INFO] Done !')


@app.route('/uploads/<path:path>')
def download_file(path):
    return send_from_directory(dataset_path, path)


@app.route('/requests/<path:path>')
def download_results_image(path):
    return send_from_directory(requests_path, path)


def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route('/creating_encodings_table', methods=['GET'])
def creating_encodings_table():
    return create_encodings_table(mysql)


@app.route('/upload_images', methods=['GET', 'POST'])
def upload_images():
    if request.method == 'POST' and 'files' in request.files:
        username = request.form.get('username') or None
        print('[INFO] username !', username)
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
                print('[INFO] Pictures saved !', local_paths)
                error_message = encode_images(username, user_id=user_id)
                if error_message:
                    raise Exception(error_message)
            except Exception as e:
                print(e)
                return {"error": str(e)}, 500
            return {"uploaded_images": public_paths}, 201
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
        users_ids = [(username, get_user_id(username, mysql)) for username in usernames]
        for username, user_id in users_ids:
            if user_id is None:
                raise Exception(f" Did not found the id of this user: {username}")
        for username, user_id in users_ids:
            error_message = encode_images(username)
            if error_message:
                raise Exception(error_message)
    except Exception as e:
        successful = False
        error_message = e
        print(e)
    finally:
        response = {
            "successful": successful and not error_message,
            "error_message": str(error_message if not successful else None),
            "time_to_complete": time.time() - start_time
        }

        return response, 500 if error_message else 201


# @app.route('/compare_users_encodings', methods=['GET'])
# def compare_users_encodings():
#     encodings = get_user_encoding(mysql, 'ouftou')
#     results = calculate_distance_mysql(encodings, mysql, distance=0.55)
#     return str(results)


@app.route('/facial_recognition', methods=['GET', 'POST'])
def upload_image():
    start_time = time.time()
    if request.method == 'POST':
        error = None
        response = None
        if 'file' not in request.files:
            return "No image uploaded!", 404

        file = request.files['file']

        if file.filename == '':
            return "Image error!", 415

        # The image file seems valid! Detect faces and return the result.
        if file and allowed_file(file.filename):
            # Saving the file for traceability
            file_name = f"{time.time()}_{file.filename}"
            # Check if folder exists
            Path(requests_path).mkdir(parents=True, exist_ok=True)
            full_path = os.path.join(requests_path, file_name)
            file.save(full_path)
            image_requested_link = f"{public_url}requests/{file_name}"
            encodings = None
            try:
                encodings = calculate_embeddings([full_path], model, sess, graph)[0]
            except Exception as e:
                error = str(e)
            # Comparing generated encoding with saved ones
            if encodings is not None:
                request_data = request.get_json()
                print(request_data)
                if request_data and request_data.get('user_id'):
                    user_id = request_data.get('user_id')
                    try:
                        distance = calculate_distance_from_user_encoding(encodings, user_id)
                        response = (user_id, distance)
                    except Exception as e:
                        error = str(e)
                else:
                    response = calculate_distance_from_mysql(encodings, mysql, distance=0.5)
            result = {
                "image_requested_link": image_requested_link,
                "operation_time": time.time() - start_time,
                "error": error,
                "response": response,
            }
            return result, 200 if not error else 500

    return '''
    <!doctype html>
    <title>Is this a picture of X?</title>
    <h1>Upload a picture !</h1>
    <form method="POST" enctype="multipart/form-data">
      <input type="file" name="file">
      <input type="submit" value="Upload">
    </form>
    '''


def calculate_distance_from_user_encoding(encodings, user_id):
    db_encodings = get_user_encoding(mysql, user_id=user_id)
    if db_encodings:
        return np.linalg.norm(encodings - db_encodings)
    return None


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


if __name__ == "__main__":
    app.run()
