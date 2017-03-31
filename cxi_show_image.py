#!/usr/bin/python
import matplotlib.pyplot as plt
import cxi_lib
import sys
import cPickle as pickle
import numpy as np


def main():

    file_data, entries_data = cxi_lib.processH5File(sys.argv[1],1)

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

        print '\nEntry %d information:'%idx
        max_len = len(max(ed.keys(), key=len))
        for k in sorted(ed.keys()):
            if k.find('image_') < 0 and k.find('mask_') < 0:
                print k.ljust(max_len),'=', str(ed[k]).strip()
            elif k.find('image_') >= 0:
                images.append(ed[k])

    image_num = len(images)

    fig = plt.figure()

    for i in range(image_num):
        a = fig.add_subplot(1,image_num,i+1)
        plot = plt.imshow(cxi_lib.ungzipImage(images[i]), interpolation='nearest')
        a.set_title('Image %d'%(i+1))
        plt.colorbar()

    plt.show()


if __name__ == '__main__':
    main()
