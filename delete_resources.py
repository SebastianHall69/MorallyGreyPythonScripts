import os
import shutil


path = os.path.abspath('.')

print(f"starting in {path}")
for file in os.listdir(path):
    if(os.path.isdir(os.path.join(path, file))):
        resource_dir = os.path.join(path, file, '_resources')
        if os.path.exists(resource_dir):
            print(f"removing: {resource_dir}")
            shutil.rmtree(resource_dir)
        else:
            print(f"DOES NOT EXIST: {resource_dir}")
