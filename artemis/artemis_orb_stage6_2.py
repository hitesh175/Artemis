import sys
import math
import random
import time
from PySide6.QtCore import Qt, QTimer, QPointF
from PySide6.QtGui import QColor, QPainter, QRadialGradient, QPen, QBrush
from PySide6.QtWidgets import QApplication, QWidget, QVBoxLayout, QLabel, QHBoxLayout, QPushButton

STATES = {
    "Idle": ("#718BA4", "Calm and ready"),
    "Listening": ("#5FB8AA", "I'm listening"),
    "Thinking": ("#8278B8", "Working on it"),
    "Speaking": ("#C3A1BD", "Speaking"),
    "Command": ("#77A5C5", "Executing command"),
    "Error": ("#D74C58", "Something needs attention"),
    "Sleep": ("#4E5669", "Resting"),
}

def mix(a, b, t):
    a, b = QColor(a), QColor(b)
    t = max(0.0, min(1.0, t))
    return QColor.fromRgbF(
        (a.redF() * (1-t) + b.redF() * t),
        (a.greenF() * (1-t) + b.greenF() * t),
        (a.blueF() * (1-t) + b.blueF() * t),
        1.0,
    )

class PlanetOrb(QWidget):
    def __init__(self):
        super().__init__()
        self.state = "Idle"
        self.prev_color = QColor(STATES["Idle"][0])
        self.color = QColor(STATES["Idle"][0])
        self.transition = 1.0
        self.sound = 0.0
        self.start = time.monotonic()
        self.setMinimumSize(370, 370)
        self.particles = [(random.uniform(0, 2*math.pi), random.uniform(.8, 1.35),
                           random.uniform(.4, 1.1)) for _ in range(75)]
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.tick)
        self.timer.start(33)

    def set_state(self, name):
        if name not in STATES or name == self.state:
            return
        self.prev_color = self.current_color()
        self.state = name
        self.color = QColor(STATES[name][0])
        self.transition = 0.0
        self.update()

    def set_audio_level(self, level):
        self.sound = max(0, min(1, float(level)))

    def current_color(self):
        return mix(self.prev_color, self.color, self.transition)

    def tick(self):
        self.transition = min(1.0, self.transition + .035)
        self.sound *= .91
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        p.fillRect(self.rect(), QColor("#0E1119"))
        t = time.monotonic() - self.start
        cx, cy = w/2, h/2
        s = min(w, h)
        base = s * .285
        speed = {"Idle":.55,"Listening":1.3,"Thinking":1.7,"Speaking":1.5,
                 "Command":1.3,"Error":2.0,"Sleep":.2}[self.state]
        breath = math.sin(t*speed*2) * (.012 if self.state=="Sleep" else .026)
        ripple = (self.sound * .07) if self.state in ("Listening", "Speaking") else 0
        radius = base * (1+breath+ripple)
        c = self.current_color()

        # Soft atmospheric haze surrounding the planet.
        for i in range(12, 0, -1):
            rr = radius*(1 + i*.037)
            halo = QColor(c)
            halo.setAlphaF(.004 + (12-i)*.0013)
            p.setPen(Qt.NoPen)
            p.setBrush(halo)
            p.drawEllipse(QPointF(cx, cy), rr, rr)

        # Sparse atmospheric dust.
        for i, (angle, dist, sz) in enumerate(self.particles):
            a = angle + t * .035 * (1 if i%2 else -1)
            rr = radius*dist*1.43
            dot = QColor(c)
            dot.setAlphaF(.13 + .18*(.5+.5*math.sin(t*.6+i)))
            p.setPen(Qt.NoPen)
            p.setBrush(dot)
            p.drawEllipse(QPointF(cx+math.cos(a)*rr, cy+math.sin(a)*rr), sz, sz)

        # Defined spherical planet disk with a smooth matte-lit surface.
        g = QRadialGradient(QPointF(cx-radius*.31, cy-radius*.4), radius*1.95)
        g.setColorAt(0, mix(c, "#E0E4E5", .48))
        g.setColorAt(.32, mix(c, "#78808B", .22))
        g.setColorAt(.68, mix(c, "#162032", .45))
        g.setColorAt(1, QColor("#10141C"))
        p.setBrush(QBrush(g))
        edge = QColor(c); edge.setAlphaF(.34)
        p.setPen(QPen(edge, 1.0))
        p.drawEllipse(QPointF(cx, cy), radius, radius)

        # Translucent moving latitude bands, clipped to the planet.
        from PySide6.QtGui import QPainterPath
        clip = QPainterPath()
        clip.addEllipse(QPointF(cx, cy), radius-1, radius-1)
        p.save()
        p.setClipPath(clip)
        for j in range(8):
            shift = math.sin(t*.15*speed+j*1.7)*radius*.13
            yy = cy-radius*.67+j*radius*.19+shift
            band = mix(c, "#D2D9DE", .35 if j%2 else .07)
            band.setAlphaF(.07 if j%2 else .10)
            p.setPen(QPen(band, 5+j%3*3))
            p.drawArc(int(cx-radius*1.1), int(yy-radius*.15),
                      int(radius*2.2), int(radius*.45), 0, 180*16)
        p.restore()

        # Thin atmospheric orbital ellipse (not a bright neon ring).
        p.save()
        p.translate(cx, cy)
        p.rotate(-23 + math.sin(t*.12)*5)
        orbit = QColor(c); orbit.setAlphaF(.38)
        p.setPen(QPen(orbit, 1.1))
        p.setBrush(Qt.NoBrush)
        p.drawEllipse(QPointF(0, 0), radius*1.23, radius*.39)
        p.restore()
        p.end()

