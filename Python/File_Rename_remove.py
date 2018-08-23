import os 
import shutil
import re
file_path =r'C:\\Users\\kristhim\\Desktop\\thimma\\git\\os_deploy\\Python\\os_reinstall'
def filesearch(path):
    for root,dir, files in os.walk(path):   
        for file in files:
            if str(file).endswith('.pyc_dis'):
                os.rename(os.path.join(root,file),os.path.join(root,"{}.py".format(str(file).split(".")[0])))
            elif str(file).endswith('.pyc'):
                os.remove(os.path.join(root,file))        

if __name__ == '__main__':
    filesearch(file_path)