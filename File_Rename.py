import os 
import shutil
import re
#'C:\Users\kristhim\Desktop\thimma\demorepo\pdf
file_path =r'C:\\Users\\kristhim\\Desktop\\thimma\\git\\os_deploy\\Python\\os_reinstall'
def filesearch(path):
    # destination = r'C:\Users\kristhim\Desktop\junkdoc'
    # if not os.path.exists(destination):
    #     os.mkdir(destination)
    #pattern = re.compile('.pdf|docx|doc')
    for root,dir, files in os.walk(path):     
        for file in files:
            if str(file).endswith('.pyc_dis'):
            	#print(os.path.join(root,file))
            	#print("{}.py".format(str(file).split(".")[0]))
            	os.rename(os.path.join(root,file),os.path.join(root,"{}.py".format(str(file).split(".")[0])))
            elif str(file).endswith('.pyc'):
            	#print(os.path.join(root,file))
            	#print(file)
            	os.remove(os.path.join(root,file))
           
if __name__ == '__main__':
    filesearch(file_path)