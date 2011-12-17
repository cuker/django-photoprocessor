from django.conf import settings
try:
    import importlib
except ImportError:
    from django.utils import importlib

default_processors = [
    'photoprocessor.processors.Adjustment',
    'photoprocessor.processors.AutoCrop',
    'photoprocessor.processors.Resize',
    'photoprocessor.processors.Quality',
    'photoprocessor.processors.Reflection',
    'photoprocessor.processors.Transpose',
    'photoprocessor.processors.Format',
    'photoprocessor.processors.DimensionInfo',
    #'photoprocessor.processors.ExtraInfo',
]

PROCESSORS = list()

for entry in getattr(settings, 'PHOTO_PROCESSORS', default_processors):
    module_name, class_name = entry.rsplit('.', 1)
    module = importlib.import_module(module_name)
    obj = getattr(module, class_name)
    if isinstance(obj, type):
        obj = obj()
    PROCESSORS.append(obj)
