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
    y_pixel_size = bottom_half['y_pixel_size'][()]
    x_pixel_size_bottom = top_half['x_pixel_size'][()]
    y_pixel_size_bottom = bottom_half['y_pixel_size'][()]

    if x_pixel_size != x_pixel_size_bottom or y_pixel_size != y_pixel_size_bottom:
        if verbose: sys.stderr.write('Error: Panels with different pixel size\n')
        return None, None

    top_corner_pos = None
    bottom_corner_pos = None
    if 'corner_position' in top_half:
        top_corner_pos = top_half['corner_position'][:]
        bottom_corner_pos = bottom_half['corner_position'][()]
    else:
        if verbose: sys.stderr.write('Error: Unknown panel position\n')
        return None, None

    res_y,res_x = top_half_data.shape
    x = range(res_x)
    y = range(res_y)
    xx, yy = np.meshgrid(x,y)

    x_coord_top = xx*x_pixel_size + top_corner_pos[0]
    y_coord_top = top_corner_pos[1] - yy*y_pixel_size

    x_coord_bottom = xx*x_pixel_size + bottom_corner_pos[0]
    y_coord_bottom = bottom_corner_pos[1] - yy*y_pixel_size

    x_coord = np.concatenate((x_coord_top.flatten(),x_coord_bottom.flatten()), axis=0)
    y_coord = np.concatenate((y_coord_top.flatten(),y_coord_bottom.flatten()), axis=0) 
    values = np.concatenate((top_half_data.flatten(),bottom_half_data.flatten()), axis=0)

    res_x = int(math.ceil((np.amax(x_coord) - np.amin(x_coord))/x_pixel_size)) + 1
    res_y = int(math.ceil((np.amax(y_coord) - np.amin(y_coord))/y_pixel_size)) + 1

    if res_x >= 3000 or res_y >= 3000:
        # Wrong detector, skipping
        return None,None

    x_min = np.amin(x_coord)
    y_max = np.amax(y_coord)

    image_data = np.zeros(res_x*res_y) #.reshape(res_y,res_x)
    mask = np.ones(res_x*res_y)*-10000

    x_coord = np.round((x_coord - x_min)/x_pixel_size).astype(int)
    y_coord = np.round((y_max - y_coord)/y_pixel_size).astype(int)

    np.put(image_data, x_coord+res_x*y_coord, values)
    np.put(mask, x_coord+res_x*y_coord, 0)

    return image_data.reshape(res_y,res_x),mask.reshape(res_y,res_x)

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
    if len(dataset.flatten()) == 1:
        return np.asscalar(dataset)
    elif len(dataset.flatten()) < 10:
        return dataset
    else:
        return '%s of shape %s' %(type(dataset),str(dataset.shape))

# Read data about 1 images in CXI 
def processEntry(entry, verbose = 0):
    data_panels = []
    entry_data = {}

    for group in entry.keys():
        if group.find('data_') >= 0:    # panel data, save for separate processing
            data_panels.append(group)
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

    panelsData = []

    for dp in data_panels:
        data_dict = readPanelData(entry[dp])
        panelsData.append(data_dict)

    converted_images = []
    converted_mask = []

    if len(data_panels)%2 == 0:
        sys.stderr.write('Entry contain data for pnCCD halves\n')
        for i in range(0,len(data_panels),2):
            image_data, mask = combinePnCCDHalves(panelsData[i],panelsData[i+1],verbose)
            
            if image_data is not None:
                converted_images.append(image_data)
                converted_mask.append(mask)

    for i in range(len(converted_images)): # Save results of conversion into image_N and mask_N
        entry_data['image_%d'%(i+1)] = gzipImage(converted_images[i])
        entry_data['mask_%d'%(i+1)] = gzipImage(converted_mask[i])

    return entry_data


def processH5File(h5file_path, verbose = 0):
    h5file = h5py.File(h5file_path, "r")
    entries = []
    file_data = {}

    for group in h5file.keys(): 
        if group.find('entry_') >= 0:
            entries.append(processEntry(h5file[group],verbose)) #Process entries
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

    return file_data, entries

def gzipImage(image_data):
    output = io.BytesIO()
    np.save(output, image_data)
    return zlib.compress(output.getvalue())

def ungzipImage(gzipped_image):
    output = io.BytesIO()
    image_data = np.load(io.BytesIO(zlib.decompress(gzipped_image)))
    return image_data