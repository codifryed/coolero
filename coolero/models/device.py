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

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum, auto
from typing import Optional, List, Type, Dict

from liquidctl.driver.base import BaseDriver

from models.device_info import DeviceInfo
from models.status import Status
from settings import Settings


class DeviceType(Enum):
    CPU = auto()
    GPU = auto()
    LIQUIDCTL = auto()


@dataclass(unsafe_hash=True)  # special care is taken so that this class is indeed hashable
class Device:
    """This is a model class containing both specific device settings and information"""

    _name: str
    _type: DeviceType
    _status_current: Status = field(compare=False)
    _status_history: List[Status] = field(init=False, default_factory=list, repr=False, compare=False)
    _colors: Dict[str, str] = field(default_factory=dict, compare=False)
    _lc_device_id: Optional[int] = None
    _lc_driver_type: Optional[Type[BaseDriver]] = None
    _lc_init_firmware_version: Optional[str] = None
    _info: Optional[DeviceInfo] = field(default=None, compare=False)

    @property
    def name(self) -> str:
        return self._name

    @property
    def name_short(self) -> str:
        return self._name.partition(' (')[0]

    @property
    def type(self) -> DeviceType:
        return self._type

    @property
    def colors(self) -> Dict[str, str]:
        return self._colors

    def color(self, channel_name: str) -> str:
        return self._colors.get(channel_name, str(Settings.theme['app_color']['context_color']))

    @property
    def status(self) -> Status:
        return self._status_current

    @status.setter
    def status(self, status: Status) -> None:
        self._status_current = status
        self._append_status_to_history(status)

    @property
    def status_history(self) -> List[Status]:
        return self._status_history

    @property
    def lc_driver_type(self) -> Optional[BaseDriver]:
        return self._lc_driver_type

    @property
    def lc_device_id(self) -> Optional[int]:
        return self._lc_device_id

    @property
    def lc_init_firmware_version(self) -> Optional[str]:
        """On some devices the firmware version only comes on initialization"""
        return self._lc_init_firmware_version

    @property
    def info(self) -> Optional[DeviceInfo]:
        """return the extracted device information, like available channels, color modes, etc"""
        return self._info

    def _append_status_to_history(self, status: Status) -> None:
        self._status_history.append(status)
        time_delta: timedelta = datetime.now() - self._status_history[0].timestamp
        if time_delta.days > 0:  # remove status history if older than a day to keep list from exploding
            self._status_history.pop(0)
