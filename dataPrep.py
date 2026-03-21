import os
import shutil

source_root = "E:/Downloads/Car Dashboard dataset/train"
target_root = "data/images/all"

os.makedirs(target_root, exist_ok=True)

counter = 0

for folder in os.listdir(source_root):
    folder_path = os.path.join(source_root, folder)
    
    if os.path.isdir(folder_path):
        for img in os.listdir(folder_path):
            src = os.path.join(folder_path, img)
            dst = os.path.join(target_root, f"dashboard_{counter}.jpg")
            shutil.copy(src, dst)
            counter += 1

print(f"Total images copied: {counter}")