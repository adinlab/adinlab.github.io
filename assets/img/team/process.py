import os
from PIL import Image

WIDTH = 170
HEIGHT = 200

def resize_image(path, output_path):
    # open image
    try:
        img = Image.open(path).convert('RGBA')
    except:
        img = Image.open(path).convert('RGB')
        new_img = Image.new('RGBA', img.size, (0, 0, 0, 0))
        new_img.paste(img, (0, 0), img)
        img = new_img

    # convert image to WIDTH x HEIGHT ratio by adding white space
    # get ratio
    w, h = img.size
    print(w, h, end=" to ")
    if w > h:
        new_h = int((w / WIDTH * HEIGHT))
        # create new image
        new_img = Image.new('RGBA', (w, new_h), (0, 0, 0, 0))
        # paste image
        new_img.paste(img, (0, int((new_h - h) / 2)))
        img = new_img
    else:
        new_w = int(w / WIDTH * HEIGHT)
        # create new image
        new_img = Image.new('RGBA', (new_w, h), (0, 0, 0, 0))
        # paste image
        new_img.paste(img, (int((new_w - w) / 2), 0))
        img = new_img

    w, h = img.size
    print(w, h)
    # save image
    img.save(f"{output_path}.png")
    

for file in os.listdir('row/'):
    try:
        print("resizing %s" % file, end="... ")
        resize_image(f"row/{file}", f"./{file}")
    except Exception as e:
        print("error resizing %s: %s" % (file, e))
        
