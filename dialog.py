# -*- coding: utf-8 -*-
import os
from PyQt5 import uic
from PyQt5 import QtWidgets # Widget = komponenta

FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'dialog.ui'))

class Dialog(QtWidgets.QDialog, FORM_CLASS):
    def __init__(self, parent=None):
        """Constructor."""
        super(Dialog, self).__init__(parent)
        # Spusti uzivatelske rozhrani z Qt Designeru
        self.setupUi(self)
        self.SaveFile = 3
