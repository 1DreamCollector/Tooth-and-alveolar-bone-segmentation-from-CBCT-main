import os
import re
import nibabel as nib
import numpy as np
from scipy import ndimage
from skimage.morphology import skeletonize_3d
import cv2

def data_load():
    with open("/data1/LJX/001/label_file_polish.txt", 'r') as f:
        image_list = f.readlines()
    image_list = [item.replace('\n', '') for item in image_list]
    return image_list


image_list = data_load()
for data_id in range(len(image_list)):
    print('---preprocess the data:', data_id)
    data_path = image_list[data_id]
    path_pos_0 = [sub_data_path.start() for sub_data_path in re.finditer('/', data_path)][-3]
    path_pos_1 = [sub_data_path.start() for sub_data_path in re.finditer('/', data_path)][-2]
    path_pos_2 = [sub_data_path.start() for sub_data_path in re.finditer('/', data_path)][-1]
    path_pos_3 = [sub_data_path.start() for sub_data_path in re.finditer('.nii.gz', data_path)][-1]
    src_data_file = os.path.join(data_path)
    src_data_vol = nib.load(src_data_file)
    original_affine = src_data_vol.affine
    label = src_data_vol.get_fdata()

    teeth_ids = np.unique(label)
    multi_db = np.zeros(label.shape)
    for label_id in range(len(teeth_ids)):
        print('the tooth id:', label_id)
        tooth_id = teeth_ids[label_id]
        if tooth_id == 0:
            continue
        bin_label = (label == tooth_id).astype(np.uint8)
        if bin_label.sum() < 500:
            print('fine one label: %d, and the num is: %d', tooth_id, bin_label.sum())
            continue
        # 对每个切片进行处理
        image_bbox = (bin_label > 0)
        z_min = np.nonzero(image_bbox)[2].min()-3
        z_max = np.nonzero(image_bbox)[2].max()+3
        x_min = np.nonzero(image_bbox)[0].min()-16
        x_max = np.nonzero(image_bbox)[0].max()+16
        y_min = np.nonzero(image_bbox)[1].min()-16
        y_max = np.nonzero(image_bbox)[1].max()+16
        if x_min < 0:
            x_min = 0
        if y_min < 0:
            y_min = 0
        if z_min < 0:
            z_min = 0
        if x_max > image_bbox.shape[0]:
            x_max = image_bbox.shape[0]
        if y_max > image_bbox.shape[1]:
            y_max = image_bbox.shape[1]
        if z_max > image_bbox.shape[2]:
            z_max = image_bbox.shape[2]
        for z in range(z_min, z_max+1):
            slice_image = bin_label[x_min:x_max,
                                  y_min:y_max, z]
            # 使用膨胀操作扩大物体边界，然后与原始图像相减，提取边缘
            kernel = np.ones((4, 4), np.uint8)  # 使用3x3的结构元素
            dilated = cv2.dilate(slice_image, kernel, iterations=1)
            edges = cv2.subtract(dilated, slice_image)
            multi_db[x_min:x_max,y_min:y_max,z][edges == 1] = tooth_id
            #if z %5 == 0:
               # print("the slice id : "+str(z))
    data = nib.Nifti1Image(multi_db[:, :, :], original_affine)
    nib.save(data, os.path.join(
             "/data1/LJX/stage_v1/" + 'bd/' + data_path[(path_pos_2 + 1):path_pos_3] + '_bd_gt.nii.gz'))

