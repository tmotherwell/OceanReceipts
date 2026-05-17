import os

path = "D:\Downloads\pokemon season 5 Master Quest 212-276 Episods Salman Sk Silver RG"
arr = os.listdir(path)
for oldfilename in arr:
    newfilename = oldfilename.split("_-_")
    newfilename[1] = int(newfilename[1])-2
    newfilename[1] = str(newfilename[1])
    newfilename = ' '.join(newfilename)
    print(newfilename)
    oldfile = os.path.join(path, oldfilename)
    newfile = os.path.join(path, newfilename)
    os.rename(oldfile,newfile)

