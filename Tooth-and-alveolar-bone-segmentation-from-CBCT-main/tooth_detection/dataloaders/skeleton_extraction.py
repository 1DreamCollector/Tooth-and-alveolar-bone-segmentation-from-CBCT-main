import os
import re
import nibabel as nib
import numpy as np
from scipy import ndimage
from skimage.morphology import skeletonize_3d


def data_load():
    with open("/data1/LJX/001/label_file_polish.txt", 'r') as f:
        image_list = f.readlines()
    image_list = [item.replace('\n','') for item in image_list]
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
    multi_skeleton = np.zeros(label.shape)
    for label_id in range(len(teeth_ids)):
        print('the tooth id:', label_id)
        tooth_id = teeth_ids[label_id]
        if tooth_id == 0:
            continue
        bin_label = (label == tooth_id).astype(np.uint8)
        if bin_label.sum() < 500:
            print('fine one label: %d, and the num is: %d', tooth_id, bin_label.sum())
            continue
        x_min = np.nonzero(bin_label)[0].min()
        x_max = np.nonzero(bin_label)[0].max()
        y_min = np.nonzero(bin_label)[1].min()
        y_max = np.nonzero(bin_label)[1].max()
        z_min = np.nonzero(bin_label)[2].min()
        z_max = np.nonzero(bin_label)[2].max()
        skeleton = skeletonize_3d(bin_label[x_min:x_max, y_min:y_max, z_min:z_max])
        #skeleton = ndimage.grey_dilation(skeleton, size= (5, 5, 5))
        multi_skeleton[x_min:x_max, y_min:y_max, z_min:z_max][skeleton == 1] = tooth_id
    data = nib.Nifti1Image(multi_skeleton[:, :, :], original_affine)
    nib.save(data, os.path.join( "/data1/LJX/stage_v1/" + 'skl/' + data_path[(path_pos_2+1):path_pos_3] + '_skl_gt.nii.gz'))

