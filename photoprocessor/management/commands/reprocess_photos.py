from optparse import make_option
from django.core.management.base import BaseCommand

from photoprocessor.fields import ImageWithProcessorsField

class Command(BaseCommand):
    help = """Reprocess the photos on your models"""
    option_list = BaseCommand.option_list + (
        make_option('--force',
            action='store_true',
            dest='force',
            default=False,
            help='Force the reprocessing'),
        make_option('--force-continue',
            action='store_true',
            dest='force_continue',
            default=False,
            help='Continue reprocessing the next image even if an exception occurs. If not set, the script will stop on unhandled exception.'),
    )
    args = '[appname.modelname ...]'

    def handle(self, *args, **kwargs):
        from django.db import models
        all_models = models.get_models()
        accepted_models = set([arg.lower() for arg in args])
        for model in all_models:
            if accepted_models:
                name = '%s.%s' % (model._meta.app_label, model._meta.object_name)
                name = name.lower()
                if name not in accepted_models:
                    continue
            for field in model._meta.local_fields:
                image_fields = list()
                if isinstance(field, ImageWithProcessorsField):
                    image_fields.append(field.name)
                if image_fields:
                    print "Processing %s with fields: %s" % (model, image_fields)
                    self.reprocess_model(model, image_fields, kwargs['force'], kwargs['force_continue'])
    
    def reprocess_model(self, model, fields, force=False, force_continue=False):
        for instance in model.objects.all():
            updated = False
            for field_name in fields:
                val = getattr(instance, field_name, None)
                if val:
                    updated = True
                    try:
                        val.reprocess(save=False, force_reprocess=force)
                    except IOError as e:
                        if force_continue:
                            print "Could not open '%s' to reprocess field '%s' for %s (pk: %s)"%(val, field_name, model, instance.pk)
                            continue
                        else:
                            raise e
            if updated:
                instance.save()

