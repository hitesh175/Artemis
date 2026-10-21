"""ARTEMIS 6.3.3: matte planetary atmosphere. Safe CPU/Qt renderer, no OpenGL.
Perfectly circular planet with flowing cloud bands and expressive mode colors.
Voice controller calls set_state and set_audio_level exactly as before.
"""
import math
import time
import numpy as np
from PySide6.QtCore import Qt, QTimer, QRectF
from PySide6.QtGui import QColor, QImage, QPainter, QRadialGradient, QPen, QBrush
from PySide6.QtWidgets import QWidget

COLORS = {
    "Idle":"#668CB8", "Listening":"#38B8AE", "Thinking":"#8176C9",
    "Speaking":"#D3A1CF", "Command":"#68AADD", "Error":"#E44F5D", "Sleep":"#4E5669"
}
SPEEDS = {
    "Idle":.28, "Listening":.77, "Thinking":1.10,
    "Speaking":.9, "Command":.85, "Error":1.28, "Sleep":.12
}

class PlanetOrb(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(370, 370)
        self.state = "Idle"
        self.rgb = np.array(QColor(COLORS["Idle"]).getRgb()[:3], dtype=np.float32)/255
        self.target = self.rgb.copy()
        self.level = 0.
        self.start = time.monotonic()
        n = self.n = 352
        v = (np.arange(n, dtype=np.float32)+.5)*2/n - 1
        self.x, self.y = np.meshgrid(v,-v)
        self.rr = self.x*self.x + self.y*self.y
        self.mask = self.rr <= 1
        self.z = np.sqrt(np.maximum(0., 1-self.rr))
        self.lat = np.arcsin(np.clip(self.y, -1, 1))
        self.lon = np.arctan2(self.x, self.z+1e-5)
        self.image = None
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.tick)
        self.timer.start(56)

    def set_state(self, name):
        if name in COLORS:
            self.state = name
            self.target = np.array(QColor(COLORS[name]).getRgb()[:3],dtype=np.float32)/255

    def set_audio_level(self, level):
        self.level = max(self.level, min(1., max(0., float(level))))

    def tick(self):
        self.rgb += (self.target-self.rgb)*.11
        self.level *= .87
        self.render()
        self.update()

    def render(self):
        t = (time.monotonic()-self.start)*SPEEDS[self.state]
        lon = self.lon + .17*t
        lat = self.lat
        # Broad non-repeating flow: horizontal winds bend into curls, slowly circulating.
        curl = (.11*np.sin(lon*3.1 + 2.0*np.sin(lat*4.4 + t*.16) + t*.18)
              + .05*np.sin(lon*7.4 - lat*5.5 - t*.31))
        adv_lat = lat + curl
        flow = (.5 + .5*np.sin(adv_lat*10.2 + 1.55*np.sin(lon*3.4 + t*.23)
                                + .34*np.cos(lon*8.6-lat*4.9+t*.39)))
        wisps = (.5 + .5*np.sin(lon*8.8 - adv_lat*7.3 - t*.30))
        thin = (.5 + .5*np.sin(adv_lat*25 + lon*11.2 + t*.42))
        cloud = np.clip(.60*flow + .26*wisps + .14*thin,0,1)
        # Matte rather than metallic: diffuse warm lights, no crisp white specular spot.
        diffuse = np.clip(.55 + .45*(-.34*self.x+.24*self.y+.89*self.z),.28,1.0)
        falloff = np.clip(.46+.54*self.z**.58,0,1)
        base = self.rgb[None,None,:]*(.38+.65*diffuse*falloff)[:,:,None]
        tint = (self.rgb[None,None,:]*.55 + np.array([.58,.69,.79],dtype=np.float32)*.45)
        highlights = (.22*np.maximum(0., cloud-.38)**1.15)[:,:,None]*tint
        depths = (.16*np.maximum(0., .55-cloud))[:,:,None]
        pixels = np.clip(base + highlights - depths,0,1)
        # Rim dimming adds spherical depth, not a thin-line stencil.
        edge = np.clip((self.z-.04)/.28,0,1)
        pixels = pixels*(.38+.62*edge)[:,:,None]
        # Alpha mask gives mathematically circular anti-aliased edges.
        alpha = np.clip((1-np.sqrt(self.rr))*self.n*.80,0,1)
        bg=np.array([14.,17.,25.], dtype=np.float32)/255
        pixels = pixels*alpha[:,:,None] + bg[None,None,:]*(1-alpha[:,:,None])
        rgba=np.empty((self.n,self.n,4),dtype=np.uint8)
        rgba[:,:,:3]=(pixels*255).astype(np.uint8)
        rgba[:,:,3]=255
        self.image=QImage(rgba.tobytes(),self.n,self.n,self.n*4,QImage.Format_RGBA8888).copy()

    def paintEvent(self, event):
        p=QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setRenderHint(QPainter.SmoothPixmapTransform)
        p.fillRect(self.rect(), QColor("#0E1119"))
        if self.image is None: self.render()
        clock=time.monotonic()-self.start
        side=min(self.width(),self.height())
        diameter=side*.665*(1+.009*math.sin(clock*.95)+.029*self.level)
        cx,cy=self.width()/2,self.height()/2
        radius=diameter/2
        c=QColor.fromRgbF(float(self.rgb[0]),float(self.rgb[1]),float(self.rgb[2]))
        # Layered semi-transparent atmosphere. Stays spherical for all modes.
        for i in range(7,0,-1):
            r=radius*(1+i*.065)
            rim=QColor(c)
            rim.setAlphaF(.009+(7-i)*.002)
            p.setBrush(rim);p.setPen(Qt.NoPen)
            p.drawEllipse(QRectF(cx-r,cy-r,2*r,2*r))
        p.drawImage(QRectF(cx-radius,cy-radius,diameter,diameter),self.image)
        # The limb of the sphere catches a little atmospheric light.
        edge=QColor(c); edge.setAlphaF(.31)
        p.setPen(QPen(edge,1.55));p.setBrush(Qt.NoBrush)
        p.drawEllipse(QRectF(cx-radius,cy-radius,diameter,diameter))
        # A transparent rim glint, limited to the upper left.
        glow=QColor(c);glow.setAlphaF(.14)
        p.setPen(QPen(glow,2.0))
        p.drawArc(QRectF(cx-radius-2,cy-radius-2,2*radius+4,2*radius+4),50*16,65*16)
        p.end()

    def closeEvent(self, event):
        self.timer.stop()
        super().closeEvent(event)

def configure_gpu():
    """Compatibility hook. Uses Qt raster rendering, not GPU/OpenGL."""
    pass
