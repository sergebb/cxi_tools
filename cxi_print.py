#!/usr/bin/env python
# coding: utf-8
import h5py
import sys

def printBranch(group, prepend):
    for i,g in enumerate(group.keys()):
        if i < len(group.keys())-1:
            #not last
            connection = '  ├─'
            next_prepend = prepend + '   │'
        else:
            connection = '  └─'
            next_prepend = prepend + '    '
        print prepend, connection, g,

        el = group.get(g, getlink=True)
        if(isinstance(el,h5py.SoftLink)):
            print '-->', el.path
        else:
            print ''

        if(isinstance(group[g],h5py.Group)):
            printBranch(group[g],next_prepend)
            print next_prepend


def main():
    f = h5py.File(sys.argv[1], "r")
    printBranch(f,'')

if __name__ == '__main__':
    main()