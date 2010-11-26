# -*- coding: utf-8 -*-
#
# Copyright © 2009-2010 CEA
# Pierre Raybaut
# Licensed under the terms of the CECILL License
# (see guiqwt/__init__.py for details)

"""Simple application based on guiqwt and guidata"""

SHOW = True # Show test in GUI-based test launcher

from PyQt4.QtGui import (QMainWindow, QMessageBox, QSplitter, QListWidget,
                         QFileDialog)
from PyQt4.QtCore import QSize, QT_VERSION_STR, PYQT_VERSION_STR, Qt, SIGNAL

import sys, platform
import numpy as np

from guidata.dataset.datatypes import DataSet, GetAttrProp
from guidata.dataset.dataitems import (IntItem, FloatArrayItem, StringItem,
                                       ChoiceItem)
from guidata.dataset.qtwidgets import DataSetEditGroupBox
from guidata.configtools import get_icon
from guidata.qthelpers import create_action, add_actions, get_std_icon
from guidata.utils import update_dataset

from guiqwt.config import _
from guiqwt.plot import ImagePlotWidget
from guiqwt.builder import make
from guiqwt.signals import SIG_LUT_CHANGED
from guiqwt.panels import ID_CONTRAST
from guiqwt.io import imagefile_to_array

APP_NAME = _("Application example")
VERSION = '1.0.0'

class ImageParam(DataSet):
    _hide_data = False
    _hide_size = True
    title = StringItem(_("Title"), default=_("Untitled"))
    data = FloatArrayItem(_("Data")).set_prop("display",
                                              hide=GetAttrProp("_hide_data"))
    width = IntItem(_("Width"), help=_("Image width (pixels)"), min=1,
                    default=100).set_prop("display",
                                          hide=GetAttrProp("_hide_size"))
    height = IntItem(_("Height"), help=_("Image height (pixels)"), min=1,
                     default=100).set_prop("display",
                                           hide=GetAttrProp("_hide_size"))

class ImageParamNew(ImageParam):
    _hide_data = True
    _hide_size = False
    type = ChoiceItem(_("Type"),
                      (("rand", _("random")), ("zeros", _("zeros"))))

class ImageListWithProperties(QSplitter):
    def __init__(self, parent):
        QSplitter.__init__(self, parent)
        self.imagelist = QListWidget(self)
        self.addWidget(self.imagelist)
        self.properties = DataSetEditGroupBox(_("Properties"), ImageParam)
        self.properties.setEnabled(False)
        self.addWidget(self.properties)

class CentralWidget(QSplitter):
    def __init__(self, parent, toolbar):
        QSplitter.__init__(self, parent)
        self.setContentsMargins(10, 10, 10, 10)
        self.setOrientation(Qt.Vertical)
        
        imagelistwithproperties = ImageListWithProperties(self)
        self.addWidget(imagelistwithproperties)
        self.imagelist = imagelistwithproperties.imagelist
        self.connect(self.imagelist, SIGNAL("currentRowChanged(int)"),
                     self.current_item_changed)
        self.connect(self.imagelist, SIGNAL("itemSelectionChanged()"),
                     self.selection_changed)
        self.properties = imagelistwithproperties.properties
        self.connect(self.properties, SIGNAL("apply_button_clicked()"),
                     self.properties_changed)
        
        self.plotwidget = ImagePlotWidget(self)
        self.connect(self.plotwidget.plot, SIG_LUT_CHANGED,
                     self.lut_range_changed)
        self.item = None # image item
        
        self.manager = manager = self.plotwidget.manager
        
        manager.add_toolbar(toolbar, "default")
        
        manager.register_standard_tools()
        manager.add_separator_tool()
        manager.register_image_tools()
        manager.add_separator_tool()
        manager.register_other_tools()
        manager.get_default_tool().activate()
        
        self.addWidget(self.plotwidget)

        self.images = [] # List of ImageParam instances
        self.lut_ranges = [] # List of LUT ranges

        self.setStretchFactor(0, 0)
        self.setStretchFactor(1, 1)
        self.setHandleWidth(10)
        self.setSizes([1, 2])
        
    def refresh_list(self):
        self.imagelist.clear()
        self.imagelist.addItems([image.title for image in self.images])
        
    def selection_changed(self):
        """Image list: selection changed"""
        row = self.imagelist.currentRow()
        self.properties.setDisabled(row == -1)
        
    def current_item_changed(self, row):
        """Image list: current image changed"""
        image, lut_range = self.images[row], self.lut_ranges[row]
        self.show_data(image.data, lut_range)
        update_dataset(self.properties.dataset, image)
        self.properties.get()
        
    def lut_range_changed(self):
        row = self.imagelist.currentRow()
        self.lut_ranges[row] = self.item.get_lut_range()
        
    def show_data(self, data, lut_range=None):
        plot = self.plotwidget.plot
        if self.item is not None:
            self.item.set_data(data)
            if lut_range is None:
                lut_range = self.item.get_lut_range()
            contrast_panel = self.manager.get_panel(ID_CONTRAST)
            contrast_panel.set_range(*lut_range)
        else:
            self.item = make.image(data)
            plot.add_item(self.item, z=0)
        plot.replot()
        
    def properties_changed(self):
        """The properties 'Apply' button was clicked: updating image"""
        row = self.imagelist.currentRow()
        image = self.images[row]
        update_dataset(image, self.properties.dataset)
        self.refresh_list()
        self.show_data(image.data)
    
    def add_image(self, image):
        self.images.append(image)
        self.lut_ranges.append(None)
        self.refresh_list()
        self.imagelist.setCurrentRow(len(self.images)-1)
        plot = self.plotwidget.plot
        plot.do_autoscale()
    
    def add_image_from_file(self, filename):
        image = ImageParam()
        image.title = unicode(filename)
        image.data = imagefile_to_array(filename)
        image.height, image.width = image.data.shape
        self.add_image(image)

