from django.db import models
from django.utils import simplejson
from django.utils.encoding import force_unicode, smart_str, smart_unicode
from django.core.files.storage import default_storage
from django.core.files import File
from django.core.files.base import ContentFile
from django.core.serializers.json import DjangoJSONEncoder
from django import forms

from lib import Image
from utils import img_to_fobj
from processors import process_image, process_image_info

import logging
import os
import datetime

class JSONFieldDescriptor(object):
    def __init__(self, field):
        self.field = field

    def __get__(self, instance=None, owner=None):
        if instance is None:
            raise AttributeError(
                "The '%s' attribute can only be accessed from %s instances."
                % (self.field.name, owner.__name__))
        
        if not hasattr(instance, self.field.get_cache_name()):
            data = instance.__dict__.get(self.field.attname, dict())
            if not isinstance(data, dict):
                data = self.field.loads(data)
                if data is None:
                    data = dict()
            setattr(instance, self.field.get_cache_name(), data)
        
        return getattr(instance, self.field.get_cache_name())

    def __set__(self, instance, value):
        instance.__dict__[self.field.attname] = value
        try:
            delattr(instance, self.field.get_cache_name())
        except AttributeError:
            pass


class JSONField(models.TextField):
    """
    A field for storing JSON-encoded data. The data is accessible as standard
    Python data types and is transparently encoded/decoded to/from a JSON
    string in the database.
    """
    serialize_to_string = True
    descriptor_class = JSONFieldDescriptor

    def __init__(self, verbose_name=None, name=None,
                 encoder=DjangoJSONEncoder(), decoder=simplejson.JSONDecoder(),
                 **kwargs):
        blank = kwargs.pop('blank', True)
        models.TextField.__init__(self, verbose_name, name, blank=blank,
                                  **kwargs)
        self.encoder = encoder
        self.decoder = decoder

    def db_type(self, connection=None):
        return "text"

    def contribute_to_class(self, cls, name):
        super(JSONField, self).contribute_to_class(cls, name)
        setattr(cls, self.name, self.descriptor_class(self))
    
    def pre_save(self, model_instance, add):
        "Returns field's value just before saving."
        descriptor = getattr(model_instance, self.attname)
        if descriptor.data is not None:
            return descriptor.data
        else:
            return self.field.value_from_object(model_instance)

    def get_db_prep_save(self, value, *args, **kwargs):
        if hasattr(value, 'data'):
            value = value.data
        if not isinstance(value, basestring):
            value = self.dumps(value)

        return super(JSONField, self).get_db_prep_save(value, *args, **kwargs)

    def value_to_string(self, obj):
        return self.dumps(self.value_from_object(obj))

    def dumps(self, data):
        return self.encoder.encode(data)

    def loads(self, val):
        try:
            val = self.decoder.decode(val)#, encoding=settings.DEFAULT_CHARSET)

            # XXX We need to investigate why this is happening once we have
            # a solid repro case.
            if isinstance(val, basestring):
                logging.warning("JSONField decode error. Expected dictionary, "
                                "got string for input '%s'" % val)
                # For whatever reason, we may have gotten back
                val = self.decoder.decode(val)#, encoding=settings.DEFAULT_CHARSET)
        except ValueError:
            val = None
        return val
    
    def south_field_triple(self):
        "Returns a suitable description of this field for South."
        # We'll just introspect the _actual_ field.
        from south.modelsinspector import introspector
        field_class = "django.db.models.fields.TextField"
        args, kwargs = introspector(self)
        # That's our definition!
        return (field_class, args, kwargs)

from django.db.models.fields.files import FieldFile

class ImageFile(FieldFile):
    def __init__(self, instance, field, data, key):
        self.image_data = data[key]
        self.key = key
        name = self.image_data['path']
        FieldFile.__init__(self, instance, field, name)
    
    @property
    def info(self):
        return self.image_data['info']
    
    def width(self):
        return self.info['size']['width']
    
    def height(self):
        return self.info['size']['height']
    
    def save(self, *args, **kwargs):
        raise NotImplementedError
    
    def delete(self, *args, **kwargs):
        raise NotImplementedError

