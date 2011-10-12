""" Photoprocessor utility functions """

import tempfile


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
