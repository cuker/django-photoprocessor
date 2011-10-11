import os 
from django.utils import unittest
from django.core.files import File

from models import Book

class BookTestCase(unittest.TestCase):

    def test_monolithic(self):
        book = Book(title='Of Mice And Men')
        image = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'thumb.jpg')
        print book.cover
        book.cover.save('image.jpg', File(open(image)))
        print book.cover
        print book.cover.data
        print book.cover.url
        
        print book.cover['thumbnail']
        print book.cover['thumbnail'].url
    
    def test_admin(self):
        import admin
