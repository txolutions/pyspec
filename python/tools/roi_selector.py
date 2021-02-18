#!/usr/bin/env python
#
#******************************************************************************
#
#  @(#)roi_selector.py	6.2  10/01/20 CSS
#
#  "pyspec" Release 6
#
#  Copyright (c) 2020
#  by Certified Scientific Software.
#  All rights reserved.
#
#  Permission is hereby granted, free of charge, to any person obtaining a
#  copy of this software ("pyspec") and associated documentation files (the
#  "Software"), to deal in the Software without restriction, including
#  without limitation the rights to use, copy, modify, merge, publish,
#  distribute, sublicense, and/or sell copies of the Software, and to
#  permit persons to whom the Software is furnished to do so, subject to
#  the following conditions:
#
#  The above copyright notice and this permission notice shall be included
#  in all copies or substantial portions of the Software.
#
#  Neither the name of the copyright holder nor the names of its contributors
#  may be used to endorse or promote products derived from this software
#  without specific prior written permission.
#
#     * The software is provided "as is", without warranty of any   *
#     * kind, express or implied, including but not limited to the  *
#     * warranties of merchantability, fitness for a particular     *
#     * purpose and noninfringement.  In no event shall the authors *
#     * or copyright holders be liable for any claim, damages or    *
#     * other liability, whether in an action of contract, tort     *
#     * or otherwise, arising from, out of or in connection with    *
#     * the software or the use of other dealings in the software.  *
#
#******************************************************************************

import os
import sys
import copy

SPECD='/usr/local/lib/spec.d'
specd = os.environ.get('SPECD', SPECD)
sys.path.append( specd )

import numpy as np
from PIL import Image

from pyspec.graphics.QVariant import *
from pyspec.client.SpecCommand import SpecCommand
from pyspec.file import tiff

FigureCanvas = mpl_backend.FigureCanvasQTAgg
NavigationToolbar = mpl_backend.NavigationToolbar2QT

from matplotlib.figure import Figure
from matplotlib.colors import LogNorm
import matplotlib.patches as patches
import matplotlib.colorbar as colorbar

from matplotlib import rcParams
rcParams.update({'font.size': 12})

class RoiNavigationBar(NavigationToolbar):
    def __init__(self, plt_canvas,parent):
        NavigationToolbar.__init__(self, plt_canvas, parent)
        self._active = "ZOOM"
        self.zoom()

        next=None

        for c in self.findChildren(QToolButton):
            if next is None:
                next=c

            # Don't want to see subplots and customize
            if str(c.text()) in ('Subplots','Customize'):
                c.defaultAction().setVisible(False)
                continue

    def press_pan(self,event):
        if event.button == 3:
           self._button_pressed = None
           return

        NavigationToolbar.press_pan(self, event)

    def press_zoom(self,event):
        if event.button == 3:
           self._button_pressed = None
           return

        NavigationToolbar.press_zoom(self, event)

