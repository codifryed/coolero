#  Coolero - monitor and control your cooling and other devices
#  Copyright (c) 2021  Guy Boldon
#  |
#  This program is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#  |
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#  |
#  You should have received a copy of the GNU General Public License
#  along with this program.  If not, see <https://www.gnu.org/licenses/>.
# ----------------------------------------------------------------------------------------------------------------------

import logging

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QMessageBox, QGraphicsDropShadowEffect

from dialogs.dialog_style import DIALOG_STYLE
from settings import Settings

_LOG = logging.getLogger(__name__)


class LegacyKraken2FirmwareDialog(QMessageBox):

    def __init__(self) -> None:
        super().__init__()
        self._dialog_style = DIALOG_STYLE.format(
            _text_size=Settings.app["font"]["text_size"],
            _font_family=Settings.app["font"]["family"],
            _text_color=Settings.theme["app_color"]["text_foreground"],
            _bg_color=Settings.theme["app_color"]["bg_one"]
        )
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(20)
        shadow.setXOffset(0)
        shadow.setYOffset(0)
        shadow.setColor(QColor(0, 0, 0, 160))
        self.setGraphicsEffect(shadow)
        self.setTextFormat(Qt.TextFormat.RichText)
        self.setWindowTitle('Upgrade Firmware')
        self.setText(
            '''
            <h3><center>Firmware upgrade needed!</center></h3>
            <p>Older Kraken (X42, X52, X62 or X72) units still running firmware 2.x do not support variable speed
            profiles.</p>
            '''
        )
        self.setInformativeText(
            '''
            <p>Please upgrade your firmware to at least version 5.x using the latest official NZXT CAM
            software for Windows.</p>
            '''
        )
        self.setStandardButtons(QMessageBox.Yes)
        self.setDefaultButton(QMessageBox.Yes)
        self.setButtonText(QMessageBox.Yes, "Ok, I'll do it.")
        self.setStyleSheet(self._dialog_style)

    def warn(self) -> int:
        return self.exec()