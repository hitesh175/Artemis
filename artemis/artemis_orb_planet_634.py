"""ARTEMIS 6.3.4: deep matte living planet. Safe CPU/Qt renderer, no OpenGL.
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
        # The sphere always has a mathematically circular silhouette.
        # Directional lighting + spherical mapping create 3D volume without OpenGL.
        t = (time.monotonic()-self.start)*SPEEDS[self.state]
        lon = self.lon + .24*t
        lat = self.lat
        # Different speeds and frequencies make the surface drift like atmospheric fluid.
        vortex = (.20*np.sin(lon*2.0 + 1.6*np.sin(lat*3.3-t*.13))
                  + .075*np.sin(lon*5.3 + lat*6.1+t*.21))
        warped = lat + vortex
        ribbon = np.sin(warped*10.6 + 1.8*np.sin(lon*2.1+t*.16))
        current = np.sin(lon*5.0 - warped*8.2 - t*.24)
        filament = np.sin(lon*11.2 + warped*15.0 + t*.30)
        # Clouds are narrow, restrained, and transparent, not broad pale blobs.
        clouds = np.clip((.56*ribbon + .31*current + .13*filament-.09)*1.65, 0, 1)
        shadows = np.clip((-.57*ribbon-.25*current-.18*filament-.28)*1.3,0,1)
        # Stable deep planetary color; highlights retain the active mode hue.
        base_color = self.rgb[None,None,:]
        lx, ly, lz = -.46, -.31, .83
        daylight = np.clip(self.x*lx + self.y*ly + self.z*lz, -.15, 1)
        shading = (.18 + .79*np.maximum(daylight,0)**.85) * (.55+.45*self.z**.55)
        base = base_color*(.42+.62*shading)[:,:,None]
        # Soft matte currents with a second tonality derived from the same hue.
        cloud_color = np.clip(base_color*.76 + .16,0,1)
        surface = base + clouds[:,:,None]*(.16+.13*shading[:,:,None])*cloud_color
        surface -= shadows[:,:,None]*(.095+.07*shading[:,:,None])
        # A controlled glow around the sunlit edge, but no glossy white hotspot.
        atmosphere = np.clip((self.z-.03)/.25,0,1)
        surface *= (.47 + .53*atmosphere)[:,:,None]
        # Slightly warmer illumination on the lit hemisphere gives tangible depth.
        warmth = np.array([.035,.026,.018],dtype=np.float32)
        surface += warmth[None,None,:]*np.maximum(daylight,0)[:,:,None]*.38
        surface = np.clip(surface,0,1)
        aa = np.clip((1-np.sqrt(self.rr))*self.n*.82,0,1)
        bg=np.array([14.,17.,25.],dtype=np.float32)/255
        pixels=surface*aa[:,:,None] + bg[None,None,:]*(1-aa[:,:,None])
        rgba=np.empty((self.n,self.n,4),dtype=np.uint8)
        rgba[:,:,:3]=(np.clip(pixels,0,1)*255).astype(np.uint8)
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
        diameter=side*.665*(1+.007*math.sin(clock*.85)+.037*self.level)
        cx,cy=self.width()/2,self.height()/2
        radius=diameter/2
        c=QColor.fromRgbF(float(self.rgb[0]),float(self.rgb[1]),float(self.rgb[2]))
        # Layered semi-transparent atmosphere. Stays spherical for all modes.
        for i in range(7,0,-1):
            r=radius*(1+i*.065)
            rim=QColor(c)
            rim.setAlphaF(.006+(7-i)*.0015)
            p.setBrush(rim);p.setPen(Qt.NoPen)
            p.drawEllipse(QRectF(cx-r,cy-r,2*r,2*r))
        p.drawImage(QRectF(cx-radius,cy-radius,diameter,diameter),self.image)
        # The limb of the sphere catches a little atmospheric light.
        edge=QColor(c); edge.setAlphaF(.24)
        p.setPen(QPen(edge,1.55));p.setBrush(Qt.NoBrush)
        p.drawEllipse(QRectF(cx-radius,cy-radius,diameter,diameter))
        # A transparent rim glint, limited to the upper left.
        glow=QColor(c);glow.setAlphaF(.11)
        p.setPen(QPen(glow,2.0))
        p.drawArc(QRectF(cx-radius-2,cy-radius-2,2*radius+4,2*radius+4),50*16,65*16)
        p.end()

    def closeEvent(self, event):
        self.timer.stop()
        super().closeEvent(event)

def configure_gpu():
    """Compatibility hook. Uses Qt raster rendering, not GPU/OpenGL."""
    pass
