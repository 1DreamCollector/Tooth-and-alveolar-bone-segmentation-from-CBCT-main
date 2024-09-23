import os

# 文件夹路径
folder_path = r'/data1/LJX/stage_v1/bd/'
# 输出文件路径
output_file_path = r'/data1/LJX/stage_v1/bd.txt'

# 打开输出文件用于写入
with open(output_file_path, 'w') as file:
    # 遍历文件夹内的所有文件
    for filename in os.listdir(folder_path):
        # 构建完整的文件路径
        file_path = os.path.join(folder_path, filename)
        # 检查是否为文件，避免列出子目录
        if os.path.isfile(file_path):
            # 写入文件路径并换行
            file.write(file_path + '\n')

print("文件路径已保存至:", output_file_path)