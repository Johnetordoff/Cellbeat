from setuptools import setup, Extension

module = Extension('audio',
                   sources=['audio.c'],
                   extra_link_args=['-framework', 'AudioToolbox', '-lpthread'],
                   )

setup(name='audio',
      version='1.0',
      ext_modules=[module])
