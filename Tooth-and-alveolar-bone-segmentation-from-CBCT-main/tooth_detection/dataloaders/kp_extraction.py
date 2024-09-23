import nibabel as nib
import numpy as np
import re
import open3d as o3d
from sklearn.cluster import DBSCAN
import os
from scipy.spatial.distance import euclidean
from skimage.measure import marching_cubes
def calculate_curvature(point_prev, point, point_next):
    dx1 = point[0] - point_prev[0]
    dy1 = point[1] - point_prev[1]
    dz1 = point[2] - point_prev[2]
    dx2 = point_next[0] - point[0]
    dy2 = point_next[1] - point[1]
    dz2 = point_next[2] - point[2]
    curvature = 2 * ((dx1*dy2 - dy1*dx2 + dx1*dz2 - dz1*dx2 + dy1*dz2 - dz1*dy2) /
                     (euclidean(point_prev, point)**2 + euclidean(point, point_next)**2 + 1e-6))
    return abs(curvature)


def find_and_save_apex_point_from_annotations(input_nii_path, annotations):
    """
    假设annotations是一个列表，包含了标注的轮廓点。
    每个点是一个三维坐标，例如[(x1, y1, z1), (x2, y2, z2), ...]
    """
    # 读取原始CT图像
    path_pos_0 = [sub_data_path.start() for sub_data_path in re.finditer('/', input_nii_path)][-3]
    path_pos_1 = [sub_data_path.start() for sub_data_path in re.finditer('/', input_nii_path)][-2]
    path_pos_2 = [sub_data_path.start() for sub_data_path in re.finditer('/', input_nii_path)][-1]
    path_pos_3 = [sub_data_path.start() for sub_data_path in re.finditer('.nii.gz', input_nii_path)][-1]
    img = nib.load(input_nii_path)
    original_affine = img.affine  # 保存原始的affine矩阵
    img = img.get_fdata()

    annotations = nib.load(annotations)
    annotations = annotations.get_fdata()

    teeth_ids = np.unique(annotations)
    multi_kp = np.zeros(annotations.shape)
    #

    for label_id in range(len(teeth_ids)):
        print('the tooth id:', label_id)
        tooth_id = teeth_ids[label_id]
        if tooth_id == 0:
            continue
        apex_points = []
        #提取出来的单颗牙齿，二值化
        bin_label = (annotations == tooth_id).astype(np.uint8)
        z_min = np.nonzero(bin_label)[2].min() - 3
        z_max = np.nonzero(bin_label)[2].max() + 3
        x_min = np.nonzero(bin_label)[0].min() - 16
        x_max = np.nonzero(bin_label)[0].max() + 16
        y_min = np.nonzero(bin_label)[1].min() - 16
        y_max = np.nonzero(bin_label)[1].max() + 16
        verts, _,_,_ = marching_cubes(bin_label, level=0.5)
        voxel_teeth = verts.astype(int)   #单颗牙齿边缘的点云
        if voxel_teeth.sum() < 500:
            print('fine one label: %d, and the num is: %d', tooth_id, voxel_teeth.sum())
            continue

        # 将点集首尾相连
        contour_with_loop = np.concatenate((voxel_teeth, [voxel_teeth[0]]))

        # 计算曲率并识别根尖点
        curvatures = np.array([calculate_curvature(contour_with_loop[i - 1], contour_with_loop[i], contour_with_loop[i + 1])
                      for i in range(1, len(contour_with_loop)-1 )])

        # 设置曲率阈值和DBSCAN参数
        curvature_threshold = 0.05
        eps = 2
        min_samples = 5

        # 筛选高曲率点
        high_curvature_points = verts[1:][curvatures > curvature_threshold]

        # 使用DBSCAN聚类识别根尖点
        if len(high_curvature_points) > 0:
            db = DBSCAN(eps=eps, min_samples=min_samples).fit(high_curvature_points)
            unique_labels = set(db.labels_) - {-1}  # 排除噪声点


            for label in unique_labels:
                cluster_points = high_curvature_points[db.labels_ == label]
                avg_point = cluster_points.mean(axis=0)
                apex_points.append(avg_point)
        else:
            print(f"No apex points found for tooth {tooth_id}.")

        for apex_point in apex_points:
            multi_kp[int(apex_point[0])-1:int(apex_point[0])+2, int(apex_point[1])-1:int(apex_point[1])+2, int(apex_point[2])-1:int(apex_point[2])+2] = tooth_id

    # 保存关键点为新的nii.gz文件
    output_nii = nib.Nifti1Image(multi_kp, affine=original_affine)
    nib.save(output_nii, os.path.join(
        input_nii_path[:(path_pos_0 + 1)] + 'stage_v1/kp/' + input_nii_path[(path_pos_2 + 1):path_pos_3] + '_kp_gt.nii.gz'))

if __name__ == "__main__":
    with open("/data1/LJX/stage_v1/bd.txt", 'r') as f:
        bd_list = f.readlines()
    bd_list = [item.replace('\n', '') for item in bd_list]

    with open("/data1/LJX/001/label_file_polish.txt", 'r') as f:
        label_list = f.readlines()
    label_list = [item.replace('\n', '') for item in label_list]

    for data_id in range(len(label_list)):
        find_and_save_apex_point_from_annotations(label_list[data_id], bd_list[data_id])