class MainWindow(QMainWindow):
    def __init__(self):
        QMainWindow.__init__(self)
        self.setup()
        
    def setup(self):
        """Setup window parameters"""
        self.setWindowIcon(get_icon('python.png'))
        self.setWindowTitle(APP_NAME)
        self.resize(QSize(600, 800))
        
        # Welcome message in statusbar:
        status = self.statusBar()
        status.showMessage(_("Welcome to guiqwt application example!"), 5000)
        
        # File menu
        file_menu = self.menuBar().addMenu(_("File"))
        new_action = create_action(self, _("New..."),
                                   shortcut="Ctrl+N",
                                   icon=get_icon('filenew.png'),
                                   tip=_("Create a new image"),
                                   triggered=self.new_image)
        open_action = create_action(self, _("Open..."),
                                    shortcut="Ctrl+O",
                                    icon=get_icon('fileopen.png'),
                                    tip=_("Open an image"),
                                    triggered=self.open_image)
        quit_action = create_action(self, _("Quit"),
                                    shortcut="Ctrl+Q",
                                    icon=get_std_icon("DialogCloseButton"),
                                    tip=_("Quit application"),
                                    triggered=self.close)
        add_actions(file_menu, (new_action, open_action, None, quit_action))
        
        # Help menu
        help_menu = self.menuBar().addMenu("?")
        about_action = create_action(self, _("About..."),
                                     icon=get_std_icon('MessageBoxInformation'),
                                     triggered=self.about)
        add_actions(help_menu, (about_action,))
        
        main_toolbar = self.addToolBar("Main")
        add_actions(main_toolbar, (new_action, open_action, ))
        
        # Set central widget:
        toolbar = self.addToolBar("Image")
        self.mainwidget = CentralWidget(self, toolbar)
        self.setCentralWidget(self.mainwidget)
        
    #------?
    def about(self):
        QMessageBox.about( self, _("About ")+APP_NAME,
              """<b>%s</b> v%s<p>%s Pierre Raybaut
              <br>Copyright &copy; 2009-2010 CEA
              <p>Python %s, Qt %s, PyQt %s %s %s""" % \
              (APP_NAME, VERSION, _("Developped by"), platform.python_version(),
               QT_VERSION_STR, PYQT_VERSION_STR, _("on"), platform.system()) )
        
    #------I/O
    def new_image(self):
        """Create a new image"""
        imagenew = ImageParamNew(title=_("Create a new image"))
        if not imagenew.edit(self):
            return
        image = ImageParam()
        image.title = imagenew.title
        if imagenew.type == 'zeros':
            image.data = np.zeros((imagenew.width, imagenew.height))
        elif imagenew.type == 'rand':
            image.data = np.random.randn(imagenew.width, imagenew.height)
        self.mainwidget.add_image(image)
    
    def open_image(self):
        """Open image file"""
        saved_in, saved_out, saved_err = sys.stdin, sys.stdout, sys.stderr
        sys.stdout = None
        filename = QFileDialog.getOpenFileName(self, _("Open"), "",
                           'Images (*.png *.jpg *.gif *.tif)\nDICOM (*.dcm)')
        sys.stdin, sys.stdout, sys.stderr = saved_in, saved_out, saved_err
        if filename:
            self.mainwidget.add_image_from_file(filename)
        
if __name__ == '__main__':
    from guidata import qapplication
    app = qapplication()
    window = MainWindow()
    window.show()
    app.exec_()
