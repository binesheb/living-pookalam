"""Assisted camera/projector calibration using projected fiducials and Pookalam detection."""
import cv2,numpy as np,time

def pattern(size):
 w,h=size;im=np.full((h,w,3),255,np.uint8); pts=[(0,0),(w-1,0),(w-1,h-1),(0,h-1)]
 for i,p in enumerate(pts):cv2.circle(im,p,24,(0,0,0),-1);cv2.putText(im,str(i+1),(p[0]+35 if p[0]<w/2 else p[0]-55,p[1]+45 if p[1]<h/2 else p[1]-25),0,.8,(0,80,255),2)
 return im,pts

def detect_points(frame):
 g=cv2.cvtColor(frame,cv2.COLOR_BGR2GRAY); _,b=cv2.threshold(g,55,255,cv2.THRESH_BINARY_INV);n,lab,st,cent=cv2.connectedComponentsWithStats(b)
 out=[]
 for i in range(1,n):
  x,y,w,h,a=st[i];
  if 150<a<8000 and .55<w/max(h,1)<1.8:out.append((a,tuple(cent[i])))
 return [p for _,p in sorted(out,reverse=True)[:4]]
def order(pts):
 p=np.float32(pts);s=p.sum(1);d=np.diff(p,axis=1).ravel();return np.float32([p[np.argmin(s)],p[np.argmin(d)],p[np.argmax(s)],p[np.argmax(d)]])
def run(cap,project,project_size,frames=45,stop=None):
 im,expected=pattern(project_size);project(im);time.sleep(.6);samples=[]
 for _ in range(frames):
  if stop is not None and stop.is_set():return None
  ok,f=cap.read()
  if not ok:continue
  pts=detect_points(f)
  if len(pts)==4:samples.append(order(pts))
 if len(samples)<max(5,frames//6):return None
 observed=np.median(np.stack(samples),axis=0).astype(np.float32)
 return {'projector_field_camera':observed.tolist(),'quality':float(len(samples)/frames),'frames':len(samples)}
