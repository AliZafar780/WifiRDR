"""PyQt6 UI components for WiMap3D."""

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QGroupBox, QStatusBar, QPushButton,
    QSpinBox, QFormLayout, QLineEdit, QTextEdit
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont

from data_model import PointCloudData
from gl_view import GLView
from ws_server import WiFiWebSocketServer


class StatusPanel(QGroupBox):
    """Panel displaying connection and metrics information."""

    def __init__(self, parent=None):
        super().__init__("Status", parent)
        self._setup_ui()

    def _setup_ui(self) -> None:
        """Setup the UI layout."""
        layout = QFormLayout()

        self.connection_label = QLabel("Disconnected")
        self.connection_label.setStyleSheet("color: red; font-weight: bold;")
        layout.addRow("Connection:", self.connection_label)

        self.clients_label = QLabel("0")
        layout.addRow("Clients:", self.clients_label)

        self.point_count_label = QLabel("0")
        layout.addRow("Points:", self.point_count_label)

        self.rssi_range_label = QLabel("- / - dBm")
        layout.addRow("RSSI Range:", self.rssi_range_label)

        self.fps_label = QLabel("0 FPS")
        layout.addRow("FPS:", self.fps_label)

        self.clear_btn = QPushButton("Clear Points")
        layout.addRow(self.clear_btn)

        self.setLayout(layout)

    def update_connection(self, connected: bool) -> None:
        """Update connection status display."""
        if connected:
            self.connection_label.setText("Connected")
            self.connection_label.setStyleSheet("color: green; font-weight: bold;")
        else:
            self.connection_label.setText("Disconnected")
            self.connection_label.setStyleSheet("color: red; font-weight: bold;")

    def update_clients(self, count: int) -> None:
        """Update client count display."""
        self.clients_label.setText(str(count))

    def update_metrics(self, point_count: int, rssi_min: int, rssi_max: int, fps: float) -> None:
        """Update metrics display."""
        self.point_count_label.setText(f"{point_count:,}")
        self.rssi_range_label.setText(f"{rssi_min} / {rssi_max} dBm")
        self.fps_label.setText(f"{fps:.1f} FPS")


class ConnectionPanel(QGroupBox):
    """Panel for WebSocket connection settings."""

    def __init__(self, parent=None):
        super().__init__("Connection Settings", parent)
        self._setup_ui()

    def _setup_ui(self) -> None:
        """Setup the UI layout."""
        layout = QFormLayout()

        self.port_input = QSpinBox()
        self.port_input.setRange(1024, 65535)
        self.port_input.setValue(8765)
        self.port_input.setEnabled(False)
        layout.addRow("Port:", self.port_input)

        self.address_label = QLabel("ws://0.0.0.0:8765")
        layout.addRow("Address:", self.address_label)

        self.setLayout(layout)


class LegendPanel(QGroupBox):
    """Panel showing RSSI color legend."""

    def __init__(self, parent=None):
        super().__init__("RSSI Legend", parent)
        self._setup_ui()

    def _setup_ui(self) -> None:
        """Setup the legend display."""
        layout = QVBoxLayout()

        legend_text = """
        <table cellpadding="5">
        <tr><td bgcolor="#000080" width="30">&nbsp;</td><td>Very Weak (&lt; -80 dBm)</td></tr>
        <tr><td bgcolor="#00FFFF" width="30">&nbsp;</td><td>Weak (-80 to -70 dBm)</td></tr>
        <tr><td bgcolor="#00FF00" width="30">&nbsp;</td><td>Good (-70 to -60 dBm)</td></tr>
        <tr><td bgcolor="#FFFF00" width="30">&nbsp;</td><td>Strong (-60 to -50 dBm)</td></tr>
        <tr><td bgcolor="#FF3300" width="30">&nbsp;</td><td>Excellent (&gt; -50 dBm)</td></tr>
        </table>
        """

        self.legend_label = QLabel(legend_text)
        self.legend_label.setTextFormat(Qt.TextFormat.RichText)
        layout.addWidget(self.legend_label)

        self.setLayout(layout)


class ControlsPanel(QGroupBox):
    """Panel showing keyboard/mouse controls."""

    def __init__(self, parent=None):
        super().__init__("Controls", parent)
        self._setup_ui()

    def _setup_ui(self) -> None:
        """Setup the controls display."""
        layout = QVBoxLayout()

        controls_text = """
        <b>Mouse:</b><br>
        &nbsp;&nbsp;• Left + Drag: Orbit<br>
        &nbsp;&nbsp;• Right + Drag: Pan<br>
        &nbsp;&nbsp;• Scroll: Zoom<br><br>
        <b>Keyboard:</b><br>
        &nbsp;&nbsp;• R: Reset View
        """

        self.controls_label = QLabel(controls_text)
        self.controls_label.setTextFormat(Qt.TextFormat.RichText)
        layout.addWidget(self.controls_label)

        self.setLayout(layout)


class MainWindow(QMainWindow):
    """Main application window."""

    def __init__(self, data: PointCloudData, ws_server: WiFiWebSocketServer):
        super().__init__()
        self.data = data
        self.ws_server = ws_server
        self.setWindowTitle("WiMap3D - Wi-Fi Signal Visualizer")
        self.setMinimumSize(1200, 800)

        self._setup_ui()
        self._setup_timer()

    def _setup_ui(self) -> None:
        """Setup the main UI layout."""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        main_layout = QHBoxLayout(central_widget)

        self.gl_view = GLView(self.data, self)
        main_layout.addWidget(self.gl_view, stretch=3)

        sidebar = QWidget()
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setSpacing(10)

        self.connection_panel = ConnectionPanel()
        sidebar_layout.addWidget(self.connection_panel)

        self.status_panel = StatusPanel()
        self.status_panel.clear_btn.clicked.connect(self._clear_points)
        sidebar_layout.addWidget(self.status_panel)

        self.legend_panel = LegendPanel()
        sidebar_layout.addWidget(self.legend_panel)

        self.controls_panel = ControlsPanel()
        sidebar_layout.addWidget(self.controls_panel)

        sidebar_layout.addStretch()

        main_layout.addWidget(sidebar, stretch=1)

        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Ready")

    def _setup_timer(self) -> None:
        """Setup the update timer for UI refresh."""
        self._update_timer = QTimer(self)
        self._update_timer.timeout.connect(self._update_ui)
        self._update_timer.start(100)

    def _update_ui(self) -> None:
        """Update UI elements with current state."""
        if self.ws_server:
            self.status_panel.update_connection(self.ws_server.is_running())
            self.status_panel.update_clients(self.ws_server.get_client_count())

        rssi_min, rssi_max = self.data.get_rssi_range()
        self.status_panel.update_metrics(
            len(self.data),
            rssi_min,
            rssi_max,
            self.gl_view.get_fps()
        )

    def _clear_points(self) -> None:
        """Clear all points from the visualization."""
        self.data.clear()
        self.gl_view.update()

    def closeEvent(self, event) -> None:
        """Handle window close event."""
        if self.ws_server:
            self.ws_server.stop()
        event.accept()
