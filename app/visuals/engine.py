"""Realtime Pookalam visual effects engine.

Renderer-agnostic effect generation for the Windows test application.
The engine works in normalized 0..1 Pookalam coordinates so the same
experience can be mapped to different floor sizes and projector resolutions.
"""
from __future__ import annotations

import math
import random
from dataclasses import dataclass
from typing import Iterable

import numpy as np


@dataclass
class Interaction:
    x: float = 0.5
    y: float = 0.5
    strength: float = 0.0
    active: bool = False


@dataclass
class Particle:
    x: float
    y: float
    vx: float
    vy: float
    life: float
    size: float
    kind: str = "petal"


class VisualEngine:
    """Generate animated Pookalam layers and particles.

    Layers are intentionally independent so the UI can toggle them while
    calibrating/testing. The renderer consumes normalized coordinates.
    """

    EFFECTS = (
        "base",
        "breathing_glow",
        "radial_wave",
        "petal_flow",
        "fireflies",
        "lotus_bloom",
        "interaction_ripple",
        "interaction_spark",
        "spiral",
        "color_pulse",
    )

    def __init__(self, seed: int = 2026):
        self.rng = random.Random(seed)
        self.particles: list[Particle] = []
        self.t = 0.0
        self.intensity = 1.0
        self.speed = 1.0
        self.effects = {name: True for name in self.EFFECTS}
        self.palette = [(255, 196, 70), (255, 120, 70), (245, 80, 120), (255, 235, 160), (255, 160, 60)]
        self._spawn_timer = 0.0

    def reset(self):
        self.particles.clear()
        self.t = 0.0
        self._spawn_timer = 0.0

    def update(self, dt: float, interaction: Interaction | None = None):
        self.t += max(0.0, min(dt, 0.1)) * self.speed
        if interaction is None:
            interaction = Interaction()
        self._spawn_timer += dt
        if self.effects.get("petal_flow", True) and self._spawn_timer > 0.07:
            self._spawn_timer = 0.0
            self._spawn_petals(interaction)
        alive=[]
        for p in self.particles:
            p.x += p.vx * dt
            p.y += p.vy * dt
            p.vy += 0.018 * dt
            p.vx *= 0.996
            p.vy *= 0.996
            p.life -= dt
            if p.life > 0 and -0.15 < p.x < 1.15 and -0.15 < p.y < 1.15:
                alive.append(p)
        self.particles=alive[-700:]

    def _spawn_petals(self, interaction: Interaction):
        for _ in range(2):
            a=self.rng.random()*math.tau
            r=0.18+self.rng.random()*0.34
            x=.5+math.cos(a)*r; y=.5+math.sin(a)*r
            if interaction.active and interaction.strength>.25:
                dx=x-interaction.x; dy=y-interaction.y
                d=max(.04,math.hypot(dx,dy))
                push=min(.22,interaction.strength*.22/d)
                x += dx/d*push*.02; y += dy/d*push*.02
            self.particles.append(Particle(x,y,math.cos(a)*.025,math.sin(a)*.025,.9+self.rng.random()*1.2,3+self.rng.random()*4))

    def _rgb(self, c, a=1.0):
        return tuple(max(0,min(255,int(v*a))) for v in c)

    def render(self, draw, width: int, height: int, mask=None, interaction: Interaction | None=None):
        """Render into a pygame-like drawing adapter.

        Adapter methods used: circle(x,y,r,fill,width=0), line(points,fill,width),
        polygon(points,fill), and ellipse(rect,fill,width=0).
        """
        if interaction is None: interaction=Interaction()
        cx,cy=width*.5,height*.5
        R=min(width,height)*.38*self.intensity
        if self.effects.get("base"):
            self._base(draw,cx,cy,R,width,height)
        if self.effects.get("breathing_glow"):
            pulse=.5+.5*math.sin(self.t*1.7)
            for i in range(5):
                rr=R*(.72+i*.045+pulse*.018)
                draw.circle(cx,cy,rr,self._rgb((255,145,60),.035),width=max(1,int(9-i)))
        if self.effects.get("radial_wave"):
            self._waves(draw,cx,cy,R)
        if self.effects.get("lotus_bloom"):
            self._lotus(draw,cx,cy,R*.22)
        if self.effects.get("spiral"):
            self._spiral(draw,cx,cy,R)
        if self.effects.get("fireflies"):
            self._fireflies(draw,cx,cy,R)
        if self.effects.get("petal_flow"):
            self._particles(draw,width,height)
        if self.effects.get("color_pulse"):
            self._color_pulse(draw,cx,cy,R)
        if self.effects.get("interaction_ripple") and interaction.active:
            self._interaction_ripple(draw,interaction,width,height,R)
        if self.effects.get("interaction_spark") and interaction.active:
            self._interaction_spark(draw,interaction,width,height,R)

    def _base(self,draw,cx,cy,R,w,h):
        for i in range(6):
            rr=R*(1-i*.095)
            col=self.palette[i%len(self.palette)]
            draw.circle(cx,cy,rr,self._rgb(col,.68),width=max(4,int(R*.028)))
        for i in range(36):
            a=math.tau*i/36+self.t*.05
            x=cx+math.cos(a)*R*.92; y=cy+math.sin(a)*R*.92
            self._petal(draw,x,y,math.atan2(y-cy,x-cx),R*.07,self.palette[i%len(self.palette)])

    def _petal(self,draw,x,y,a,r,col):
        ux,uy=math.cos(a),math.sin(a); vx,vy=-uy,ux
        pts=[(x+ux*r*1.7,y+uy*r*1.7),(x+vx*r*.75,y+vy*r*.75),(x-ux*r*.8,y-uy*r*.8),(x-vx*r*.75,y-vy*r*.75)]
        draw.polygon(pts,self._rgb(col,.78))

    def _waves(self,draw,cx,cy,R):
        for j in range(4):
            phase=(self.t*.16+j*.25)%1
            rr=R*(.15+phase*.9)
            alpha=(1-phase)*.22
            draw.circle(cx,cy,rr,self._rgb((255,224,120),alpha),width=max(2,int(6*(1-phase))))

    def _lotus(self,draw,cx,cy,r):
        for i in range(12):
            a=math.tau*i/12+self.t*.08
            px=cx+math.cos(a)*r*.42; py=cy+math.sin(a)*r*.42
            self._petal(draw,px,py,a,r*.42,(255,190+int(30*math.sin(a)),180))
        draw.circle(cx,cy,r*.16,(255,232,140),width=0)

    def _spiral(self,draw,cx,cy,R):
        pts=[]
        for i in range(150):
            a=i*.14+self.t*.16; rr=R*.06+R*.82*(i/149)
            pts.append((cx+math.cos(a)*rr,cy+math.sin(a)*rr))
        draw.line(pts,self._rgb((255,195,75),.20),width=max(1,int(R*.008)))

    def _fireflies(self,draw,cx,cy,R):
        for i in range(42):
            a=math.tau*(i/42)+self.t*(.03+(i%5)*.004)
            rr=R*(.35+.25*math.sin(i*7.1)**2)
            x=cx+math.cos(a)*rr; y=cy+math.sin(a)*rr
            pulse=.4+.6*(.5+.5*math.sin(self.t*3+i))
            draw.circle(x,y,2+pulse*2,self._rgb((255,235,145),.75*pulse),width=0)

    def _particles(self,draw,w,h):
        for p in self.particles:
            alpha=max(0,min(1,p.life))*.85
            col=self.palette[int(p.x*97+ p.y*31)%len(self.palette)]
            draw.circle(p.x*w,p.y*h,p.size,self._rgb(col,alpha),width=0)

    def _color_pulse(self,draw,cx,cy,R):
        q=.5+.5*math.sin(self.t*.9)
        draw.circle(cx,cy,R*.64,self._rgb((255,105,90),.045*q),width=max(2,int(R*.025)))

    def _interaction_ripple(self,draw,interaction,w,h,R):
        x=interaction.x*w; y=interaction.y*h
        for i in range(5):
            phase=(self.t*1.4+i*.19)%1
            rr=R*(.04+phase*.55)*(.5+.8*interaction.strength)
            draw.circle(x,y,rr,self._rgb((255,231,110),(1-phase)*.32),width=max(2,int(R*.012*(1-phase))))

    def _interaction_spark(self,draw,interaction,w,h,R):
        x=interaction.x*w; y=interaction.y*h
        for i in range(24):
            a=math.tau*i/24+self.t*1.8
            rr=R*(.08+.20*interaction.strength)+R*.04*math.sin(self.t*4+i)
            px=x+math.cos(a)*rr; py=y+math.sin(a)*rr
            draw.circle(px,py,2.5+2*interaction.strength,self._rgb((255,220,95),.9),width=0)

    def set_effect(self,name,enabled):
        if name in self.effects:self.effects[name]=bool(enabled)

    def set_all(self,enabled):
        for k in self.effects:self.effects[k]=bool(enabled)
