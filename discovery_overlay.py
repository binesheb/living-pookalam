"""Visually pleasing projected discovery sequence for physical Pookalam analysis."""
import cv2, numpy as np, math, time

def frame(size, vision, step, total, source=None):
 w,h=size; img=np.zeros((h,w,3),np.uint8); cx,cy=vision['center']; r=vision['radius']; sx=w/640.; sy=h/640.; C=(int(cx*sx),int(cy*sy)); R=int(r*min(sx,sy)); t=time.perf_counter();
 # scan lines + discovery circle
 for rr in range(max(20,int(R*(step+1)/max(total,1))),R+1,max(18,int(R*.16))): cv2.circle(img,C,rr,(35,90,180),1,cv2.LINE_AA)
 ang=(t*2.5+step*.7)%(math.tau); p=(int(C[0]+math.cos(ang)*R),int(C[1]+math.sin(ang)*R)); cv2.line(img,C,p,(80,220,255),2,cv2.LINE_AA); cv2.circle(img,p,8,(80,220,255),-1,cv2.LINE_AA)
 cv2.circle(img,C,R,(0,210,255),2,cv2.LINE_AA); cv2.circle(img,C,max(8,int(R*.08)),(80,255,180),2,cv2.LINE_AA)
 labels=['SCANNING FLOOR','IDENTIFYING CIRCLE','READING COLOURS','MAPPING PATTERNS','ANALYSING PETALS','POOKALAM READY']; text=labels[min(step,len(labels)-1)]
 cv2.putText(img,'LIVING POOKALAM', (28,45),cv2.FONT_HERSHEY_SIMPLEX,.9,(220,240,255),2,cv2.LINE_AA); cv2.putText(img,text,(28,78),cv2.FONT_HERSHEY_SIMPLEX,.62,(80,220,255),2,cv2.LINE_AA)
 if step>=2 and source is not None:
  small=cv2.resize(source,(160,160)); x=w-190; y=25; img[y:y+160,x:x+160]=cv2.addWeighted(img[y:y+160,x:x+160],.25,small,.75,0); cv2.rectangle(img,(x,y),(x+160,y+160),(0,210,255),1)
 if step>=3:
  for a in np.linspace(0,math.tau,24,endpoint=False):
   q=(int(C[0]+math.cos(a)*R*.78),int(C[1]+math.sin(a)*R*.78)); cv2.line(img,C,q,(45,120,220),1,cv2.LINE_AA)
 cv2.putText(img,f'{int((step+1)*100/total)}%',(28,h-28),cv2.FONT_HERSHEY_SIMPLEX,.7,(220,240,255),2,cv2.LINE_AA)
 return img

def run(window, size, vision, artwork, seconds=6, stop=None):
 start=time.perf_counter(); total=6
 while time.perf_counter()-start<seconds:
  if stop is not None and stop.is_set(): return False
  elapsed=time.perf_counter()-start; step=min(total-1,int(elapsed/(seconds/total)))
  cv2.imshow(window,frame(size,vision,step,total,artwork)); cv2.waitKey(1); time.sleep(1/45)
 return True
