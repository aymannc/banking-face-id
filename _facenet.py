import os

import matplotlib.pyplot as plt
# Commented out IPython magic to ensure Python compatibility.
import numpy as np
from imageio import imread
from imutils import paths
from keras.models import load_model
from scipy.spatial import distance

from _mtcnn import extract_face

image_dir_basepath = 'data/images/'
names = ['anc']
image_size = 160
model_path = 'facenet_keras.h5'


def prewhiten(x):
    if x.ndim == 4:
        axis = (1, 2, 3)
        size = x[0].size
    elif x.ndim == 3:
        axis = (0, 1, 2)
        size = x.size
    else:
        raise ValueError('Dimension should be 3 or 4')

    mean = np.mean(x, axis=axis, keepdims=True)
    std = np.std(x, axis=axis, keepdims=True)
    std_adj = np.maximum(std, 1.0 / np.sqrt(size))
    y = (x - mean) / std_adj
    return y


def l2_normalize(x, axis=-1, epsilon=1e-10):
    output = x / np.sqrt(np.maximum(np.sum(np.square(x), axis=axis, keepdims=True), epsilon))
    return output


def load_and_align_images(filepaths):
    aligned_images = []
    for filepath in filepaths:
        print('[INFO] Aligning image :', filepath)
        aligned_images.append(extract_face(filepath)[0])
    return np.array(aligned_images)


def calculate_embeddings(filepaths):
    aligned_images = prewhiten(load_and_align_images(filepaths))

    model = load_model(model_path)
    pd = []
    for i in range(len(aligned_images)):
        print('[INFO] model.predict')
        pd.append(model.predict(aligned_images[i]))
    embs = l2_normalize(np.concatenate(pd))

    return embs


def calc_dist(img_name0, img_name1):
    return distance.euclidean(data[img_name0]['emb'], data[img_name1]['emb'])


def calc_dist_plot(img_name0, img_name1):
    plt.subplot(1, 2, 1)
    plt.imshow(imread(data[img_name0]['image_filepath']))
    plt.subplot(1, 2, 2)
    plt.imshow(imread(data[img_name1]['image_filepath']))
    return calc_dist(img_name0, img_name1)


data = {}


def get_embeddings():
    imagePaths = list(paths.list_images(image_dir_basepath))
    print('paths', imagePaths)
    for name in names:
        image_dirpath = image_dir_basepath + name
        image_filepaths = [os.path.join(image_dirpath, f) for f in os.listdir(image_dirpath)]
        print('paths2', image_filepaths)
        embs = calculate_embeddings(image_filepaths)
        for i in range(len(image_filepaths)):
            data['{}{}'.format(name, i)] = {'image_filepath': image_filepaths[i],
                                            'emb': embs[i]}

    calculated_distance = round(calc_dist_plot("NaitCherif1", "NaitCherif0"), 1)
    print(calculated_distance, 'Same' if calculated_distance <= 0.55 else 'Different', 'person')

    return data
