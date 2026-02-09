import math
import numpy as np
from OpenGL.GL import *
from OpenGL.GLU import *
from PyQt6.QtOpenGLWidgets import QOpenGLWidget
from PyQt6.QtCore import Qt, QPoint, QTimer
from PyQt6.QtGui import QMouseEvent, QWheelEvent, QKeyEvent
from data_model import PointCloudData, WiFiSample


class PointCloudGLView(QOpenGLWidget):
    """OpenGL widget for rendering 3D point cloud heatmap."""

    # RSSI color gradient: excellent (-30) -> poor (-90)
    # Maps to colors: green -> yellow -> orange -> red
    RSSI_MIN = -90.0
    RSSI_MAX = -30.0

    def __init__(self, point_cloud: PointCloudData, parent=None):
        super().__init__(parent)
        self.point_cloud = point_cloud
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setMinimumSize(400, 300)

        # Camera state
        self.camera_distance = 50.0
        self.camera_azimuth = 45.0  # Horizontal rotation (degrees)
        self.camera_elevation = 30.0  # Vertical rotation (degrees)
        self.camera_target = np.array([0.0, 0.0, 0.0], dtype=np.float32)

        # Mouse interaction state
        self._last_mouse_pos: QPoint = QPoint()
        self._is_rotating = False
        self._is_panning = False

        # Point rendering
        self._point_vbo = None
        self._color_vbo = None
        self._point_count = 0
        self._point_size = 4.0
        self._needs_update = True

        # Auto-rotate (optional)
        self._auto_rotate = False
        self._auto_rotate_speed = 0.5

        # Update timer for smooth rendering
        self._update_timer = QTimer(self)
        self._update_timer.timeout.connect(self._on_update_timer)
        self._update_timer.start(33)  # ~30 FPS

    def _on_update_timer(self) -> None:
        """Called periodically to update the view."""
        if self._auto_rotate:
            self.camera_azimuth += self._auto_rotate_speed
            self.camera_azimuth %= 360
            self.update()
        elif self._needs_update:
            self.update()

    def initializeGL(self) -> None:
        """Initialize OpenGL state."""
        glClearColor(0.1, 0.1, 0.15, 1.0)  # Dark blue-gray background
        glEnable(GL_DEPTH_TEST)
        glEnable(GL_POINT_SMOOTH)
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        glPointSize(self._point_size)

    def resizeGL(self, width: int, height: int) -> None:
        """Handle widget resize."""
        glViewport(0, 0, width, max(height, 1))
        self.update()

    def paintGL(self) -> None:
        """Render the scene."""
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)

        # Set up projection matrix
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        aspect = self.width() / max(self.height(), 1)
        gluPerspective(45.0, aspect, 0.1, 1000.0)

        # Set up modelview matrix
        glMatrixMode(GL_MODELVIEW)
        glLoadIdentity()

        # Position camera
        self._setup_camera()

        # Draw axes
        self._draw_axes()

        # Draw grid
        self._draw_grid()

        # Draw point cloud
        self._update_point_buffers()
        self._draw_points()

        self._needs_update = False

    def _setup_camera(self) -> None:
        """Position the camera based on current azimuth/elevation/distance."""
        azimuth_rad = math.radians(self.camera_azimuth)
        elevation_rad = math.radians(self.camera_elevation)

        # Convert spherical to Cartesian
        eye_x = self.camera_target[0] + self.camera_distance * math.cos(elevation_rad) * math.cos(azimuth_rad)
        eye_y = self.camera_target[1] + self.camera_distance * math.cos(elevation_rad) * math.sin(azimuth_rad)
        eye_z = self.camera_target[2] + self.camera_distance * math.sin(elevation_rad)

        gluLookAt(
            eye_x, eye_y, eye_z,
            self.camera_target[0], self.camera_target[1], self.camera_target[2],
            0.0, 0.0, 1.0  # Up vector is Z
        )

    def _draw_axes(self) -> None:
        """Draw coordinate axes for reference."""
        glDisable(GL_DEPTH_TEST)
        glLineWidth(2.0)
        glBegin(GL_LINES)
        # X axis - red
        glColor3f(1.0, 0.3, 0.3)
        glVertex3f(0, 0, 0)
        glVertex3f(10, 0, 0)
        # Y axis - green
        glColor3f(0.3, 1.0, 0.3)
        glVertex3f(0, 0, 0)
        glVertex3f(0, 10, 0)
        # Z axis - blue
        glColor3f(0.3, 0.3, 1.0)
        glVertex3f(0, 0, 0)
        glVertex3f(0, 0, 10)
        glEnd()
        glEnable(GL_DEPTH_TEST)

    def _draw_grid(self) -> None:
        """Draw a ground plane grid."""
        glDisable(GL_DEPTH_TEST)
        glLineWidth(1.0)
        glColor3f(0.2, 0.2, 0.25)
        size = 50
        step = 5
        glBegin(GL_LINES)
        for i in range(-size, size + 1, step):
            glVertex3f(i, -size, 0)
            glVertex3f(i, size, 0)
            glVertex3f(-size, i, 0)
            glVertex3f(size, i, 0)
        glEnd()
        glEnable(GL_DEPTH_TEST)

    def _rssi_to_color(self, rssi: float) -> tuple:
        """Convert RSSI value to RGB color using heatmap gradient."""
        # Normalize RSSI to 0-1 range (clamped)
        t = (rssi - self.RSSI_MIN) / (self.RSSI_MAX - self.RSSI_MIN)
        t = max(0.0, min(1.0, t))

        # Heatmap: red (poor) -> orange -> yellow -> green (excellent)
        if t < 0.33:
            # Red to orange
            local_t = t / 0.33
            r = 1.0
            g = 0.3 + 0.4 * local_t
            b = 0.1
        elif t < 0.66:
            # Orange to yellow
            local_t = (t - 0.33) / 0.33
            r = 1.0
            g = 0.7 + 0.3 * local_t
            b = 0.1
        else:
            # Yellow to green
            local_t = (t - 0.66) / 0.34
            r = 1.0 - 0.7 * local_t
            g = 1.0
            b = 0.1 + 0.2 * local_t

        return (r, g, b)

    def _update_point_buffers(self) -> None:
        """Update OpenGL buffers with current point cloud data."""
        points = self.point_cloud.get_all()

        if not points:
            self._point_count = 0
            return

        # Build position and color arrays
        positions = []
        colors = []

        for sample in points:
            positions.extend([sample.x, sample.y, sample.z])
            r, g, b = self._rssi_to_color(sample.rssi)
            colors.extend([r, g, b])

        self._positions_array = np.array(positions, dtype=np.float32)
        self._colors_array = np.array(colors, dtype=np.float32)
        self._point_count = len(points)

    def _draw_points(self) -> None:
        """Render the point cloud."""
        if self._point_count == 0:
            return

        glPointSize(self._point_size)

        # Use vertex arrays for efficient rendering
        glEnableClientState(GL_VERTEX_ARRAY)
        glEnableClientState(GL_COLOR_ARRAY)

        glVertexPointer(3, GL_FLOAT, 0, self._positions_array)
        glColorPointer(3, GL_FLOAT, 0, self._colors_array)

        glDrawArrays(GL_POINTS, 0, self._point_count)

        glDisableClientState(GL_COLOR_ARRAY)
        glDisableClientState(GL_VERTEX_ARRAY)

    def request_update(self) -> None:
        """Request a redraw of the view."""
        self._needs_update = True

    # Mouse interaction handlers

    def mousePressEvent(self, event: QMouseEvent) -> None:
        """Handle mouse button press."""
        self._last_mouse_pos = event.pos()

        if event.button() == Qt.MouseButton.LeftButton:
            self._is_rotating = True
        elif event.button() == Qt.MouseButton.RightButton:
            self._is_panning = True

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        """Handle mouse button release."""
        if event.button() == Qt.MouseButton.LeftButton:
            self._is_rotating = False
        elif event.button() == Qt.MouseButton.RightButton:
            self._is_panning = False

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        """Handle mouse movement for orbit/pan."""
        dx = event.pos().x() - self._last_mouse_pos.x()
        dy = event.pos().y() - self._last_mouse_pos.y()
        self._last_mouse_pos = event.pos()

        sensitivity = 0.5

        if self._is_rotating:
            self.camera_azimuth -= dx * sensitivity
            self.camera_elevation = max(-89, min(89, self.camera_elevation + dy * sensitivity))
            self.update()

        elif self._is_panning:
            # Pan the target point
            azimuth_rad = math.radians(self.camera_azimuth)
            pan_speed = self.camera_distance * 0.001

            # Calculate pan direction based on camera orientation
            self.camera_target[0] -= dx * pan_speed * math.sin(azimuth_rad)
            self.camera_target[1] += dx * pan_speed * math.cos(azimuth_rad)
            self.camera_target[2] += dy * pan_speed
            self.update()

    def wheelEvent(self, event: QWheelEvent) -> None:
        """Handle mouse wheel for zooming."""
        delta = event.angleDelta().y()
        zoom_factor = 0.9 if delta > 0 else 1.1
        self.camera_distance = max(1.0, min(500.0, self.camera_distance * zoom_factor))
        self.update()

    def keyPressEvent(self, event: QKeyEvent) -> None:
        """Handle key presses."""
        if event.key() == Qt.Key.Key_R:
            # Reset camera
            self.camera_distance = 50.0
            self.camera_azimuth = 45.0
            self.camera_elevation = 30.0
            self.camera_target = np.array([0.0, 0.0, 0.0], dtype=np.float32)
            self.update()
        elif event.key() == Qt.Key.Key_Space:
            # Toggle auto-rotate
            self._auto_rotate = not self._auto_rotate
