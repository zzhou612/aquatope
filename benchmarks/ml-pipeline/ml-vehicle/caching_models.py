import numpy as np
from gluoncv import data, model_zoo, utils


def is_box_valid(box: list) -> bool:
    for pos in box:
        if pos < 0:
            return False
    return True


# pre-trained SSD models
net = model_zoo.get_model('ssd_512_resnet50_v1_voc', pretrained=True)
im_fname = utils.download('https://github.com/dmlc/web-data/blob/master/' +
                          'gluoncv/detection/street_small.jpg?raw=true',
                          path='street_small.jpg')
x, img = data.transforms.presets.ssd.load_test(im_fname, short=512)
print('Shape of pre-processed image:', x.shape)
class_IDs, scores, bounding_boxes = net(x)

for i in range(class_IDs.shape[1]):
    class_id = int(class_IDs[0][i][0].asscalar())
    score = float(scores[0][i][0].asscalar())
    bounding_box = bounding_boxes[0][i].asnumpy().tolist()
    if class_id != -1 and is_box_valid(bounding_box) and score > 0.5:
        print(class_id)
        print(score)
        print(net.classes[class_id])
        print(bounding_box)
