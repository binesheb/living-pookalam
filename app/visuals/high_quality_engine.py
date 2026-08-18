"""High-quality 1080p visual engine for Live Pookalam.

Designed for the field projector: deterministic animation, bounded object count,
Pookalam-aware geometry and a clean adapter boundary so the same renderer works
for preview and production output.
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
    kind: str = "gold"
    phase: float = 0.0


class VisualEngine:
    """Production visual engine tuned for a 1920x1080 projector."""

    EFFECTS = (
        "base", "breathing_glow", "radial_wave", "petal_flow", "fireflies",
        "lotus_bloom", "interaction_ripple", "interaction_spark", "spiral",
        "color_pulse", "edge_glow", "edge_trace", "edge_electric",
        "edge_particles", "edge_draw", "edge_pulse", "ring_pulse",
        "radial_rays", "gold_dust", "sparkle", "golden_shimmer", "deepam",
        "flower_bloom", "petal_drift", "petal_shimmer", "water_ripple",
        "liquid_edge", "energy_ring", "shockwave", "touch_burst", "touch_trail",
        "region_react", "reveal", "dissolve", "bloom", "light_sweep", "flower_shower",
        "magic_ring", "aurora", "mandala_spin", "starfield", "petal_burst",
        "golden_rain", "heartbeat", "center_beacon", "edge_spark", "color_wave",
    )

    def __init__(self, seed: int = 2026):
        self.rng = random.Random(seed)
        self.particles: list[Particle] = []
        self.t = 0.0
        self.intensity = 1.0
        self.speed = 1.0
        self.effects = {name: True for name in self.EFFECTS}
        self.palette = [(255, 196, 70), (255, 125, 65), (245, 80, 120), (255, 235, 160), (255, 165, 60)]
        self._spawn_timer = 0.0
        self._last_interaction = Interaction()
        self.max_particles = 900

    def reset(self):
        self.particles.clear(); self.t = 0.0; self._spawn_timer = 0.0
        self._last_interaction = Interaction()

    def update(self, dt: float, interaction: Interaction | None = None):
        dt = max(0.0, min(float(dt), 0.05))
        self.t += dt * self.speed
        interaction = interaction or Interaction()
        self._last_interaction = interaction
        self._spawn_timer += dt
        if self._spawn_timer >= 0.045:
            self._spawn_timer = 0.0
            if any(self.effects.get(k) for k in ("petal_flow", "petal_drift", "gold_dust", "flower_shower", "golden_rain", "starfield", "petal_burst")):
                self._spawn_particles(interaction)
        alive=[]
        for p in self.particles:
            p.x += p.vx*dt; p.y += p.vy*dt
            p.vx *= 0.998; p.vy *= 0.998
            p.vy += 0.006*dt
            p.life -= dt
            if p.life > 0 and -0.2 < p.x < 1.2 and -0.2 < p.y < 1.2: alive.append(p)
        self.particles = alive[-self.max_particles:]

    def _spawn_particles(self, interaction: Interaction):
        count = 3 if not interaction.active else 7
        for _ in range(count):
            a=self.rng.random()*math.tau
            r=0.18+self.rng.random()*0.72
            x=.5+math.cos(a)*r*.48; y=.5+math.sin(a)*r*.48
            kind="petal" if self.effects.get("petal_flow") or self.effects.get("petal_drift") else "gold"
            if self.effects.get("starfield") and self.rng.random()<.25: kind="star"
            self.particles.append(Particle(x,y,math.cos(a)*.006,math.sin(a)*.004+.004,
                                            1.0+self.rng.random()*1.8,2+self.rng.random()*4,kind,self.rng.random()*math.tau))

    @staticmethod
    def _rgb(c,a=1.0): return tuple(max(0,min(255,int(v*a))) for v in c)

    def render(self, draw, width:int, height:int, mask=None, interaction:Interaction|None=None, pattern:Any=None):
        interaction=interaction or Interaction()
        if pattern is None:
            cx,cy=width*.5,height*.5; R=min(width,height)*.38
        else:
            pw=max(1,float(getattr(pattern,"width",width))); ph=max(1,float(getattr(pattern,"height",height)))
            pc=getattr(pattern,"centre",(pw*.5,ph*.5)); cx=float(pc[0])/pw*width; cy=float(pc[1])/ph*height
            R=min(width/pw,height/ph)*float(getattr(pattern,"radius",min(pw,ph)*.38))
        R*=max(.2,min(1.5,self.intensity))
        if self.effects.get("base"): self._base(draw,cx,cy,R)
        if self.effects.get("bloom") or self.effects.get("breathing_glow"): self._glow(draw,cx,cy,R)
        if self.effects.get("center_beacon"): self._beacon(draw,cx,cy,R)
        if self.effects.get("radial_rays"): self._rays(draw,cx,cy,R)
        if self.effects.get("radial_wave") or self.effects.get("color_wave"): self._waves(draw,cx,cy,R)
        if self.effects.get("ring_pulse"): self._rings(draw,cx,cy,R,pattern)
        if self.effects.get("spiral") or self.effects.get("mandala_spin"): self._spiral(draw,cx,cy,R)
        if self.effects.get("lotus_bloom") or self.effects.get("flower_bloom"): self._lotus(draw,cx,cy,R*.22)
        if self.effects.get("fireflies") or self.effects.get("starfield"): self._fireflies(draw,cx,cy,R)
        if self.effects.get("petal_flow") or self.effects.get("petal_drift") or self.effects.get("gold_dust") or self.effects.get("flower_shower") or self.effects.get("golden_rain") or self.effects.get("petal_burst"): self._particles(draw,width,height)
        if self.effects.get("golden_shimmer") or self.effects.get("light_sweep"): self._sweep(draw,cx,cy,R)
        if self.effects.get("deepam"): self._deepam(draw,cx,cy,R)
        if self.effects.get("aurora"): self._aurora(draw,cx,cy,R)
        if self.effects.get("heartbeat"): self._heartbeat(draw,cx,cy,R)
        if self.effects.get("color_pulse"): self._color_pulse(draw,cx,cy,R)
        if pattern is not None and getattr(pattern,"contour",None) is not None: self._edge(draw,pattern,width,height)
        if interaction.active: self._interaction(draw,interaction,width,height,R)

    def _base(self,d,cx,cy,R):
        for i in range(5):
            rr=R*(.96-i*.10); d.circle(cx,cy,rr,self._rgb(self.palette[i],.18),width=max(2,int(R*.018)))
        for i in range(36):
            a=math.tau*i/36+self.t*.025; self._petal(d,cx+math.cos(a)*R*.89,cy+math.sin(a)*R*.89,a,R*.045,self.palette[i%5])

    def _petal(self,d,x,y,a,r,c):
        ux,uy=math.cos(a),math.sin(a); vx,vy=-uy,ux
        d.polygon([(x+ux*r*1.8,y+uy*r*1.8),(x+vx*r*.7,y+vy*r*.7),(x-ux*r*.9,y-uy*r*.9),(x-vx*r*.7,y-vy*r*.7)],self._rgb(c,.68))

    def _glow(self,d,cx,cy,R):
        pulse=.5+.5*math.sin(self.t*1.25)
        for i in range(7): d.circle(cx,cy,R*(.55+i*.045+pulse*.012),self._rgb((255,150,70),.028),width=max(1,8-i))

    def _beacon(self,d,cx,cy,R):
        q=.5+.5*math.sin(self.t*2.4); d.circle(cx,cy,R*.09+q*R*.025,self._rgb((255,240,170),.65),width=0); d.circle(cx,cy,R*.17+q*R*.03,self._rgb((255,200,80),.12),width=max(2,int(R*.012)))

    def _rays(self,d,cx,cy,R):
        for i in range(24):
            a=math.tau*i/24+self.t*.015; d.line([(cx,cy),(cx+math.cos(a)*R,cy+math.sin(a)*R)],self._rgb((255,225,150),.045),width=max(1,int(R*.004)))

    def _waves(self,d,cx,cy,R):
        for j in range(5):
            p=(self.t*.13+j*.21)%1; rr=R*(.08+p*.92); d.circle(cx,cy,rr,self._rgb((255,220,120),(.22*(1-p))),width=max(2,int(7*(1-p))))

    def _rings(self,d,cx,cy,R,pattern):
        rings=getattr(pattern,"rings",()) if pattern is not None else (.2,.38,.56,.74,.9)
        base=getattr(pattern,"radius",R) if pattern is not None else 1
        for i,v in enumerate(rings):
            rr=float(v)/max(1,float(base))*R if pattern is not None else R*float(v)
            q=.5+.5*math.sin(self.t*1.4+i*.8); d.circle(cx,cy,rr,self._rgb((255,205,90),.10*q),width=max(1,int(2+4*q)))

    def _spiral(self,d,cx,cy,R):
        pts=[]
        for i in range(120):
            q=i/119; a=i*.16+self.t*.10; rr=R*(.04+.88*q); pts.append((cx+math.cos(a)*rr,cy+math.sin(a)*rr))
        d.line(pts,self._rgb((255,200,80),.22),width=max(1,int(R*.006)))

    def _lotus(self,d,cx,cy,r):
        for i in range(16):
            a=math.tau*i/16+self.t*.03; self._petal(d,cx+math.cos(a)*r*.45,cy+math.sin(a)*r*.45,a,r*.32,(255,185+int(35*math.sin(a)),175))
        d.circle(cx,cy,r*.16,self._rgb((255,235,150),.9),width=0)

    def _fireflies(self,d,cx,cy,R):
        for i in range(52):
            a=math.tau*i/52+self.t*(.018+(i%4)*.002); rr=R*(.28+.45*((i*17)%31)/31); q=.25+.75*(.5+.5*math.sin(self.t*2.7+i*1.7)); d.circle(cx+math.cos(a)*rr,cy+math.sin(a)*rr,1.5+q*2.5,self._rgb((255,238,155),q*.8),width=0)

    def _particles(self,d,w,h):
        for p in self.particles:
            a=max(0,min(1,p.life))*.8; c=(255,220,100) if p.kind=="gold" else ((255,180,205) if p.kind=="petal" else (255,250,190)); r=p.size
            if p.kind=="star":
                x,y=p.x*w,p.y*h; d.line([(x-r*2,y),(x+r*2,y)],self._rgb(c,a),width=1); d.line([(x,y-r*2),(x,y+r*2)],self._rgb(c,a),width=1)
            else: d.circle(p.x*w,p.y*h,r,self._rgb(c,a),width=0)

    def _sweep(self,d,cx,cy,R):
        a=(self.t*.35)%math.tau; x=cx+math.cos(a)*R; y=cy+math.sin(a)*R; d.circle(x,y,R*.16,self._rgb((255,235,160),.10),width=max(2,int(R*.035)))

    def _deepam(self,d,cx,cy,R):
        q=.5+.5*math.sin(self.t*3.0); d.circle(cx,cy+R*.10,R*.10,self._rgb((255,175,55),.55),width=0); d.circle(cx,cy+R*.02,R*(.16+q*.025),self._rgb((255,220,120),.08),width=max(2,int(R*.012)))

    def _aurora(self,d,cx,cy,R):
        for i in range(8):
            a=self.t*.12+i*.35; x=cx+math.cos(a)*R*.45; y=cy+math.sin(a*1.7)*R*.35; d.circle(x,y,R*.18,self._rgb((120,220,255),.025),width=max(2,int(R*.025)))

    def _heartbeat(self,d,cx,cy,R):
        q=.5+.5*math.sin(self.t*2.0); d.circle(cx,cy,R*(.72+q*.025),self._rgb((255,90,100),.10),width=max(2,int(R*.012)))

    def _color_pulse(self,d,cx,cy,R):
        q=.5+.5*math.sin(self.t*.8); d.circle(cx,cy,R*.64,self._rgb((255,105,90),.045*q),width=max(2,int(R*.02)))

    def _edge(self,d,pattern,w,h):
        pts=[(float(x)/max(1,pattern.width)*w,float(y)/max(1,pattern.height)*h) for x,y in pattern.contour.reshape(-1,2)]
        if len(pts)<3:return
        closed=pts+[pts[0]]
        if self.effects.get("edge_glow"):
            for wp,a in ((18,.025),(11,.055),(6,.12)): d.line(closed,self._rgb((185,120,255),a),width=wp)
        if self.effects.get("edge_electric") or self.effects.get("edge_spark"):
            seg=[]
            step=max(1,len(pts)//80)
            for i in range(0,len(pts),step):
                x,y=pts[i]; j=(i+1)%len(pts); nx,ny=pts[j]; wob=4*math.sin(self.t*6+i*2.1); seg.extend([(x,y),(nx+wob,ny-wob)])
            d.line(seg,self._rgb((100,220,255),.72),width=3)
        if self.effects.get("edge_trace") or self.effects.get("edge_pulse"):
            n=len(pts); head=int((self.t*.18%1)*n); span=max(8,int(n*.10)); trace=[pts[(head-i)%n] for i in range(span)]
            d.line(trace,self._rgb((255,235,125),.9),width=max(3,int(w*.0025)))
        if self.effects.get("edge_particles"):
            n=len(pts); step=max(1,n//45)
            for i in range(0,n,step):
                x,y=pts[(i+int(self.t*18))%n]; d.circle(x,y,2.5,self._rgb((255,225,120),.9),width=0)
        if self.effects.get("edge_draw") or self.effects.get("reveal"):
            count=max(2,int(len(pts)*((self.t*.055)%1))); d.line(pts[:count],self._rgb((255,210,90),.8),width=4)
        if self.effects.get("liquid_edge"): d.line(closed,self._rgb((80,210,255),.32+.08*math.sin(self.t*2)),width=7)

    def _interaction(self,d,inter,w,h,R):
        x,y=inter.x*w,inter.y*h
        if self.effects.get("interaction_ripple") or self.effects.get("water_ripple") or self.effects.get("shockwave"):
            for i in range(6):
                p=(self.t*1.25+i*.17)%1; rr=R*(.03+p*.62)*(.6+.7*inter.strength); c=(80,215,255) if self.effects.get("water_ripple") else (255,225,105); d.circle(x,y,rr,self._rgb(c,(1-p)*.30),width=max(2,int(R*.012*(1-p))))
        if self.effects.get("touch_burst") or self.effects.get("interaction_spark") or self.effects.get("energy_ring"):
            for i in range(32):
                a=math.tau*i/32+self.t*1.5; rr=R*(.06+.20*inter.strength); d.circle(x+math.cos(a)*rr,y+math.sin(a)*rr,2+2*inter.strength,self._rgb((255,220,95),.9),width=0)
        if self.effects.get("touch_trail"):
            for i in range(14):
                q=i/14; d.circle(x-inter.velocity_x*w*q*.35,y-inter.velocity_y*h*q*.35,max(1,4*(1-q)),self._rgb((190,120,255),(1-q)*.55),width=0)

    def set_effect(self,name,enabled):
        if name in self.effects:self.effects[name]=bool(enabled)

    def set_all(self,enabled):
        for key in self.effects:self.effects[key]=bool(enabled)

    def apply_preset(self,effect_ids):
        self.set_all(False); self.effects["base"]=True
        for effect_id in effect_ids:self.set_effect(effect_id,True)
