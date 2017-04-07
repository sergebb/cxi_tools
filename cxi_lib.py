#!/usr/bin/python
import h5py
import sys
import io
import numpy as np
import math
import zlib

# convert data from 2 pnCCD panels into 2d image
def combinePnCCDHalves(top_half, bottom_half, verbose = 0):
    top_half_data = top_half['data'][:]
    bottom_half_data = bottom_half['data'][:]

    x_pixel_size = top_half['x_pixel_size'][()]
    y_pixel_size = top_half['y_pixel_size'][()]
    x_pixel_size_bottom = bottom_half['x_pixel_size'][()]
    y_pixel_size_bottom = bottom_half['y_pixel_size'][()]

    if x_pixel_size != x_pixel_size_bottom or y_pixel_size != y_pixel_size_bottom:
        if verbose: sys.stderr.write('Error: Panels with different pixel size\n')
        return None

    top_corner_pos = None
    bottom_corner_pos = None
    if 'corner_position' in top_half:
        top_corner_pos = top_half['corner_position'][()]
        bottom_corner_pos = bottom_half['corner_position'][()]
    else:
        if verbose: sys.stderr.write('Error: Unknown panel position\n')
        return None

    res_y,res_x = top_half_data.shape
    x = range(res_x)
    y = range(res_y)
    xx, yy = np.meshgrid(x,y)

    x_coord = np.zeros(res_x*res_y*2).reshape(res_y*2,res_x)
    y_coord = np.zeros(res_x*res_y*2).reshape(res_y*2,res_x)
    values = np.zeros(res_x*res_y*2).reshape(res_y*2,res_x)

    x_coord[:res_y,:] = xx*x_pixel_size + top_corner_pos[0]
    y_coord[:res_y,:] = top_corner_pos[1] - yy*y_pixel_size
    values[:res_y,:] = top_half_data

    x_coord[res_y:,:] = xx*x_pixel_size + bottom_corner_pos[0]
    y_coord[res_y:,:] = bottom_corner_pos[1] - yy*y_pixel_size
    values[res_y:,:] = bottom_half_data

    x_coord = x_coord.ravel()
    y_coord = y_coord.ravel()
    values = values.ravel()

    res_x = int(math.ceil((np.amax(x_coord) - np.amin(x_coord))/x_pixel_size)) + 1
    res_y = int(math.ceil((np.amax(y_coord) - np.amin(y_coord))/y_pixel_size)) + 1

    if res_x*res_y >= 2e7:
        if verbose: sys.stderr.write('Skip image: Wrong detector size\n')
        # Wrong detector, skipping
        return None

    x_min = np.amin(x_coord)
    y_max = np.amax(y_coord)

    image_data = np.ones(res_x*res_y)*-10000

    x_coord = np.round((x_coord - x_min)/x_pixel_size).astype(int)
    y_coord = np.round((y_max - y_coord)/y_pixel_size).astype(int)

    np.put(image_data, x_coord+res_x*y_coord, values)

    return image_data.reshape(res_y,res_x)

# combine data and mask into 2d image
def extractPnCCDImageData(full_pnCCD, verbose = 0):
    data = full_pnCCD['data'][:]

    if 'mask' in full_pnCCD:
        mask = full_pnCCD['mask'][:]

        if data.shape != mask.shape:
            if verbose: sys.stderr.write('Error: Image and mask have different size\n')
            return None

        data[mask!=0] = -10000

    return data

# remove gaps on the sides
def trimImage(image_data):
    v_max = np.amax(image_data,axis=1)
    h_max = np.amax(image_data,axis=0)

    v_left = np.argmax(v_max>=0)
    v_right = len(v_max) - np.argmax(v_max[::-1]>=0)
    h_left = np.argmax(h_max>=0)
    h_right = len(h_max) - np.argmax(h_max[::-1]>=0)

    return image_data[v_left:v_right,h_left:h_right]

