#  Coolero - monitor and control your cooling and other devices
#  Copyright (c) 2021  Guy Boldon
#  All credit for basis of the user interface (GUI) goes to: Wanderson M.Pimenta
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

from PySide6.QtCore import Signal, QPropertyAnimation, QEasingCurve
from PySide6.QtGui import Qt
from PySide6.QtWidgets import QWidget, QPushButton, QVBoxLayout, QFrame

from view.core.functions import Functions
from .py_div import PyDiv
from .py_left_menu_button import PyLeftMenuButton


class PyLeftMenu(QWidget):
    clicked = Signal(object)
    released = Signal(object)

    def __init__(
            self,
            parent: QWidget = None,
            app_parent: QWidget = None,
            dark_one: str = "#1b1e23",
            dark_three: str = "#21252d",
            dark_four: str = "#272c36",
            bg_one: str = "#2c313c",
            icon_color: str = "#c3ccdf",
            icon_color_hover: str = "#dce1ec",
            icon_color_pressed: str = "#edf0f5",
            icon_color_active: str = "#f5f6f9",
            context_color: str = "#568af2",
            text_foreground: str = "#8a95aa",
            text_active: str = "#dce1ec",
            duration_time: int = 500,
            radius: int = 8,
            minimum_width: int = 50,
            maximum_width: int = 240,
            icon_path: str = "icon_menu.svg",
            icon_path_close: str = "icon_menu_close.svg",
            toggle_text: str = "Hide Menu",
            toggle_tooltip: str = "Show menu"
    ) -> None:
        super().__init__()
        self._dark_one = dark_one
        self._dark_three = dark_three
        self._dark_four = dark_four
        self._bg_one = bg_one
        self._icon_color = icon_color
        self._icon_color_hover = icon_color_hover
        self._icon_color_pressed = icon_color_pressed
        self._icon_color_active = icon_color_active
        self._context_color = context_color
        self._text_foreground = text_foreground
        self._text_active = text_active
        self._duration_time = duration_time
        self._radius = radius
        self._minimum_width = minimum_width
        self._maximum_width = maximum_width
        self._icon_path = Functions.set_svg_icon(icon_path)
        self._icon_path_close = Functions.set_svg_icon(icon_path_close)
        # init later used properties:
        self.animation: QPropertyAnimation = None
        self.menu_button: PyLeftMenuButton = None
        self.left_menu_layout: QVBoxLayout = None
        self.bg: QFrame = None
        self.top_frame: QFrame = None
        self.bottom_frame: QFrame = None
        self._layout: QVBoxLayout = None
        self.top_layout: QVBoxLayout = None
        self.bottom_layout: QVBoxLayout = None

        self._parent = parent
        self._app_parent = app_parent

        self.setup_ui()

        self.bg.setStyleSheet(f"background: {dark_one}; border-radius: {radius};")

        self.toggle_button = PyLeftMenuButton(
            app_parent,
            text=toggle_text,
            tooltip_text=toggle_tooltip,
            dark_one=self._dark_one,
            dark_three=self._dark_three,
            dark_four=self._dark_four,
            bg_one=self._bg_one,
            icon_color=self._icon_color,
            icon_color_hover=self._icon_color_active,
            icon_color_pressed=self._icon_color_pressed,
            icon_color_active=self._icon_color_active,
            context_color=self._context_color,
            text_foreground=self._text_foreground,
            text_active=self._text_active,
            icon_path=icon_path,
        )
        self.toggle_button.clicked.connect(self.toggle_animation)
        self.div_top = PyDiv(dark_four)

        self.top_layout.addWidget(self.toggle_button)
        self.top_layout.addWidget(self.div_top)

        self.div_bottom = PyDiv(dark_four)
        self.div_bottom.hide()
        self.bottom_layout.addWidget(self.div_bottom)

    def add_menu_button(self,
                        btn_icon: str, btn_id: str, btn_text: str, btn_tooltip: str, show_top: bool, is_active: bool
                        ) -> None:
        self.menu_button = PyLeftMenuButton(
            self._app_parent,
            text=btn_text,
            btn_id=btn_id,
            tooltip_text=btn_tooltip,
            dark_one=self._dark_one,
            dark_three=self._dark_three,
            dark_four=self._dark_four,
            bg_one=self._bg_one,
            icon_color=self._icon_color,
            icon_color_hover=self._icon_color_active,
            icon_color_pressed=self._icon_color_pressed,
            icon_color_active=self._icon_color_active,
            context_color=self._context_color,
            text_foreground=self._text_foreground,
            text_active=self._text_active,
            icon_path=btn_icon,
            is_active=is_active
        )
        self.menu_button.clicked.connect(self.btn_clicked)
        self.menu_button.released.connect(self.btn_released)

        if show_top:
            self.top_layout.addWidget(self.menu_button)
        else:
            self.div_bottom.show()
            self.bottom_layout.addWidget(self.menu_button)

    # left menu emit signals
    def btn_clicked(self) -> None:
        self.clicked.emit(self.menu_button)

    def btn_released(self) -> None:
        self.released.emit(self.menu_button)

    # expand / retract left menu
    def toggle_animation(self) -> None:
        self.animation = QPropertyAnimation(self._parent, b"minimumWidth")
        self.animation.stop()
        if self.width() <= self._minimum_width:
            self.animation.setStartValue(self.width())
            self.animation.setEndValue(self._maximum_width)
            self.toggle_button.set_active_toggle(True)
            self.toggle_button.set_icon(self._icon_path_close)
        else:
            self.animation.setStartValue(self.width())
            self.animation.setEndValue(self._minimum_width)
            self.toggle_button.set_active_toggle(False)
            self.toggle_button.set_icon(self._icon_path)
        self.animation.setEasingCurve(QEasingCurve.InOutCubic)
        self.animation.setDuration(self._duration_time)
        self.animation.start()

    def select_only_one(self, widget: str) -> None:
        """Selects only one button"""
        for btn in self.findChildren(QPushButton):
            if btn.objectName() == widget:
                btn.set_active(True)
            else:
                btn.set_active(False)

    def select_only_one_tab(self, btn_object_name: str) -> None:
        """Selects only one tab button"""
        for btn in self.findChildren(QPushButton):
            if btn.objectName() == btn_object_name:
                btn.set_active_tab(True)
            else:
                btn.set_active_tab(False)

    def deselect_all(self) -> None:
        """Deselects all buttons"""
        for btn in self.findChildren(QPushButton):
            btn.set_active(False)

    def deselect_all_tab(self) -> None:
        """Deselects all tab buttons"""
        for btn in self.findChildren(QPushButton):
            btn.set_active_tab(False)

    def setup_ui(self) -> None:
        self.left_menu_layout = QVBoxLayout(self)
        self.left_menu_layout.setContentsMargins(0, 0, 0, 0)

        self.bg = QFrame()
        self.top_frame = QFrame()
        self.bottom_frame = QFrame()

        self._layout = QVBoxLayout(self.bg)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self.top_layout = QVBoxLayout(self.top_frame)
        self.top_layout.setContentsMargins(0, 0, 0, 0)
        self.top_layout.setSpacing(1)
        self.bottom_layout = QVBoxLayout(self.bottom_frame)
        self.bottom_layout.setContentsMargins(0, 0, 0, 8)
        self.bottom_layout.setSpacing(1)
        self._layout.addWidget(self.top_frame, 0, Qt.AlignTop)
        self._layout.addWidget(self.bottom_frame, 0, Qt.AlignBottom)
        self.left_menu_layout.addWidget(self.bg)