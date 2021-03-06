#!/usr/bin/env python

import os
import sys
from optparse import OptionParser
import numpy as np
import cxi_lib
import cxidb25_gap


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
    iskip = 0
    for idx, cxi_file in enumerate(cxi_files):
        _, _, image_iters = cxi_lib.processH5File(cxi_file)

        # total_len = sum([i.GetLen() for i in image_iters])

        inum = 0
        for img_iter in image_iters:
            for img in img_iter:
                sys.stderr.write("\r%3d%% (%d/%d), extracted %d images, skipped %d images" % \
                 (int((idx)*100/len(cxi_files)), idx, len(cxi_files), image_count + inum, iskip))

                clipped_img = np.clip(img, 0, np.amax(img))

                if (threshold > 0) and (np.sum(clipped_img) < threshold):
                    if bg_reduction:
                        # background_data.append(img)
                        # if len(background_data) > 100:
                        #     background_data.pop(0)
                        if background_data is None:
                            background_data = clipped_img
                        else:
                            try:
                                stack = np.stack([clipped_img, background_data])
                                background_data = np.average(stack, \
                                                            weights=[1, background_counter], axis=0)
                            except ValueError:
                                iskip += 1
                                continue
                            # background_data = np.amax(stack, axis=0)
                        background_counter = min(background_counter+1, 100)
                    iskip += 1
                else:
                    npyname = '%s/%s_%04d'%(dirname, \
                                            os.path.splitext(os.path.basename(cxi_file))[0], \
                                            (inum+1))
                    if bg_reduction:
                        if background_data is not None:
                            try:
                                clipped_img = np.subtract(clipped_img, background_data)
                                clipped_img -= cxi_lib.compute_noise_level(clipped_img)
                                clipped_img[clipped_img < 0] = 0
                                clipped_img[img < -100] = -10000
                                clipped_img[background_data > 100] = -10000
                            except ValueError:
                                pass
                        else:
                            clipped_img -= cxi_lib.compute_noise_level(clipped_img)
                            clipped_img[clipped_img < 0] = 0
                            clipped_img[img < -100] = -10000

                        img = clipped_img

                    # img = cxidb25_gap.RecoverGap(img, 20, -5)
                    np.save(npyname, img)
                    inum += 1

        image_count += inum

    sys.stderr.write("\r%3d%% (%d/%d), extracted %d images, skipped %d images\n" % \
                     (100, len(cxi_files), len(cxi_files), image_count, iskip))

if __name__ == '__main__':
    main()
