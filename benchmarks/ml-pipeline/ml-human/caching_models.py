import numpy as np
from gluoncv import data, model_zoo, utils


def is_box_valid(box: list) -> bool:
    for pos in box:
        if pos < 0:
            return False
    return True


# pre-trained Faster RCNN models
net = model_zoo.get_model('faster_rcnn_resnet50_v1b_voc', pretrained=True)
im_fname = utils.download('https://github.com/dmlc/web-data/blob/master/' +
                          'gluoncv/detection/biking.jpg?raw=true',
                          path='biking.jpg')
x, orig_img = data.transforms.presets.rcnn.load_test(im_fname)
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
