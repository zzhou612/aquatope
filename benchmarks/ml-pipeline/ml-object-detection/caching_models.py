import numpy as np
from gluoncv import data, model_zoo, utils


def is_box_valid(box: list) -> bool:
    for pos in box:
        if pos < 0:
            return False
    return True


#  pre-trained YOLO models
net = model_zoo.get_model('yolo3_darknet53_voc', pretrained=True)
im_fname = utils.download('https://raw.githubusercontent.com/zhreshold/' +
                          'mxnet-ssd/master/data/demo/dog.jpg',
                          path='dog.jpg')
x, img = data.transforms.presets.yolo.load_test(im_fname, short=512)
print('Shape of pre-processed image:', x.shape)
class_IDs, scores, bounding_boxs = net(x)
for i in range(class_IDs.shape[1]):
    class_id = int(class_IDs[0][i][0].asscalar())
    if class_id != -1:
        print(class_id)
        print(net.classes[class_id])
        print(bounding_boxs[0][i].asnumpy().tolist())
