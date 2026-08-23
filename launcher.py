"""Runtime launcher: optional artwork, debug control, and interaction effects."""
import threading, time
import cv2
import numpy as np
import main as app
from effects import EffectsEngine

app.VERSION = '2.7.0'
_original_build_projection = app.build_projection

def build_projection_optional(img, cfg):
    if img is None:
        _, _, pw, ph = app.projector_geometry()
        return np.zeros((ph, pw, 3), dtype=np.uint8)
    return _original_build_projection(img, cfg)
app.build_projection = build_projection_optional

_original_toggle_debug = app.App.toggle_debug
def toggle_debug_reliable(self):
    _original_toggle_debug(self)
    if not self.debug.is_set(): app.debug_close(); cv2.waitKey(1)
app.App.toggle_debug = toggle_debug_reliable

def interaction_with_effects(img, stop_event, debug_event):
    if not app.CONFIG.exists(): raise RuntimeError('Calibrate first')
    cfg=app.json.loads(app.CONFIG.read_text()); _,_,pw,ph=app.projector_geometry(); stable=app.build_projection(img,cfg); pname=app.projector_window('Living Pookalam - Projection',stable)
    cap=cv2.VideoCapture(cfg['camera_index']); field=np.float32(cfg['projector_field_camera']); floor=np.float32(cfg['floor_boundary_camera'])
    Hfield=cv2.getPerspectiveTransform(field,np.float32([[0,0],[pw,0],[pw,ph],[0,ph]])); Hfloor=cv2.getPerspectiveTransform(floor,np.float32([[0,0],[640,0],[640,640],[0,640]]))
    scene_base,floor_base=app.learn_baseline(cap,field,Hfloor,stop_event,debug=debug_event.is_set())
    if scene_base is None: cap.release(); return
    fx=EffectsEngine(pw,ph); kernel=np.ones((5,5),np.uint8); frame_count=0; tick=time.time(); fps=0
    while not stop_event.is_set():
        ok,frame=cap.read()
        if not ok: continue
        debug=debug_event.is_set(); frame_count+=1
        if time.time()-tick>=1: fps=frame_count/(time.time()-tick); frame_count=0; tick=time.time()
        fdiff,motion=app.difference(frame,scene_base); fieldmask=np.zeros(motion.shape,np.uint8); cv2.fillPoly(fieldmask,[field.astype(np.int32)],255); motion=cv2.morphologyEx(cv2.bitwise_and(motion,fieldmask),cv2.MORPH_OPEN,kernel); motion=cv2.dilate(motion,None,iterations=2)
        cnt,_=cv2.findContours(motion,cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE); hits=[]
        for q in cnt:
            if cv2.contourArea(q)<250: continue
            m=cv2.moments(q)
            if not m['m00']: continue
            p=cv2.perspectiveTransform(np.float32([[[m['m10']/m['m00'],m['m01']/m['m00']]]]),Hfield)[0,0]; hits.append(p); fx.trigger(float(p[0]),float(p[1]),'field')
        rectified=cv2.warpPerspective(frame,Hfloor,(640,640)); rdiff,rmask=app.difference(rectified,floor_base); rmask=cv2.morphologyEx(rmask,cv2.MORPH_OPEN,kernel); rmask=cv2.dilate(rmask,None,iterations=2); contours,_=cv2.findContours(rmask,cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE); interactions=[]; floor_debug=rectified.copy()
        for q in contours:
            if cv2.contourArea(q)<500: continue
            x,y,w,h=cv2.boundingRect(q); u,v=(x+w/2)/640,(y+h/2)/640; interactions.append((u,v)); cv2.rectangle(floor_debug,(x,y),(x+w,y+h),(0,255,0),2); p=cv2.perspectiveTransform(np.float32([[[x+w/2,y+h/2]]]),np.linalg.inv(Hfloor))[0,0]; pp=cv2.perspectiveTransform(np.float32([[p]]),Hfield)[0,0]; fx.trigger(float(pp[0]),float(pp[1]),'floor')
        effect=fx.render(stable); cv2.imshow(pname,effect)
        if debug:
            view=frame.copy(); cv2.polylines(view,[field.astype(np.int32)],True,(0,255,255),2); cv2.polylines(view,[floor.astype(np.int32)],True,(0,255,0),2); cv2.putText(view,f'DEBUG | FPS {fps:.1f} | FIELD {len(hits)} | FLOOR {len(interactions)}',(15,30),0,.65,(0,0,255),2)
            cv2.imshow('Debug - Camera',view); cv2.imshow('Debug - Scene Baseline',scene_base); cv2.imshow('Debug - Field Difference',fdiff); cv2.imshow('Debug - Field Mask',motion); cv2.imshow('Debug - Floor Live',floor_debug); cv2.imshow('Debug - Floor Baseline',floor_base); cv2.imshow('Debug - Floor Difference',rdiff); cv2.imshow('Debug - Floor Mask',rmask)
        else: app.debug_close()
        cv2.waitKey(1)
    cap.release(); app.debug_close(); cv2.destroyAllWindows()

app.interaction_loop=interaction_with_effects

def project_optional(self):
    if self.worker and self.worker.is_alive(): return
    self.stop.clear(); img=None if self.image is None else cv2.cvtColor(np.array(self.image),cv2.COLOR_RGB2BGR)
    self.set_state('Starting interactive effects — learning stable scene for 10 seconds',True)
    def work():
        try: app.interaction_loop(img,self.stop,self.debug)
        except Exception as e: self.after(0,lambda:app.messagebox.showerror('Interactive Pookalam',str(e)))
        finally: self.after(0,lambda:self.set_state('Experience stopped'))
    self.worker=threading.Thread(target=work,daemon=True); self.worker.start()
app.App.project=project_optional

if __name__=='__main__': app.main()
