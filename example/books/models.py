from django.db import models

from photoprocessor.fields import ImageWithProcessorsField

thumbnails = {'thumbnail':{'resize':{'width':100, 'height':100, 'crop':'smart'}, 'quality':90},
              'display': {'resize':{'width':500, 'height':500, 'crop':'smart'}, 'quality':90}}

class Book(models.Model):
    title = models.CharField(max_length=128)
    cover = ImageWithProcessorsField(upload_to='books', thumbnails=thumbnails)