class ImageWithProcessorsFieldFile(FieldFile):
    def __init__(self, instance, field, data):
        self.data = data
        self.image_data = self.data.get('original', dict())
        if isinstance(self.image_data, basestring): #old style
            self.image_data = {'path':self.image_data}
            self.data['original'] = self.image_data
        name = self.image_data.get('path', None)
        FieldFile.__init__(self, instance, field, name)
    
    def image(self):
        self.file.open()
        self.file.seek(0)
        try:
            return Image.open(self.file)
        except IOError:
            self.file.seek(0)
            cf = ContentFile(self.file.read())
            return Image.open(cf)
    
    @property
    def info(self):
        return self.image_data['info']
    
    def width(self):
        return self.info['size']['width']
    
    def height(self):
        return self.info['size']['height']
    
    def has_key(self, key):
        return key in self.field.thumbnails
    
    def __contains__(self, key):
        return self.has_key(key)
    
    #TODO __setitem__ should manually specify the image
    
    def __getitem__(self, key):
        if key in self.field.thumbnails:
            if key not in self.data and 'original' in self.data:
                #generate image
                name = self.name
                base_name, base_ext = os.path.splitext(os.path.basename(name))
                try:
                    source_image = self.image()
                except IOError:
                    if self.field.no_image is not None:
                        return self.field.no_image
                    return FieldFile(self.instance, self.field, None)
                config = self.field.thumbnails[key]
                
                thumb_name = '%s-%s%s' % (base_name, key, base_ext)
                self.data[key] = self._process_thumbnail(source_image, thumb_name, config)
                self.instance.save()
            
            if key in self.data:
                return ImageFile(self.instance, self.field, self.data, key)
            if self.field.no_image is not None:
                return self.field.no_image
            return FieldFile(self.instance, self.field, None)
        raise KeyError
    
    def _process_thumbnail(self, source_image, thumb_name, config):
        img, info = process_image(source_image, config)
        
        thumb_name = self.field.generate_filename(self.instance, thumb_name)
        #not efficient, requires image to be loaded into memory
        thumb_fobj = ContentFile(img_to_fobj(img, info).read())
        thumb_name = self.storage.save(thumb_name, thumb_fobj)
        
        return {'path':thumb_name, 'config':config, 'info':info}
    
    def _get_url(self):
        if not self and self.field.no_image is not None:
            return self.field.no_image.url
        return FieldFile._get_url(self)
    url = property(_get_url)
    
    def reprocess_info(self, save=True):
        source_image = self.image()
        self.data['original']['info'] = process_image_info(source_image)
        if save:
            self.instance.save()
    reprocess_info.alters_data = True
    
    def reprocess_thumbnail_info(self, save=True):
        source_image = self.image()
        for key, config in self.field.thumbnails.iteritems():
            if key in self.data:
                info = process_image_info(source_image, config)
                self.data[key]['info'] = info
        if save:
            self.instance.save()
    reprocess_thumbnail_info.alters_data = True
    
    def reprocess_thumbnails(self, save=True, force_reprocess=False):
        base_name, base_ext = os.path.splitext(os.path.basename(self.name))
        source_image = self.image()
        for key, config in self.field.thumbnails.iteritems(): #TODO rename to specs
            if not force_reprocess and key in self.data and self.data[key].get('config') == config:
                continue
            thumb_name = '%s-%s%s' % (base_name, key, base_ext)
            self.data[key] = self._process_thumbnail(source_image, thumb_name, config)

        # Save the object because it has changed, unless save is False
        if save:
            self.instance.save()
    reprocess_thumbnails.alters_data = True
    
    def reprocess(self, save=True, force_reprocess=False):
        self.reprocess_info(save=False)
        self.reprocess_thumbnails(save=False, force_reprocess=force_reprocess)
        if save:
            self.instance.save()
    reprocess.alters_data = True
    
    def save(self, name, content, save=True, force_reprocess=True):
        name = self.field.generate_filename(self.instance, name)
        self.name = self.storage.save(name, content)
        self.data['original'] = {'path':self.name}

        # Update the filesize cache
        self._size = content.size
        self._committed = True
        
        #now update the children
        base_name, base_ext = os.path.splitext(os.path.basename(name))
        source_image = self.image()
        for key, config in self.field.thumbnails.iteritems(): #TODO rename to specs
            if not force_reprocess and key in self.data and self.data[key].get('config') == config:
                continue
            thumb_name = '%s-%s%s' % (base_name, key, base_ext)
            self.data[key] = self._process_thumbnail(source_image, thumb_name, config)
        
        self.data['original']['info'] = process_image_info(source_image)
        self.image_data = self.data['original']

        # Save the object because it has changed, unless save is False
        if save:
            self.instance.save()
    save.alters_data = True

    def delete(self, save=True):
        # Only close the file if it's already open, which we know by the
        # presence of self._file
        if hasattr(self, '_file'):
            self.close()
            del self.file

        self.storage.delete(self.name)
        
        for key, image in self.data.iteritems():
            if key != 'original':
                self.storage.delete(image['path'])

        self.name = None
        self.data['original'] = {}
        self.image_data = self.data['original']

        # Delete the filesize cache
        if hasattr(self, '_size'):
            del self._size
        self._committed = False

        if save:
            self.instance.save()
    delete.alters_data = True

