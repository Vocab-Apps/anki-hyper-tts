import sys
import os
import aqt.qt

from . import version
from . import constants


class NonAliasedImage(aqt.qt.QWidget):
    def __init__(self, pixmap):
        aqt.qt.QWidget.__init__(self)
        self._pixmap = pixmap
        # self.setMinimumSize(self._pixmap.width(), self._pixmap.height())
        self.setFixedWidth(self._pixmap.width())
        self.setFixedHeight(self._pixmap.height())

    def paintEvent(self,event):
        painter = aqt.qt.QPainter(self)
        painter.setRenderHint(aqt.qt.QPainter.RenderHint.SmoothPixmapTransform)
        painter.setRenderHint(aqt.qt.QPainter.RenderHint.Antialiasing)
        painter.drawPixmap(self.rect(), self._pixmap)

def get_graphic(graphic_name):
    return NonAliasedImage(aqt.qt.QPixmap(get_graphics_path(graphic_name)))

def get_header_label(text):
    header = aqt.qt.QLabel()
    header.setText(text)
    font = aqt.qt.QFont()
    font.setBold(True)
    font.setWeight(75)  
    font.setPointSize(20)
    header.setFont(font)
    return header

def get_medium_label(text):
    label = aqt.qt.QLabel()
    label.setText(text)
    font = aqt.qt.QFont()
    label_font_size = 12
    font.setBold(True)
    font.setPointSize(label_font_size)
    label.setFont(font)
    return label

def get_service_header_label(text):
    header = aqt.qt.QLabel()
    header.setText(text)
    font = aqt.qt.QFont()
    font.setBold(True)
    font.setWeight(70)
    font.setPointSize(12)
    header.setFont(font)
    return header

def get_small_cta_label(text):
    label = aqt.qt.QLabel()
    label.setText(text)
    font = aqt.qt.QFont()
    label_font_size = 8
    font.setItalic(True)
    font.setPointSize(label_font_size)
    label.setFont(font)
    return label

def get_large_button_font():
    font2 = aqt.qt.QFont()
    font2.setPointSize(14)
    return font2        

def get_large_checkbox_font():
    font2 = aqt.qt.QFont()
    font2.setPointSize(12)
    return font2

def get_large_combobox_font():
    font2 = aqt.qt.QFont()
    font2.setPointSize(10)
    return font2

def get_version_font():
    font2 = aqt.qt.QFont()
    font2.setPointSize(10)
    font2.setItalic(True)
    return font2        

def process_label_text(text):
    return text.replace('\n', '<br/>')


def get_graphics_path(filename):
    current_dir = os.path.dirname(__file__)
    root_dir = os.path.join(current_dir, os.pardir)
    return os.path.join(root_dir, 'graphics', filename)

def get_hypertts_label_header(hypertts_pro_enabled):
    hlayout = aqt.qt.QHBoxLayout()
    if hypertts_pro_enabled:
        graphic_name = constants.GRAPHICS_PRO_BANNER
    else:
        graphic_name = constants.GRAPHICS_LITE_BANNER
    logo = get_graphic(graphic_name)
    version_label = aqt.qt.QLabel('v' + version.ANKI_HYPER_TTS_VERSION)
    version_label.setFont(get_version_font())

    hlayout.addStretch()
    hlayout.addWidget(logo)
    hlayout.addWidget(version_label)
    return hlayout
