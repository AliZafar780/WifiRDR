"""OpenGL-based 3D point cloud viewer with interactive camera controls."""

import math
import numpy as np
from OpenGL.GL import *
from OpenGL.GLU import *
from PyQt6.QtOpenGLWidgets import QOpenGLWidget
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtWidgets import QApplication

from data_model import PointCloudData, WiFiSample


def rssi_to_color(rssi: int, rssi_min: int = -90, rssi_max: int = -30) -> tuple[float, float, float]:
    """Convert RSSI value to RGB color using a heatmap gradient."""
    normalized = (rssi - rssi_min) / (rssi_max - rssi_min)
    normalized = max(0.0, min(1.0, normalized))

    if normalized < 0.25:
        t = normalized / 0.25
        return (0.0, t * 0.5, 1.0)
    elif normalized < 0.5:
        t = (normalized - 0.25) / 0.25
        return (0.0, 0.5 + t * 0.5, 1.0 - t)
    elif normalized < 0.75:
        t = (normalized - 0.5) / 0.25
        return (t, 1.0, 0.0)
    else:
        t = (normalized - 0.75) / 0.25
        return (1.0, 1.0 - t * 0.8, 0.0)


class Camera:
    """Simple orbit camera for 3D navigation."""

    def __init__(self):
        self.distance = 10.0
        self.azimuth = 45.0
        self.elevation = 30.0
        self.target = np.array([0.0, 0.0, 0.0], dtype=np.float32)
        self.fov = 60.0
        self.near = 0.1
        self.far = 1000.0

    def get_position(self) -> np.ndarray:
        """Calculate camera position in world space."""
        azimuth_rad = math.radians(self.azimuth)
        elevation_rad = math.radians(self.elevation)

        x = self.distance * math.cos(elevation_rad) * math.cos(azimuth_rad)
        y = self.distance * math.cos(elevation_rad) * math.sin(azimuth_rad)
        z = self.distance * math.sin(elevation_rad)

        return self.target + np.array([x, y, z], dtype=np.float32)

    def apply(self, width: int, height: int) -> None:
        """Apply camera transformations to OpenGL."""
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        aspect = width / height if height > 0 else 1.0
        gluPerspective(self.fov, aspect, self.near, self.far)

        glMatrixMode(GL_MODELVIEW)
        glLoadIdentity()

        pos = self.get_position()
        gluLookAt(
            pos[0], pos[1], pos[2],
            self.target[0], self.target[1], self.target[2],
            0.0, 0.0, 1.0
        )

    def orbit(self, dx: float, dy: float) -> None:
        """Orbit camera around target."""
        self.azimuth += dx * 0.5
        self.elevation = max(-89.0, min(89.0, self.elevation + dy * 0.5))

    def zoom(self, delta: float) -> None:
        """Zoom in/out by changing distance."""
        self.distance = max(0.1, self.distance * (1.0 - delta * 0.1))

    def pan(self, dx: float, dy: float) -> None:
        """Pan the camera target."""
        azimuth_rad = math.radians(self.azimuth)

        right = np.array([math.cos(azimuth_rad), math.sin(azimuth_rad), 0.0])
        up = np.array([0.0, 0.0, 1.0])

        self.target += right * dx * self.distance * 0.01
        self.target += up * dy * self.distance * 0.01

    def reset(self) -> None:
        """Reset camera to default view."""
        self.distance = 10.0
        self.azimuth = 45.0
        self.elevation = 30.0
        self.target = np.array([0.0, 0.0, 0.0], dtype=np.float32)


