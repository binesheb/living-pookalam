"""Artwork-aware effects rendered in normalized floor coordinates."""
import math, random, time
import cv2, numpy as np

class EffectsEngine:
 def __init__(self,w,h,artwork=None,floor_to_projector=None):
  self.w,self.h=w,h; self.H=floor_to_projector; self.ripples=[]; self.spark=[]; self.fireflies=[]; self.last=0; self.t0=time.time(); self.palette=[(120,200,255),(255,180,80),(180,255,160)]
  self.cx=self.cy=320; self.radius=300; self.edge=np.zeros((640,640),np.uint8); self.detail=np.zeros((640,640),np.uint8)
  if artwork is not None:
   a=cv2.resize(artwork,(640,640)); z=a.reshape(-1,3).astype(np.float32); _,lab,cent=cv2.kmeans(z,6,None,(cv2.TERM_CRITERIA_EPS+cv2.TERM_CRITERIA_MAX_ITER,20,1),3,cv2.KMEANS_PP_CENTERS); self.palette=[tuple(map(int,c)) for c in cent]
   g=cv2.cvtColor(a,cv2.COLOR_BGR2GRAY); self.edge=cv2.Canny(g,55,150); self.detail=cv2.dilate(self.edge,np.ones((3,3),np.uint8),iterations=1)
   _,self.bright=cv2.threshold(g,190,255,cv2.THRESH_BINARY)
   circles=cv2.HoughCircles(cv2.GaussianBlur(g,(9,9),2),cv2.HOUGH_GRADIENT,1.2,120,param1=120,param2=32,minRadius=120,maxRadius=315)
   if circles is not None:
    x,y,r=circles[0][0]; self.cx,self.cy,self.radius=int(x),int(y),int(r)
   # Fallback circle from non-dark artwork extent when Hough detection is weak.
   else:
    mask=cv2.threshold(g,18,255,cv2.THRESH_BINARY)[1]; cnt,_=cv2.findContours(mask,cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE)
    if cnt:
     (x,y),r=cv2.minEnclosingCircle(max(cnt,key=cv2.contourArea)); self.cx,self.cy,self.radius=int(x),int(y),int(r)
  else:self.bright=np.zeros((640,640),np.uint8)
  self.design_mask=np.zeros((640,640),np.uint8); cv2.circle(self.design_mask,(self.cx,self.cy),self.radius,255,-1)
  self.rings=[]
  for rr in np.linspace(self.radius*.18,self.radius*.92,5): self.rings.append(float(rr))
  for _ in range(36): self.fireflies.append(self._spawn_firefly())
 def _spawn_firefly(self):
  a=random.random()*math.tau; r=self.radius*math.sqrt(random.random()); x=np.clip(self.cx+math.cos(a)*r,0,639); y=np.clip(self.cy+math.sin(a)*r,0,639); return [x,y,random.random()*6.28,random.random()*2+0.4,random.choice(self.palette)]
 def trigger(self,x,y,zone='floor'):
  now=time.time()
  if now-self.last<.12:return
  self.last=now; x=float(np.clip(x,0,639)); y=float(np.clip(y,0,639)); c=random.choice(self.palette)
  if self.design_mask[int(y),int(x)]==0:return
  self.ripples.append([x,y,now,c,zone])
  for _ in range(18):
   a=random.random()*math.tau; s=random.uniform(20,100); self.spark.append([x,y,math.cos(a)*s,math.sin(a)*s,now,c])
 def _floor_overlay(self):
  now=time.time(); o=np.zeros((640,640,3),np.uint8); glow=np.zeros_like(o)
  self.ripples=[r for r in self.ripples if now-r[2]<1.8]
  for x,y,t,c,z in self.ripples:
   age=now-t; rad=int(12+age*170); cv2.circle(glow,(int(x),int(y)),rad,c,max(1,int(10-age*5)))
  glow=cv2.GaussianBlur(glow,(0,0),10); o=cv2.addWeighted(o,1,glow,.7,0)
  self.spark=[p for p in self.spark if now-p[4]<1.5]
  for x,y,vx,vy,t,c in self.spark:
   age=now-t; px=int(x+vx*age); py=int(y+vy*age+28*age*age)
   if 0<=px<640 and 0<=py<640 and self.design_mask[py,px]: cv2.circle(o,(px,py),max(1,int(4-age*2)),c,-1)
  # Subtle shimmer follows detected artwork edges and radial pattern bands.
  phase=(math.sin((now-self.t0)*2.0)+1)*.5
  ys,xs=np.where(self.detail>0)
  if len(xs):
   step=max(1,len(xs)//90)
   for i in range(int(phase*12)%step,len(xs),step):
    x,y=int(xs[i]),int(ys[i]); cv2.circle(o,(x,y),1+int(phase),random.choice(self.palette),-1)
  for rr in self.rings:
   cv2.ellipse(o,(self.cx,self.cy),(int(rr),int(rr)),0,0,360,random.choice(self.palette),1)
  # Fireflies remain inside the detected circular design and prefer detail/bright areas.
  for i,f in enumerate(self.fireflies):
   x,y,a,spd,c=f; nx=x+math.cos(a+now*.7)*spd; ny=y+math.sin(a+now*.9)*spd
   if (nx-self.cx)**2+(ny-self.cy)**2>self.radius**2: self.fireflies[i]=self._spawn_firefly(); continue
   self.fireflies[i][0:2]=[nx,ny]
   if self.bright[int(ny),int(nx)] or self.detail[int(ny),int(nx)] or random.random()<.025:
    halo=np.zeros_like(o); cv2.circle(halo,(int(nx),int(ny)),6,c,-1); halo=cv2.GaussianBlur(halo,(0,0),4); o=cv2.addWeighted(o,1,halo,.35,0); cv2.circle(o,(int(nx),int(ny)),2,c,-1)
  return o
 def render_floor(self,base):
  o=self._floor_overlay(); o=cv2.bitwise_and(o,o,mask=self.design_mask); return cv2.addWeighted(base,1,o,.72,0)
 def render(self,frame): return frame
