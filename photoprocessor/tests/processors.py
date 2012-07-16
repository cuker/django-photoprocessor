from django.utils import unittest

from common import MockImage

from photoprocessor import processors

class ResizeTestCase(unittest.TestCase):
    def setUp(self):
        self.processor = processors.Resize()
    
    def test_scale_resize(self):
        img = MockImage((100, 200))
        config = {'resize':{'width':50, 'height':50, 'crop':'scale',}}
        info = {}
        
        new_image = self.processor.process(img, config, info)
        self.assertEqual(new_image.size, (25,50))

