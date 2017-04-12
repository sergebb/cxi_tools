#!/usr/bin/env python
import os
import sys
import numpy as np
import cxi_lib
from optparse import OptionParser


def main():
    usage = "usage: %prog [options] cxi_files"
    parser = OptionParser(usage=usage)
    parser.add_option("-o", "--output", dest="output",
                      help="output directory", metavar="DIR")
    parser.add_option("-t", "--thresh", dest="thresh",
                      help="Threshold number of photons per images", type='int',
                      metavar="VALUE", default=0)
    parser.add_option("-r", action="store_true", dest="reduct",
                      help="Background reduction", default=False)

    (parsed_options, parsed_args) = parser.parse_args()


    if not parsed_options.output:
        dirname = '.'
    else:
        dirname = parsed_options.output
    if not os.path.exists(dirname):
        os.makedirs(dirname)

    threshold = parsed_options.thresh
    bg_reduction = parsed_options.reduct
    cxi_files = parsed_args

    for cf in cxi_files:
        filetype = cf.split('.')[-1]
        if not os.path.isfile(cf) or filetype != 'cxi':
            cxi_files.pop(cf)

    sys.stderr.write('Selected %d files\n'%len(cxi_files))

    background_data = None
    background_counter = 0

    image_count = 0
    for idx,cf in enumerate(cxi_files):
        _, _, image_iters = cxi_lib.processH5File(cf)

        total_len = sum([i.GetLen() for i in image_iters])

        inum = 0
        iskip = 0
        for it in image_iters:
            for img in it:
                sys.stderr.write("\r%3d%% (%d/%d), extracted %d images, skipped %d images" % (int((idx)*100/len(cxi_files)), idx, len(cxi_files), image_count + inum, iskip + 1))
                if threshold > 0 and np.sum(img) < threshold:
                    if bg_reduction:
                        if background_data is None:
                            background_data = img
                        else:
                            stack = np.stack([img,background_data])
                            background_data = np.average(stack, weights=[1,background_counter], axis=0)
                        background_counter = min(background_counter+1, 100)
                    iskip += 1
                else:
                    npyname = '%s/%s_%04d'%(dirname,os.path.splitext(os.path.basename(cf))[0],(inum + 1))
                    if bg_reduction and background_data is not None:
                        img = np.subtract(img,background_data)
                        img[img<0] = 0
                    np.save(npyname, img)
                    inum += 1

        image_count += inum

    sys.stderr.write("\r%3d%% (%d/%d), extracted %d images\n" % (100, len(cxi_files), len(cxi_files), image_count))

if __name__ == '__main__':
    main()
