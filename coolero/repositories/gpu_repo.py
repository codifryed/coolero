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
from enum import Enum, auto
from typing import Optional, List

import GPUtil
import pyamdgpuinfo
from GPUtil import GPU
from pyamdgpuinfo import GPUInfo

from models.channel_info import ChannelInfo
from models.device_info import DeviceInfo
from models.device_status import DeviceStatus
from models.speed_options import SpeedOptions
from models.status import Status
from repositories.devices_repository import DevicesRepository

_LOG = logging.getLogger(__name__)


class DetectedGPUType(Enum):
    NVIDIA = auto()
    AMD = auto()


class GpuRepo(DevicesRepository):
    """Repo for GPU Status"""

    _gpu_statuses: List[DeviceStatus] = []
    _detected_gpu_type: Optional[DetectedGPUType] = None

    def __init__(self) -> None:
        super().__init__()
        _LOG.info('Initialized with status: %s', self._gpu_statuses)

    @property
    def statuses(self) -> List[DeviceStatus]:
        """Returns empty list if no GPU found"""
        return self._gpu_statuses

    def update_statuses(self) -> None:
        for gpu in self._gpu_statuses:
            gpu.status = self._request_status()
            _LOG.debug('GPU device: %s status was updated with status: %s',
                       gpu.device_name,
                       gpu.status)

    def shutdown(self) -> None:
        self._gpu_statuses.clear()
        _LOG.debug("GPU Repo shutdown")

    def _initialize_devices(self) -> None:
        self._detect_gpu_type()
        status = self._request_status()
        if status is not None:
            channel_info = ChannelInfo(SpeedOptions(
                # todo: use cpu algorithm and scheduler for gpu too
                profiles_enabled=False,
                fixed_enabled=True
            ))
            self._gpu_statuses.append(DeviceStatus(
                # todo: adjust to handle multiple gpus (make device_id general)
                'gpu',
                status,
                _device_info=DeviceInfo(channels={'pump': channel_info, 'fan': channel_info})
            ))

    def _detect_gpu_type(self) -> None:
        if len(GPUtil.getGPUs()) > 0:
            self._detected_gpu_type = DetectedGPUType.NVIDIA
        elif pyamdgpuinfo.detect_gpus() > 0:
            self._detected_gpu_type = DetectedGPUType.AMD
        else:
            _LOG.warning('No GPU Device detected')

    def _request_status(self) -> Optional[Status]:
        if self._detected_gpu_type == DetectedGPUType.NVIDIA:
            gpu_nvidia: GPU = GPUtil.getGPUs()[0]
            return Status(
                device_description=gpu_nvidia.name,
                device_temperature=gpu_nvidia.temperature,
                load_percent=gpu_nvidia.load * 100
            )
        if self._detected_gpu_type == DetectedGPUType.AMD:
            gpu_amd: GPUInfo = pyamdgpuinfo.get_gpu(0)
            return Status(
                device_description=gpu_amd.name,
                device_temperature=gpu_amd.query_temperature(),
                load_percent=gpu_amd.query_load()
            )
        return None
