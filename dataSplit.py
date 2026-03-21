import os
import random
import shutil

source = "data/images/all"
train_dir = "data/images/train"
val_dir = "data/images/val"
test_dir = "data/images/test"

os.makedirs(train_dir, exist_ok=True)
os.makedirs(val_dir, exist_ok=True)
os.makedirs(test_dir, exist_ok=True)

images = os.listdir(source)
random.shuffle(images)

train_split = int(0.7 * len(images))
val_split = int(0.9 * len(images))

for i, img in enumerate(images):
    src = os.path.join(source, img)

    if i < train_split:
        dst = os.path.join(train_dir, img)
    elif i < val_split:
        dst = os.path.join(val_dir, img)
    else:
        dst = os.path.join(test_dir, img)

    shutil.copy(src, dst)

print("Dataset split complete.")