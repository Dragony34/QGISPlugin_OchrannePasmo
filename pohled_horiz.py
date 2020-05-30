# -*- coding: utf-8 -*-
"""
/***************************************************************************

                    QGIS plugin Ochranne pasmo horizontu

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
from PyQt5.QtWidgets import QAction
from .dialog import Dialog
from gdalconst import *
from osgeo.gdalnumeric import *
import numpy as np

class Ochranne_pasmo:
    # Implementace QGIS pluginu
    def __init__(self, iface):
        """Constructor.

        :param iface: An interface instance that will be passed to this class
            which provides the hook by which you can manipulate the QGIS
            application at run time.
        :type iface: QgsInterface
        """
        # Ulozeni reference na QGIS interface
        self.iface = iface
        self.canvas = iface.mapCanvas()
        self.vstupDialog = Dialog()

    def initGui(self):
        # Vytvoreni a konfigurace nastrojove listy pro spusteni pluginu
        self.toolbar = self.iface.addToolBar("Vypočítá ochranné pásmo horizontu")
        self.toolbar.setObjectName("Vypočítá ochranné pásmo horizontu")

        self.find_btn = QAction(QIcon(os.path.join(os.path.dirname(__file__), "horizont.png")), "Vypočítá ochranné pásmo horizontu", self.iface.mainWindow())
        self.toolbar.addActions([self.find_btn])
        self.find_btn.triggered.connect(self.vymezeniOchrannehoPasma)

    def vymezeniOchrannehoPasma(self):

        # Nacteni vstupu z dialogoveho okna
        self.vstupDialog.mQgsFileWidget.setStorageMode(3)
        self.vstupDialog.mQgsFileWidget.setFilter(("GeoTif (*.tif)"))
        self.vstupDialog.exec_()
        self.dmt = self.vstupDialog.mMapLayerComboBox.currentLayer().source()
        self.hrbetnice = self.vstupDialog.mMapLayerComboBox_2.currentLayer().source()
        velikostPasma = self.vstupDialog.lineEdit.text()
        soubor = self.vstupDialog.mQgsFileWidget.filePath()

        # Nacteni vstupnich rastru terenu a hrbetnic
        datasetTeren = gdal.Open(str(self.dmt), GA_ReadOnly)                           # otevre raster dataset pro cteni
        band1Teren = datasetTeren.GetRasterBand(1)
        rasterVysek = band1Teren.ReadAsArray()
        datasetHrbetnice = gdal.Open(str(self.hrbetnice), GA_ReadOnly)
        band1Hrbetnice = datasetHrbetnice.GetRasterBand(1)
        rasterHrbetnice = band1Hrbetnice.ReadAsArray()

        #Zjisteni velikosti rastru - poctu sloupcu a radku
        sloupce = datasetTeren.RasterXSize  # velikost rastru v x-ove souradnici - pocet sloupcu
        radky = datasetTeren.RasterYSize    # velikost rastru v y-ove souradnici - pocet radku

        # Vytvoreni prazdnych dvourozmernych rastru o velikosti odpovidajici poctu radku a sloupcu vstupnimu rastru vysek
        rasterSnizeni = np.ones((radky, sloupce))                           # vytvoreni rastru plneho jednicek
        rasterAkumulace = np.full(shape=(radky, sloupce), fill_value=-9999,
                                  dtype=np.int)                             # vytvoreni rastru plneho -9999 jako integer
        rasterOchrannePasmo = np.ones((radky, sloupce))
        rasterOchrannePasmo2 = np.full(shape=(radky, sloupce), fill_value=-9999, dtype=np.int)

        adresar = soubor[0:soubor.rfind('\\')]           # nalezne cestu k vytupnimu souboru
        # vytvoreni slozek pro mezivysledky a rasterove vystupy do mista kde deklaruju vystup
        cesta_mezidata = str(adresar) + "/mezidata"
        if not os.path.exists(cesta_mezidata):
            os.makedirs(cesta_mezidata)
        cesta_vystupy = str(adresar) + "/rasterove vystupy"
        if not os.path.exists(cesta_vystupy):
            os.makedirs(cesta_vystupy)

        # Vymezeni okraju rastru a naplneni okraju fixni hodnotou
        def upravaOkraju():
            for sloupec in range(0, sloupce):
                rasterSnizeni[0][sloupec] = 0                   # horni prazdny okrajovy radek pixelu naplneny nulami
                rasterSnizeni[radky - 1][sloupec] = 0           # dolni prazdny okrajovy radek pixelu naplneny nulami
                rasterAkumulace[0][sloupec] = -10000            # horni prazdny okrajovy radek pixelu naplneny -10000
                rasterAkumulace[radky - 1][sloupec] = -10000    # dolni prazdny okrajovy radek pixelu naplneny -10000
            for radek in range(0, radky):
                rasterSnizeni[radek][0] = 0                     # levy prazdny okrajovy sloupec pixelu naplneny nulami
                rasterSnizeni[radek][sloupce - 1] = 0           # pravy prazdny okrajovy sloupec pixelu naplneny nulami
                rasterAkumulace[radek][0] = -10000              # levy prazdny okrajovy sloupec pixelu naplneny -10000
                rasterAkumulace[radek][sloupce - 1] = -10000    # pravy prazdny okrajovy sloupec pixelu naplneny -10000

        upravaOkraju()

        # Metoda pro vypocet ubytku vysek terenu
        def snizeni():
            for sloupec in range(1, sloupce - 1):                           # smycka projizdi vsechny sloupce rastru
                for radek in range(1, radky - 1):                           # smycka projizdi vsechny radky rastru
                    Zpracovavana = rasterVysek[radek][sloupec]              # pixel ktery smycka pouziva k porovnani s okolnimi pixely
                    LevaHorni = rasterVysek[radek - 1][sloupec - 1]         # okolni pixel
                    StredniHorni = rasterVysek[radek - 1][sloupec]          # okolni pixel
                    PravaHorni = rasterVysek[radek - 1][sloupec + 1]        # okolni pixel
                    LevaStredni = rasterVysek[radek][sloupec - 1]           # okolni pixel
                    PravaStredni = rasterVysek[radek][sloupec + 1]          # okolni pixel
                    LevaDolni = rasterVysek[radek + 1][sloupec - 1]         # okolni pixel
                    StredniDolni = rasterVysek[radek + 1][sloupec]          # okolni pixel
                    PravaDolni = rasterVysek[radek + 1][sloupec + 1]        # okolni pixel

                    # nejvyssi snizeni = nejvetsi ubytek vysky z okolnich pixelu
                    maximalniHodnota = max(LevaDolni, LevaHorni, LevaStredni, StredniDolni, StredniHorni, PravaDolni,
                                           PravaStredni, PravaHorni)
                    rozdil = Zpracovavana - maximalniHodnota
                    if rozdil < 0:          # pokud bude rozdil zaporny
                        Snizeni = rozdil    # zapise se snizeni o kolik metru
                    else:                   # pokud nebude zaporny
                        Snizeni = 0         # tzn zpracovavana bunka je nejvyssi z okoli, tedy nulove snizeni vuci okoli
                    # vysledek se zapise od rastru snizeni
                    rasterSnizeni[radek][sloupec] = Snizeni

        snizeni()

        # nacteni pixelu (XY souradnic) kde jsou v rasteru hrbetnice
        okoliHrbetnic = []
        for sloupec in range(1, sloupce - 1):
            for radek in range(1, radky - 1):
                if rasterHrbetnice[radek][sloupec] != 0:        # pokud ma hrbetnice jinou hodnotu nez 0 (coz ma vzdy defaultne)
                    okoliHrbetnic.append((radek, sloupec))      # prida tento pixel do seznamu okoliHrbetnic
                    rasterSnizeni[radek][sloupec] = 0           # a v rasterSnizeni se nastavi pixel na danem miste na 0

        # Priprava rastru akumulace - nastaveni hodnoty 0 pro bunky kde jsou hrbetnice
        index = 0
        while index < len(okoliHrbetnic):
            radek = okoliHrbetnic[index][0]
            sloupec = okoliHrbetnic[index][1]
            rasterAkumulace[radek][sloupec] = 0                 # v rastru plnem -9999 najde a deklaruje pozici hrbetnice a da jim hodnotu 0
            index = index + 1

        # Metoda pro vypocet akumulace ubytku vysek od hrbetnice
        def akumulace():
            index = 0
            # cyklus je rizen poctem bunek v seznamu okoliHrbetnic kde uz jsou pred spustenim cyklu zapsane bunky hrbetnic
            # v prubehu cyklu jsou do seznamu pridavany okolni pixely, ktere doposud nebyly zpracovany v procesu akumulace ubytku vysek
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

                # pokud zpracovavana bunka je oznacenou bunkou (ma hodnotu -9998), tak jeste nebyla vyplnena a pocita se pro ni akumulace
                if Zpracovavana == -9998:   # -9998 je oznaceni pixelu, ktere jeste nebyly zpracovany akumulaci
                    akumulaceZOkoli = max(LevaDolni, LevaHorni, LevaStredni, StredniDolni, StredniHorni, PravaDolni,
                                             PravaStredni, PravaHorni)      # zapise se maximalni akumulace z okoli
                    # snizeni se pricte k akumulaci z okoli a zapise se do rastru akumulace
                    rasterAkumulace[radek][sloupec] = akumulaceZOkoli + rasterSnizeni[radek][sloupec]
                # pokud je dana bunka -9999, oznacim ji -9998, aby se pridala do seznamu okoliHrbetnic pro vypocet akumulace
                if LevaHorni == -9999:    # hodnota NODATA
                    rasterAkumulace[radek - 1][sloupec - 1] = -9998
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

        # Prochazeni rastru akumulace a klasifikace pixelu kde uz akumulace dosahla limitu pro ochranne pasmo
        def ochrannePasmo():
            ochranne_pasmo = int(velikostPasma)
            for sloupec in range(0, sloupce):
                for radek in range(0, radky):
                    if abs(rasterAkumulace[radek][
                               sloupec]) <= ochranne_pasmo:          # pokud je hodnota akumulace mensi nebo rovno limitu pro ochranne pasmo
                        rasterOchrannePasmo[radek][sloupec] = 1      # -> chraneno
                    else:
                        rasterOchrannePasmo[radek][sloupec] = -9999  # jinak -> nechraneno

        ochrannePasmo()

        # Rozsireni ochranneho pasma o jeden pixel okolo ochranneho pasma
        # z logickeho hlediska je toto potreba, protoze pri pouziti hrubeho terenu jeden pixel muze byt obrovsky a dana hranice ochranneho pasma
        # by mohla vest uprostred pixelu tzn cast pixelu je jeste v ochrannem pasmu ale tento kod uz by ho neoznacil jako chraneny -> proto rozsireni
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

        # ulozeni rastru do souboru .tif
        def ulozeniRastru(ds, soubor, dataOut):
            driver = gdal.GetDriverByName("GTiff")
            dsOut = driver.Create(soubor, ds.RasterXSize, ds.RasterYSize, 1, band1Teren.DataType)
            CopyDatasetInfo(ds, dsOut)
            bandOut = dsOut.GetRasterBand(1)
            BandWriteArray(bandOut, dataOut)

        ulozeniRastru(datasetTeren, (cesta_mezidata + "/ochr_pasmo1.tif"), rasterOchrannePasmo)
        ulozeniRastru(datasetTeren, (cesta_mezidata + "/snizeni.tif"), rasterSnizeni)
        ulozeniRastru(datasetTeren, (cesta_vystupy + "/ochr_pasmo_final.tif"), rasterOchrannePasmo2)
        ulozeniRastru(datasetTeren, (cesta_mezidata + "/akumulace.tif"), rasterAkumulace)
        ulozeniRastru(datasetTeren, soubor, rasterOchrannePasmo2)  # ulozi vystup tam kam zadam

    def unload(self):
        # odstraneni ikony z panelu nastroju QGISu
        del self.toolbar
