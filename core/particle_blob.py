"""Dark, organic particle volume driven by the existing speaker envelope.

No microphone, second audio stream, model calls, OpenGL, or new dependencies.
"""
from __future__ import annotations

import math
import numpy as np
from PyQt6.QtCore import QPointF, QRectF, Qt
from PyQt6.QtGui import QColor, QBrush, QPen, QPolygonF, QRadialGradient, QImage, QPainter


class ParticleBlob:
    def __init__(self, count=2400, seed=56):
        rng = np.random.default_rng(seed)
        y = rng.uniform(-1, 1, count)
        azimuth = rng.uniform(0, math.tau, count)
        ring = np.sqrt(1 - y * y)
        # Dense outer folds, with a second population circulating inside.
        radii = np.where(rng.random(count) < .72,
                         rng.uniform(.83, 1, count), rng.uniform(.18, .87, count))
        self._points = np.column_stack((ring * np.cos(azimuth), y,
                                        ring * np.sin(azimuth))) * radii[:, None]
        self._seeds = rng.uniform(0, math.tau, count)
        self.phase = 0.0
        self.energy = 0.0
        self._time = 0.0
        self._body_cache = None

    def step(self, dt, amplitude, *, speaking=False, muted=False):
        dt = max(0.0, min(.1, float(dt)))
        target = min(1.0, max(0.0, float(amplitude))) if speaking and not muted else 0.0
        tau = .07 if target > self.energy else .28
        self.energy += (target - self.energy) * (1 - math.exp(-dt / tau))
        self.phase += dt * (.11 + self.energy * 1.55)
        self._time += dt

    def positions(self):
        """Projection geometry exposed separately for deterministic QA."""
        p = self._points
        t = self.phase
        angle = t + .14 * np.sin(p[:, 1] * 3 + t * .7)
        ca, sa = np.cos(angle), np.sin(angle)
        x = p[:, 0] * ca + p[:, 2] * sa
        z = -p[:, 0] * sa + p[:, 2] * ca
        tilt = .23 * math.sin(t * .53) + .18
        y = p[:, 1] * math.cos(tilt) - z * math.sin(tilt)
        z = p[:, 1] * math.sin(tilt) + z * math.cos(tilt)
        fold = (.065 * np.sin(3.6 * x + 2.8 * y + t * 1.3)
                + .055 * np.cos(4 * z - 2.2 * y + t * .8))
        turbulence = self.energy * .13 * np.sin(self._seeds + t * 3.7 + y * 5)
        radius = 1 + fold + turbulence + self.energy * .10
        perspective = 3.8 / (3.8 - z * .45)
        return x * radius * perspective, y * radius * perspective, z

    def _paint_body(self, painter, cx, cy, radius):
        # A low, smoky backlight separates charcoal particles from the dark UI.
        glow = QRadialGradient(QPointF(cx, cy), radius * 1.5)
        glow.setFocalPoint(QPointF(cx - radius * .15, cy - radius * .12))
        glow.setColorAt(0, QColor(45, 49, 64, 110))
        glow.setColorAt(.52, QColor(27, 31, 45, 85))
        glow.setColorAt(1, QColor(8, 11, 18, 0))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(glow))
        painter.drawEllipse(QRectF(cx - radius * 1.5, cy - radius * 1.5,
                                  radius * 3, radius * 3))
        # A dark body gives the moving particles depth, instead of a glowing orb.
        body = QRadialGradient(QPointF(cx, cy), radius * 1.2)
        body.setFocalPoint(QPointF(cx - radius * .25, cy - radius * .25))
        body.setColorAt(0, QColor(23, 26, 35, 120))
        body.setColorAt(.64, QColor(4, 6, 11, 190))
        body.setColorAt(1, QColor(8, 11, 18, 0))
        painter.setBrush(QBrush(body))
        painter.drawEllipse(QRectF(cx - radius * 1.2, cy - radius * 1.2,
                                  radius * 2.4, radius * 2.4))
    def paint(self, painter, cx, cy, radius):
        painter.save()
        size = max(2, int(math.ceil(radius * 3)) + 4)
        if self._body_cache is None or self._body_cache[0] != size:
            image = QImage(size, size, QImage.Format.Format_ARGB32_Premultiplied)
            image.fill(Qt.GlobalColor.transparent)
            body_painter = QPainter(image)
            body_painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            self._paint_body(body_painter, size / 2, size / 2, radius)
            body_painter.end()
            self._body_cache = (size, image)
        painter.drawImage(QPointF(cx - size / 2, cy - size / 2), self._body_cache[1])
        x, y, depth = self.positions()
        # Batch points by depth; no per-particle brushes, gradients or allocations
        # beyond the screen coordinates. Work stays bounded on ordinary CPUs.
        for bucket in range(8):
            mask = np.clip(((depth + 1) * 4).astype(int), 0, 7) == bucket
            front = bucket / 7
            shade = int(33 + front * 65 + self.energy * 15)
            pen = QPen(QColor(shade, shade + 3, shade + 12,
                              int(70 + front * 145)), .75 + front * .7)
            pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            painter.setPen(pen)
            points = QPolygonF([QPointF(cx + float(px) * radius, cy + float(py) * radius)
                                for px, py in zip(x[mask], y[mask])])
            painter.drawPoints(points)
        painter.restore()
