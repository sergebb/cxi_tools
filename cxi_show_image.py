#!/usr/bin/python
import matplotlib.pyplot as plt
from matplotlib.colors import LogNorm 
import cxi_lib
import sys
import cPickle as pickle
import numpy as np


def main():

    file_data, entries_data, image_iters = cxi_lib.processH5File(sys.argv[1],1)

    #Output file data
    print 'CXI File information:'
    max_len = len(max(file_data.keys(), key=len))
    for k in file_data.keys():
        print k.ljust(max_len),'=', str(file_data[k]).strip()

    #Output entries
    images = []
    for idx,ed in enumerate(entries_data):
        if ed is None:
            continue

    total_len = sum([i.GetLen() for i in image_iters])
    print 'Total len =', total_len
    image_num = min(total_len, 5)

    images = []
    for it in image_iters:
        for img in it:
            images.append(img)
            if len(images) >= image_num:
                break

        if len(images) >= image_num:
            break

    fig = plt.figure()

    for i in range(len(images)):
        img = images[i]
        img[img<0] = 0
        a = fig.add_subplot(1,image_num,i+1)
        plot = plt.imshow(img+1, interpolation='nearest',norm=LogNorm(vmin=1,vmax=np.amax(img)))
        a.set_title('Image %d'%(i+1))
        plt.colorbar()

    plt.show()


if __name__ == '__main__':
    main()
