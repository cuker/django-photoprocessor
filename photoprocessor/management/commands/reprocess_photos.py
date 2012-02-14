from optparse import make_option
from django.core.management.base import BaseCommand

from photoprocessor.fields import ImageWithProcessorsFieldFile

class Command(BaseCommand):
    help = """Reprocess the photos on your models"""
    option_list = BaseCommand.option_list + (
        make_option('--force',
            action='store_true',
            dest='force',
            default=False,
            help='Force the reprocessing'),
    )
    args = '[appname.modelname ...]'

    def handle(self, *args, **kwargs):
        from django.db import models
        all_models = models.get_models()
        accepted_models = set([arg.lower() for arg in args])
        for model in all_models:
            if accepted_models:
                name = '%s.%s' % (model._meta.app_name, model._meta.object_name)
                name = name.lower()
                if name not in accepted_models:
                    continue
            for field in model._meta.get_local_fields():
                image_fields = list()
                if isinstance(field, ImageWithProcessorsFieldFile):
                    image_fields.append(field.name)
                if image_fields:
                    self.reprocess_model(model, image_fields, kwargs['force'])
    
    def reprocess_model(self, model, fields, force=False):
        for instance in model.objects.all():
            updated = False
            for field_name in fields:
                val = getattr(instance, field_name, None)
                if val:
                    updated = True
                    val.reprocess(save=False, force_reprocess=force)
            if updated:
                val.save()