class extractPnCCDImageIter:
    def __init__(self, full_pnCCD_array, verbose = 0):
        self.data_array = full_pnCCD_array
        self.shape = self.data_array['data'].shape
        self.i = 0
        self.n = self.shape[0]

        if self.data_array['data'].shape != self.data_array['mask'].shape:
            if verbose: sys.stderr.write('Error: Image and mask have different size\n')
            self.n = 0

    def __iter__(self):
        # Iterators are iterables too.
        # Adding this functions to make them so.
        return self

    def GetLen(self):
        return self.n

    def next(self):
        if self.i < self.n:
            data = self.data_array['data'][self.i]
            if 'mask' in self.data_array:
                mask = self.data_array['mask'][self.i]
                data[mask<=512] = -10000
            self.i += 1
            return trimImage(data)
        else:
            raise StopIteration()

class entryImagesIter:
    def __init__(self, verbose = 0):
        self.entry_images_data = []
        self.next_start_idx = []
        self.i = 0
        self.n = 0
        self.verbose = verbose

    def __iter__(self):
        # Iterators are iterables too.
        # Adding this functions to make them so.
        return self

    def AddPnCCDhalves(self, top_half, bottom_half):
        self.entry_images_data.append([top_half,bottom_half])
        self.n += 1
        self.next_start_idx.append(self.n)

    def AddSingleImage(self, full_pnCCD):
        self.entry_images_data.append(full_pnCCD)
        self.n += 1
        self.next_start_idx.append(self.n)

    def AddImageArray(self, full_pnCCD_array):
        array_iter = extractPnCCDImageIter(full_pnCCD_array,self.verbose)
        self.entry_images_data.append(array_iter)
        self.n += array_iter.GetLen()
        self.next_start_idx.append(self.n)

    def GetLen(self):
        return self.n

    def next(self):
        while self.i < self.n:
            j = 0
            while self.i >= self.next_start_idx[j]: j += 1 # moving to proper cell in entry_images_data

            # if self.verbose: sys.stderr.write('Read data from cell %d\n'%j)
            if isinstance(self.entry_images_data[j], list) and len(self.entry_images_data[j]) == 2:
                # if self.verbose: sys.stderr.write('PnCCD halves\n')
                image_data = combinePnCCDHalves(self.entry_images_data[j][0],self.entry_images_data[j][1],self.verbose)
            elif isinstance(self.entry_images_data[j], extractPnCCDImageIter):
                # if self.verbose: sys.stderr.write('Image array\n')
                image_data = self.entry_images_data[j].next()
            elif isinstance(self.entry_images_data[j], dict):
                # if self.verbose: sys.stderr.write('Single image\n')
                image_data = trimImage(extractPnCCDImageData(self.entry_images_data[j],self.verbose))
            else:
                sys.stderr.write('Error: Unknown type in entryImagesIter data\n')
                print type(self.entry_images_data[j])

            self.i += 1
            if image_data is not None:
                return image_data
            # else continue

        raise StopIteration()

# Extract intensiry data and panel parameters.
def readPanelData(data_panel):
    data_dict = {}

    for data_name in data_panel.keys():
        data_dict[data_name] = data_panel.get(data_name)

    if 'data' in data_panel.keys():
        data_link = data_panel.get('data',getlink = True)
        if(isinstance(data_link,h5py.SoftLink)):
            link_path = data_link.path
            link_folder_path = link_path[:link_path.rfind('/')]
            link_folder = data_panel.file[link_folder_path]

            for data_name in link_folder.keys():
                data_dict[data_name] = link_folder.get(data_name)
    else:
        return None

    return data_dict

