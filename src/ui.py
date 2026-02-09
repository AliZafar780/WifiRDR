from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QSpinBox, QDoubleSpinBox,
    QGroupBox, QStatusBar, QSplitter, QTextEdit
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QColor
from data_model import PointCloudData
from gl_view import PointCloudGLView


class ConnectionStatusWidget(QWidget):
    """Widget showing WebSocket connection status."""

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.status_label = QLabel("Disconnected")
        self.status_label.setStyleSheet("color: red; font-weight: bold;")

        self.client_count_label = QLabel("Clients: 0")

        layout.addWidget(QLabel("Status:"))
        layout.addWidget(self.status_label)
        layout.addStretch()
        layout.addWidget(self.client_count_label)

    def set_connected(self, connected: bool) -> None:
        """Update the connection status display."""
        if connected:
            self.status_label.setText("Connected")
            self.status_label.setStyleSheet("color: green; font-weight: bold;")
        else:
            self.status_label.setText("Disconnected")
            self.status_label.setStyleSheet("color: red; font-weight: bold;")

    def set_client_count(self, count: int) -> None:
        """Update the client count display."""
        self.client_count_label.setText(f"Clients: {count}")


class StatsPanel(QWidget):
    """Panel showing point cloud statistics."""

    def __init__(self, point_cloud: PointCloudData, parent=None):
        super().__init__(parent)
        self.point_cloud = point_cloud

        layout = QVBoxLayout(self)

        # Point count group
        points_group = QGroupBox("Point Statistics")
        points_layout = QVBoxLayout(points_group)

        self.point_count_label = QLabel("Points: 0")
        self.max_points_label = QLabel("Max Points: 0")
        self.received_label = QLabel("Total Received: 0")
        self.dropped_label = QLabel("Total Dropped: 0")

        points_layout.addWidget(self.point_count_label)
        points_layout.addWidget(self.max_points_label)
        points_layout.addWidget(self.received_label)
        points_layout.addWidget(self.dropped_label)

        layout.addWidget(points_group)

        # Bounds group
        bounds_group = QGroupBox("Bounding Box")
        bounds_layout = QVBoxLayout(bounds_group)

        self.x_bounds_label = QLabel("X: -")
        self.y_bounds_label = QLabel("Y: -")
        self.z_bounds_label = QLabel("Z: -")

        bounds_layout.addWidget(self.x_bounds_label)
        bounds_layout.addWidget(self.y_bounds_label)
        bounds_layout.addWidget(self.z_bounds_label)

        layout.addWidget(bounds_group)

        # RSSI legend
        legend_group = QGroupBox("RSSI Color Legend")
        legend_layout = QVBoxLayout(legend_group)

        legend_text = QLabel(
            "<span style='color: #00FF00'>■</span> -30 dBm (Excellent)<br>"
            "<span style='color: #FFFF00'>■</span> -50 dBm (Good)<br>"
            "<span style='color: #FF8800'>■</span> -70 dBm (Fair)<br>"
            "<span style='color: #FF0000'>■</span> -90 dBm (Poor)"
        )
        legend_text.setTextFormat(Qt.TextFormat.RichText)
        legend_layout.addWidget(legend_text)

        layout.addWidget(legend_group)

        # Controls
        controls_group = QGroupBox("Controls")
        controls_layout = QVBoxLayout(controls_group)

        self.clear_btn = QPushButton("Clear Points")
        controls_layout.addWidget(self.clear_btn)

        # Point size control
        size_layout = QHBoxLayout()
        size_layout.addWidget(QLabel("Point Size:"))
        self.point_size_spin = QDoubleSpinBox()
        self.point_size_spin.setRange(1.0, 20.0)
        self.point_size_spin.setValue(4.0)
        self.point_size_spin.setSingleStep(0.5)
        size_layout.addWidget(self.point_size_spin)
        controls_layout.addLayout(size_layout)

        layout.addWidget(controls_group)

        layout.addStretch()

        # Update timer
        self._update_timer = QTimer(self)
        self._update_timer.timeout.connect(self.update_stats)
        self._update_timer.start(500)  # Update every 500ms

    def update_stats(self) -> None:
        """Update the statistics display."""
        stats = self.point_cloud.get_stats()
        bounds = self.point_cloud.get_bounds()

        self.point_count_label.setText(f"Points: {stats['count']:,}")
        self.max_points_label.setText(f"Max Points: {stats['max']:,}")
        self.received_label.setText(f"Total Received: {stats['total_received']:,}")
        self.dropped_label.setText(f"Total Dropped: {stats['total_dropped']:,}")

        self.x_bounds_label.setText(f"X: [{bounds[0]:.2f}, {bounds[1]:.2f}]")
        self.y_bounds_label.setText(f"Y: [{bounds[2]:.2f}, {bounds[3]:.2f}]")
        self.z_bounds_label.setText(f"Z: [{bounds[4]:.2f}, {bounds[5]:.2f}]")


