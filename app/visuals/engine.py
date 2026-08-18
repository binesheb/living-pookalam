"""Realtime, pattern-aware visual engine for Live Pookalam.

The renderer is deliberately independent from Tkinter. It consumes normalized
Pookalam geometry and an interaction point, then draws effect layers through a
small adapter. This makes the same effects usable for previews and the full
projector surface.
"""
from __future__ import annotations

import math
import random
from dataclasses import dataclass
from typing import Any


@dataclass
class Interaction:
    x: float = 0.5
    y: float = 0.5
    strength: float = 0.0
    active: bool = False
    velocity_x: float = 0.0
    velocity_y: float = 0.0


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
    """Render a layered, Pookalam-aware experience."""

    EFFECTS = (
        "base", "breathing_glow", "radial_wave", "petal_flow", "fireflies",
        "lotus_bloom", "interaction_ripple", "interaction_spark", "spiral",
        "color_pulse", "edge_glow", "edge_trace", "edge_electric",
        "edge_particles", "edge_draw", "edge_pulse", "ring_pulse",
        "radial_rays", "gold_dust", "sparkle", "golden_shimmer", "deepam",
        "flower_bloom", "petal_drift", "petal_shimmer", "water_ripple",
        "liquid_edge", "energy_ring", "shockwave", "touch_burst", "touch_trail",
        "region_react", "reveal", "dissolve",
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
        self._last_interaction = Interaction()

    def reset(self):
        self.particles.clear()
        self.t = 0.0
        self._spawn_timer = 0.0
        self._last_interaction = Interaction()

    def update(self, dt: float, interaction: Interaction | None = None):
        dt = max(0.0, min(dt, 0.1))
        self.t += dt * self.speed
        interaction = interaction or Interaction()
        self._last_interaction = interaction
        self._spawn_timer += dt
        if self._spawn_timer > 0.055 and (self.effects.get("petal_flow") or self.effects.get("petal_drift") or self.effects.get("gold_dust")):
            self._spawn_timer = 0.0
            self._spawn_particles(interaction)
        alive = []
        for p in self.particles:
            p.x += p.vx * dt
            p.y += p.vy * dt
            p.vy += 0.012 * dt
            p.vx *= 0.996
            p.vy *= 0.996
            p.life -= dt
            if p.life > 0 and -0.2 < p.x < 1.2 and -0.2 < p.y < 1.2:
                alive.append(p)
        self.particles = alive[-1200:]

    def _spawn_particles(self, interaction: Interaction):
        for _ in range(2 if not interaction.active else 4):
            a = self.rng.random() * math.tau
            r = 0.12 + self.rng.random() * 0.43
            x, y = 0.5 + math.cos(a) * r, 0.5 + math.sin(a) * r
            if interaction.active:
                dx, dy = x - interaction.x, y - interaction.y
                d = max(0.04, math.hypot(dx, dy))
                push = min(0.15, interaction.strength * 0.16 / d)
                x += dx / d * push * 0.03
                y += dy / d * push * 0.03
            kind = "gold" if self.effects.get("gold_dust") else "petal"
            self.particles.append(Particle(x, y, math.cos(a) * .018, math.sin(a) * .018,
                                            .8 + self.rng.random() * 1.5, 2 + self.rng.random() * 4, kind))

    @staticmethod
    def _rgb(c, a=1.0):
        return tuple(max(0, min(255, int(v * a))) for v in c)

    @staticmethod
    def _hex(c):
        return "#%02x%02x%02x" % tuple(max(0, min(255, int(v))) for v in c)

    def render(self, draw, width: int, height: int, mask=None, interaction: Interaction | None = None, pattern: Any = None):
        interaction = interaction or Interaction()
        cx = width * .5 if pattern is None else float(getattr(pattern, "centre", (.5, .5))[0]) * width
        cy = height * .5 if pattern is None else float(getattr(pattern, "centre", (.5, .5))[1]) * height
        if pattern is not None and getattr(pattern, "width", width):
            cx = float(getattr(pattern, "centre", (pattern.width / 2, pattern.height / 2))[0]) / pattern.width * width
            cy = float(getattr(pattern, "centre", (pattern.width / 2, pattern.height / 2))[1]) / pattern.height * height
            R = min(width / pattern.width, height / pattern.height) * float(getattr(pattern, "radius", min(pattern.width, pattern.height) * .38))
        else:
            R = min(width, height) * .38
        R *= self.intensity

        if self.effects.get("base"): self._base(draw, cx, cy, R)
        if self.effects.get("breathing_glow"): self._breathing(draw, cx, cy, R)
        if self.effects.get("radial_rays"): self._rays(draw, cx, cy, R)
        if self.effects.get("radial_wave"): self._waves(draw, cx, cy, R)
        if self.effects.get("ring_pulse"): self._rings(draw, cx, cy, R, pattern)
        if self.effects.get("lotus_bloom") or self.effects.get("flower_bloom"): self._lotus(draw, cx, cy, R * .22)
        if self.effects.get("spiral"): self._spiral(draw, cx, cy, R)
        if self.effects.get("fireflies"): self._fireflies(draw, cx, cy, R)
        if self.effects.get("petal_flow") or self.effects.get("petal_drift") or self.effects.get("gold_dust"): self._particles(draw, width, height)
        if self.effects.get("color_pulse"): self._color_pulse(draw, cx, cy, R)
        if pattern is not None and getattr(pattern, "contour", None) is not None:
            self._edge_effects(draw, pattern, width, height)
        if interaction.active:
            self._interaction(draw, interaction, width, height, R)

    def _base(self, draw, cx, cy, R):
        for i in range(6):
            rr = R * (1 - i * .095)
            draw.circle(cx, cy, rr, self._rgb(self.palette[i % len(self.palette)], .68), width=max(4, int(R * .028)))
        for i in range(36):
            a = math.tau * i / 36 + self.t * .05
            x, y = cx + math.cos(a) * R * .92, cy + math.sin(a) * R * .92
            self._petal(draw, x, y, a, R * .07, self.palette[i % len(self.palette)])

    def _petal(self, draw, x, y, a, r, col):
        ux, uy = math.cos(a), math.sin(a); vx, vy = -uy, ux
        pts = [(x + ux*r*1.7, y + uy*r*1.7), (x + vx*r*.75, y + vy*r*.75),
               (x - ux*r*.8, y - uy*r*.8), (x - vx*r*.75, y - vy*r*.75)]
        draw.polygon(pts, self._rgb(col, .78))

    def _breathing(self, draw, cx, cy, R):
        pulse = .5 + .5 * math.sin(self.t * 1.7)
        for i in range(5):
            rr = R * (.72 + i*.045 + pulse*.018)
            draw.circle(cx, cy, rr, self._rgb((255,145,60), .035), width=max(1, int(9-i)))

    def _waves(self, draw, cx, cy, R):
        for j in range(4):
            phase = (self.t * .16 + j * .25) % 1
            rr = R * (.15 + phase * .9)
            draw.circle(cx, cy, rr, self._rgb((255,224,120), (1-phase)*.22), width=max(2, int(6*(1-phase))))

    def _rings(self, draw, cx, cy, R, pattern):
        rings = getattr(pattern, "rings", ()) if pattern is not None else tuple(R*f for f in (.22,.38,.54,.70,.86))
        for i, value in enumerate(rings):
            rr = value if pattern is None else float(value) / max(1, getattr(pattern, "radius", 1)) * R
            pulse = .5 + .5 * math.sin(self.t * 1.3 + i * .8)
            draw.circle(cx, cy, rr, self._rgb((255,205,90), .10 * pulse), width=max(1, int(2 + 3*pulse)))

    def _lotus(self, draw, cx, cy, r):
        for i in range(12):
            a = math.tau*i/12 + self.t*.08
            px, py = cx+math.cos(a)*r*.42, cy+math.sin(a)*r*.42
            self._petal(draw, px, py, a, r*.42, (255,190+int(30*math.sin(a)),180))
        draw.circle(cx, cy, r*.16, (255,232,140), width=0)

    def _spiral(self, draw, cx, cy, R):
        pts=[]
        for i in range(150):
            a=i*.14+self.t*.16; rr=R*.06+R*.82*(i/149)
            pts.append((cx+math.cos(a)*rr, cy+math.sin(a)*rr))
        draw.line(pts, self._rgb((255,195,75), .20), width=max(1,int(R*.008)))

    def _rays(self, draw, cx, cy, R):
        for i in range(20):
            a = math.tau*i/20 + self.t*.04
            x, y = cx + math.cos(a)*R*.96, cy + math.sin(a)*R*.96
            draw.line([(cx,cy),(x,y)], self._rgb((255,218,130), .08), width=2)

    def _fireflies(self, draw, cx, cy, R):
        for i in range(42):
            a=math.tau*(i/42)+self.t*(.03+(i%5)*.004); rr=R*(.35+.25*math.sin(i*7.1)**2)
            pulse=.4+.6*(.5+.5*math.sin(self.t*3+i))
            draw.circle(cx+math.cos(a)*rr, cy+math.sin(a)*rr, 2+pulse*2, self._rgb((255,235,145), .75*pulse), width=0)

    def _particles(self, draw, w, h):
        for p in self.particles:
            alpha=max(0,min(1,p.life))*.85
            col=(255,215,100) if p.kind == "gold" else self.palette[int(p.x*97+p.y*31)%len(self.palette)]
            draw.circle(p.x*w,p.y*h,p.size,self._rgb(col,alpha),width=0)

    def _color_pulse(self, draw, cx, cy, R):
        q=.5+.5*math.sin(self.t*.9); draw.circle(cx,cy,R*.64,self._rgb((255,105,90),.045*q),width=max(2,int(R*.025)))

    def _edge_points(self, pattern, width, height):
        contour = getattr(pattern, "contour", None)
        if contour is None: return []
        pts = contour.reshape(-1,2)
        pw, ph = max(1, pattern.width), max(1, pattern.height)
        return [(float(x)/pw*width, float(y)/ph*height) for x,y in pts]

    def _edge_effects(self, draw, pattern, width, height):
        pts = self._edge_points(pattern, width, height)
        if len(pts) < 3: return
        if self.effects.get("edge_glow"):
            for width_px, alpha in ((16,.035),(10,.07),(5,.13)):
                draw.line(pts + [pts[0]], self._rgb((190,120,255), alpha), width=width_px)
        if self.effects.get("edge_trace") or self.effects.get("edge_pulse"):
            n = len(pts); head = int((self.t * .22 % 1.0) * n); span=max(5,int(n*.08))
            trace=[pts[(head-i)%n] for i in range(span)]
            for i,p in enumerate(trace):
                a=(1-i/max(1,len(trace)-1))
                draw.circle(p[0],p[1],max(2,int(5*a)),self._rgb((255,235,120),a*.9),width=0)
        if self.effects.get("edge_electric"):
            seg=[]
            for i in range(0,len(pts),max(1,len(pts)//60)):
                x,y=pts[i]; j=(i+1)%len(pts); nx,ny=pts[j]
                wob=3*math.sin(self.t*5+i*1.7); seg.extend([(x,y),(nx+wob,ny-wob)])
            draw.line(seg,self._rgb((110,220,255),.7),width=3)
        if self.effects.get("edge_particles"):
            for i in range(0,len(pts),max(1,len(pts)//35)):
                x,y=pts[(i+int(self.t*12))%len(pts)]; draw.circle(x,y,2.5,self._rgb((255,220,110),.9),width=0)
        if self.effects.get("edge_draw") or self.effects.get("reveal"):
            count=max(2,int(len(pts)*((self.t*.06)%1)))
            draw.line(pts[:count],self._rgb((255,205,80),.65),width=4)
        if self.effects.get("liquid_edge"):
            draw.line(pts+[pts[0]],self._rgb((80,210,255),.28+.10*math.sin(self.t*2)),width=7)

    def _interaction(self, draw, interaction, w, h, R):
        x,y=interaction.x*w, interaction.y*h
        if self.effects.get("interaction_ripple") or self.effects.get("water_ripple") or self.effects.get("shockwave"):
            for i in range(5):
                phase=(self.t*1.4+i*.19)%1; rr=R*(.04+phase*.55)*(.5+.8*interaction.strength)
                col=(90,210,255) if self.effects.get("water_ripple") else (255,231,110)
                draw.circle(x,y,rr,self._rgb(col,(1-phase)*.32),width=max(2,int(R*.012*(1-phase))))
        if self.effects.get("interaction_spark") or self.effects.get("touch_burst") or self.effects.get("energy_ring"):
            for i in range(28):
                a=math.tau*i/28+self.t*1.8; rr=R*(.08+.20*interaction.strength)+R*.04*math.sin(self.t*4+i)
                draw.circle(x+math.cos(a)*rr,y+math.sin(a)*rr,2.5+2*interaction.strength,self._rgb((255,220,95),.9),width=0)
        if self.effects.get("touch_trail") and interaction.active:
            for i in range(12):
                q=i/12; px=x-interaction.velocity_x*w*q*.4; py=y-interaction.velocity_y*h*q*.4
                draw.circle(px,py,max(1,4*(1-q)),self._rgb((190,120,255),(1-q)*.55),width=0)

    def set_effect(self,name,enabled):
        if name in self.effects: self.effects[name]=bool(enabled)

    def set_all(self,enabled):
        for key in self.effects: self.effects[key]=bool(enabled)

    def apply_preset(self, effect_ids):
        self.set_all(False)
        self.effects["base"] = True
        for effect_id in effect_ids:
            self.set_effect(effect_id, True)
