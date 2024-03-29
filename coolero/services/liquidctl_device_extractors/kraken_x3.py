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

from liquidctl.driver import kraken3
from liquidctl.driver.kraken3 import KrakenX3

from coolero.models.channel_info import ChannelInfo
from coolero.models.device_info import DeviceInfo
from coolero.models.lighting_mode import LightingMode
from coolero.models.speed_options import SpeedOptions
from coolero.models.status import TempStatus, ChannelStatus
from coolero.services.liquidctl_device_extractors import LiquidctlDeviceInfoExtractor

_LOG = logging.getLogger(__name__)


# pylint: disable=protected-access
class KrakenX3Extractor(LiquidctlDeviceInfoExtractor):
    supported_driver = KrakenX3
    _channels: Dict[str, ChannelInfo] = {}
    _lighting_speeds: List[str] = []
    _min_liquid_temp = 20
    _max_liquid_temp = 60
    _backwards_enabled_modes: List[str] = [
        'spectrum-wave',
        'marquee-3',
        'marquee-4',
        'marquee-5',
        'marquee-6',
        'covering-marquee',
        'moving-alternating-3',
        'moving-alternating-4',
        'moving-alternating-5',
        'moving-alternating-6',
        'rainbow-flow',
        'super-rainbow',
        'rainbow-pulse'
    ]
    _speed_disabled_modes: List[str] = [
        'off',
        'fixed',
        'super-fixed'
    ]

    @classmethod
    def extract_info(cls, device_instance: KrakenX3) -> DeviceInfo:
        for channel_name, (_, duty_min, duty_max) in kraken3._SPEED_CHANNELS_KRAKENX.items():
            cls._channels[channel_name] = ChannelInfo(
                speed_options=SpeedOptions(
                    min_duty=duty_min,
                    max_duty=duty_max,
                    profiles_enabled=True,
                    fixed_enabled=True
                )
            )

        for channel_name in kraken3._COLOR_CHANNELS_KRAKENX:
            cls._channels[channel_name] = ChannelInfo(
                lighting_modes=cls._get_filtered_color_channel_modes(channel_name)
            )

        cls._lighting_speeds = list(kraken3._ANIMATION_SPEEDS.keys())

        return DeviceInfo(
            channels=cls._channels,
            lighting_speeds=cls._lighting_speeds,
            temp_min=cls._min_liquid_temp,
            temp_max=cls._max_liquid_temp,
            profile_max_length=9,
            temp_ext_available=True
        )

    @classmethod
    def _get_filtered_color_channel_modes(cls, channel_name: str) -> List[LightingMode]:
        channel_modes: List[LightingMode] = []
        for mode_name, (_, _, speed_scale, min_colors, max_colors) in kraken3._COLOR_MODES.items():
            if 'backwards' not in mode_name:
                channel_modes.append(LightingMode(
                    mode_name, cls._channel_to_frontend_name(mode_name),
                    min_colors, max_colors,
                    (speed_scale > 0) and mode_name not in cls._speed_disabled_modes,
                    mode_name in cls._backwards_enabled_modes
                ))
        return channel_modes

    @classmethod
    def _get_temperatures(cls, status_dict: Dict[str, Any], device_id: int) -> List[TempStatus]:
        temps = []
        liquid = cls._get_liquid_temp(status_dict)
        if liquid is not None:
            temps.append(TempStatus('liquid', liquid, 'Liquid', f'LC#{device_id} Liquid'))
        return temps

    @classmethod
    def _get_channel_statuses(cls, status_dict: Dict[str, Any]) -> List[ChannelStatus]:
        channel_statuses: List[ChannelStatus] = []
        pump_rpm = cls._get_pump_rpm(status_dict)
        pump_duty = cls._get_pump_duty(status_dict)
        if pump_rpm is not None or pump_duty is not None:
            channel_statuses.append(ChannelStatus('pump', rpm=pump_rpm, duty=pump_duty))
        return channel_statuses
