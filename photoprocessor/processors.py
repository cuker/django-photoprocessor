#Adapted from imagekit's processors.py
""" 


"""
from lib import Image, ImageEnhance, ImageColor, ImageFilter, ImageChops
from utils import _compare_entropy

class ImageProcessor(object):
    """ Base image processor class """
    info_only = False

    def process(self, img, config, info):
        return img


class Adjustment(ImageProcessor):
    config_vars = ['color', 'brightness', 'contrast', 'sharpness']
    key = 'adjustment'

    def process(self, img, config, info):
        if config.get(self.key, False):
            img = img.convert('RGB')
            for name in ['Color', 'Brightness', 'Contrast', 'Sharpness']:
                factor = config[self.key].get(name, 1.0)
                if factor != 1.0:
                    try:
                        img = getattr(ImageEnhance, name)(img).enhance(factor)
                    except ValueError:
                        pass
        return img

class Format(ImageProcessor):
    config_vars = ['format']
    format = 'JPEG'
    extension = 'jpg'

    def process(self, img, config, info):
        if 'format' in config:
            info['format'] = config['format']
        return img

class Quality(ImageProcessor):
    config_vars = ['quality']

    def process(self, img, config, info):
        if 'quality' in config:
            info['quality'] = config['quality']
        return img

class DimensionInfo(ImageProcessor):
    info_only = True
    
    def process(self, img, config, info):
        info['size'] = {'width': img.size[0],
                        'height': img.size[1],}
        return img

class ExtraInfo(ImageProcessor): #CONSIDER this should only be done on the original image
    info_only = True
    
    def process(self, img, config, info):
        info['extra_info'] = img.info
        return img

class Reflection(ImageProcessor):
    config_vars = ['background_color', 'size', 'opacity']
    key = 'reflection'
    background_color = '#FFFFFF'
    size = 0.0
    opacity = 0.6

    def process(self, img, config, info):
        if self.key not in config:
            return img
        # convert bgcolor string to rgb value
        config = config[self.key]
        background_color = ImageColor.getrgb(config.get('background_color', self.background_color))
        # handle palleted images
        img = img.convert('RGB')
        # copy orignial image and flip the orientation
        reflection = img.copy().transpose(Image.FLIP_TOP_BOTTOM)
        # create a new image filled with the bgcolor the same size
        background = Image.new("RGB", img.size, background_color)
        # calculate our alpha mask
        start = int(255 - (255 * config.get('opacity', self.opacity)))  # The start of our gradient
        steps = int(255 * config.get('size', self.size))  # The number of intermedite values
        increment = (255 - start) / float(steps)
        mask = Image.new('L', (1, 255))
        for y in range(255):
            if y < steps:
                val = int(y * increment + start)
            else:
                val = 255
            mask.putpixel((0, y), val)
        alpha_mask = mask.resize(img.size)
        # merge the reflection onto our background color using the alpha mask
        reflection = Image.composite(background, reflection, alpha_mask)
        # crop the reflection
        reflection_height = int(img.size[1] * config.get('size', self.size))
        reflection = reflection.crop((0, 0, img.size[0], reflection_height))
        # create new image sized to hold both the original image and the reflection
        composite = Image.new("RGB", (img.size[0], img.size[1]+reflection_height), background_color)
        # paste the orignal image and the reflection into the composite image
        composite.paste(img, (0, 0))
        composite.paste(reflection, (0, img.size[1]))
        # Save the file as a JPEG
        info['format'] = 'JPEG'
        # return the image complete with reflection effect
        return composite

class AutoCrop(ImageProcessor):
    """
    Removes white space from around the image
    """
    key = 'autocrop'
    
    def process(self, img, config, info):
        if self.key not in config:
            return img
        bw = img.convert('1')
        bw = bw.filter(ImageFilter.MedianFilter)
        # White background.
        bg = Image.new('1', img.size, 255)
        diff = ImageChops.difference(bw, bg)
        bbox = diff.getbbox()
        if bbox:
            img = img.crop(bbox)
        return img