class LogPanel(QWidget):
    """Panel for displaying log messages."""

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMaximumBlockCount(1000)
        layout.addWidget(self.log_text)

        self.clear_btn = QPushButton("Clear Log")
        layout.addWidget(self.clear_btn)

        self.clear_btn.clicked.connect(self.log_text.clear)

    def append_log(self, message: str) -> None:
        """Append a message to the log."""
        self.log_text.append(message)


class MainWindow(QMainWindow):
    """Main application window."""

    clear_requested = pyqtSignal()
    point_size_changed = pyqtSignal(float)

    def __init__(self, point_cloud: PointCloudData, port: int = 8765):
        super().__init__()
        self.point_cloud = point_cloud
        self.port = port

        self.setWindowTitle("WiMap3D - Wi-Fi Signal Heatmap")
        self.setMinimumSize(1024, 768)

        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)

        # Splitter for resizable panels
        splitter = QSplitter(Qt.Orientation.Horizontal)
        main_layout.addWidget(splitter)

        # Left panel: GL view
        self.gl_view = PointCloudGLView(point_cloud)
        splitter.addWidget(self.gl_view)

        # Right panel: controls and stats
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(10, 10, 10, 10)

        # Connection status
        self.connection_widget = ConnectionStatusWidget()
        right_layout.addWidget(self.connection_widget)

        # Port info
        port_label = QLabel(f"WebSocket Port: {port}")
        right_layout.addWidget(port_label)

        # Stats panel
        self.stats_panel = StatsPanel(point_cloud)
        self.stats_panel.clear_btn.clicked.connect(self._on_clear_clicked)
        self.stats_panel.point_size_spin.valueChanged.connect(self._on_point_size_changed)
        right_layout.addWidget(self.stats_panel)

        # Log panel
        self.log_panel = LogPanel()
        self.log_panel.setMaximumHeight(200)
        right_layout.addWidget(self.log_panel)

        splitter.addWidget(right_panel)

        # Set splitter proportions (70% GL view, 30% panel)
        splitter.setSizes([700, 300])

        # Status bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Ready - Use sample_sender.py to stream data")

        # Animation timer to keep GL view updated
        self._anim_timer = QTimer(self)
        self._anim_timer.timeout.connect(self._on_anim_tick)
        self._anim_timer.start(33)  # ~30 FPS

        self._frame_count = 0

    def _on_anim_tick(self) -> None:
        """Animation tick - request GL view update periodically."""
        self._frame_count += 1
        # Update every frame to show new points
        self.gl_view.request_update()

        # Update stats every 10 frames
        if self._frame_count % 10 == 0:
            self.stats_panel.update_stats()

    def _on_clear_clicked(self) -> None:
        """Handle clear button click."""
        self.point_cloud.clear()
        self.gl_view.request_update()
        self.clear_requested.emit()
        self.log_panel.append_log("Point cloud cleared")

    def _on_point_size_changed(self, size: float) -> None:
        """Handle point size change."""
        self.gl_view._point_size = size
        self.gl_view.update()
        self.point_size_changed.emit(size)

    def set_connected(self, connected: bool) -> None:
        """Update connection status."""
        self.connection_widget.set_connected(connected)

    def set_client_count(self, count: int) -> None:
        """Update client count."""
        self.connection_widget.set_client_count(count)

    def log_message(self, message: str) -> None:
        """Add a log message."""
        self.log_panel.append_log(message)
