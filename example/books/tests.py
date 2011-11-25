import os 

from django.utils import unittest
from django.core.files import File
from django.core import serializers

from models import Book

class BookTestCase(unittest.TestCase):

    def test_monolithic(self):
        book = Book(title='Of Mice And Men')
        image = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'thumb.jpg')
        print book.cover
        book.cover.save('image.jpg', File(open(image, 'rb')))
        print book.cover
        print book.cover.data
        print book.cover.url
        
        print book.cover['thumbnail']
        print book.cover['thumbnail'].url
        print book.cover['thumbnail'].width()
        
        print serializers.serialize("xml", [book])
        print serializers.serialize("json", [book])
        
        book.cover.reprocess_thumbnail_info()
        print book.cover['thumbnail'].width()
    
    def test_admin(self):
        import admin