class Resize(ImageProcessor):
    config_vars = ['width', 'height', 'crop', 'upscale',]
    #crop in ('smart', 'scale')
    key = 'resize'
    crop = False
    upscale = False

    def process(self, img, config, info):
        if self.key not in config:
            return img
        cur_width, cur_height = img.size
        config = config[self.key]
        size = config['width'], config['height']
        crop = config.get('crop', self.crop)
        upscale = config.get('upscale', self.upscale)
        
        source_x, source_y = [float(v) for v in img.size]
        target_x, target_y = [float(v) for v in size]

        if crop or not target_x or not target_y:
            scale = max(target_x / source_x, target_y / source_y)
        else:
            scale = min(target_x / source_x, target_y / source_y)

        # Handle one-dimensional targets.
        if not target_x:
            target_x = source_x * scale
        elif not target_y:
            target_y = source_y * scale

        if scale < 1.0 or (scale > 1.0 and upscale):
            # Resize the image to the target size boundary. Round the scaled
            # boundary sizes to avoid floating point errors.
            img = img.resize((int(round(source_x * scale)),
                              int(round(source_y * scale))),
                              resample=Image.ANTIALIAS)

        if crop:
            # Use integer values now.
            source_x, source_y = img.size
            # Difference between new image size and requested size.
            diff_x = int(source_x - min(source_x, target_x))
            diff_y = int(source_y - min(source_y, target_y))
            if diff_x or diff_y:
                # Center cropping (default).
                halfdiff_x, halfdiff_y = diff_x // 2, diff_y // 2
                box = [halfdiff_x, halfdiff_y,
                       min(source_x, int(target_x) + halfdiff_x),
                       min(source_y, int(target_y) + halfdiff_y)]
                #TODO edge crop?
                if crop == 'smart': #TODO this does not appear to work
                    left = top = 0
                    right, bottom = source_x, source_y
                    while diff_x:
                        slice = min(diff_x, max(diff_x // 5, 10))
                        start = img.crop((left, 0, left + slice, source_y))
                        end = img.crop((right - slice, 0, right, source_y))
                        add, remove = _compare_entropy(start, end, slice, diff_x)
                        left += add
                        right -= remove
                        diff_x = diff_x - add - remove
                    while diff_y:
                        slice = min(diff_y, max(diff_y // 5, 10))
                        start = img.crop((0, top, source_x, top + slice))
                        end = img.crop((0, bottom - slice, source_x, bottom))
                        add, remove = _compare_entropy(start, end, slice, diff_y)
                        top += add
                        bottom -= remove
                        diff_y = diff_y - add - remove
                    box = (left, top, right, bottom)
                # Finally, crop the image!
                if crop != 'scale':
                    img = img.crop(box)
        return img

class Transpose(ImageProcessor):
    """ Rotates or flips the image

    Method should be one of the following strings:
        - FLIP_LEFT RIGHT
        - FLIP_TOP_BOTTOM
        - ROTATE_90
        - ROTATE_270
        - ROTATE_180
        - auto

    If method is set to 'auto' the processor will attempt to rotate the image
    according to the EXIF Orientation data.

    """
    config_vars = ['method']
    key = 'transpose'
    
    EXIF_ORIENTATION_STEPS = {
        1: [],
        2: ['FLIP_LEFT_RIGHT'],
        3: ['ROTATE_180'],
        4: ['FLIP_TOP_BOTTOM'],
        5: ['ROTATE_270', 'FLIP_LEFT_RIGHT'],
        6: ['ROTATE_270'],
        7: ['ROTATE_90', 'FLIP_LEFT_RIGHT'],
        8: ['ROTATE_90'],
    }

    method = 'auto'

    def process(self, img, config, info):
        if self.key not in config:
            return img
        config = config[self.key]
        if config['method'] == 'auto':
            try:
                orientation = img._getexif()[0x0112]
                ops = self.EXIF_ORIENTATION_STEPS[orientation]
            except:
                ops = []
        else:
            ops = [config['method']]
        for method in ops:
            img = img.transpose(getattr(Image, method))
        return img

#image is Image.open(afile)
def process_image(image, config):
    from settings import PROCESSORS
    info = {'format':image.format}
    img = image.copy()
    for proc in PROCESSORS:
        img = proc.process(img, config, info)
    img.format = info['format']
    return img, info

def process_image_info(image, config={}):
    from settings import PROCESSORS
    info = {'format':image.format}
    img = image.copy()
    for proc in PROCESSORS:
        if proc.info_only:
            img = proc.process(img, config, info)
    return info

