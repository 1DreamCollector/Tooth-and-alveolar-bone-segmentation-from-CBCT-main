from networks.vnet import VNet
import torch
import os
import nibabel as nib
import numpy as np
from roi_dect import roi_detection
from networks.vnet_roi import VNet_roi
def load_model():
    net_roi = VNet_roi(n_channels=1, n_classes=2, normalization='batchnorm', has_dropout=False).cuda(0)
    save_mode_path = os.path.join(r'/data1/LJX/Tooth-and-alveolar-bone-segmentation-from-CBCT-main/roi_localization/model/iter_3000.pth')
    net_roi.load_state_dict(torch.load(save_mode_path))
    print("init weight from {}".format(save_mode_path))
    net_roi.eval()
    return net_roi

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
def label_rescale(image_label, w_ori, h_ori, z_ori, flag):
    w_ori, h_ori, z_ori = int(w_ori), int(h_ori), int(z_ori)
    # resize label map (int)
    if flag == 'trilinear':
        teeth_ids = np.unique(image_label)
        image_label_ori = torch.zeros((w_ori, h_ori, z_ori)).cuda(0)
        image_label = torch.from_numpy(image_label).cuda(0)
        for label_id in range(len(teeth_ids)):
            image_label_bn = (image_label == teeth_ids[label_id]).float()
            # image_label_bn = torch.from_numpy(image_label_bn.astype(float))
            image_label_bn = image_label_bn[None, None, :, :, :]
            image_label_bn = torch.nn.functional.interpolate(image_label_bn, size=(w_ori, h_ori, z_ori),
                                                             mode='trilinear')
            image_label_bn = image_label_bn[0, 0, :, :, :]
            image_label_ori[image_label_bn > 0.5] = teeth_ids[label_id]
        image_label = image_label_ori.cpu().data.numpy()

    if flag == 'nearest':
        image_label = torch.from_numpy(image_label).cuda(0)
        image_label = image_label[None, None, :, :, :].float()
        image_label = torch.nn.functional.interpolate(image_label, size=(w_ori, h_ori, z_ori), mode='nearest')
        image_label = image_label[0, 0, :, :, :].cpu().data.numpy()
    return image_label
def inference(image, net_roi, low_bound, up_bound, w_o, h_o, d_o, ):
    w, h, d = image.shape

    # roi binary segmentation parameters, the input spacing is 0.4 mm
    print('---run the roi binary segmentation.')
    stride_xy = 224
    stride_z = 224
    patch_size_roi_stage = (256, 256, 256)
    label_roi = roi_detection(net_roi, image[0:w:2, 0:h:2, 0:d:2], stride_xy, stride_z, patch_size_roi_stage)
    return label_roi


if __name__ == '__main__':
    _base_dir = r"/data1/LJX/001/"
    directory1 = os.path.join(_base_dir, "img")
    for root1, dirs, files in os.walk(directory1):
        image_list = [os.path.join(root1, name) for name in files]
    image_list = [item.replace('\n', '') for item in image_list]
    net_roi = load_model()

    for data_id in range(len(image_list)):
        print('**********process the data:', data_id)
        image, low_bound, up_bound, w_o, h_o, d_o = read_data(image_list[data_id])
        tooth_label = inference(image, net_roi, low_bound, up_bound, w_o, h_o, d_o)
        affine = np.eye(4)  # 4x4的单位矩阵
        nifti_image = nib.Nifti1Image(tooth_label.astype(np.int32), affine)
        # 保存为.nii.gz文件
        filename = image_list[data_id]
        filename = os.path.basename(filename)
        save_path = os.path.join("/data1/LJX/reference_tooth_stage1/", filename)
        nib.save(nifti_image, save_path)
