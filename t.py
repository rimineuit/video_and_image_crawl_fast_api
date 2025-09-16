import gdown
import os
def download_folder_and_rename(id: str, img_dir='./image'):
    gdown.download_folder(id)
    def rename_file_in_folder(img_dir=img_dir):
        for f in os.listdir(img_dir):
            os.rename(os.path.join(img_dir, f), os.path.join(img_dir, f"{f}.png"))
    
    rename_file_in_folder(img_dir)
    
id = '1Cpb31dJSmGcrCnt7hdz3HW4wxFJvw2uS'

download_folder_and_rename(id)