import numpy as np
import argparse
import sys,os  
import cv2
import time
caffe_root = '../../../../../../caffe_train/'
sys.path.insert(0, caffe_root + 'python')  
import caffe  

minMargin = 36

def make_parser():
    parser = argparse.ArgumentParser()
    parser.add_argument('--model', type=str, help='.prototxt file for inference', default = '../net/face_detector.prototxt')
    parser.add_argument('--weights', type=str, help='.caffemodel file for inference', default = '../net/face_detector.caffemodel')
    parser.add_argument('--facemodel', type=str, help='.prototxt file for inference face landmarks', default = '../net/face_attributes.prototxt')
    parser.add_argument('--faceweights', type=str, help='.caffemodel file for inference face landmarks weights', default = '../net/face_attributes.caffemodel')
    return parser

parser1 = make_parser()
args = parser1.parse_args()
net_file= args.model
caffe_model= args.weights
face_file= args.facemodel
face_model= args.faceweights


if not os.path.exists(caffe_model):
    print(caffe_model + " does not exist")
    exit()
if not os.path.exists(net_file):
    print(net_file + " does not exist")
    exit()
caffe.set_mode_gpu();
caffe.set_device(0);
net = caffe.Net(net_file,caffe_model,caffe.TEST) 
face_net = caffe.Net(face_file,face_model,caffe.TEST) 

CLASSES = ('background', 'face')
gender_content = ('male', 'female')
glasses_content = ('wearing glasses', 'not wearing glasses')


test_dir = "../images"

def max_(m,n):
	if m > n:
		return m
	return n


def min_(m,n):
	if m > n:
		return n
	return m


def preprocessdet(src, size):
    img = cv2.resize(src, size)
    img = img - [103.94, 116.78, 123.68]
    img = img * 0.007843
    return img


def preprocess(src, size):
    img = cv2.resize(src, size)
    img = img - 127.5
    img = img * 0.007843
    return img


def post_facedet(img, out):
    h = img.shape[0]
    w = img.shape[1]
    box = out['detection_out'][0,0,:,3:7] * np.array([w, h, w, h])
    cls = out['detection_out'][0,0,:,1]
    conf = out['detection_out'][0,0,:,2]
    return box.astype(np.int32), conf, cls


def post_faceattributes(img, out):
    h = img.shape[0]
    w = img.shape[1]
    facepoints = out['multiface_output'][0,0:10] * np.array([w, w, w, w, w, h, h, h, h, h])
    faceangle = out['multiface_output'][0,10:13]
    gender = out['multiface_output'][0,13:15]
    gender_index = np.argmax(gender)
    glass = out['multiface_output'][0,15:17]
    glass_index = np.argmax(glass)
    return facepoints.astype(np.int32), faceangle, gender_content[gender_index], glasses_content[glass_index]


def detect(imgfile):
   frame = cv2.imread(imgfile)
   start = time.time()
   #frame=cv2.flip(frame,1)
   h = frame.shape[0]
   w = frame.shape[1]
   inputSize = (net.blobs['data'].data.shape[3], net.blobs['data'].data.shape[2])
   img = preprocessdet(frame, inputSize)
   img = img.astype(np.float32)
   img = img.transpose((2, 0, 1))

   net.blobs['data'].data[...] = img
   out = net.forward()
   box, conf, cls = post_facedet(frame, out)
   end = time.time()
   print("face detect time: %.3f"%(end - start))
   for i in range(len(box)):
      if conf[i]>=0.25:
         p1 = (box[i][0], box[i][1])
         p2 = (box[i][2], box[i][3])
         
         x1 = max_(0, box[i][0] - minMargin/2)
         x2 = min_(box[i][2] + minMargin/2, w)
         y1 = max_(0, box[i][1] - minMargin/2)
         y2 = min_(box[i][3] + minMargin/2, h)
         
         p11 = (x1, y1)
         p22 = (x2, y2)
         start = time.time()
         ori_img = frame[y1:y2, x1:x2, :]
         ############face attributes#######################
         size = (face_net.blobs['data'].data.shape[3], face_net.blobs['data'].data.shape[2])
         attri_img = preprocess(ori_img, size)
         attri_img = attri_img.astype(np.float32)
         attri_img = attri_img.transpose((2, 0, 1))
         face_net.blobs['data'].data[...] = attri_img
         face_out = face_net.forward()
         boxpoint, faceangle, gender, glass = post_faceattributes(ori_img, face_out)
         end = time.time()
         print("face attributes time: %.3f"%(end - start))
         yaw, pitch, roll = faceangle
         for jj in range(5):
             point = (boxpoint[jj], boxpoint[jj+5])
             cv2.circle(ori_img, point, 3, (0,0,213), -1)
         cv2.rectangle(frame, p1, p2, (0,255,0))
         p3 = (max(p1[0], 15), max(p1[1], 15))
         title = " %s,  %s" % (gender, glass)
         print(title)
         cv2.putText(frame, title, p3, cv2.FONT_ITALIC, 0.5, (0, 255, 0), 1)
   name = test_dir + '/' + imgfile.split("/")[-1].split('.jpg')[0] + '_crop.jpg'
   cv2.imwrite(name, frame)
   cv2.imshow("face", frame)
   k = cv2.waitKey(30) & 0xff
   if k == 27 : 
      return False

if __name__=="__main__":
    for f in os.listdir(test_dir):
        if detect(test_dir + "/" + f) == False:
           break
