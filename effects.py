"""Artwork-aware effects rendered in normalized floor coordinates."""
import math, random, time
import cv2, numpy as np

class EffectsEngine:
 def __init__(self,w,h,artwork=None,floor_to_projector=None):
  self.w,self.h=w,h; self.H=floor_to_projector; self.ripples=[]; self.spark=[]; self.fireflies=[]; self.last=0; self.t0=time.time(); self.palette=[(120,200,255),(255,180,80),(180,255,160)]
  if artwork is not None:
   a=cv2.resize(artwork,(256,256)); z=a.reshape(-1,3).astype(np.float32); _,lab,cent=cv2.kmeans(z,6,None,(cv2.TERM_CRITERIA_EPS+cv2.TERM_CRITERIA_MAX_ITER,20,1),3,cv2.KMEANS_PP_CENTERS); self.palette=[tuple(map(int,c)) for c in cent]
   g=cv2.cvtColor(a,cv2.COLOR_BGR2GRAY); _,self.bright=cv2.threshold(g,190,255,cv2.THRESH_BINARY); self.bright=cv2.resize(self.bright,(640,640))
  else:self.bright=np.zeros((640,640),np.uint8)
  for _ in range(28): self.fireflies.append([random.randrange(640),random.randrange(640),random.random()*6.28,random.random()*2+0.4,random.choice(self.palette)])
 def trigger(self,x,y,zone='floor'):
  now=time.time()
  if now-self.last<.12:return
  self.last=now
  # input x/y are normalized floor pixels; floor-only effects stay on the warped design.
  x=np.clip(x,0,639); y=np.clip(y,0,639); c=random.choice(self.palette)
  self.ripples.append([x,y,now,c,zone])
  for _ in range(16):
   a=random.random()*math.tau; s=random.uniform(25,110); self.spark.append([x,y,math.cos(a)*s,math.sin(a)*s,now,c])
 def _floor_overlay(self):
  now=time.time(); o=np.zeros((640,640,3),np.uint8)
  self.ripples=[r for r in self.ripples if now-r[2]<1.8]
  for x,y,t,c,z in self.ripples:
   age=now-t; rad=int(12+age*170); glow=np.zeros_like(o); cv2.circle(glow,(int(x),int(y)),rad,c,max(1,int(10-age*5))); glow=cv2.GaussianBlur(glow,(0,0),8); o=cv2.addWeighted(o,1,glow,.65,0)
  self.spark=[p for p in self.spark if now-p[4]<1.5]
  for x,y,vx,vy,t,c in self.spark:
   age=now-t; px=int(x+vx*age); py=int(y+vy*age+28*age*age); s=max(1,int(4-age*2)); cv2.circle(o,(px,py),s,c,-1)
  # Artwork-guided shimmer and wandering fireflies.
  phase=(np.sin((now-self.t0)*2.0)+1)*0.5
  for i,f in enumerate(self.fireflies):
   x,y,a,spd,c=f; x=(x+math.cos(a+now*.7)*spd)%640; y=(y+math.sin(a+now*.9)*spd)%640; self.fireflies[i][0:2]=[x,y]
   if self.bright[int(y),int(x)] or random.random()<.04: cv2.circle(o,(int(x),int(y)),max(1,int(2+phase*2)),c,-1)
  return o
 def render_floor(self,base):
  o=self._floor_overlay(); return cv2.addWeighted(base,1,o,.75,0)
 def render(self,frame):
  # Compatibility fallback for full-frame effects.
  return frame