class ImageWithProcessorsDesciptor(JSONFieldDescriptor):
    def __get__(self, instance=None, owner=None):
        if instance is None:
            raise AttributeError(
                "The '%s' attribute can only be accessed from %s instances."
                % (self.field.name, owner.__name__))
        
        data = JSONFieldDescriptor.__get__(self, instance, owner)
        
        return self.field.attr_class(instance, self.field, data)

    def __set__(self, instance, value):
        if isinstance(value, basestring):
            try:
                self.field.loads(value)
            except ValueError:
                pass
            else:
                JSONFieldDescriptor.__set__(self, instance, value)
        elif isinstance(value, dict):
            if value:
                JSONFieldDescriptor.__set__(self, instance, value)
        elif isinstance(value, File):
            name = os.path.split(value.name)[-1]
            content = value
            self.__get__(instance).save(name, content, False)

class ImageWithProcessorsField(JSONField):
    descriptor_class = ImageWithProcessorsDesciptor
    attr_class = ImageWithProcessorsFieldFile
    
    def __init__(self, **kwargs):
        kwargs.setdefault('blank', False)
        self.thumbnails = kwargs.pop('thumbnails')
        self.upload_to = kwargs.pop('upload_to')
        self.no_image = kwargs.pop('no_image', None)
        self.storage = kwargs.pop('storage', default_storage)
        JSONField.__init__(self, **kwargs)
    
    def value_to_string(self, obj):
        """
        Returns a string value of this field from the passed obj.
        This is used by the serialization framework.
        """
        return smart_unicode(self.dumps(self._get_val_from_obj(obj).data))
    
    def contribute_to_class(self, cls, name):
        from copy import copy
        self = copy(self) #allow inherited models to have their own thumbnails defined
        super(ImageWithProcessorsField, self).contribute_to_class(cls, name)
        setattr(cls, self.name, self.descriptor_class(self))
    
    def get_directory_name(self):
        return os.path.normpath(force_unicode(datetime.datetime.now().strftime(smart_str(self.upload_to))))

    def get_filename(self, filename):
        return os.path.normpath(self.storage.get_valid_name(os.path.basename(filename)))

    def generate_filename(self, instance, filename):
        return os.path.join(self.get_directory_name(), self.get_filename(filename))
    
    def save_form_data(self, instance, data):
        # Important: None means "no change", other false value means "clear"
        # This subtle distinction (rather than a more explicit marker) is
        # needed because we need to consume values that are also sane for a
        # regular (non Model-) Form to find in its cleaned_data dictionary.
        if data is not None:
            # This value will be converted to unicode and stored in the
            # database, so leaving False as-is is not acceptable.
            setattr(instance, self.name, data)

    def formfield(self, **kwargs):
        from django.contrib.admin import widgets
        if 'widget' in kwargs and kwargs['widget'] == widgets.AdminTextareaWidget:
            kwargs['widget'] = widgets.AdminFileWidget
        defaults = {'form_class': forms.FileField, 'max_length': self.max_length}
        # If a file has been provided previously, then the form doesn't require
        # that a new file is provided this time.
        # The code to mark the form field as not required is used by
        # form_for_instance, but can probably be removed once form_for_instance
        # is gone. ModelForm uses a different method to check for an existing file.
        if 'initial' in kwargs:
            defaults['required'] = False
        defaults.update(kwargs)
        #print defaults
        return super(ImageWithProcessorsField, self).formfield(**defaults)

