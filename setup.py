#/usr/bin/env python
import photoprocessor

try:
    from setuptools import setup, find_packages
except ImportError:
    from distutils.core import setup, find_packages

setup(
    name='django-photoprocessor',
    version=photoprocessor.__version__,
    description='Automated image processing for Django.',
    author='Jason Kraus',
    author_email='jasonk@cukerinteractive.com',
    license='BSD',
    url='http://github.com/cuker/django-photoprocessor/',
    packages=find_packages(exclude=['example', 'example.*']),
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Environment :: Web Environment',
        'Framework :: Django',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 2.5',
        'Programming Language :: Python :: 2.6',
        'Programming Language :: Python :: 2.7',
        'Topic :: Utilities'
    ]
)
