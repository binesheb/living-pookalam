"""Detect a physical circular Pookalam and derive its camera-space boundary."""
import cv2, numpy as np

def _ellipse_boundary(cx,cy,axes,angle):
    # Four cardinal points on the observed ellipse. These are the camera-space
    # anchors used to map a square/circular design onto the real floor Pookalam.
    a,b=axes[0]/2.0,axes[1]/2.0; t=np.deg2rad(angle)
    pts=[]
    for dx,dy in ((0,-b),(a,0),(0,b),(-a,0)):
        x=cx+dx*np.cos(t)-dy*np.sin(t); y=cy+dx*np.sin(t)+dy*np.cos(t); pts.append([x,y])
    return np.float32(pts)

def detect_pookalam(frame):
    src=cv2.resize(frame,(640,640)); hsv=cv2.cvtColor(src,cv2.COLOR_BGR2HSV); gray=cv2.cvtColor(src,cv2.COLOR_BGR2GRAY)
    sat=hsv[:,:,1]; texture=cv2.Laplacian(gray,cv2.CV_8U,ksize=3)
    mask=cv2.inRange(sat,45,255)
    mask=cv2.bitwise_or(mask,cv2.threshold(texture,24,255,cv2.THRESH_BINARY)[1])
    mask=cv2.morphologyEx(mask,cv2.MORPH_CLOSE,np.ones((17,17),np.uint8))
    mask=cv2.morphologyEx(mask,cv2.MORPH_OPEN,np.ones((7,7),np.uint8))
    circles=cv2.HoughCircles(cv2.GaussianBlur(gray,(9,9),2),cv2.HOUGH_GRADIENT,1.2,100,param1=110,param2=30,minRadius=90,maxRadius=315)
    candidates=[]
    if circles is not None:
        for x,y,r in np.round(circles[0]).astype(int): candidates.append((.72,float(x),float(y),float(r),0.0))
    cnts,_=cv2.findContours(mask,cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE)
    for c in cnts:
        area=cv2.contourArea(c)
        if area<15000 or len(c)<20: continue
        peri=cv2.arcLength(c,True); circ=(4*np.pi*area/(peri*peri)) if peri else 0
        if circ<.25: continue
        (x,y),(ma,mi),ang=cv2.fitEllipse(c)
        r=max(ma,mi)/2.0
        if 70<=r<=330:
            score=min(.95,.45+.5*circ); candidates.append((score,x,y,r,ang,(ma,mi)))
    if not candidates:
        cx=cy=320.; r=300.; angle=0.; axes=(600.,600.); confidence=.0
    else:
        best=max(candidates,key=lambda z:z[0]); confidence,cx,cy,r,angle=best[:5]; axes=best[5] if len(best)>5 else (2*r,2*r)
    r=max(60,min(float(r),318.))
    if len(candidates) and len(best)>5:
        boundary=_ellipse_boundary(cx,cy,axes,angle)
        # Keep the anchors inside the 640x640 analysis canvas.
        boundary[:,0]=np.clip(boundary[:,0],4,635); boundary[:,1]=np.clip(boundary[:,1],4,635)
    else:
        boundary=np.float32([[cx-r,cy-r],[cx+r,cy-r],[cx+r,cy+r],[cx-r,cy+r]])
    design_mask=np.zeros((640,640),np.uint8)
    cv2.ellipse(design_mask,(int(cx),int(cy)),(max(1,int(axes[0]/2)),max(1,int(axes[1]/2))),float(angle),0,360,255,-1)
    artwork=cv2.bitwise_and(src,src,mask=design_mask)
    return {'artwork':artwork,'mask':design_mask,'center':(int(cx),int(cy)),'radius':int(r),'confidence':float(confidence),'boundary':boundary.tolist(),'ellipse':{'center':[float(cx),float(cy)],'axes':[float(axes[0]),float(axes[1])],'angle':float(angle)}}
