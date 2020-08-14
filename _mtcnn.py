import matplotlib.pyplot as plt
from PIL import Image
from mtcnn.mtcnn import MTCNN
from numpy import asarray


# extract a single face from a given photograph
def extract_face(filename, required_size=(160, 160)):
    # load image from file
    image = Image.open(filename)
    # convert to RGB, if needed
    image = image.convert('RGB')
    # convert to array
    pixels = asarray(image)
    # displaying the image
    plt.imshow(image)
    plt.show()
    # create the detector, using default weights
    detector = MTCNN()
    # detect faces in the image
    results = detector.detect_faces(pixels)
    print(results)
    faces_array = []
    # extract the bounding box from the first face
    for result in results:
        x1, y1, width, height = result['box']
        x1, y1 = abs(x1), abs(y1)
        x2, y2 = x1 + width, y1 + height
        # extract the face
        face = pixels[y1:y2, x1:x2]
        # resize pixels to the model size
        image = Image.fromarray(face)
        image = image.resize(required_size)
        image = asarray(image)
        faces_array.append(image)
        plt.imshow(image)
        plt.show()
    return faces_array
