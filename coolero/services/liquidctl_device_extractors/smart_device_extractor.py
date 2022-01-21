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
from typing import List, Dict, Any

from liquidctl.driver import smart_device
from liquidctl.driver.smart_device import SmartDevice

from models.channel_info import ChannelInfo
from models.device_info import DeviceInfo
from models.lighting_mode import LightingMode
from models.speed_options import SpeedOptions
from models.status import TempStatus, ChannelStatus
from services.liquidctl_device_extractors import LiquidctlDeviceInfoExtractor

_LOG = logging.getLogger(__name__)


# pylint: disable=protected-access
class SmartDeviceExtractor(LiquidctlDeviceInfoExtractor):
    supported_driver = SmartDevice
    _channels: Dict[str, ChannelInfo] = {}
    _lighting_speeds: List[str] = []

    @classmethod
    def extract_info(cls, device_instance: SmartDevice) -> DeviceInfo:
        for channel_name, (_, min_duty, max_duty) in device_instance._speed_channels.items():
            cls._channels[channel_name] = ChannelInfo(
                speed_options=SpeedOptions(
                    min_duty=min_duty,
                    max_duty=max_duty,
                    profiles_enabled=False,
                    fixed_enabled=True,
                )
            )
        # special channel 'sync' for all fans
        if len(cls._channels.keys()) > 1:
            cls._channels['sync'] = ChannelInfo(
                speed_options=SpeedOptions(
                    min_duty=smart_device._MIN_DUTY,
                    max_duty=smart_device._MAX_DUTY,
                    profiles_enabled=False,
                    fixed_enabled=True
                )
            )

        for channel_name in device_instance._color_channels.keys():
            cls._channels[channel_name] = ChannelInfo(
                lighting_modes=cls._get_filtered_color_channel_modes(device_instance)
            )

        cls._lighting_speeds = list(smart_device._ANIMATION_SPEEDS.keys())

        return DeviceInfo(
            channels=cls._channels,
            lighting_speeds=cls._lighting_speeds,
        )

    @classmethod
    def _get_filtered_color_channel_modes(cls, device_instance: SmartDevice) -> List[LightingMode]:
        channel_modes = []
        for mode_name, (_, _, moving_byte, min_colors, max_colors) in device_instance._COLOR_MODES.items():
            # todo: direction(backwards) needs to done by hand per mode
            if 'backwards' not in mode_name:  # remove deprecated modes
                channel_modes.append(LightingMode(mode_name, min_colors, max_colors, (moving_byte == 0x10), False))
        return channel_modes

    @classmethod
    def _get_temperatures(cls, status_dict: Dict[str, Any]) -> List[TempStatus]:
        temps = []
        noise_level = cls._get_noise_level(status_dict)
        if noise_level is not None:
            temps.append(TempStatus('noise', noise_level))
        return temps

    @classmethod
    def _get_channel_statuses(cls, status_dict: Dict[str, Any]) -> List[ChannelStatus]:
        channel_statuses: List[ChannelStatus] = []
        multiple_fans_rpm = cls._get_multiple_fans_rpm(status_dict)
        for name, rpm in multiple_fans_rpm:
            channel_statuses.append(ChannelStatus(name, rpm=rpm))
        return channel_statuses