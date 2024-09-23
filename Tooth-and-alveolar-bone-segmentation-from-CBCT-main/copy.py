#!/usr/bin/env python
# coding=utf-8
'''
@Author ： LiJunXiong
@Institute : cumt
@Project :
@Data :
'''
import os
import shutil


def copy_structure_and_nii_only(source_dir, target_dir):
    # 创建目标目录结构
    if not os.path.exists(target_dir):
        os.makedirs(target_dir)

    # 遍历原始目录
    for root, dirs, files in os.walk(source_dir):
        # 构建目标路径
        target_root = root.replace(source_dir, target_dir, 1)
        count = target_root.count("\\")
        if not os.path.exists(target_root) and count <= 3:
            os.makedirs(target_root)

        # 复制 .nii.gz 文件
        for file in files:
            if file.endswith('.nii.gz'):
                source_file = os.path.join(root, file)
                target_file = os.path.join(target_root, file)
                shutil.copyfile(source_file, target_file)

    print(f"复制结构和 .nii.gz 文件完成。目标目录：{target_dir}")


if __name__ == "__main__":
    source_dir = r'Z:\DataCT\LabeledData\003'
    target_dir = r'D:\smileLink\CTdata'

    copy_structure_and_nii_only(source_dir, target_dir)
