"""Lightweight interaction effects for Living Pookalam."""
import math, random, time
import cv2, numpy as np

class EffectsEngine:
    def __init__(self, width, height):
        self.w, self.h = width, height
        self.ripples=[]; self.particles=[]; self.trails=[]
        self.last_hit={}; self.t0=time.time()
    def trigger(self, x, y, zone='field'):
        now=time.time(); key=zone
        if now-self.last_hit.get(key,0)<0.10:return
        self.last_hit[key]=now
        color=(80+random.randrange(120),160+random.randrange(90),220+random.randrange(35))
        self.ripples.append([float(x),float(y),now,random.randint(18,36),color,zone])
        for _ in range(14 if zone=='floor' else 8):
            a=random.random()*math.tau; s=random.uniform(40,170)
            self.particles.append([float(x),float(y),math.cos(a)*s,math.sin(a)*s,now,color,zone])
        self.trails.append([float(x),float(y),now,color,zone])
    def render(self, frame):
        now=time.time(); out=frame.copy(); overlay=np.zeros_like(out)
        # Ambient breathing halo around the centre.
        pulse=(math.sin((now-self.t0)*1.4)+1)*0.5
        radius=int(min(self.w,self.h)*(0.055+0.02*pulse))
        cv2.circle(overlay,(self.w//2,self.h//2),radius,(35,55,90),2)
        self.ripples=[r for r in self.ripples if now-r[2]<1.8]
        for x,y,t,base,c,z in self.ripples:
            age=now-t; rad=int(base+age*(300 if z=='field' else 220)); thick=max(1,int(5-age*2)); cv2.circle(overlay,(int(x),int(y)),rad,c,thick)
        self.particles=[p for p in self.particles if now-p[4]<1.5]
        for x,y,vx,vy,t,c,z in self.particles:
            age=now-t; px=int(x+vx*age); py=int(y+vy*age+90*age*age); size=max(1,int(5-age*3)); cv2.circle(overlay,(px,py),size,c,-1)
        self.trails=[p for p in self.trails if now-p[2]<1.1]
        for i,p in enumerate(self.trails):
            x,y,t,c,z=p; alpha=max(0.0,1-(now-t)/1.1); cv2.circle(overlay,(int(x),int(y)),max(3,int(14*alpha)),c,-1)
            if i: cv2.line(overlay,(int(self.trails[i-1][0]),int(self.trails[i-1][1])),(int(x),int(y)),c,2)
        return cv2.addWeighted(out,1.0,overlay,0.65,0)
