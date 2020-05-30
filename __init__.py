# -*- coding: utf-8 -*-
"""
/***************************************************************************
 pohled_horiz
                    QGIS plugin Ochranne pasmo horizontu

 Vypočítá ochranné pásmo horizontu

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
"""

def classFactory(iface):
    """Load Ochranne_pasmo class from file pohled_horiz.

    :param iface: A QGIS interface instance.
    :type iface: QgsInterface
    """
    from .pohled_horiz import Ochranne_pasmo
    return Ochranne_pasmo(iface)