""" Photoprocessor utility functions """

import tempfile
import math

from lib import Image


def img_to_fobj(img, info, **kwargs):
    tmp = tempfile.TemporaryFile()

    # Preserve transparency if the image is in Pallette (P) mode.
    if img.mode == 'P':
        kwargs['transparency'] = len(img.split()[-1].getcolors())
    else:
        img.convert('RGB')
    
    if 'quality' in info:
        kwargs['quality'] = info['quality']
    img.save(tmp, info['format'], **kwargs)
    tmp.seek(0)
    return tmp

def image_entropy(im):
    """
Calculate the entropy of an image. Used for "smart cropping".
"""
    #if not isinstance(im, Image):
    #    # Can only deal with PIL images. Fall back to a constant entropy.
    #    return 0
    hist = im.histogram()
    hist_size = float(sum(hist))
    hist = [h / hist_size for h in hist]
    return -sum([p * math.log(p, 2) for p in hist if p != 0])

def _compare_entropy(start_slice, end_slice, slice, difference):
    """
Calculate the entropy of two slices (from the start and end of an axis),
returning a tuple containing the amount that should be added to the start
and removed from the end of the axis.

"""
    start_entropy = image_entropy(start_slice)
    end_entropy = image_entropy(end_slice)
    if end_entropy and abs(start_entropy / end_entropy - 1) < 0.01:
        # Less than 1% difference, remove from both sides.
        if difference >= slice * 2:
            return slice, slice
        half_slice = slice // 2
        return half_slice, slice - half_slice
    if start_entropy > end_entropy:
        return 0, slice
    else:
        return slice, 0