# Extract text data and arrays with len <10 (everything except panels data)
# and save it to dictionary
def extractDataFromGroup(group):
    group_dict = {}
    for g in group.keys():
        if g.find('detector_') >=0:     
            continue
        if(isinstance(group[g],h5py.Group)):
            next_group_dict = extractDataFromGroup(group[g])
            for k in next_group_dict.keys():
                group_dict[g+'/'+k] = next_group_dict[k]
        else:
            group_dict[g]  = prepareDataset(group[g][()])

    return group_dict


def prepareDataset(dataset):
    if type(dataset) == str:
        return dataset
    if len(dataset.ravel()) == 1:
        return np.asscalar(dataset)
    elif len(dataset.ravel()) < 10:
        return dataset
    else:
        return '%s of shape %s' %(type(dataset),str(dataset.shape))

# Read data about 1 images in CXI 
def processEntry(entry, verbose = 0):
    data_panels = []
    data_image = []
    entry_data = {}

    image_iter = entryImagesIter(verbose)

    for group in entry.keys():
        if group.find('data_') >= 0:    # panel data, save for separate processing
            data_panels.append(group)
        elif group.find('image_') >= 0:    # panel data, save for separate processing
            data_image.append(group)
        else:                           # text data, just extract and save to dictionary
            if(isinstance(entry[group],h5py.Group)):
                next_group_dict = extractDataFromGroup(entry[group])
                for k in next_group_dict.keys():
                    entry_data[group+'/'+k] = next_group_dict[k]
            else:
                entry_data[group] = prepareDataset(entry[group][()])

    if len(data_panels) == 0:
        if verbose: sys.stderr.write('Error: No image data in entry\n')
        return None

    panels_dict = []

    for dp in data_panels:
        data_dict = readPanelData(entry[dp])
        if data_dict != None:
            panels_dict.append(data_dict)

    if len(panels_dict) == 0:
        for di in data_image:
            data_dict = readPanelData(entry[di])
            if data_dict != None:
                panels_dict.append(data_dict)

    if len(panels_dict)%2 == 0 and panels_dict[0]['data'].shape == (512,1024):
        if verbose: sys.stderr.write('Entry contain data for pnCCD halves\n')
        for i in range(0,len(data_panels),2):
            image_iter.AddPnCCDhalves(panels_dict[i],panels_dict[i+1])
    else:
        if verbose: sys.stderr.write('Entry contain data for full pnCCD\n')
        for i in range(len(data_panels)):
            data_shape = panels_dict[i]['data'].shape
            if len(data_shape) == 2:
                image_iter.AddSingleImage(panels_dict[i])

            elif len(data_shape) == 3:
                if verbose: sys.stderr.write('Entry contain data for %d images\n'%data_shape[0])
                image_iter.AddImageArray(panels_dict[i])

    return entry_data,image_iter


def processH5File(h5file_path, verbose = 0):
    h5file = h5py.File(h5file_path, "r")
    entries = []
    image_iters = []
    file_data = {}

    for group in h5file.keys(): 
        if group.find('entry_') >= 0:
            entry_data, image_iter = processEntry(h5file[group],verbose)
            entries.append(entry_data) #Process entries
            image_iters.append(image_iter)
        else:                                                   #Just save text data
            if(isinstance(h5file[group],h5py.Group)):
                next_group_dict = extractDataFromGroup(h5file[group])
                for k in next_group_dict.keys():
                    file_data[group+'/'+k] = next_group_dict[k]
            else:
                file_data[group] = prepareDataset(h5file[group][()])

    if verbose: 
        if len(entries) == 0:
            sys.stderr.write('No images in file\n')
        elif len(entries) == 1:
            sys.stderr.write('Found 1 image\n')
        else:
            sys.stderr.write('Found %d images\n'%len(entries))

    return file_data, entries, image_iters

def gzipImage(image_data):
    output = io.BytesIO()
    np.save(output, image_data)
    return zlib.compress(output.getvalue())

def ungzipImage(gzipped_image):
    output = io.BytesIO()
    image_data = np.load(io.BytesIO(zlib.decompress(gzipped_image)))
    return image_data