class RoiSelector(QWidget):

    image_dir = "/data/images"

    rows = 514
    cols = 1030

    tiffoffset = 4096

    help_text = "Navigate and ZOOM on image with help of LEFT button and Navigation Bar\n" \
           "Select ROI by clicking and dragging with RIGHT mouse button\n" \
           "Then click apply to send to spec"

    def __init__(self,*args):

        super(RoiSelector,self).__init__(*args)

        self.spec_app = None
        self.roiname = None
        self.xbeg = self.xend = self.ybeg = self.yend = None
        self.log_set = True
        self.data = None

        #self.load_data = self.loadDataAlbula
        #self.load_data = self.loadDataNumpy
        self.load_data = self.loadDataTiff

        #  other possible methods to load data
        #self.load_data = self.loadDataSpec
        #self.load_data = self.loadDataArray

        thelayout = QVBoxLayout()
        self.setLayout(thelayout)

        self.counter_layout = QHBoxLayout()
        self.color_layout = QHBoxLayout()
        self.bottom_layout = QHBoxLayout()

        self.selecting = False
        self.last_rect = None

        self.minval = None
        self.maxval = None

        # create a figure, add an axes area and make space for a colorbar
        self.fig = Figure(figsize=(300,200), dpi=100)
        self.axes = self.fig.add_subplot(111)

        self.caxes, kw = colorbar.make_axes(self.axes, location="right", pad=0.05, fraction=0.046)

        # set all font sizes to 9
        lblsz = 9
        self.axes.tick_params(labelsize=lblsz)    
        self.axes.tick_params(labelsize=lblsz)    
        self.caxes.tick_params(labelsize=lblsz)
        self.caxes.tick_params(labelsize=lblsz)

        # create a qt widget that contains the figure
        self.figcanvas = FigureCanvas(self.fig)
        self.figcanvas.setParent(self)
        self.figcanvas.setFocusPolicy(Qt.StrongFocus)
        self.figcanvas.setFocus()

        self.navbar = RoiNavigationBar(self.figcanvas, self)

        self.top_text = QLabel()
        self.top_text.setText(self.help_text)
        self.top_text.setStyleSheet("font-style: italic;")

        #
        counters_label = QLabel("Setting ROI for counter:")
        self.counter_label = QLabel()
        self.counter_combo = QComboBox()

        # add button and put everything in qt layout
        self.coordlab = QLabel()

        selection_label = QLabel("Selection:")
        self.selection_wid = QLineEdit()
        self.selection_wid.setText("----")
        self.selection_wid.setReadOnly(True)

        colormap_label = QLabel("Colormap:")
        self.colormap_combo = QComboBox()
        self.colormap_combo.insertItems(0,["hot","nipy_spectral","gist_rainbow","prism", "gist_ncar","binary","gray"])
        self.colormap_combo.currentIndexChanged.connect(self.colormap_changed)
        self.colormap = "hot"

        self.log_scale_rb = QRadioButton("Log")
        self.log_scale_rb.toggled.connect(self.log_scale_set)
        self.log_scale_rb.setChecked(self.log_set)

        minval_label = QLabel("Min:")
        self.minval_le = QLineEdit()
        self.minval_le.returnPressed.connect(self.minval_changed)
        maxval_label = QLabel("Max:")
        self.maxval_le = QLineEdit()
        self.maxval_le.returnPressed.connect(self.maxval_changed)

        change_but = QPushButton("Change Image")
        change_but.clicked.connect(self.load_image)

        apply_but = QPushButton("Apply")
        apply_but.clicked.connect(self.send_roi_to_spec)

        close_but = QPushButton("Close")
        close_but.clicked.connect(self.close_me)
 
 
        thelayout.addWidget(self.navbar)
        thelayout.addWidget(self.top_text)
        thelayout.addWidget(self.figcanvas)
        thelayout.addWidget(self.coordlab)

        thelayout.addLayout(self.counter_layout)
        thelayout.addLayout(self.color_layout)
        thelayout.addLayout(self.bottom_layout)

        self.counter_layout.addWidget(counters_label)
        self.counter_layout.addWidget(self.counter_label)
        self.counter_layout.addWidget(self.counter_combo)
        self.counter_layout.addWidget(selection_label)
        self.counter_layout.addWidget(self.selection_wid)

        self.color_layout.addWidget(self.log_scale_rb)
        self.color_layout.addWidget(colormap_label)
        self.color_layout.addWidget(self.colormap_combo)
        self.color_layout.addWidget(minval_label)
        self.color_layout.addWidget(self.minval_le)
        self.color_layout.addWidget(maxval_label)
        self.color_layout.addWidget(self.maxval_le)

        self.bottom_layout.addWidget(apply_but)
        self.bottom_layout.addWidget(change_but)
        self.bottom_layout.addWidget(close_but)
      
        self.counter_combo.currentIndexChanged.connect(self.counter_selected)

        # register for matplotlib events
        self.figcanvas.mpl_connect("button_press_event", self.start_selection)
        self.figcanvas.mpl_connect("button_release_event", self.end_selection)
        self.figcanvas.mpl_connect("motion_notify_event", self.mouse_moved)

    def set_spec(self, specname):
        self.spec_app = specname

        try:
            spec_cmd = SpecCommand(self.getcounters_macro, "localhost:%s" % self.spec_app)
            self.counters = spec_cmd()
        except:
            import traceback
            traceback.print_exc()
            self.counters = None

        if self.counters:
            self.cnts = self.counters.split(",")
            if len(self.cnts) > 1:
                self.counter_label.hide()
                self.counter_combo.insertItems(0,self.cnts)
            else:
                self.counter_combo.hide()

            self.set_roiname(self.cnts[0])

    def set_detector(self, prefix):
        self.setroi_macro = "%s_setroi" % prefix
        self.getroi_macro = "%s_getroi" % prefix
        self.getcounters_macro = "%s_getcounters" % prefix

    def set_roiname(self, roiname):
        if roiname is None:
            print("Ignoring set_roiname")
            return

        self.roiname = roiname
        if len(self.cnts) == 1:
            self.counter_label.setText(self.roiname)
        spec_cmd = SpecCommand(self.getroi_macro, "localhost:%s" % self.spec_app)
        roivals = spec_cmd(self.roiname)
        self.set_coords(roivals)

    def counter_selected(self,index):
        selected = str(self.counter_combo.currentText())
        self.set_roiname(selected)

    def colormap_changed(self,index):
        self.colormap = str(self.colormap_combo.currentText())
        self.show_image()

    def log_scale_set(self,flag):
        self.log_set = flag
        if self.data is None:
             return
        self.show_image()

    def minval_changed(self):
        try:
            self.minval = int(str(self.minval_le.text()))
            self.show_image()
        except:
            pass

    def maxval_changed(self):
        try:
            self.maxval = int(str(self.maxval_le.text()))
            self.show_image()
        except:
            import traceback
            traceback.print_exc()
            pass

    def set_coords(self,coords):
        self.xbeg = int(coords["begx"])
        self.ybeg = int(coords["begy"])
        self.xend = int(coords["endx"])
        self.yend = int(coords["endy"])

        selection_text = "(%s,%s) (%s,%s)" % (self.xbeg, self.ybeg, self.xend, self.yend)
        self.selection_wid.setText(selection_text)

        self.show_roi_rect()

    def show_roi_rect(self):
        if None in [self.xend, self.yend, self.xbeg, self.ybeg]:
             return
        self.width  = self.xend - self.xbeg
        self.height  = self.yend - self.ybeg

        x0,y0,w,h = self.xbeg,self.ybeg, self.width,self.height

        if self.last_rect:
            try:
                self.last_rect.remove() 
            except:
                #import traceback
                #traceback.print_exc()
                print("last_rect exists but it cannot be removed")

        self.last_rect = self.axes.add_patch(patches.Rectangle( (x0, y0), w, h, color="white", fill=False) )
        self.figcanvas.draw()

    def start_selection(self,ev):
        if ev.inaxes == self.axes and ev.button == 3:
            self.selecting = True
            self.xbeg, self.ybeg = int(round(ev.xdata)), int(round(ev.ydata))
            if self.last_rect:
                try:
                    self.last_rect.remove() 
                except:
                    print("last_rect exists but it cannot be removed")
                finally:
                    self.last_rect = None

    def mouse_moved(self,ev):
        # if selecting draw rectangle while moving
        # show position if on canvas
        if ev.inaxes == self.axes:
            x = int(round(ev.xdata))
            y = int(round(ev.ydata))
            z = self.img_data[y][x]
            pos_str = "x=%3.2f, y=%3.2f, value=%3.2f" % (x,y,z)
            self.coordlab.setText(pos_str)

            if self.selecting:
                if None in [x,y]:
                    return
                self.xend, self.yend = x,y
                self.show_roi_rect()

    def end_selection(self,ev):
        if self.selecting:
            # self.xend, self.yend = int(round(ev.xdata)), int(round(ev.ydata))
            self.selecting = False

            if self.xbeg > self.xend:
               self.xbeg, self.xend = self.xend, self.xbeg
            if self.ybeg > self.yend:
               self.ybeg, self.yend = self.yend, self.ybeg

            selection_text = "(%s,%s) (%s,%s)" % (self.xbeg, self.ybeg, self.xend, self.yend)
            self.selection_wid.setText(selection_text)

    def send_roi_to_spec(self):

        if None in [self.roiname, self.xbeg, self.xend, self.ybeg, self.yend]:
             print("Please select a ROI")
             return
             
        spec_cmd = SpecCommand(self.setroi_macro, "localhost:%s" % self.spec_app)
        try:
            spec_cmd(self.roiname, self.xbeg, self.ybeg, self.xend, self.yend)
        except:
            print("Failed sending command to spec")

        #self.close_me()

    def close_me(self):
        sys.exit(0)

    def load_image(self):
        self.last_rect = None 
        self.load_data()
        self.minval = self.data.min()
        self.maxval = self.data.max()
        self.show_image()

    def show_image(self):

        self.axes.clear() 
        
        self.img_data = copy.copy(self.data)

        if self.maxval is not None:
            # apply max threshold
            max_idx = self.img_data > self.maxval
            self.img_data[max_idx] = self.maxval
           
        if self.minval is not None:
            # apply max threshold
            min_idx = self.img_data < self.minval
            self.img_data[min_idx] = self.minval
           
        self.minval_le.setText(str(self.minval))
        self.maxval_le.setText(str(self.maxval))

        width, height = self.img_data.shape 
        y,x = np.mgrid[0:width,0:height]

        if self.log_set:
            # make sure there is no neg values.
            # with matplotlib > 2.0 this is done with SymLogNorm and no data manipulation
            zmin = self.img_data.min()
            zmax = self.img_data.max()
            if zmin <= 0 :
                self.img_data[:] = self.img_data[:] - (zmin -2 )
                zmin = self.img_data.min()

            im=self.axes.pcolormesh(x,y,self.img_data, norm=LogNorm(vmin=zmin, vmax=zmax))
        else:
            im=self.axes.pcolormesh(x,y,self.img_data)
        self.axes.axis([x.min(), x.max(), y.min(), y.max()])

        #im=self.axes.imshow(self.img_data, interpolation='nearest')
        ##self.axes.invert_yaxis()

        self.fig.colorbar(im,cax=self.caxes,orientation="vertical")
        im.set_cmap(self.colormap)
        self.axes.set_aspect("auto")
        self.show_roi_rect()
        self.figcanvas.draw()

        return

    def loadDataSpec(self):
        import datashm
        self.data = datashm.getdata(self.spec_app, "dat")

    def loadDataNumpy(self):
        print("Load data numpy")
        filename = self.get_filename()
        im = Image.open(filename)
        self.data = np.array(im)
        print("image loaded with shape %s- sum = %s" % (self.data.shape, self.data.sum()))

    def loadDataTiff(self):
        filename = self.get_filename()
        im = tiff.TiffFile(filename)
        i0 = im.series[0]
        self.data = i0.asarray()
        print("image loaded with shape %s- sum = %s" % (self.data.shape, self.data.sum()))

    def loadDataArray(self):
        import array
        filename = self.get_filename()
        fd = open(filename,"rb")
        fd.seek(self.tiffoffset)  # skip the header
        arr = array.array("I")
        arr.fromfile(fd,self.rows*self.cols)
        self.data = []
        for i in range(self.rows):
            self.data.append( arr[self.cols*i:self.cols*(i+1)].tolist() )

        return self.data

    def loadDataAlbula(self):
        sys.path.append("/home/specadm/spec_dist/dectris/albula/3.2/python")
        import dectris.albula

        filename = self.get_filename()

        if dectris.albula.versionMajor() == 3:
            series = dectris.albula.DImageSeries()
            series.open(str(filename))
            first = series.first()
            img0 = series[first]
        else:
            container = dectris.albula.DImageIntContainer()
            container.openSeries(filename)
            first = container.first()
            img0 = container[first]

        self.data = img0.data()

    def get_filename(self):
        answ = QFileDialog.getOpenFileName(self, "Open Image", self.image_dir, "*");
        print("answer is %s" % str(answ))
        if isinstance(answ, str):
            filename = str(answ)
        else:
            filename = answ[0]
        print("filename is %s" % str(filename))
        return filename


def printUsage():
    print("Usage: %s spec_app detector" % sys.argv[0])

def main():
    import sys

    nb_args = len(sys.argv)
    
    if nb_args != 3:
        print("Wrong usage")
        printUsage() 
        sys.exit(0)

    spec = sys.argv[1]
    detector = sys.argv[2]

    app = QApplication([])
    win = QMainWindow()
    wid = RoiSelector()


    win.setCentralWidget(wid)
    win.show()
    win.resize( 500, 700 )
    wid.set_detector(detector)
    wid.set_spec(spec)
    wid.load_image()

    try:
        sys.exit(app.exec_())
    except BaseException as e:
        import traceback
        print( traceback.print_exc() )
        print( str(e) )

if __name__ == '__main__':
    main()