class ArtemisVoice(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("ARTEMIS — Living Planet Voice Mode (Prototype)")
        self.resize(820, 720)
        self.setStyleSheet("""
          QWidget { background:#0E1119; color:#DDE4EF; font-family:'Segoe UI'; }
          QLabel#heading { color:#8795A8; font-size:13px; letter-spacing:3px; }
          QLabel#state { font-size:24px; font-weight:600; }
          QLabel#subtitle { color:#8F9BAD; font-size:13px; }
          QPushButton { background:#1D2634; color:#DDE4EF; border:1px solid #344052;
                        border-radius:18px; padding:10px 15px; }
          QPushButton:hover { background:#2A3749; }
        """)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(30, 25, 30, 25)
        heading = QLabel("A R T E M I S")
        heading.setObjectName("heading")
        heading.setAlignment(Qt.AlignCenter)
        outer.addWidget(heading)
        outer.addStretch(1)
        self.orb = PlanetOrb()
        outer.addWidget(self.orb, 1)
        self.state_label = QLabel("Idle")
        self.state_label.setObjectName("state")
        self.state_label.setAlignment(Qt.AlignCenter)
        outer.addWidget(self.state_label)
        self.subtitle = QLabel("Calm and ready")
        self.subtitle.setObjectName("subtitle")
        self.subtitle.setAlignment(Qt.AlignCenter)
        outer.addWidget(self.subtitle)
        outer.addStretch(1)
        controls = QHBoxLayout()
        for name in STATES:
            btn = QPushButton(name)
            btn.clicked.connect(lambda checked=False, n=name: self.change(n))
            controls.addWidget(btn)
        outer.addLayout(controls)
        hint = QLabel("Preview controls • Voice recognition is not connected yet")
        hint.setObjectName("subtitle")
        hint.setAlignment(Qt.AlignCenter)
        outer.addWidget(hint)

    def change(self, mode):
        self.orb.set_state(mode)
        self.state_label.setText(mode)
        self.subtitle.setText(STATES[mode][1])

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = ArtemisVoice()
    window.show()
    sys.exit(app.exec())
