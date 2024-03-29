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
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List, Dict

from matplotlib.animation import FuncAnimation
from matplotlib.artist import Artist
from matplotlib.backend_bases import PickEvent, DrawEvent, MouseEvent, MouseButton
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg
from matplotlib.figure import Figure
from matplotlib.legend import Legend
from matplotlib.lines import Line2D
from matplotlib.text import Text

from coolero.models.device import Device, DeviceType
from coolero.models.status import Status
from coolero.repositories.gpu_repo import GPU_FAN
from coolero.services.utils import MathUtils
from coolero.settings import Settings, UserSettings
from coolero.view_models.device_observer import DeviceObserver
from coolero.view_models.device_subject import DeviceSubject

_LOG = logging.getLogger(__name__)
DRAW_INTERVAL_MS: int = 1_000


class SystemOverviewCanvas(FigureCanvasQTAgg, FuncAnimation, DeviceObserver):
    """Class to plot and animate System Overview histogram"""

    _cpu_lines_initialized: bool = False
    _gpu_lines_initialized: bool = False
    _liquidctl_lines_initialized: bool = False
    _hwmon_lines_initialized: bool = False
    _composite_lines_initialized: bool = False

    def __init__(self,
                 width: int = 16,  # width/height ratio & inches for print
                 height: int = 9,
                 dpi: int = 120,
                 bg_color: str = Settings.theme['app_color']['bg_one'],
                 text_color: str = Settings.theme['app_color']['text_foreground'],
                 title_color: str = Settings.theme["app_color"]["text_title"]
                 ) -> None:
        self._bg_color = bg_color
        self._text_color = text_color
        self._devices: List[Device] = []
        self._cpu_data: DeviceData
        self._gpu_data: Dict[Device, DeviceData] = {}
        self._lc_devices_data: Dict[Device, DeviceData] = {}
        self._hwmon_devices_data: Dict[Device, DeviceData] = {}
        self._composite_data: DeviceData
        self.x_limit: int = 60  # the age, in seconds, of data to display:

        # Setup
        self.fig = Figure(figsize=(width, height), dpi=dpi, layout='tight', facecolor=bg_color, edgecolor=text_color)
        self.axes = self.fig.add_subplot(111, facecolor=bg_color)
        self.legend: Legend | None = None
        self.axes.set_ylim(-1, 101)
        self.axes.set_xlim(self.x_limit, 0)  # could make this modifiable to scaling & zoom
        self._drawn_artists: List[Artist] = []  # used by the matplotlib implementation for blit animation

        # Grid
        self.axes.grid(True, linestyle='dotted', color=text_color, alpha=0.5)
        self.axes.margins(x=0, y=0.05)
        self.axes.tick_params(colors=text_color)
        self.axes.set_yticks(
            [0, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100],
            ['0°/%', '10°/%', '20°/%', '30°/%', '40°/%', '50°/%', '60°/%', '70°/%', '80°/%', '90°/%', '100°/%', ])
        self.axes.set_xticks(
            [30, 60],
            ['30s', '1m'])
        self.axes.spines['top'].set_edgecolor(bg_color)
        self.axes.spines['right'].set_edgecolor(bg_color)
        self.axes.spines['right'].set_animated(True)
        self.axes.spines[['bottom', 'left']].set_edgecolor(text_color)

        # Lines
        self.lines: List[Line2D] = []
        self.legend_artists: Dict[Artist, Line2D] = {}

        # Interactions
        self.fig.canvas.mpl_connect('pick_event', self._on_pick)
        self.fig.canvas.mpl_connect('button_press_event', self._on_mouse_click_scroll)
        self.fig.canvas.mpl_connect('scroll_event', self._on_mouse_click_scroll)
        self.zoom_level: int = 1

        # Initialize
        FigureCanvasQTAgg.__init__(self, self.fig)
        FuncAnimation.__init__(self, self.fig, func=self.draw_frame, interval=DRAW_INTERVAL_MS, blit=True)

    def draw_frame(self, frame: int) -> List[Artist]:
        """Is used to draw every frame of the chart animation"""
        now: datetime = datetime.now()
        self._set_cpu_data(now)
        self._set_gpu_data(now)
        self._set_lc_device_data(now)
        self._set_hwmon_device_data(now)
        self._set_composite_data(now)
        self._drawn_artists = list(self.lines)  # pylint: disable=attribute-defined-outside-init
        self._drawn_artists.append(self.axes.spines['right'])
        if self.legend is not None:
            self._drawn_artists.append(self.legend)
        self.event_source.interval = DRAW_INTERVAL_MS  # return to normal speed after first frame
        return self._drawn_artists

    def notify_me(self, subject: DeviceSubject) -> None:  # type: ignore
        if self._devices:
            return
        self._devices = subject.devices
        cpu = self._get_first_device_with_type(DeviceType.CPU)
        if cpu is not None:
            self._initialize_cpu_lines(cpu)
        if gpus := self._get_devices_with_type(DeviceType.GPU):
            self._initialize_gpu_lines(gpus)
        if devices := self._get_devices_with_type(DeviceType.LIQUIDCTL):
            self._initialize_liquidctl_lines(devices)
        if hwmon_devices := self._get_devices_with_type(DeviceType.HWMON):
            self._initialize_hwmon_lines(hwmon_devices)
        if composite_device := self._get_first_device_with_type(DeviceType.COMPOSITE):
            self._initialize_composite_lines(composite_device)
        self.legend = self.init_legend(self._bg_color, self._text_color)
        self._redraw_canvas()

    def init_legend(self, bg_color: str, text_color: str) -> Legend:
        legend = self.axes.legend(loc='upper left', facecolor=bg_color, edgecolor=text_color, framealpha=0.9)
        legend.set_animated(True)
        for legend_line, legend_text, ax_line in zip(legend.get_lines(), legend.get_texts(), self.lines):
            is_visible: bool = Settings.is_overview_line_visible(legend_text.get_text())
            alpha: float = 1.0 if is_visible else 0.2
            legend_line.set_picker(True)
            legend_line.set_pickradius(7)
            legend_line.set_alpha(alpha)
            legend_text.set_color(text_color)
            legend_text.set_picker(True)
            legend_text.set_alpha(alpha)
            ax_line.set_visible(is_visible)
            self.legend_artists[legend_line] = ax_line
            self.legend_artists[legend_text] = ax_line
        return legend

    def redraw_workaround(self) -> None:
        """In some situations artifacts appear from hiding and showing the graph, in this case we manually clear"""
        self._redraw_canvas()

    def _set_cpu_data(self, now: datetime) -> None:
        cpu = self._get_first_device_with_type(DeviceType.CPU)
        if self._cpu_lines_initialized and cpu:
            for name, temps in self._cpu_data.temps(now).items():
                self._get_line_by_label(name).set_data(self._cpu_data.ages_seconds(), temps)
            for name, duties in self._cpu_data.duties(now).items():
                self._get_line_by_label(name).set_data(self._cpu_data.ages_seconds(), duties)

    def _set_gpu_data(self, now: datetime) -> None:
        if not self._gpu_lines_initialized:
            return
        gpus = self._get_devices_with_type(DeviceType.GPU)
        for gpu in gpus:
            for name, temps in self._gpu_data[gpu].temps(now).items():
                self._get_line_by_label(
                    self._create_gpu_label(name, len(gpus), gpu.type_id)
                ).set_data(self._gpu_data[gpu].ages_seconds(), temps)
            for name, duties in self._gpu_data[gpu].duties(now).items():
                self._get_line_by_label(
                    self._create_gpu_label(name, len(gpus), gpu.type_id)
                ).set_data(self._gpu_data[gpu].ages_seconds(), duties)

    def _set_lc_device_data(self, now: datetime) -> None:
        if not self._liquidctl_lines_initialized:
            return
        for device in self._get_devices_with_type(DeviceType.LIQUIDCTL):
            for name, temps in self._lc_devices_data[device].temps(now).items():
                self._get_line_by_label(
                    self._create_device_label(device.name_short, name, device.type_id)
                ).set_data(self._lc_devices_data[device].ages_seconds(), temps)
            for name, duty in self._lc_devices_data[device].duties(now).items():
                self._get_line_by_label(
                    self._create_device_label(device.name_short, name, device.type_id)
                ).set_data(self._lc_devices_data[device].ages_seconds(), duty)

    def _set_hwmon_device_data(self, now: datetime) -> None:
        if not self._hwmon_lines_initialized:
            return
        for device in self._get_devices_with_type(DeviceType.HWMON):
            for name, temps in self._hwmon_devices_data[device].temps(now).items():
                self._get_line_by_label(
                    self._create_device_label(device.name, name, device.type_id)
                ).set_data(self._hwmon_devices_data[device].ages_seconds(), temps)
            for name, duty in self._hwmon_devices_data[device].duties(now).items():
                self._get_line_by_label(
                    self._create_device_label(device.name, name, device.type_id)
                ).set_data(self._hwmon_devices_data[device].ages_seconds(), duty)

    def _set_composite_data(self, now: datetime) -> None:
        composite_device = self._get_first_device_with_type(DeviceType.COMPOSITE)
        if self._composite_lines_initialized and composite_device:
            for name, temps in self._composite_data.temps(now).items():
                self._get_line_by_label(name).set_data(self._composite_data.ages_seconds(), temps)

    def _get_first_device_with_type(self, device_type: DeviceType) -> Optional[Device]:
        return next(
            iter(self._get_devices_with_type(device_type)),
            None
        )

    def _get_devices_with_type(self, device_type: DeviceType) -> List[Device]:
        return [device for device in self._devices if device.type == device_type]

    def _initialize_cpu_lines(self, cpu: Device) -> None:
        lines_cpu = []
        for temp_status in cpu.status.temps:
            lines_cpu.append(
                Line2D([], [], color=cpu.color(temp_status.name), label=temp_status.name, linewidth=2)
            )
        for channel_status in cpu.status.channels:
            lines_cpu.append(
                Line2D([], [], color=cpu.color(channel_status.name), label=channel_status.name,
                       linestyle='dashed', linewidth=1)
            )
        self.lines.extend(lines_cpu)
        for line in lines_cpu:
            self.axes.add_line(line)
        self._cpu_data = DeviceData(cpu.status_history, smoothing_enabled_device=True)
        self._cpu_lines_initialized = True
        _LOG.debug('initialized cpu lines')

    def _initialize_gpu_lines(self, gpus: List[Device]) -> None:
        lines_gpu: List[Line2D] = []
        for gpu in gpus:
            lines_gpu.extend(
                Line2D(
                    [], [], color=gpu.color(temp_status.name),
                    label=self._create_gpu_label(temp_status.name, len(gpus), gpu.type_id),
                    linewidth=2
                )
                for temp_status in gpu.status.temps
            )
            for channel_status in gpu.status.channels:
                linestyle = 'dashdot' if channel_status.name == GPU_FAN else 'dashed'
                lines_gpu.append(
                    Line2D(
                        [], [], color=gpu.color(channel_status.name),
                        label=self._create_gpu_label(channel_status.name, len(gpus), gpu.type_id),
                        linestyle=linestyle, linewidth=1
                    )
                )
            self._gpu_data[gpu] = DeviceData(gpu.status_history, smoothing_enabled_device=True)
        self.lines.extend(lines_gpu)
        for line in lines_gpu:
            self.axes.add_line(line)
        self._gpu_lines_initialized = True
        _LOG.debug('initialized gpu lines')

    def _initialize_liquidctl_lines(self, devices: List[Device]) -> None:
        for device in devices:
            if device.lc_driver_type is None:
                continue
            lines_liquidctl = [
                Line2D(
                    [], [], color=device.color(temp_status.name),
                    label=self._create_device_label(device.name_short, temp_status.name, device.type_id),
                    linewidth=2
                )
                for temp_status in device.status.temps
            ]
            for channel_status in device.status.channels:
                if channel_status.duty is not None:
                    linestyle = 'dashdot' if channel_status.name.startswith('fan') else 'dashed'
                    lines_liquidctl.append(
                        Line2D(
                            [], [], color=device.color(channel_status.name),
                            label=self._create_device_label(
                                device.name_short, channel_status.name, device.type_id
                            ),
                            linestyle=linestyle, linewidth=1
                        )
                    )
            self.lines.extend(lines_liquidctl)
            for line in lines_liquidctl:
                self.axes.add_line(line)
            self._lc_devices_data[device] = DeviceData(device.status_history)
        self._liquidctl_lines_initialized = True
        _LOG.debug('initialized liquidctl lines')

    def _initialize_hwmon_lines(self, hwmon_devices: List[Device]) -> None:
        lines_hwmon: List[Line2D] = []
        for device in hwmon_devices:
            lines_hwmon.extend(
                Line2D(
                    [], [], color=device.color(temp_status.name),
                    label=self._create_device_label(device.name, temp_status.name, device.type_id),
                    linewidth=2
                )
                for temp_status in device.status.temps
            )
            for channel_status in device.status.channels:
                linestyle = 'dashdot' if channel_status.name.startswith('fan') else 'dashed'
                lines_hwmon.append(
                    Line2D(
                        [], [], color=device.color(channel_status.name),
                        label=self._create_device_label(device.name, channel_status.name, device.type_id),
                        linestyle=linestyle, linewidth=1
                    )
                )
            self._hwmon_devices_data[device] = DeviceData(device.status_history, smoothing_enabled_device=False)
        self.lines.extend(lines_hwmon)
        for line in lines_hwmon:
            self.axes.add_line(line)
        self._hwmon_lines_initialized = True
        _LOG.debug('initialized hwmon lines')

    def _initialize_composite_lines(self, composite_device: Device) -> None:
        lines_composite = [
            Line2D([], [], color=composite_device.color(temp_status.name), label=temp_status.name, linewidth=2)
            for temp_status in composite_device.status.temps
        ]
        self._composite_data = DeviceData(composite_device.status_history)
        self.lines.extend(lines_composite)
        for line in lines_composite:
            self.axes.add_line(line)
        self._composite_lines_initialized = True
        _LOG.debug('initialized composite lines')

    @staticmethod
    def _create_gpu_label(channel_name: str, number_gpus: int, current_gpu_id: int) -> str:
        return f'#{current_gpu_id} {channel_name}' if number_gpus > 1 else channel_name

    def _create_device_label(self, device_name: str, channel_name: str, device_id: int) -> str:
        has_same_name_as_other_device: bool = any(
            device.name_short == device_name and device.type_id != device_id
            for device in self._devices
        )
        prefix = f'LC#{device_id} ' if has_same_name_as_other_device else ''
        return f'{prefix}{device_name} {channel_name.capitalize()}'

    def _redraw_canvas(self) -> None:
        self._blit_cache.clear()
        self.event_source.interval = 10
        self.draw()

    def _get_line_by_label(self, label: str) -> Line2D:
        try:
            return next(line for line in self.lines if line.get_label() == label)
        except StopIteration:
            _LOG.error('No Initialized Plot Line found for label: %s', label)
            return Line2D([], [])

    def _on_pick(self, event: PickEvent) -> None:
        """hide/show specific lines from the legend"""
        if event.mouseevent.button != MouseButton.LEFT:
            return
        chosen_artist = event.artist
        ax_line = self.legend_artists.get(chosen_artist)
        if ax_line is None:
            _LOG.error('Chosen artist in system overview legend was not found')
            return
        is_visible: bool = not ax_line.get_visible()
        ax_line.set_visible(is_visible)
        for artist in (artist for artist, line in self.legend_artists.items() if line == ax_line):
            artist.set_alpha(1.0 if is_visible else 0.2)
            if isinstance(artist, Text):
                Settings.overview_line_is_visible(artist.get_text(), is_visible)
        self.event_source.interval = 100

    def _on_mouse_click_scroll(self, event: MouseEvent) -> None:
        """Zoom action of the main graph"""
        if event.button == MouseButton.RIGHT:
            if self.zoom_level < 4:
                self.zoom_level += 1
            else:
                self.zoom_level = 1
        elif event.button == 'down':
            if self.zoom_level < 4:
                self.zoom_level += 1
            else:
                return
        elif event.button == 'up':
            if self.zoom_level > 1:
                self.zoom_level -= 1
            else:
                return
        else:
            return
        x_limit_in_seconds: int = 0
        if self.zoom_level == 1:
            x_limit_in_seconds = 60
            self.axes.set_xticks(
                [30, 60],
                ['30s', '1m'])
        elif self.zoom_level == 2:
            x_limit_in_seconds = 5 * 60
            self.axes.set_xticks(
                [60, 180, 300],
                ['1m', '3m', '5m'])
        elif self.zoom_level == 3:
            x_limit_in_seconds = 15 * 60
            self.axes.set_xticks(
                [60, 300, 600, 900],
                ['1m', '5m', '10m', '15m'])
        elif self.zoom_level == 4:
            x_limit_in_seconds = 30 * 60
            self.axes.set_xticks(
                [60, 300, 600, 900, 1200, 1800],
                ['1m', '5m', '10m', '15m', '20m', '30m'])
        self.axes.set_xlim(x_limit_in_seconds, 0)
        self.event_source.interval = 100
        self.draw()

    def _end_redraw(self, event: DrawEvent) -> None:
        """We override this so that our animation is redrawn quickly after a plot resize"""
        super()._end_redraw(event)
        self.event_source.interval = 100


