import os
import torch.nn as nn
import re
import argparse
import torch
import nibabel as nib
import numpy as np
from skimage import morphology
from cnt_skl_dect import cnt_skl_detection
from roi_dect import roi_detection
from ins_tooth_seg import ins_tooth_seg
#net-roi
from networks.vnet_roi import VNet_roi
#net-cnt,net-skl
from networks.vnet import VNet
#ins-net
from networks.vnet_ins_seg import VNet_singleTooth


parser = argparse.ArgumentParser()
parser.add_argument('--gpu', type=str,  default='0, 1, 2, 3', help='GPU to use')
FLAGS = parser.parse_args()

os.environ['CUDA_VISIBLE_DEVICES'] = FLAGS.gpu

num_classes = 2

with open("/data1/LJX/001/img_file_polish.txt", 'r') as f:
    image_list = f.readlines()
image_list = [item.replace('\n','') for item in image_list]


def read_data(data_patch):
    src_data_file = os.path.join(data_patch)
    src_data_vol = nib.load(src_data_file)
    image = src_data_vol.get_fdata()
    w, h, d = image.shape
    spacing = src_data_vol.header['pixdim'][1:4]
    image = label_rescale(image, w*(spacing[0]/0.2), h*(spacing[0]/0.2), d*(spacing[0]/0.2), 'nearest')
    if image[image > -1000].mean() < -100:
        intensity_scale = (-60 + 1000) / (image[image > -1000].mean() + 1000)
        image = (image + 1000) * intensity_scale - 1000
    image[image < 500] = 500
    image[image > 2500] = 2500
    image = (image - 500)/(2500 - 500)
    low_bound = np.percentile(image, 5)
    up_bound = np.percentile(image, 99.9)
    return image, low_bound, up_bound, w, h, d

def initialize_weights(m):
    if isinstance(m, (nn.Conv2d, nn.ConvTranspose2d)):
        nn.init.kaiming_normal_(m.weight, mode='fan_out', nonlinearity='relu')
        if m.bias is not None:
            nn.init.constant_(m.bias, 0)
    elif isinstance(m, (nn.BatchNorm2d, nn.InstanceNorm2d)):
        nn.init.constant_(m.weight, 1)
        nn.init.constant_(m.bias, 0)

def load_model():
    net_roi = VNet_roi(n_channels=1, n_classes=2, normalization='batchnorm', has_dropout=False).cuda(0)
    save_mode_path = os.path.join(r'/data1/LJX/Tooth-and-alveolar-bone-segmentation-from-CBCT-main/roi_localization/model/iter_3000.pth')
    net_roi.load_state_dict(torch.load(save_mode_path))
    print("init weight from {}".format(save_mode_path))
    net_roi.eval()

    net_cnt = VNet(n_channels=1, n_classes=3, normalization='batchnorm', has_dropout=True).cuda(1)
    net_skl = VNet(n_channels=1, n_classes=3, normalization='batchnorm', has_dropout=True).cuda(1)
    # load model of cnt
    save_mode_path = os.path.join(r"/data1/LJX/Tooth-and-alveolar-bone-segmentation-from-CBCT-main/model/NC_1st_stage_cntV2_HZ_02_(1000data_256size_intensityClip)/ours_transformer/iter_13000.pth")
    net_cnt.load_state_dict(torch.load(save_mode_path))
    print("init weight from {}".format(save_mode_path))
    net_cnt.eval()

    # load model of skl
    save_mode_path = os.path.join(r"/data1/LJX/Tooth-and-alveolar-bone-segmentation-from-CBCT-main/model/NC_1st_stage_sklV2_HZ_02_(1000data_256size_intensityClip)/ours_transformer/iter_1000.pth")
    net_skl.load_state_dict(torch.load(save_mode_path))
    print("init weight from {}".format(save_mode_path))
    net_skl.eval()

    ins_net = VNet_singleTooth(n_channels=2, n_classes=2, normalization='batchnorm', has_dropout=True).cuda(1)
    # save_mode_path = os.path.join('../iter_seg.pth')
    # ins_net.load_state_dict(torch.load(save_mode_path))
    ins_net.apply(initialize_weights)
    ins_net.eval()

    return net_roi, net_cnt, net_skl, ins_net
    #return net_roi


def label_rescale(image_label, w_ori, h_ori, z_ori, flag):
    w_ori, h_ori, z_ori = int(w_ori), int(h_ori), int(z_ori)
    # resize label map (int)
    if flag == 'trilinear':
        teeth_ids = np.unique(image_label)
        image_label_ori = torch.zeros((w_ori, h_ori, z_ori)).cuda(0)
        image_label = torch.from_numpy(image_label).cuda(0)
        for label_id in range(len(teeth_ids)):
            image_label_bn = (image_label == teeth_ids[label_id]).float()
            #image_label_bn = torch.from_numpy(image_label_bn.astype(float))
            image_label_bn = image_label_bn[None, None, :, :, :]
            image_label_bn = torch.nn.functional.interpolate(image_label_bn, size=(w_ori, h_ori, z_ori), mode='trilinear')
            image_label_bn = image_label_bn[0, 0, :, :, :]
            image_label_ori[image_label_bn > 0.5] = teeth_ids[label_id]
        image_label = image_label_ori.cpu().data.numpy()
    
    if flag == 'nearest':
        image_label = torch.from_numpy(image_label).cuda(0)
        image_label = image_label[None, None, :, :, :].float()
        image_label = torch.nn.functional.interpolate(image_label, size=(w_ori, h_ori, z_ori), mode='nearest')
        image_label = image_label[0, 0, :, :, :].cpu().data.numpy()
    return image_label




