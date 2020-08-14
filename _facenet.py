import numpy as np
from keras.models import load_model

from _mtcnn import extract_face

image_dir_basepath = './data/images/'
image_size = 160
model_path = 'facenet_keras.h5'
model = load_model(model_path)


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
        print('[INFO] prossesing ', filepath)
        face = extract_face(filepath)[0]
        aligned_images.append(face)
    return np.array(aligned_images)


def calc_embedings(filepaths, batch_size=1):
    print('[INFO] prewhiten')
    aligned_images = prewhiten(load_and_align_images(filepaths))
    pd = []
    for start in range(0, len(aligned_images), batch_size):
        print('[INFO] calculating embeddings  n = ', start)
        pd.append(model.predict_on_batch(aligned_images[start:start + batch_size]))
    embs = l2_normalize(np.concatenate(pd))
    return embs


def calc_dist(emb1, emb2):
    return np.linalg.norm(emb1 - emb2)