@dataclass(frozen=True)
class DeviceData:
    """This class improves graph efficiency by storing and only calculating changed data"""
    history: List[Status]
    smoothing_enabled_device: bool = False
    _temps: Dict[str, List[float]] = field(default_factory=lambda: defaultdict(list), init=False)
    _duties: Dict[str, List[float]] = field(default_factory=lambda: defaultdict(list), init=False)
    _ages_seconds: List[int] = field(default_factory=list, init=False)
    _ages_timestamps: List[datetime] = field(default_factory=list, init=False)
    _smoothing_enabled_user: bool = field(
        default=Settings.user.value(UserSettings.ENABLE_SMOOTHING, defaultValue=True, type=bool),
        init=False)
    _smoothing_window_size: int = field(default=2, init=False)

    def temps(self, now: datetime) -> Dict[str, List[float]]:
        self._synchronize_data(now)
        return self._temps

    def duties(self, now: datetime) -> Dict[str, List[float]]:
        self._synchronize_data(now)
        return self._duties

    def ages_seconds(self) -> List[int]:
        return self._ages_seconds

    def _synchronize_data(self, now: datetime) -> None:
        if self._ages_seconds:
            self._remove_outdated_data()
        current_data_size = len(self._ages_seconds)
        statuses_to_sync = len(self.history) - current_data_size
        if statuses_to_sync > 0:
            smoothing_enabled = self.smoothing_enabled_device and self._smoothing_enabled_user
            smoothing_window = self._smoothing_window_size \
                if smoothing_enabled and current_data_size > self._smoothing_window_size else 0
            for status in self.history[-statuses_to_sync:]:
                for temp_status in status.temps:
                    if smoothing_window:
                        temps_to_average = self._temps[temp_status.name][-(smoothing_window * 2):]
                        temps_to_average.append(temp_status.temp)
                        temp = MathUtils.current_value_from_moving_average(temps_to_average, smoothing_window, False)
                    else:
                        temp = temp_status.temp
                    self._temps[temp_status.name].append(temp)
                for channel_status in status.channels:
                    if channel_status.duty is not None:
                        if smoothing_window:
                            duties_to_average = self._duties[channel_status.name][-(smoothing_window * 2):]
                            duties_to_average.append(channel_status.duty)
                            duty = MathUtils.current_value_from_moving_average(
                                duties_to_average, smoothing_window, False
                            )
                        else:
                            duty = channel_status.duty
                        self._duties[channel_status.name].append(duty)
            self._ages_seconds.clear()
            self._ages_timestamps.clear()
            for status in self.history:
                self._ages_seconds.append((now - status.timestamp).seconds)
                self._ages_timestamps.append(status.timestamp)

    def _remove_outdated_data(self) -> None:
        while self._ages_timestamps and self.history[0].timestamp != self._ages_timestamps[0]:
            self._ages_timestamps.pop(0)
            self._ages_seconds.pop(0)
            for temp in self._temps.values():
                temp.pop(0)
            for duty in self._duties.values():
                duty.pop(0)