def img_crop(image_bbox):
    image_bbox = morphology.remove_small_objects(image_bbox.astype(bool), 2500, connectivity=3).astype(int)
    if image_bbox.sum() > 0:
        #if None:
        x_min = np.nonzero(image_bbox)[0].min()-32
        x_max = np.nonzero(image_bbox)[0].max()+32
        
        y_min = np.nonzero(image_bbox)[1].min()-16
        y_max = np.nonzero(image_bbox)[1].max()+16

        z_min = np.nonzero(image_bbox)[2].min()-16
        z_max = np.nonzero(image_bbox)[2].max()+16
            
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
    if image_bbox.sum() == 0:
        x_min, x_max, y_min, y_max, z_min, z_max = -1, image_bbox.shape[0], 0, image_bbox.shape[1], 0, image_bbox.shape[2]
    return x_min, x_max, y_min, y_max, z_min, z_max




def inference(image, net_roi, net_cnt, net_skl, ins_net, low_bound, up_bound, w_o, h_o, d_o):
# def inference(image, net_roi, low_bound, up_bound, w_o, h_o, d_o,):
    w, h, d = image.shape
    
    # roi binary segmentation parameters, the input spacing is 0.4 mm
    print('---run the roi binary segmentation.')
    stride_xy = 224
    stride_z = 224
    patch_size_roi_stage = (256, 256, 256)
    with torch.no_grad():
        label_roi = roi_detection(net_roi, image[0:w:2, 0:h:2, 0:d:2], stride_xy, stride_z, patch_size_roi_stage)
    # affine = np.eye(4)  # 4x4的单位矩阵
    # nifti_image = nib.Nifti1Image(label_roi, affine)
    # # 保存为.nii.gz文件
    # nib.save(nifti_image, 'test.nii.gz')

    label_roi = label_rescale(label_roi, w, h, d, 'trilinear')
    
    # crop image
    x_min, x_max, y_min, y_max, z_min, z_max = img_crop(label_roi)
    if x_min == -1: # non-foreground label
        whole_label = np.zeros((w, h, d))
        return whole_label
    #提取出来感兴趣的区域
    image = image[x_min:x_max, y_min:y_max, z_min:z_max]
    w2, h2, d2 = image.shape
    
    # 1st stage parameters, the input spacing is 0.4 mm
    print('---run the 1st stage network.')
    stride_xy = 64
    stride_z = 64
    patch_size_1st_stage = (128, 128, 128)
    ins_skl_map = cnt_skl_detection(net_cnt, net_skl, image[0:w:2, 0:h:2, 0:d:2], stride_xy, stride_z, patch_size_1st_stage)
    #ins_skl_map = label_rescale(ins_skl_map, w, h, d, 'nearest')


    # 2nd stage parameters, the input spacing is 0.2 mm
    print('---run the 2nd stege network.')
    patch_size = np.array([96, 96, 176])
    teeth_ids = np.unique(ins_skl_map)
    tooth_label = ins_tooth_seg(ins_net, image, ins_skl_map, patch_size)        #
    whole_label = np.zeros((w, h, d))
    whole_label[x_min:x_max, y_min:y_max, z_min:z_max] = tooth_label

    whole_label = label_rescale(whole_label, w_o, h_o, d_o, 'trilinear')
    return whole_label


if __name__ == '__main__':
    net_roi, net_cnt, net_skl, ins_net = load_model()
    #net_roi = load_model()
    for data_id in range(len(image_list)):
        print('**********process the data:', data_id)
        image, low_bound, up_bound, w_o, h_o, d_o = read_data(image_list[data_id])
        tooth_label = inference(image, net_roi, net_cnt, net_skl, ins_net, low_bound, up_bound, w_o, h_o, d_o)
        #tooth_label = inference(image, net_roi, low_bound, up_bound, w_o, h_o, d_o)

        path_pos_0 = [sub_data_path.start() for sub_data_path in re.finditer('/', image_list[data_id])][-3]
        path_pos_1 = [sub_data_path.start() for sub_data_path in re.finditer('/', image_list[data_id])][-2]
        path_pos_2 = [sub_data_path.start() for sub_data_path in re.finditer('/', image_list[data_id])][-1]
        path_pos_3 = [sub_data_path.start() for sub_data_path in re.finditer('.nii.gz', image_list[data_id])][-1]

        nib.save(nib.Nifti1Image(tooth_label.astype(np.float32), np.eye(4)), "../" + image_list[data_id][(path_pos_0+1):path_pos_1] + '_' + image_list[data_id][(path_pos_1+1):path_pos_2] + '_' + image_list[data_id][(path_pos_2+1):path_pos_3] + ".nii.gz")

    #print(metric)
