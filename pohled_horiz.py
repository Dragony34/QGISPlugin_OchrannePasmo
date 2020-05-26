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

        #Nacteni vstupnich rastru terenu a hrbetnic
        datasetTeren = gdal.Open(str(self.dmt), GA_ReadOnly)                                              #otevre raster dataset pro cteni
        band1Teren = datasetTeren.GetRasterBand(1)
        rasterVysek = band1Teren.ReadAsArray()
        datasetHrbetnice = gdal.Open(str(self.hrbetnice), GA_ReadOnly)
        band1Hrbetnice = datasetHrbetnice.GetRasterBand(1)
        rasterHrbetnice = band1Hrbetnice.ReadAsArray()

        # Print pro kontrolu obsahu rasteru
        print(rasterVysek)
        # print(rasterHrbetnice)

        #Zjisteni velikosti rastru - poctu sloupcu a radku
        sloupce = datasetTeren.RasterXSize  # velikost rastru v x-ove souradnici - pocet sloupcu
        radky = datasetTeren.RasterYSize

        # Vytvoreni prazdnych rastru - vytvoreni prazdneho dvourozmerneho pole rasterSnizeni, ... o velikosti
        # odpovidajici poctu radku a sloupcu vstupnimu rastru vysek
        rasterSnizeni = np.ones((radky, sloupce))
        rasterAkumulace = np.full(shape=(radky, sloupce), fill_value=-9999,
                                  dtype=np.int)  # vytvori raster plny -9999 jako integer
        rasterOchrannePasmo = np.ones((radky, sloupce))
        rasterOchrannePasmo2 = np.full(shape=(radky, sloupce), fill_value=-9999, dtype=np.int)

        adresar = soubor[0:soubor.rfind('\\')]
        # vytvoreni slozek pro mezivysledky do mista kde deklaruju vystup
        cesta_mezidata = str(adresar) + "/mezidata"
        if not os.path.exists(cesta_mezidata):
            os.makedirs(cesta_mezidata)
        cesta_vystupy = str(adresar) + "/rasterove vystupy"
        if not os.path.exists(cesta_vystupy):
            os.makedirs(cesta_vystupy)

        def upravaOkraju():
            for sloupec in range(0, sloupce):
                rasterSnizeni[0][sloupec] = 0  # horni prazdny radek okraj  (kdyztak prohodit znamenko)
                rasterSnizeni[radky - 1][sloupec] = 0  # spodni prazdny radek okraj (kdyztak prehodit znamenko)
                rasterAkumulace[0][sloupec] = -10000  # horni prazdny radek okraj  (kdyztak prohodit znamenko)
                rasterAkumulace[radky - 1][sloupec] = -10000  # spodni prazdny radek okraj (kdyztak prehodit znamenko)
            for radek in range(0, radky):
                rasterSnizeni[radek][0] = 0  # levy prazdny sloupec okraj
                rasterSnizeni[radek][sloupce - 1] = 0
                rasterAkumulace[radek][0] = -10000  # levy prazdny sloupec okraj
                rasterAkumulace[radek][sloupce - 1] = -10000
            # Pro kontrolu - ulozeni rastru terenu
            ulozeniDoAscii((cesta_mezidata + '/okrajeSnizeni.txt'), rasterSnizeni, radky, sloupce)
            ulozeniDoAscii((cesta_mezidata + '/okrajeAkumulace.txt'), rasterAkumulace, radky, sloupce)
            ulozeniDoAscii((cesta_mezidata + '/okrajeRastruVysek.txt'), rasterVysek, radky, sloupce)
            ulozeniDoAscii((cesta_mezidata + '/rasterHrbetnice.txt'), rasterHrbetnice, radky, sloupce)
            # ulozeniDoAscii('mezidata/rasterVysek.txt', rasterVysek, radky, sloupce)

        upravaOkraju()

        # print(rasterSnizeni)

        # Metoda pro vypocet ubytku vysek terenu
        def snizeni():
            for sloupec in range(1, sloupce - 1):  # smycka projizdi vsechny sloupce rastru
                for radek in range(1, radky - 1):  # smycka projizdi vsechny radky rastru
                    Zpracovavana = rasterVysek[radek][sloupec]
                    LevaHorni = rasterVysek[radek - 1][sloupec - 1]
                    StredniHorni = rasterVysek[radek - 1][sloupec]
                    PravaHorni = rasterVysek[radek - 1][sloupec + 1]
                    LevaStredni = rasterVysek[radek][sloupec - 1]
                    PravaStredni = rasterVysek[radek][sloupec + 1]
                    LevaDolni = rasterVysek[radek + 1][sloupec - 1]
                    StredniDolni = rasterVysek[radek + 1][sloupec]
                    PravaDolni = rasterVysek[radek + 1][sloupec + 1]

                    # nejvyssi snizeni = nejvetsi ubytek vysky
                    maximalniHodnota = max(LevaDolni, LevaHorni, LevaStredni, StredniDolni, StredniHorni, PravaDolni,
                                           PravaStredni, PravaHorni)
                    rozdil = Zpracovavana - maximalniHodnota
                    if rozdil < 0:  # pokud bude rozdil zaporny
                        Snizeni = rozdil  # zapise se snizeni o kolik metru
                    else:  # pokud ne
                        Snizeni = 0  # tzn zpracovavana bunka je nejvyssi z okoli, tedy nulove snizeni vuci okoli
                    rasterSnizeni[radek][sloupec] = Snizeni

        snizeni()
        ulozeniDoAscii((cesta_mezidata + '/rasterSnizeni.txt'), rasterSnizeni, radky, sloupce)

        # nacteni xy souradnic kde jsou v rasteru hrbetnice
        okoliHrbetnic = []
        for sloupec in range(1, sloupce - 1):
            for radek in range(1, radky - 1):
                if rasterHrbetnice[radek][sloupec] != 0:
                    okoliHrbetnic.append((radek, sloupec))
                    rasterSnizeni[radek][sloupec] = 0
        # print(okoliHrbetnic)

        # print(rasterSnizeni)

        index = 0
        while index < len(okoliHrbetnic):
            radek = okoliHrbetnic[index][0]
            sloupec = okoliHrbetnic[index][1]
            rasterAkumulace[radek][sloupec] = 0  # v rastru plném -9999 toto urci kde jsou hrbetnice a oznaci je nulou
            index = index + 1

        # print(rasterAkumulace)

        # Metoda pro vypocet akumulace ubytku vysek od hrbetnice
        def akumulace():
            index = 0
            while index < len(okoliHrbetnic):
                radek = okoliHrbetnic[index][0]
                sloupec = okoliHrbetnic[index][1]

                Zpracovavana = rasterAkumulace[radek][sloupec]
                LevaHorni = rasterAkumulace[radek - 1][sloupec - 1]
                StredniHorni = rasterAkumulace[radek - 1][sloupec]
                PravaHorni = rasterAkumulace[radek - 1][sloupec + 1]
                LevaStredni = rasterAkumulace[radek][sloupec - 1]
                PravaStredni = rasterAkumulace[radek][sloupec + 1]
                LevaDolni = rasterAkumulace[radek + 1][sloupec - 1]
                StredniDolni = rasterAkumulace[radek + 1][sloupec]
                PravaDolni = rasterAkumulace[radek + 1][sloupec + 1]

                # projizdime okoli bunek a pokud narazime na nevyplnenou bunku oznacime ji a pridame do seznamu
                # pokud zpracovavana bunka je nami oznacenou bunkou tak jeste nebyla vyplnena a musime ji vyplnit
                if Zpracovavana == -9998:  # -9998 je nase oznaceni proto, aby nasledna akumulace z okoli nebyla ovlivnena nasim oznacenim
                    # minAkumulaceZOkoli tedy bude stale ukazovat maximalni snizeni
                    minAkumulaceZOkoli = max(LevaDolni, LevaHorni, LevaStredni, StredniDolni, StredniHorni, PravaDolni,
                                             PravaStredni, PravaHorni)
                    rasterAkumulace[radek][sloupec] = minAkumulaceZOkoli + rasterSnizeni[radek][sloupec]
                if LevaHorni == -9999:  # NODATA
                    # LevaHroni (viz radek nize) je -9998 proto aby jsme tento bod znovu nepridavali do seznamu (dtto u ostatnich okolnich pixelu)
                    rasterAkumulace[radek - 1][sloupec - 1] = -9998  # LevaHorni
                    okoliHrbetnic.append((radek - 1, sloupec - 1))
                if StredniHorni == -9999:
                    rasterAkumulace[radek - 1][sloupec] = -9998
                    okoliHrbetnic.append((radek - 1, sloupec))
                if PravaHorni == -9999:
                    rasterAkumulace[radek - 1][sloupec + 1] = -9998
                    okoliHrbetnic.append((radek - 1, sloupec + 1))
                if LevaStredni == -9999:
                    rasterAkumulace[radek][sloupec - 1] = -9998
                    okoliHrbetnic.append((radek, sloupec - 1))
                if PravaStredni == -9999:
                    rasterAkumulace[radek][sloupec + 1] = -9998
                    okoliHrbetnic.append((radek, sloupec + 1))
                if LevaDolni == -9999:
                    rasterAkumulace[radek + 1][sloupec - 1] = -9998
                    okoliHrbetnic.append((radek + 1, sloupec - 1))
                if StredniDolni == -9999:
                    rasterAkumulace[radek + 1][sloupec] = -9998
                    okoliHrbetnic.append((radek + 1, sloupec))
                if PravaDolni == -9999:
                    rasterAkumulace[radek + 1][sloupec + 1] = -9998
                    okoliHrbetnic.append((radek + 1, sloupec + 1))
                index = index + 1

        akumulace()
        ulozeniDoAscii((cesta_mezidata + '/rasterAkumulace.txt'), rasterAkumulace, radky, sloupce)

        # print(rasterAkumulace)

        def ochrannePasmo():
            ochranne_pasmo = int(velikostPasma)
            for sloupec in range(0, sloupce):
                for radek in range(0, radky):
                    if abs(rasterAkumulace[radek][
                               sloupec]) <= ochranne_pasmo:  # pokud je velikost ochranneho pasma vetsi nez akumulace ubytku vysek
                        rasterOchrannePasmo[radek][sloupec] = 1  # -> chraneno
                    else:
                        rasterOchrannePasmo[radek][sloupec] = -9999  # jinak -> nechraneno

        ochrannePasmo()

        # rozsireni ochranneho pasma o jeden pixel okolo ochranneho pasma
        def rozsireniPasma():
            for sloupec in range(0, sloupce):
                for radek in range(0, radky):
                    if rasterOchrannePasmo[radek][sloupec] == 1:
                        rasterOchrannePasmo2[radek][sloupec] = rasterOchrannePasmo[radek][sloupec]
                        rasterOchrannePasmo2[radek - 1][sloupec - 1] = 1
                        rasterOchrannePasmo2[radek - 1][sloupec] = 1
                        rasterOchrannePasmo2[radek - 1][sloupec + 1] = 1
                        rasterOchrannePasmo2[radek][sloupec - 1] = 1
                        rasterOchrannePasmo2[radek][sloupec + 1] = 1
                        rasterOchrannePasmo2[radek + 1][sloupec - 1] = 1
                        rasterOchrannePasmo2[radek + 1][sloupec] = 1
                        rasterOchrannePasmo2[radek + 1][sloupec + 1] = 1

        rozsireniPasma()

        ulozeniDoAscii((cesta_mezidata + '/ochrannePasmo.txt'), rasterOchrannePasmo2, radky, sloupce)


        def ulozeniRastru(ds, soubor, dataOut):
            driver = gdal.GetDriverByName("GTiff")
            dsOut = driver.Create(soubor, ds.RasterXSize, ds.RasterYSize, 1, band1Teren.DataType)
            CopyDatasetInfo(ds, dsOut)
            bandOut = dsOut.GetRasterBand(1)
            BandWriteArray(bandOut, dataOut)

        ulozeniRastru(datasetTeren, (cesta_vystupy + "/ochr_pasmo1.tif"), rasterOchrannePasmo)
        ulozeniRastru(datasetTeren, (cesta_vystupy + "/snizeni.tif"), rasterSnizeni)
        ulozeniRastru(datasetTeren, (cesta_vystupy + "/ochr_pasmo_final.tif"), rasterOchrannePasmo2)
        ulozeniRastru(datasetTeren, (cesta_vystupy + "/akumulace.tif"), rasterAkumulace)
        ulozeniRastru(datasetTeren, soubor, rasterOchrannePasmo2)  # ulozi vystup tam kam zadám

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