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

from dataclasses import dataclass
from typing import Optional

from models.device_status import DeviceStatus
from view.widgets.channel_group_box.channel_group_box import ChannelGroupBox


@dataclass(frozen=True)
class DeviceLayouts:
    device_status: DeviceStatus
    speed_layout: Optional[ChannelGroupBox] = None
    lighting_layout: Optional[ChannelGroupBox] = None
    other_layout: Optional[ChannelGroupBox] = None