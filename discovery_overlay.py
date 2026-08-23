"""Audience-facing Pookalam discovery overlay with live countdowns."""
import cv2,numpy as np,math,time
LABELS=['SCANNING FLOOR','IDENTIFYING CIRCLE','READING COLOURS','MAPPING PATTERNS','ANALYSING PETALS','POOKALAM READY']
def frame(size,vision,step,total,elapsed,duration,source=None):
 w,h=size;img=np.zeros((h,w,3),np.uint8);cx,cy=vision['center'];r=vision['radius'];sx=w/640.;sy=h/640.;C=(int(cx*sx),int(cy*sy));R=int(r*min(sx,sy));t=time.perf_counter();remain=max(0,duration-elapsed);phase=duration/total;phase_elapsed=elapsed-step*phase;phase_remain=max(0,phase-phase_elapsed)
 for rr in range(max(20,int(R*(step+1)/max(total,1))),R+1,max(18,int(R*.16))):cv2.circle(img,C,rr,(35,90,180),1,cv2.LINE_AA)
 ang=(t*2.5+step*.7)%math.tau;p=(int(C[0]+math.cos(ang)*R),int(C[1]+math.sin(ang)*R));cv2.line(img,C,p,(80,220,255),2,cv2.LINE_AA);cv2.circle(img,p,8,(80,220,255),-1,cv2.LINE_AA);cv2.circle(img,C,R,(0,210,255),2,cv2.LINE_AA);cv2.circle(img,C,max(8,int(R*.08)),(80,255,180),2,cv2.LINE_AA)
 text=LABELS[min(step,len(LABELS)-1)];cv2.putText(img,'LIVING POOKALAM',(28,45),cv2.FONT_HERSHEY_SIMPLEX,.9,(220,240,255),2,cv2.LINE_AA);cv2.putText(img,text,(28,78),cv2.FONT_HERSHEY_SIMPLEX,.62,(80,220,255),2,cv2.LINE_AA)
 if step>=2 and source is not None:
  small=cv2.resize(source,(160,160));x=w-190;y=25;img[y:y+160,x:x+160]=cv2.addWeighted(img[y:y+160,x:x+160],.25,small,.75,0);cv2.rectangle(img,(x,y),(x+160,y+160),(0,210,255),1)
 if step>=3:
  for a in np.linspace(0,math.tau,24,endpoint=False):q=(int(C[0]+math.cos(a)*R*.78),int(C[1]+math.sin(a)*R*.78));cv2.line(img,C,q,(45,120,220),1,cv2.LINE_AA)
 pct=min(100,int(elapsed*100/duration));barw=max(120,w-360);cv2.rectangle(img,(28,h-58),(28+barw,h-43),(35,55,80),-1);cv2.rectangle(img,(28,h-58),(28+int(barw*pct/100),h-43),(80,220,255),-1);cv2.putText(img,f'{pct}%  |  {remain:04.1f}s remaining',(28,h-20),cv2.FONT_HERSHEY_SIMPLEX,.62,(220,240,255),2,cv2.LINE_AA);cv2.putText(img,f'PHASE {step+1}/{total}  {phase_remain:03.1f}s',(w-285,h-20),cv2.FONT_HERSHEY_SIMPLEX,.55,(80,220,255),1,cv2.LINE_AA)
 return img
def run(window,size,vision,artwork,seconds=6,stop=None,on_progress=None):
 start=time.perf_counter();total=len(LABELS)
 while True:
  elapsed=time.perf_counter()-start
  if elapsed>=seconds:break
  if stop is not None and stop.is_set():return False
  step=min(total-1,int(elapsed/(seconds/total)));remain=max(0,seconds-elapsed)
  if on_progress:on_progress(step,total,remain,LABELS[step])
  cv2.imshow(window,frame(size,vision,step,total,elapsed,seconds,artwork));cv2.waitKey(1);time.sleep(1/45)
 return True
