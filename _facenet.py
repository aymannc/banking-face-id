import numpy as np
from tensorflow.python.keras.backend import set_session

from _mtcnn import extract_face


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


def calculate_embeddings(filepaths, model, sess, graph, batch_size=1):
    aligned_images = prewhiten(load_and_align_images(filepaths))
    print('[INFO] Done aligning images')
    pd = []
    for i in range(len(aligned_images)):
        print('[INFO] Calculating encodings')
        with graph.as_default():
            set_session(sess)
            embedding = model.predict_on_batch(aligned_images[i:i + batch_size])
        pd.append(embedding)
    embs = l2_normalize(np.concatenate(pd))
    return embs
