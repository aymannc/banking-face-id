import json
import os
import time
from pathlib import Path

import requests
from flask import Flask, jsonify, request, send_from_directory, Response
from flask_cors import CORS
from flask_mysqldb import MySQL
from imutils import paths

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}
data_set_path = "./data/images"
results_path = "./data/results"
public_url = 'http://127.0.0.1:5000/'
app = Flask(__name__, static_url_path='')
CORS(app)
# run_with_ngrok(app)
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = ''
app.config['MYSQL_DB'] = 'adria'

mysql = MySQL(app)

data = {}
data_load_time = 0.0
number_of_requests = 0


@app.route('/uploads/<path:path>')
def download_file(path):
    return send_from_directory(data_set_path, path)


@app.route('/results/<path:path>')
def download_results_image(path):
    return send_from_directory(results_path, path)


# For google colab hosting
# @app.before_first_request
def get_ngrok_url():
    global public_url
    url = "http://localhost:4040/api/tunnels"
    res = requests.get(url)
    res_unicode = res.content.decode("utf-8")
    res_json = json.loads(res_unicode)
    public_url = res_json["tunnels"][1]["public_url"] + "/"
    return res_json["tunnels"][1]["public_url"] + "/"


def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def create_encodings_table():
    query = 'CREATE TABLE IF NOT EXISTS encodings(id bigint(20) NOT NULL AUTO_INCREMENT,userID bigint(20) NOT NULL,'
    for i in range(128):
        query += F'encoding{i} decimal(9,8) NOT NULL,'
    query += 'PRIMARY KEY (id), FOREIGN KEY (userID) REFERENCES abonne(id))'

    cursor = mysql.connection.cursor()
    cursor.execute(query)
    return query


def get_user_id(username):
    cursor = mysql.connection.cursor()
    query = F"SELECT id from abonne where username='{username}'"
    cursor.execute(query)
    data = cursor.fetchone()
    return data[0] if data else None


def insert_encodings(encoding, username):
    user_id = get_user_id(username)
    try:
        if user_id:
            query = F"insert into encodings values(null,{user_id}"
            for value in encoding:
                query += F',{value}'
            query += ')'
            connection = mysql.connection
            cursor = connection.cursor()
            cursor.execute(query)
            connection.commit()
            return True
    except Exception as _:
        return False
    finally:
        return False


@app.route('/upload_images', methods=['GET', 'POST'])
def upload_file():
    username = request.form.get('username') or "default"
    print("username", username)
    if request.method == 'POST' and 'files' in request.files:
        link_list = []
        try:
            for file in request.files.getlist('files'):
                if file and allowed_file(file.filename):
                    base_path = os.path.join(data_set_path, username)
                    file_name = f"{username}_{time.time()}{file.filename}"
                    Path(base_path).mkdir(parents=True, exist_ok=True)
                    full_path = os.path.join(base_path, file_name)
                    file.save(full_path)
                    link_list.append(f"{public_url}uploads/{username}/{file_name}")
        except Exception as e:
            print(e)
        return jsonify({"file_path": link_list})
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


@app.route('/facial_recognition', methods=['GET', 'POST'])
def upload_image():
    if request.method == 'POST':
        if 'file' not in request.files:
            return Response(
                "No image uploaded!",
                status=404
            )

        file = request.files['file']

        if file.filename == '':
            return Response("Image error!", status=415)

        if file and allowed_file(file.filename): pass
        # The image file seems valid! Detect faces and return the result.
        # return detect_faces_in_image(file)

    # If no valid image file was uploaded, show the file upload form:
    return '''
    <!doctype html>
    <title>Is this a picture of X?</title>
    <h1>Upload a picture !</h1>
    <form method="POST" enctype="multipart/form-data">
      <input type="file" name="file">
      <input type="submit" value="Upload">
    </form>
    '''


@app.route('/faces_encoding', methods=['GET', 'POST'])
def faces_encoding():
    successful = True
    error_message = None

    start_time = time.time()
    try:
        print("[INFO] quantifying faces...")
        # Example of output ['dataset\\anc\\Nait Cherif.jpg',...]
        imagePaths = list(paths.list_images(data_set_path))
        print(imagePaths)

        for (i, imagePath) in enumerate(imagePaths):
            # extract the person name from the image path
            print(f"[INFO] processing image {i + 1}/{len(imagePaths)}")
            name = imagePath.split(os.path.sep)[-2]
            insert_encodings(encoding, name)
    except Exception as e:
        successful = False
        error_message = e
        print(e)
    finally:
        response = jsonify({
            "successful": successful,
            "error_message": str(error_message),
            "time_to_complete": time.time() - start_time
        })
        return response


#
#
# def detect_faces_in_image(file_stream):
#     start_time = time.time()
#     print("[INFO] recognizing faces...")
#     original_img = Image.open(file_stream).convert('RGB')
#     # printm()
#     img = np.array(original_img)
#     boxes = face_recognition.face_locations(img, model="cnn", number_of_times_to_upsample=2)
#     encodings = face_recognition.face_encodings(img, boxes, num_jitters=10, model="large")
#     # Get face encodings for any faces in the uploaded image
#     names = []
#
#     for encoding in encodings:
#         global data
#         matches = face_recognition.compare_faces(
#             data["encodings"], encoding, tolerance=0.45)
#         name = "Unknown"
#         if True in matches:
#             # find the indexes of all matched faces then initialize a
#             # dictionary to count the total number of times each face
#             # was matched
#             matchedIdxs = [i for (i, b) in enumerate(matches) if b]
#             counts = {}
#             # loop over the matched indexes and maintain a count for
#             # each recognized face
#             for i in matchedIdxs:
#                 name = data["names"][i]
#                 counts[name] = counts.get(name, 0) + 1
#             # determine the recognized face with the largest number of
#             # votes (note: in the event of an unlikely tie Python will
#             # select first entry in the dictionary)
#             name = max(counts, key=counts.get)
#             name = name if name != "ANC" else "Nait Cherif"
#             print("[INFO]counts", counts)
#             # update the list of names
#         names.append(name)
#     image = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
#     for (top, right, bottom, left), name in zip(boxes, names):
#         # Draw a box around the face
#         cv2.rectangle(image, (left - 20, top - 20),
#                       (right + 20, bottom + 20), (255, 0, 0), 2)
#
#         # Draw a label with a name below the face
#         cv2.rectangle(image, (left - 20, bottom),
#                       (right + 20, bottom + 20), (255, 0, 0), cv2.FILLED)
#         font = cv2.FONT_HERSHEY_DUPLEX
#         cv2.putText(image, name, (left - 20, bottom + 15),
#                     font, 0.7, (255, 255, 255))
#
#     # show the output image
#     file_name = f"{time.time()}.jpg"
#     file_path = f"{results_path}/{file_name}"
#     cv2.imwrite(file_path, image)
#     show_image(file_path)
#     result = {
#         "results_file_url": f"{public_url}results/{file_name}",
#         "faces_found_in_image": names,
#         "faces_load_time": data_load_time,
#         "data_rec_time": time.time() - start_time
#     }
#     return jsonify(result)


if __name__ == "__main__":
    app.run()
