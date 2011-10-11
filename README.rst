=====================
django-photoprocessor
=====================

Step 1
******

::

    $ pip install django-photoprocessor

(or clone the source and put the photoprocessor module on your path)

Step 2
******

Add ImageWithProcessorField to your models.

::

    # myapp/models.py

    from django.db import models
    from imagemaker.fields import ImageWithProcessorsField
    
    thumbnails = {'thumbnail':{'resize':{'width':100, 'height':100, 'crop':'center'}, 'quality':90},
                  'display': {'resize':{'width':500, 'height':500, 'crop':'center'}, 'quality':90}}

    class Photo(models.Model):
        name = models.CharField(max_length=100)
        original_image = ImageWithProcessorsField(upload_to='books', thumbnails=thumbnails)

Step 3
******

Access your thumbnails

::

    photo = Photo(name='myphoto')
    photo.original_image.save('myfile.jpg', myfileobj)
    print photo.original_image['thumbnail'].url