class GLView(QOpenGLWidget):
    """OpenGL widget for rendering 3D point cloud."""

    def __init__(self, data: PointCloudData, parent=None):
        super().__init__(parent)
        self.data = data
        self.camera = Camera()

        self._mouse_pos = None
        self._left_pressed = False
        self._right_pressed = False

        self._point_vbo = None
        self._color_vbo = None
        self._point_count = 0
        self._needs_update = True

        self._fps = 0.0
        self._frame_count = 0
        self._last_time = 0

        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

        self._update_timer = QTimer(self)
        self._update_timer.timeout.connect(self._trigger_update)
        self._update_timer.start(33)

    def _trigger_update(self) -> None:
        """Trigger a redraw at ~30 FPS."""
        self._needs_update = True
        self.update()

    def initializeGL(self) -> None:
        """Initialize OpenGL state."""
        glClearColor(0.05, 0.05, 0.1, 1.0)
        glEnable(GL_DEPTH_TEST)
        glEnable(GL_PROGRAM_POINT_SIZE)
        glPointSize(4.0)

    def resizeGL(self, width: int, height: int) -> None:
        """Handle resize events."""
        glViewport(0, 0, width, height)

    def paintGL(self) -> None:
        """Render the scene."""
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)

        self.camera.apply(self.width(), self.height())

        self._draw_grid()
        self._draw_points()
        self._update_fps()

    def _draw_grid(self) -> None:
        """Draw a reference grid on the XY plane."""
        glDisable(GL_DEPTH_TEST)
        glColor3f(0.2, 0.2, 0.3)
        glBegin(GL_LINES)

        grid_size = 10
        grid_spacing = 1.0

        for i in range(-grid_size, grid_size + 1):
            glVertex3f(i * grid_spacing, -grid_size * grid_spacing, 0.0)
            glVertex3f(i * grid_spacing, grid_size * grid_spacing, 0.0)

            glVertex3f(-grid_size * grid_spacing, i * grid_spacing, 0.0)
            glVertex3f(grid_size * grid_spacing, i * grid_spacing, 0.0)

        glEnd()
        glEnable(GL_DEPTH_TEST)

    def _draw_points(self) -> None:
        """Draw the point cloud."""
        if not self.data.samples:
            return

        rssi_min, rssi_max = self.data.get_rssi_range()

        glBegin(GL_POINTS)
        for sample in self.data.samples:
            color = rssi_to_color(sample.rssi, rssi_min, rssi_max)
            glColor3f(color[0], color[1], color[2])
            glVertex3f(sample.x, sample.y, sample.z)
        glEnd()

    def _update_fps(self) -> None:
        """Update FPS counter."""
        import time
        current_time = time.time()
        self._frame_count += 1

        if current_time - self._last_time >= 1.0:
            self._fps = self._frame_count / (current_time - self._last_time)
            self._frame_count = 0
            self._last_time = current_time

    def get_fps(self) -> float:
        """Return current FPS."""
        return self._fps

    def mousePressEvent(self, event) -> None:
        """Handle mouse press."""
        self._mouse_pos = (event.pos().x(), event.pos().y())
        if event.button() == Qt.MouseButton.LeftButton:
            self._left_pressed = True
        elif event.button() == Qt.MouseButton.RightButton:
            self._right_pressed = True

    def mouseReleaseEvent(self, event) -> None:
        """Handle mouse release."""
        if event.button() == Qt.MouseButton.LeftButton:
            self._left_pressed = False
        elif event.button() == Qt.MouseButton.RightButton:
            self._right_pressed = False

    def mouseMoveEvent(self, event) -> None:
        """Handle mouse movement for camera control."""
        if self._mouse_pos is None:
            return

        dx = event.pos().x() - self._mouse_pos[0]
        dy = event.pos().y() - self._mouse_pos[1]
        self._mouse_pos = (event.pos().x(), event.pos().y())

        if self._left_pressed:
            self.camera.orbit(dx, -dy)
            self.update()
        elif self._right_pressed:
            self.camera.pan(-dx, dy)
            self.update()

    def wheelEvent(self, event) -> None:
        """Handle scroll wheel for zooming."""
        delta = event.angleDelta().y() / 120.0
        self.camera.zoom(delta)
        self.update()

    def keyPressEvent(self, event) -> None:
        """Handle key presses."""
        if event.key() == Qt.Key.Key_R:
            self.camera.reset()
            self.update()
