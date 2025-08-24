# ui/fonts.py
import os
from kivy.core.text import LabelBase
from kivy.resources import resource_add_path
from kivy.uix.spinner import SpinnerOption

FONT_NAME = "UniversalMono"

def _register_font() -> bool:
    """Register a mono font that has good Greek/math coverage."""
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    font_dir = os.path.join(base, 'assets', 'fonts')
    if os.path.isdir(font_dir):
        resource_add_path(font_dir)

    for candidate in ('DejaVuSansMono-Bold.ttf', 'DejaVuSansMono.ttf', 'DejaVuSans.ttf'):
        fp = os.path.join(font_dir, candidate)
        if os.path.exists(fp):
            LabelBase.register(name=FONT_NAME, fn_regular=fp)
            return True
    return False

_FONT_OK = _register_font()

def FKW(**kwargs):
    """Font kwargs helper: sprinkle **FKW() on font-capable widgets."""
    if _FONT_OK:
        kwargs.setdefault('font_name', FONT_NAME)
    return kwargs

class UniSpinnerOption(SpinnerOption):
    def __init__(self, **kwargs):
        super().__init__(**FKW(**kwargs))
