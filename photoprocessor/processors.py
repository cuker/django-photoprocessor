#Adapted from imagekit's processors.py
""" 


"""
from lib import Image, ImageEnhance, ImageColor


PROCESSORS = dict()

def register_image_processor(key, processor):
    if isinstance(processor, type):
        processor = processor(key)
    PROCESSORS[key] = processor

class ImageProcessor(object):
    """ Base image processor class """
    def __init__(self, key):
        self.key = key

    def process(self, img, fmt, config):
        return img, fmt


class Adjustment(ImageProcessor):
    config_vars = ['color', 'brightness', 'contrast', 'sharpness']

    def process(self, img, fmt, config):
        if config.get(self.key, False):
            img = img.convert('RGB')
            for name in ['Color', 'Brightness', 'Contrast', 'Sharpness']:
                factor = config[self.key].get(name, 1.0)
                if factor != 1.0:
                    try:
                        img = getattr(ImageEnhance, name)(img).enhance(factor)
                    except ValueError:
                        pass
        return img, fmt

register_image_processor('adjustment', Adjustment)

class Format(ImageProcessor):
    config_vars = ['format']
    format = 'JPEG'
    extension = 'jpg'

    def process(self, img, fmt, config):
        return img, config.get('format', fmt)

register_image_processor('format', Format)

class Reflection(ImageProcessor):
    config_vars = ['background_color', 'size', 'opacity']
    background_color = '#FFFFFF'
    size = 0.0
    opacity = 0.6

    def process(self, img, fmt, config):
        if self.key not in config:
            return img, fmt
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
        fmt = 'JPEG'
        # return the image complete with reflection effect
        return composite, fmt

register_image_processor('reflection', Reflection)

class Resize(ImageProcessor):
    config_vars = ['width', 'height', 'crop', 'upscale', 'crop_horizontal', 'crop_vertical']
    crop = False
    upscale = False
    crop_horizontal = 1
    crop_vertical = 1

    def process(self, img, fmt, config):
        if self.key not in config:
            return img, fmt
        cur_width, cur_height = img.size
        config = config[self.key]
        if config.get('crop', False):
            crop_horz = config.get('crop_horizontal', self.crop_horizontal)
            crop_vert = config.get('crop_vertical', self.crop_vertical)
            ratio = max(float(config['width']) / cur_width, float(config['height']) / cur_height)
            resize_x, resize_y = ((cur_width * ratio), (cur_height * ratio))
            crop_x, crop_y = (abs(config['width'] - resize_x), abs(config['height'] - resize_y))
            x_diff, y_diff = (int(crop_x / 2), int(crop_y / 2))
            box_left, box_right = {
                0: (0, config['width']),
                1: (int(x_diff), int(x_diff + config['width'])),
                2: (int(crop_x), int(resize_x)),
            }[crop_horz]
            box_upper, box_lower = {
                0: (0, config['height']),
                1: (int(y_diff), int(y_diff + config['height'])),
                2: (int(crop_y), int(resize_y)),
            }[crop_vert]
            box = (box_left, box_upper, box_right, box_lower)
            img = img.resize((int(resize_x), int(resize_y)), Image.ANTIALIAS).crop(box)
        else:
            if not config.get('width', None) is None and not config.get('height') is None:
                ratio = min(float(config['width']) / cur_width,
                            float(config['height']) / cur_height)
            else:
                if config.get('width', None) is None:
                    ratio = float(config['height']) / cur_height
                else:
                    ratio = float(config['width']) / cur_width
            new_dimensions = (int(round(cur_width * ratio)),
                              int(round(cur_height * ratio)))
            if new_dimensions[0] > cur_width or \
               new_dimensions[1] > cur_height:
                if not config.get('upscale', False):
                    return img, fmt
            img = img.resize(new_dimensions, Image.ANTIALIAS)
        return img, fmt

register_image_processor('resize', Resize)

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

    def process(self, img, fmt, config):
        if self.key not in config:
            return img, fmt
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
        return img, fmt

register_image_processor('transpose', Transpose)

#image is Image.open(afile)
def process_image(image, config):
    fmt = image.format
    img = image.copy()
    for proc in PROCESSORS.itervalues():
        img, fmt = proc.process(img, fmt, config)
    img.format = fmt
    return img, fmt

