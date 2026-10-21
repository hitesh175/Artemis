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
        breath = math.sin(t*speed*2) * (.004 if self.state=="Sleep" else .012)
        ripple = (self.sound * .045) if self.state == "Listening" else (.018*max(0, math.sin(t*5.8))) if self.state == "Speaking" else 0
        radius = base * (1+breath+ripple)
        c = self.current_color()

        # A planet stays spherical. All visual energy moves *inside* this circle.
        from PySide6.QtGui import QPainterPath
        body = QPainterPath()
        body.addEllipse(QPointF(cx, cy), radius, radius)

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
        p.drawPath(body)

        # Slowly flowing, translucent material; all strokes stay inside the planet.
        from PySide6.QtGui import QPainterPath
        clip = body
        p.save()
        p.setClipPath(clip)
        for layer in range(11):
            path = QPainterPath()
            phase = t * (0.09 + 0.009 * layer) * speed
            y0 = cy + (layer-5) * radius * .23
            for k in range(81):
                x = cx-radius*1.35 + k * radius*2.7/80
                u = (x-cx)/radius
                yy = (y0
                      + radius*.105*math.sin(u*2.9 + phase + layer*.8)
                      + radius*.042*math.sin(u*6.1 - phase*.67 + layer*1.73))
                if k == 0:
                    path.moveTo(x, yy)
                else:
                    path.lineTo(x, yy)
            col = mix(c, "#CFD5DD", .18 if layer%2 else .5)
            col.setAlphaF(.18 if layer%2 else .13)
            p.setPen(QPen(col, 2.2 + (layer%4)*1.2))
            p.drawPath(path)

        # Floating wisps and current lines move at different speeds.
        for idx in range(6):
            phase = t*(.12 + idx*.025)*speed + idx*1.8
            bx = cx + radius*.58*math.cos(phase)
            by = cy + radius*.56*math.sin(phase*.73)
            patch = QRadialGradient(QPointF(bx, by), radius*(.20+idx*.028))
            center = mix(c, "#E2E1DF", .24 + .04*(idx%3))
            center.setAlphaF(.18 + .04*(idx%3))
            end = QColor(center); end.setAlpha(0)
            patch.setColorAt(0, center)
            patch.setColorAt(1, end)
            p.setPen(Qt.NoPen)
            p.setBrush(QBrush(patch))
            p.drawEllipse(QPointF(bx, by), radius*.24, radius*.19)

        # Visible sweeping semi-transparent atmospheric belts.
        for layer in range(3):
            q = QPainterPath()
            drift = t*(.2+layer*.03)*speed
            for k in range(101):
                x = cx-radius*1.2 + k*radius*2.4/100
                u = (x-cx)/radius
                yy = cy + (layer-1)*radius*.47 + radius*.22*math.sin(u*2.5+drift+layer)
                if k == 0: q.moveTo(x,yy)
                else: q.lineTo(x,yy)
            belt = QColor(c); belt.setAlphaF(.13 if layer == 1 else .09)
            p.setPen(QPen(belt, 18 + 7*layer))
            p.setBrush(Qt.NoBrush)
            p.drawPath(q)
        p.restore()

        # Crisp, restrained atmospheric boundary: never distorted.
        p.setBrush(Qt.NoBrush)
        edge2 = QColor(c)
        edge2.setAlphaF(.28)
        p.setPen(QPen(edge2, 1.15))
        p.drawEllipse(QPointF(cx, cy), radius, radius)

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
