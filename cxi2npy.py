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

    (parsed_options, parsed_args) = parser.parse_args()


    if not parsed_options.output:
        dirname = '.'
    else:
        dirname = parsed_options.output
    if not os.path.exists(dirname):
        os.makedirs(dirname)

    cxi_files = parsed_args

    for cf in cxi_files:
        filetype = cf.split('.')[-1]
        if not os.path.isfile(cf) or filetype != 'cxi':
            cxi_files.pop(cf)

    sys.stderr.write('Selected %d files\n'%len(cxi_files))

    image_count = 0
    for idx,cf in enumerate(cxi_files):
        _, _, image_iters = cxi_lib.processH5File(cf)

        total_len = sum([i.GetLen() for i in image_iters])

        inum = 0
        for it in image_iters:
            for img in it:
                sys.stderr.write("\r%3d%% (%d/%d), extracted %d images" % (int((idx)*100/len(cxi_files)), idx, len(cxi_files), image_count + inum - 1))
                npyname = '%s/%s_%04d'%(dirname,os.path.splitext(os.path.basename(cf))[0],(inum + 1))
                np.save(npyname, img)
                inum += 1

        image_count += inum

    sys.stderr.write("\r%3d%% (%d/%d), extracted %d images\n" % (100, len(cxi_files), len(cxi_files), image_count))

if __name__ == '__main__':
    main()
