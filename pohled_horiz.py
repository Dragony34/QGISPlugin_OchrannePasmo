# -*- coding: utf-8 -*-
"""
/***************************************************************************

                                 A QGIS plugin

 XXXXX

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
"""
import os
import sys
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QAction, QLineEdit, QCompleter, QMessageBox, QProgressBar
from qgis.core import *
from qgis.gui import *
from .dialog import Dialog
from osgeo import gdal
from gdalconst import *
from osgeo.gdalnumeric import *
import numpy as np

class Ochranne_pasmo:
    """QGIS Plugin Implementation."""

    def __init__(self, iface):
        """Constructor.

        :param iface: An interface instance that will be passed to this class
            which provides the hook by which you can manipulate the QGIS
            application at run time.
        :type iface: QgsInterface
        """
        # Save reference to the QGIS interface
        self.iface = iface
        self.canvas = iface.mapCanvas()
        self.vstupDialog = Dialog()

    def initGui(self):
        """Create the menu entries and toolbar icons inside the QGIS GUI."""

        # Configure toolbar widget
        self.toolbar = self.iface.addToolBar("Shows view horizon from point")
        self.toolbar.setObjectName("Shows view horizon from point")

        self.find_btn = QAction(QIcon(os.path.join(os.path.dirname(__file__), "horizont.png")), "Show view horizon", self.iface.mainWindow())
        self.toolbar.addActions([self.find_btn])
        self.find_btn.triggered.connect(self.vymezeniOchrannehoPasma)

    def vymezeniOchrannehoPasma(self):

        #Nacteni vstupu z dialogoveho okna
        self.vstupDialog.mQgsFileWidget.setStorageMode(3)
        self.vstupDialog.mQgsFileWidget.setFilter(("GeoTif (*.tif)"))
        self.vstupDialog.exec_()
        self.dmt = self.vstupDialog.mMapLayerComboBox.currentLayer().source()
        self.hrbetnice = self.vstupDialog.mMapLayerComboBox_2.currentLayer().source()
        velikostPasma = self.vstupDialog.lineEdit.text()
        soubor = self.vstupDialog.mQgsFileWidget.filePath()
        # Pro kontrolu - vypis souboru, kam se bude ukladat vysledek v zalozce PohledHoriz v QGIS
        print("Vystup se bude ukladat do:" + str(soubor), "PohledHoriz")
        #        QgsMessageLog.logMessage("Vystup se bude ukladat do:" + str(soubor), 'PohledHoriz')
        # Zjisteni adresare, do ktereho se bude vypisovat vystup - budou se do něj ukladat i mezivystupy
        adresar = soubor[0:soubor.rfind('\\')]
        # Pro kontrolu - vypis adresare, kam se budou ukladat mezivysledky v zalozce PohledHoriz v QGIS
        print("Mezivysledky se budou ukladat do adresare:" + str(adresar), "PohledHoriz")
        #        QgsMessageLog.logMessage("Mezivysledky se budou ukladat do adresare:" + str(adresar), 'PohledHoriz')

        #Nacteni vstupnich rastru terenu a hrbetnic
        datasetTeren = gdal.Open(str(self.dmt), GA_ReadOnly)                                              #otevre raster dataset pro cteni
        band1Teren = datasetTeren.GetRasterBand(1)
        rasterVysek = band1Teren.ReadAsArray()
        datasetHrbetnice = gdal.Open(str(self.hrbetnice), GA_ReadOnly)
        band1Hrbetnice = datasetHrbetnice.GetRasterBand(1)
        rasterHrbetnice = band1Hrbetnice.ReadAsArray()

        #Zjisteni velikosti rastru - poctu sloupcu a radku
        self.sloupce = datasetTeren.RasterXSize
        self.radky = datasetTeren.RasterYSize
        sloupce = datasetTeren.RasterXSize  # velikost rastru v x-ove souradnici - pocet sloupcu
        radky = datasetTeren.RasterYSize

        #Pro kontrolu - vypis poctu sloupcu a radku v zalozce PohledHoriz v QGIS
        print("sloupcu:" + str(sloupce), "PohledHoriz")
        #       QgsMessageLog.logMessage("sloupcu:" + str(sloupce), 'PohledHoriz')#velikost rastru v y-ove souradnici - pocet radku
        print("radku:" + str(radky), "PohledHoriz")
        #        QgsMessageLog.logMessage("radku:" + str(radky), 'PohledHoriz')

        #Vytvoreni prazdnych rastru - vytvoreni prazdneho dvourozmerneho pole rasterSnizeni, ... o velikosti odpovidajici poctu radku a sloupcu vstupnimu rastru vysek
        rasterSnizeni = np.ones((radky, sloupce))
        rasterAkumulace = np.ones((radky, sloupce))
        rasterAkumulaceDalsi = np.ones((radky, sloupce))
        rasterOchrannePasmo = np.ones((radky, sloupce))

        #minimalniHodnota = -9999

        ##Metoda pro pripravu okraju rastru - je potreba?
        def upravaOkraju():
            # doplnit kod pro upravu okraju rastru (vynulovani hodnot na okrajich
            print("Upravuji okraje rastru", 'PohledHoriz')
            #       QgsMessageLog.logMessage("Upravuji okraje rastru", 'PohledHoriz')
            # Pro kontrolu - ulozeni rastru terenu
            ulozeniRastru(self, datasetTeren, adresar + "\\vstupniTeren.tif", rasterVysek)

        ##Metoda pro vypocet ubytku vysek terenu
        def snizeni():
            # doplnit kod pro vypocet snizeni (treci povrch pro analyzu sireni)
            # jako vstup se pouzije rasterVysek, vystup bude rasterSnizeni
            print("Pocitam ubytky vysek terenu", 'PohledHoriz')
            #       QgsMessageLog.logMessage("Pocitam ubytky vysek terenu", 'PohledHoriz')
            # Pro kontrolu - ulozeni rastru snizeni
            ulozeniRastru(self, datasetTeren, adresar + "\\ubytkyVysek.tif", rasterSnizeni)

        ##Metoda pro vypocet akumulace ubytku vysek od hrbetnice
        def akumulace():
            # doplnit kod pro vypocet akumulace (cost v ramci analyzy sireni)
            # jako vstupy se pouziji rasterSnizeni a rasterHrbetnice, vystup bude rasterAkumulace
            print("Pocitam akumulaci", 'PohledHoriz')
            #       QgsMessageLog.logMessage("Pocitam akumulaci", 'PohledHoriz')
            # Pro kontrolu - ulozeni rastru akumulace
            ulozeniRastru(self, datasetTeren, adresar  + "\\akumulace.tif", rasterAkumulace)

        ##Metoda pro vypocet ochranneho pasma
        def ochrannePasmo():
            # doplnit kod pro vypocet ochranneho pasma
            # jako vstupy se pouziji rasterAkumulace a velikostPasma, vystup bude rasterOchrannePasmo
            print("Pocitam ochranne pasmo", 'PohledHoriz')
            #QgsMessageLog.logMessage("Pocitam ochranne pasmo", 'PohledHoriz')
            ulozeniRastru(self, datasetTeren, soubor, rasterOchrannePasmo)

        def ulozeniRastru(self, ds, soubor, dataOut):
            driver = gdal.GetDriverByName("GTiff")
            dsOut = driver.Create(soubor, ds.RasterXSize, ds.RasterYSize, 1, band1Teren.DataType)
            CopyDatasetInfo(ds, dsOut)
            bandOut = dsOut.GetRasterBand(1)
            BandWriteArray(bandOut, dataOut)

        upravaOkraju()
        snizeni()
        akumulace()
        ochrannePasmo()

    def unload(self):
        """Removes the icon (toolbar) from QGIS GUI."""
        # remove the toolbar
        del self.toolbar