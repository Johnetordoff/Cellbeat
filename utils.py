import os
from kivy.uix.image import Image


def load_texture(asset_path):
    """
    A generic texture loader. Assumes asset_path is relative to the current file.
    """
    full_path = os.path.join(os.path.dirname(__file__), asset_path)
    return Image(source=full_path).texture


