"""Detect a physical Pookalam from a rectified calibrated floor image."""
import cv2, numpy as np

def detect_pookalam(frame):
    src=cv2.resize(frame,(640,640)); hsv=cv2.cvtColor(src,cv2.COLOR_BGR2HSV); gray=cv2.cvtColor(src,cv2.COLOR_BGR2GRAY)
    # Flowers are normally more colourful/textured than surrounding floor.
    sat=hsv[:,:,1]; val=hsv[:,:,2]; texture=cv2.Laplacian(gray,cv2.CV_8U,ksize=3)
    mask=cv2.inRange(sat,35,255); mask=cv2.bitwise_or(mask,cv2.threshold(texture,20,255,cv2.THRESH_BINARY)[1])
    mask=cv2.morphologyEx(mask,cv2.MORPH_CLOSE,np.ones((15,15),np.uint8)); mask=cv2.morphologyEx(mask,cv2.MORPH_OPEN,np.ones((7,7),np.uint8))
    circles=cv2.HoughCircles(cv2.GaussianBlur(gray,(9,9),2),cv2.HOUGH_GRADIENT,1.2,100,param1=100,param2=28,minRadius=90,maxRadius=315)
    cx=cy=320; radius=300; confidence=0.0
    if circles is not None:
        x,y,r=circles[0][0]; cx,cy,radius=int(x),int(y),int(r); confidence=.8
    else:
        cnt,_=cv2.findContours(mask,cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE)
        if cnt:
            c=max(cnt,key=cv2.contourArea); (x,y),r=cv2.minEnclosingCircle(c); cx,cy,radius=int(x),int(y),int(r); confidence=min(.7,cv2.contourArea(c)/(640*640))
    radius=max(60,min(radius,318)); design_mask=np.zeros((640,640),np.uint8); cv2.circle(design_mask,(cx,cy),radius,255,-1)
    artwork=cv2.bitwise_and(src,src,mask=design_mask)
    return {'artwork':artwork,'mask':design_mask,'center':(cx,cy),'radius':radius,'confidence':float(confidence)}
