"""Optimized artwork-aware effects for smooth real-time animation."""
import math, random, time
import cv2, numpy as np
class EffectsEngine:
 def __init__(self,w,h,artwork=None,floor_to_projector=None):
  self.w,self.h=w,h; self.H=floor_to_projector; self.ripples=[]; self.spark=[]; self.fireflies=[]; self.last=0.; self.t0=time.perf_counter(); self.palette=[(120,200,255),(255,180,80),(180,255,160)]; self.cx=self.cy=320; self.radius=300
  a=cv2.resize(artwork,(640,640)) if artwork is not None else np.zeros((640,640,3),np.uint8); z=a.reshape(-1,3).astype(np.float32); _,_,cent=cv2.kmeans(z,6,None,(cv2.TERM_CRITERIA_EPS+cv2.TERM_CRITERIA_MAX_ITER,12,2),1,cv2.KMEANS_PP_CENTERS); self.palette=[tuple(map(int,c)) for c in cent]
  g=cv2.cvtColor(a,cv2.COLOR_BGR2GRAY); edge=cv2.Canny(g,60,150); self.detail=cv2.dilate(edge,np.ones((3,3),np.uint8)); self.edge_pts=np.column_stack(np.where(self.detail>0))
  _,self.bright=cv2.threshold(g,190,255,cv2.THRESH_BINARY); circles=cv2.HoughCircles(cv2.GaussianBlur(g,(9,9),2),cv2.HOUGH_GRADIENT,1.2,120,param1=120,param2=32,minRadius=120,maxRadius=315)
  if circles is not None:self.cx,self.cy,self.radius=map(int,circles[0][0])
  else:
   cnt,_=cv2.findContours(cv2.threshold(g,18,255,cv2.THRESH_BINARY)[1],cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE)
   if cnt:(p,r)=cv2.minEnclosingCircle(max(cnt,key=cv2.contourArea)); self.cx,self.cy,self.radius=int(p[0]),int(p[1]),int(r)
  self.design_mask=np.zeros((640,640),np.uint8); cv2.circle(self.design_mask,(self.cx,self.cy),self.radius,255,-1); self.rings=np.linspace(self.radius*.2,self.radius*.9,4).astype(int); self.edge_count=len(self.edge_pts)
  for _ in range(24):self.fireflies.append(self._spawn())
 def _spawn(self):
  a=random.random()*math.tau; r=self.radius*math.sqrt(random.random()); return [self.cx+math.cos(a)*r,self.cy+math.sin(a)*r,random.random()*math.tau,random.uniform(.5,1.6),random.choice(self.palette)]
 def trigger(self,x,y,zone='floor'):
  now=time.perf_counter()
  if now-self.last<.08:return
  self.last=now; x=float(np.clip(x,0,639)); y=float(np.clip(y,0,639))
  if self.design_mask[int(y),int(x)]==0:return
  c=random.choice(self.palette); self.ripples.append((x,y,now,c));
  for _ in range(10):
   a=random.random()*math.tau; s=random.uniform(30,110); self.spark.append((x,y,math.cos(a)*s,math.sin(a)*s,now,c))
 def _floor_overlay(self):
  now=time.perf_counter(); o=np.zeros((640,640,3),np.uint8); self.ripples=[r for r in self.ripples if now-r[2]<1.4]
  for x,y,t,c in self.ripples:
   age=now-t; cv2.circle(o,(int(x),int(y)),int(10+age*220),c,max(1,int(7-age*4)))
  self.spark=[p for p in self.spark if now-p[4]<1.1]
  for x,y,vx,vy,t,c in self.spark:
   age=now-t; px=int(x+vx*age); py=int(y+vy*age+18*age*age)
   if 0<=px<640 and 0<=py<640 and self.design_mask[py,px]:cv2.circle(o,(px,py),max(1,int(4-age*3)),c,-1)
  if self.edge_count:
   phase=int((now-self.t0)*60)%max(1,self.edge_count); stride=max(1,self.edge_count//55)
   pts=self.edge_pts[phase::stride][:55]
   for y,x in pts:cv2.circle(o,(int(x),int(y)),1,random.choice(self.palette),-1)
  for rr in self.rings:cv2.circle(o,(self.cx,self.cy),int(rr),self.palette[int(rr)%len(self.palette)],1)
  for i,f in enumerate(self.fireflies):
   x,y,a,s,c=f; nx=x+math.cos(a+now*.8)*s; ny=y+math.sin(a+now*1.1)*s
   if (nx-self.cx)**2+(ny-self.cy)**2>self.radius*self.radius:self.fireflies[i]=self._spawn(); continue
   self.fireflies[i][0:2]=[nx,ny]
   if self.bright[int(ny),int(nx)] or random.random()<.015:cv2.circle(o,(int(nx),int(ny)),2,c,-1)
  return o
 def render_floor(self,base):
  o=self._floor_overlay(); cv2.bitwise_and(o,o,o,mask=self.design_mask); return cv2.addWeighted(base,1,o,.65,0)
 def render(self,frame):return frame
