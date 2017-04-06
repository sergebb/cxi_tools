#!/usr/bin/python
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
        sys.stderr.write("\r%3d%% (%d/%d), extracted %d images" % (int((idx+1)*100/len(cxi_files)), idx, len(cxi_files), image_count))
        _, entries_data = cxi_lib.processH5File(cf)

        images = []
        for idx,ed in enumerate(entries_data):
            if ed is None:
                continue
            for k in ed.keys():
                if k.find('image_') >= 0 and k.find('/') < 0:
                    images.append(cxi_lib.ungzipImage(ed[k]))

        if len(images) > 1:
            for inum,img in enumerate(images):
                npyname = '%s/%s_%04d'%(dirname,os.path.splitext(os.path.basename(cf))[0],(inum+1))
                np.save(npyname, img)
        elif len(images) == 1:
            npyname = '%s/%s'%(dirname,os.path.splitext(os.path.basename(cf))[0])
            np.save(npyname, images[0])

        image_count += len(images)

    sys.stderr.write("\r%3d%% (%d/%d), extracted %d images\n" % (100, len(cxi_files), len(cxi_files), image_count))

if __name__ == '__main__':
    main()
