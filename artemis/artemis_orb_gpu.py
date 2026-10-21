"""ARTEMIS 6.3.2 safe planet renderer: animated 3D-like planet without OpenGL.
Drop-in compatible with artemis_orb_voice_gpu.py; avoids native Qt/OpenGL crashes.
"""
import time
import math
import numpy as np
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QColor, QImage, QPainter
from PySide6.QtWidgets import QWidget

COLORS = {
    'Idle':'#718BA4', 'Listening':'#5FB8AA', 'Thinking':'#8278B8',
    'Speaking':'#C3A1BD', 'Command':'#77A5C5', 'Error':'#D74C58', 'Sleep':'#4E5669'
}
SPEEDS = {'Idle':.22,'Listening':.55,'Thinking':.82,'Speaking':.68,
          'Command':.63,'Error':1.0,'Sleep':.10}

class PlanetOrb(QWidget):
    """Perfect round silhouette, drifting matte clouds, simulated spherical depth."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(370,370)
        self.state = 'Idle'
        self._rgb = np.array(QColor(COLORS['Idle']).getRgb()[:3], dtype=np.float32)/255.0
        self._target = self._rgb.copy()
        self._level = 0.0
        self._start = time.monotonic()
        self._last_frame = None
        self._n = 310
        q = (np.arange(self._n, dtype=np.float32) + .5) / self._n * 2 - 1
        self._x, self._y = np.meshgrid(q, -q)
        self._r2 = self._x**2 + self._y**2
        self._z = np.sqrt(np.clip(1-self._r2, 0,1))
        self._mask = (self._r2 <= 1)
        self._light = np.clip(.4 + .63*(-.38*self._x + .46*self._y + .79*self._z),.12,1.12)
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(55)

    def set_state(self, name):
        if name in COLORS:
            self.state = name
            self._target = np.array(QColor(COLORS[name]).getRgb()[:3],dtype=np.float32)/255.0

    def set_audio_level(self, level):
        self._level = max(self._level, max(0.,min(1.,float(level))))

    def _tick(self):
        self._rgb = .91*self._rgb + .09*self._target
        self._level *= .88
        self._render()
        self.update()

    def _render(self):
        t = (time.monotonic()-self._start)*SPEEDS[self.state]
        x,y,z = self._x,self._y,self._z
        # Simulated planet rotation around Y and volumetric turbulent surface bands.
        theta = t*.22
        a = x*np.cos(theta) - z*np.sin(theta)
        b = x*np.sin(theta) + z*np.cos(theta)
        lat = y + .10*np.sin(a*7 + b*2 + t*.41)
        sw = (np.sin(a*8 + lat*7 + t*.25) * .19 +
              np.sin(b*13 - lat*9 - t*.36) * .13 +
              np.sin(a*19 + b*14 + lat*4 + t*.47) * .06)
        band = np.sin(lat*19 + sw*4 + .8*np.sin(a*4 + t*.3))
        clouds = .5 + .28*np.sin(a*5 + lat*6 + t*.3) + .18*np.sin(b*10-lat*8-t*.21)+sw
        matter = np.clip(.48*clouds + .30*(band*.5+.5) + .22*(.5+.5*np.sin(a*14+b*8+t*.16)),0,1)
        shade = (.22+.91*matter)*self._light*(.60+.4*np.power(z,.47))
        color = self._rgb[None,None,:]*shade[:,:,None] + (.035+.065*matter)[:,:,None]
        # Matte atmospheric edge; circle boundary remains mathematically exact.
        color += self._rgb[None,None,:]*(.07*np.power(1-z,3))[:,:,None]
        bg = np.array([14.,17.,25.],dtype=np.float32)/255.
        pixels = np.broadcast_to(bg,(self._n,self._n,3)).copy()
        pixels[self._mask] = np.clip(color[self._mask],0,1)
        arr = np.empty((self._n,self._n,4),dtype=np.uint8)
        arr[:,:,:3] = np.clip(pixels*255,0,255).astype(np.uint8)
        arr[:,:,3] = 255
        self._last_frame = QImage(arr.tobytes(),self._n,self._n,self._n*4,QImage.Format_RGBA8888).copy()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.SmoothPixmapTransform)
        painter.fillRect(self.rect(),QColor('#0E1119'))
        if self._last_frame is None:
            self._render()
        area=min(self.width(),self.height())
        diameter=int(area*.68*(1+.007*math.sin((time.monotonic()-self._start)*1.1)+.025*self._level))
        left=(self.width()-diameter)//2
        top=(self.height()-diameter)//2
        painter.drawImage(left,top,self._last_frame.scaled(diameter,diameter,Qt.IgnoreAspectRatio,Qt.SmoothTransformation))
        painter.end()

    def closeEvent(self,event):
        self._timer.stop()
        super().closeEvent(event)

def configure_gpu():
    """Compatibility hook: safe mode requires no OpenGL context."""
    pass
