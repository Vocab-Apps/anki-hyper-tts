import sys
import os
import logging
import PyQt5

version = __import__('version', globals(), locals(), [], sys._addon_import_level_base)
constants = __import__('constants', globals(), locals(), [], sys._addon_import_level_base)


class NonAliasedImage(PyQt5.QtWidgets.QWidget):
    def __init__(self, pixmap):
        PyQt5.QtWidgets.QWidget.__init__(self)
        self._pixmap = pixmap
        # self.setMinimumSize(self._pixmap.width(), self._pixmap.height())
        self.setFixedWidth(self._pixmap.width())
        self.setFixedHeight(self._pixmap.height())

    def paintEvent(self,event):
        # logging.info('paintEvent')
        painter = PyQt5.QtGui.QPainter(self)
        painter.setRenderHint(PyQt5.QtGui.QPainter.SmoothPixmapTransform)
        painter.setRenderHint(PyQt5.QtGui.QPainter.Antialiasing)
        painter.drawPixmap(self.rect(), self._pixmap)

def get_graphic(graphic_name):
    return NonAliasedImage(PyQt5.QtGui.QPixmap(get_graphics_path(graphic_name)))

def get_header_label(text):
    header = PyQt5.QtWidgets.QLabel()
    header.setText(text)
    font = PyQt5.QtGui.QFont()
    font.setBold(True)
    font.setWeight(75)  
    font.setPointSize(20)
    header.setFont(font)
    return header

def get_medium_label(text):
    label = PyQt5.QtWidgets.QLabel()
    label.setText(text)
    font = PyQt5.QtGui.QFont()
    label_font_size = 13
    font.setBold(True)
    font.setPointSize(label_font_size)
    label.setFont(font)
    return label

def get_large_button_font():
    font2 = PyQt5.QtGui.QFont()
    font2.setPointSize(14)
    return font2        

def get_large_checkbox_font():
    font2 = PyQt5.QtGui.QFont()
    font2.setPointSize(12)
    return font2

def get_large_combobox_font():
    font2 = PyQt5.QtGui.QFont()
    font2.setPointSize(10)
    return font2

def get_version_font():
    font2 = PyQt5.QtGui.QFont()
    font2.setPointSize(10)
    font2.setItalic(True)
    return font2        

def process_label_text(text):
    return text.replace('\n', '<br/>')


def get_graphics_path(filename):
    return os.path.join(os.path.dirname(__file__), 'graphics', filename)

def get_hypertts_label_header(hypertts_pro_enabled):
    hlayout = PyQt5.QtWidgets.QHBoxLayout()
    if hypertts_pro_enabled:
        graphic_name = constants.GRAPHICS_PRO_BANNER
    else:
        graphic_name = constants.GRAPHICS_LITE_BANNER
    logo = get_graphic(graphic_name)
    version_label = PyQt5.QtWidgets.QLabel('v' + version.ANKI_HYPER_TTS_VERSION)
    version_label.setFont(get_version_font())

    hlayout.addStretch()
    hlayout.addWidget(logo)
    hlayout.addWidget(version_label)
    return hlayout
