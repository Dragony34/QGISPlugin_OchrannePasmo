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
from .dialog import Dialog
from qgis.core import *
from qgis.gui import *
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

        # Zjisteni adresare, do ktereho se bude vypisovat vystup - budou se do něj ukladat i mezivystupy
        adresar = soubor[0:soubor.rfind('\\')]
        # vytvoreni slozek pro mezivysledky do mista kde deklaruju vystup
        cesta_mezidata = str(adresar) + "/mezidata"
        if not os.path.exists(cesta_mezidata):
            os.makedirs(cesta_mezidata)
        cesta_vystupy = str(adresar) + "/rasterove vystupy"
        if not os.path.exists(cesta_vystupy):
            os.makedirs(cesta_vystupy)

        # Nacteni vstupnich rastru terenu a hrbetnic
        datasetTeren = gdal.Open(str(self.dmt), GA_ReadOnly)  # otevre raster dataset pro cteni
        bandTeren = datasetTeren.GetRasterBand(1)
        rasterVysek = bandTeren.ReadAsArray()
        datasetHrbetnice = gdal.Open(str(self.hrbetnice), GA_ReadOnly)
        band1Hrbetnice = datasetHrbetnice.GetRasterBand(1)
        rasterHrbetnice = band1Hrbetnice.ReadAsArray()

        # Print pro kontrolu obsahu rasteru
        # print(rasterVysek)
        # print(rasterHrbetnice)

        # Zjisteni velikosti rastru - poctu sloupcu a radku
        sloupce = datasetTeren.RasterXSize  # velikost rastru v x-ove souradnici - pocet sloupcu
        radky = datasetTeren.RasterYSize

        # Vytvoreni prazdneho dvourozmerneho pole o velikosti odpovidajici poctu radku a sloupcu vstupnimu rastru vysek

        rasterOchrannePasmo = np.full(shape=(radky, sloupce), fill_value=-9999, dtype=np.int)  # vytvori raster plny -9999 jako integer

        def ulozeniRastru(ds, soubor, dataOut):
            driver = gdal.GetDriverByName("GTiff")
            dsOut = driver.Create(soubor, ds.RasterXSize, ds.RasterYSize, 1, bandTeren.DataType)
            CopyDatasetInfo(ds, dsOut)
            bandOut = dsOut.GetRasterBand(1)
            BandWriteArray(bandOut, dataOut)

        def upravaOkraju():
            for sloupec in range(0, sloupce):
                rasterVysek[0][sloupec] = -9999  # horni prazdny radek okraj  (kdyztak prohodit znamenko)
                rasterVysek[radky - 1][sloupec] = -9999  # spodni prazdny radek okraj (kdyztak prehodit znamenko)
            for radek in range(0, radky):
                rasterVysek[radek][0] = -9999  # levy prazdny sloupec okraj
                rasterVysek[radek][sloupce - 1] = -9999

            ulozeniDoAscii((cesta_mezidata + '/okrajeRastruVysek.txt'), rasterVysek, radky, sloupce)

        upravaOkraju()

        # nacteni xy souradnic kde jsou v rasteru hrbetnice
        bodyHrbetnic = []
        for sloupec in range(1, sloupce - 1):
            for radek in range(1, radky - 1):
                if rasterHrbetnice[radek][sloupec] == 0:
                    bodyHrbetnic.append((radek, sloupec))

        ochrannePasmo = []
        def pasmo():
            index = 0
            while index < len(bodyHrbetnic):
                rasterPasmoBodHrbet = np.ones((radky, sloupce)) #na zacatku cyklu je pomocny raster generovan znovu. Pri finalnim mergi pak tak resi sporne
                                                                # body, kde z jednoho bodu hrbetnice by v ochrannem pasmu byt meli a z druheho ne
                okoliBoduHrbetnice = []
                souradnice = bodyHrbetnic[index]
                okoliBoduHrbetnice.append(souradnice)
                vyskaBoduHrbetnice = rasterVysek[souradnice[0]][souradnice[1]]
                indexOkoli = 0
                while indexOkoli < len(okoliBoduHrbetnice):
                    radek = okoliBoduHrbetnice[indexOkoli][0]
                    sloupec = okoliBoduHrbetnice[indexOkoli][1]
                    ochrannePasmo.append((radek, sloupec))      #=Zpracovavana
                    #LevaHorni
                    rozdil = vyskaBoduHrbetnice - rasterVysek[radek - 1][sloupec - 1]
                    if rozdil <= int(velikostPasma):
                        if rozdil >= 0:    #pokud rozdil nebude zaporny, tzn jdeme nad vysku bodu hrbetnice, tzn jdeme do kopce (klidne i uprostred svahu)
                            if rasterPasmoBodHrbet[radek - 1][sloupec - 1] == 1:
                                okoliBoduHrbetnice.append((radek - 1, sloupec - 1))
                                rasterPasmoBodHrbet[radek - 1][sloupec - 1] = 0         #oznaceno ze uz jsme ten urcity pixel projeli
                    #StredniHorni
                    rozdil = vyskaBoduHrbetnice - rasterVysek[radek - 1][sloupec]
                    if rozdil <= int(velikostPasma):
                        if rozdil >= 0:
                            if rasterPasmoBodHrbet[radek - 1][sloupec] == 1:
                                okoliBoduHrbetnice.append((radek - 1, sloupec))
                                rasterPasmoBodHrbet[radek - 1][sloupec] = 0
                    #PravaHorni
                    rozdil = vyskaBoduHrbetnice - rasterVysek[radek - 1][sloupec + 1]
                    if rozdil <= int(velikostPasma):
                        if rozdil >= 0:
                            if rasterPasmoBodHrbet[radek - 1][sloupec + 1] == 1:
                                okoliBoduHrbetnice.append((radek - 1, sloupec + 1))
                                rasterPasmoBodHrbet[radek - 1][sloupec + 1] = 0
                    #LevaStredni
                    rozdil = vyskaBoduHrbetnice - rasterVysek[radek][sloupec - 1]
                    if rozdil <= int(velikostPasma):
                        if rozdil >= 0:
                            if rasterPasmoBodHrbet[radek][sloupec - 1] == 1:
                                okoliBoduHrbetnice.append((radek, sloupec - 1))
                                rasterPasmoBodHrbet[radek][sloupec - 1] = 0
                    #PravaStredni
                    rozdil = vyskaBoduHrbetnice - rasterVysek[radek][sloupec + 1]
                    if rozdil <= int(velikostPasma):
                        if rozdil >= 0:
                            if rasterPasmoBodHrbet[radek][sloupec + 1] == 1:
                                okoliBoduHrbetnice.append((radek, sloupec + 1))
                                rasterPasmoBodHrbet[radek][sloupec + 1] = 0
                    #LevaDolni
                    rozdil = vyskaBoduHrbetnice - rasterVysek[radek + 1][sloupec - 1]
                    if rozdil <= int(velikostPasma):
                        if rozdil >= 0:
                            if rasterPasmoBodHrbet[radek + 1][sloupec - 1] == 1:
                                okoliBoduHrbetnice.append((radek + 1, sloupec - 1))
                                rasterPasmoBodHrbet[radek + 1][sloupec - 1] = 0
                    #StredniDolni
                    rozdil = vyskaBoduHrbetnice - rasterVysek[radek + 1][sloupec]
                    if rozdil <= int(velikostPasma):
                        if rozdil >= 0:
                            if rasterPasmoBodHrbet[radek + 1][sloupec] == 1:
                                okoliBoduHrbetnice.append((radek + 1, sloupec))
                                rasterPasmoBodHrbet[radek + 1][sloupec] = 0
                    #PravaDolni
                    rozdil = vyskaBoduHrbetnice - rasterVysek[radek + 1][sloupec + 1]
                    if rozdil <= int(velikostPasma):
                        if rozdil >= 0:
                            if rasterPasmoBodHrbet[radek + 1][sloupec + 1] == 1:
                                okoliBoduHrbetnice.append((radek + 1, sloupec + 1))
                                rasterPasmoBodHrbet[radek + 1][sloupec + 1] = 0

                    indexOkoli = indexOkoli + 1

                #Print jednoho z ochrannych pasem pro jeden bod hrbetnice
                if index == 0:      #pokud bude jenom vrchol tak 0, pokud linie bodu (hrbetnice), tak zobrazi prvni z nich
                    ulozeniRastru(datasetTeren, (cesta_mezidata + "/pasmoBoduHrbet.tif"), rasterPasmoBodHrbet)

                index = index + 1

        pasmo()

        #Zapis ochranneho pasma do rastru (merge predchozich pomocnych rasteru vsech bodu hrbetnice)
        indexPasmo = 0
        while indexPasmo < len(ochrannePasmo):
            radek = ochrannePasmo[indexPasmo][0]
            sloupec = ochrannePasmo[indexPasmo][1]
            rasterOchrannePasmo[radek][sloupec] = 1
            indexPasmo = indexPasmo + 1


        ulozeniRastru(datasetTeren, (cesta_vystupy + "/ochr_pasmo.tif"), rasterOchrannePasmo)
        ulozeniRastru(datasetTeren, soubor, rasterOchrannePasmo)    #ulozi vystup tam kam zadám

    def unload(self):
        """Removes the icon (toolbar) from QGIS GUI."""
        # remove the toolbar
        del self.toolbar


def ulozeniDoAscii(soubor, pole, radky, sloupce):
    soubor = open(soubor, 'w')
    soubor.write("ncols          " + str(sloupce) + '\n')
    soubor.write("nrows          " + str(radky) + '\n')
    soubor.write("xllcorner     -475650.97663479" + '\n')
    soubor.write("yllcorner     -1134520.3457931" + '\n')
    soubor.write("cellsize      200" + '\n')
    soubor.write("NODATA_value  -9999" + '\n')
    for sloupec in range(0, sloupce):
        for radek in range(0, radky):
            soubor.write(str(pole[radek][sloupec]) + " ")
        soubor.write('\n')
    soubor.close()