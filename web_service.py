import os
import time
from pathlib import Path

import numpy as np
import tensorflow as tf
from flask import Flask, request, send_from_directory
from flask_cors import CORS
from flask_mysqldb import MySQL
from tensorflow.python.keras.backend import set_session
from tensorflow.python.keras.models import load_model

from _facenet import calculate_embeddings
from mysql_queries import insert_encodings, create_encodings_table, get_user_id, calculate_distance_from_mysql, \
    get_user_encoding, check_user_by_id, encodings_exits, get_username_by_id

# Constants
MAX_DISTANCE = 0.6
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}
images_path = 'data/'
dataset_path = os.path.join(images_path, "uploads/")
requests_path = os.path.join(images_path, "requests/")
public_url = 'http://127.0.0.1:5000/'

# App creation
app = Flask(__name__)
CORS(app)
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = ''
app.config['MYSQL_DB'] = 'adria'
mysql = MySQL(app)

print('[INFO] loading model')
sess = tf.Session()
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


@app.route('/upload_images', methods=['POST'])
def upload_images():
    if 'files' in request.files and request.form.get('username'):
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
                encode_images(username, user_id=user_id)
            except Exception as e:
                try:
                    url = public_url + str(e.args[1]).split('/', 1)[1].replace('\\', '/')
                    error_message = F"{e.args[0]}: {url}"
                except Exception as _:
                    error_message = str(e)
                print(error_message)
                return {"error": error_message}, 400
            return {"uploaded_images": public_paths}, 201
        else:
            return {"error": "Didn't found the user "}, 404


@app.route('/encode_user_images', methods=['POST'])
def encode_user_images(username=None):
    start_time = time.time()
    status_code = 201
    error_message = None
    try:
        username = username or get_username_by_id(request.form['user_id'], mysql)
        if username:
            try:
                # TODO : add check for 0 faces
                encode_images(username)
            except Exception as e:
                status_code = 400
                try:
                    url = public_url + str(e.args[1]).split('/', 1)[1].replace('\\', '/')
                    error_message = F"{e.args[0]}: {url}"
                except Exception as _:
                    error_message = e
        else:
            error_message = "Username not found"
            status_code = 404
    except Exception as _:
        error_message = "You didn't provide a user id"
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
            # TODO : add check for 0 faces
            error_message = encode_images(username)
    except Exception as e:
        try:
            url = public_url + str(e.args[1]).split('/', 1)[1].replace('\\', '/')
            error_message = F"{e.args[0]} {url}"
        except Exception as _:
            error_message = str(e)
        successful = False
        print(e)
    finally:
        response = {
            "successful": successful and not error_message,
            "error_message": str(error_message if not successful else None),
            "time_to_complete": time.time() - start_time
        }

        return response, 400 if error_message else 201


@app.route('/facial_recognition', methods=['POST'])
def upload_image():
    start_time = time.time()
    error = None
    response = None
    image_requested_link = None
    
    if 'file' not in request.files:
        return {"error": "No image uploaded!"}, 404

    file = request.files['file']

    if file.filename == '':
        return {"error": "Image error!"}, 415

    # The image file seems valid! Detect faces and return the result.
    if file and allowed_file(file.filename):
        # Check for user
        user_id = None
        try:
            form_user_id = request.form['user_id']
            if form_user_id:
                # Check the database
                user_id = check_user_by_id(form_user_id, mysql)
                if user_id is None:
                    error = f"Didn't found a user with the id {form_user_id}"
                    user_id = -1
                else:
                    user_id = user_id if encodings_exits(user_id, mysql) else -1
                    error = None if user_id != -1 else f"Didn't found embeddings for a user with the " \
                                                       f"id {form_user_id} "
        except Exception as e:
            print(e)
            user_id = None
        # If the id is None or valid( not equal to -1 )
        if user_id != -1:
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
                try:
                    error = F"{e.args[0]} {public_url + str(e.args[1]).split('/', 1)[1]}"
                except Exception as _:
                    error = str(e)
            # Comparing generated encoding with saved ones
            if encodings is not None:
                try:
                    if user_id:
                        distance, username = calculate_distance_from_user_encoding(encodings, user_id)
                        print('Distance ', distance)
                        if distance < MAX_DISTANCE:
                            response = {
                                "id": int(user_id),
                                "distance": distance,
                                "username": username
                            }
                    else:
                        data = calculate_distance_from_mysql(encodings, mysql, distance=MAX_DISTANCE)
                        if data is not None:
                            response = []
                            for e in data:
                                response.append({
                                    "id": int(e[0]),
                                    "distance": float(e[1]),
                                    "username": e[2],
                                })
                except Exception as e:
                    print(e)
                    error = str(e)
        result = {
            "distance_used": MAX_DISTANCE,
            "image_requested_link": image_requested_link,
            "operation_time": time.time() - start_time,
            "error": error,
            "response": response,
        }
        return result, 200 if not error else 400


def calculate_distance_from_user_encoding(encodings, user_id):
    db_encodings, username = get_user_encoding(mysql, user_id=user_id)
    if db_encodings:
        return np.linalg.norm(encodings - db_encodings), username
    return None


def encode_images(username, user_id=None):
    path = os.path.join(dataset_path, username)
    images = [os.path.join(path, f) for f in os.listdir(path) if os.path.isfile(os.path.join(path, f))]
    if len(images) == 0:
        raise Exception('No images found for this user: ' + username)
    encodings = calculate_embeddings(images, model, sess, graph)
    print('[INFO] Calculating the mean')
    mean = np.mean(encodings, axis=0)
    insert_encodings(mean, username, mysql, user_id)


if __name__ == "__main__":
    app.run()
