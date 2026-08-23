"""Runtime launcher with physical Pookalam discovery experience."""
import threading,time,cv2,numpy as np
import main as app
from effects import EffectsEngine
from pookalam_vision import detect_pookalam
from discovery_overlay import run as run_discovery
app.VERSION='3.2.2'
_orig=app.build_projection
def build_projection_optional(img,cfg):
 if img is None:
  _,_,pw,ph=app.projector_geometry();return np.zeros((ph,pw,3),np.uint8)
 return _orig(img,cfg)
app.build_projection=build_projection_optional
_old=app.App.toggle_debug
def toggle_debug_reliable(self):
 _old(self)
 if not self.debug.is_set():app.debug_close();cv2.waitKey(1)
app.App.toggle_debug=toggle_debug_reliable

def interaction_with_effects(img,stop_event,debug_event,progress=None):
 if not app.CONFIG.exists():raise RuntimeError('Calibrate first')
 cfg=app.json.loads(app.CONFIG.read_text());_,_,pw,ph=app.projector_geometry();stable=app.build_projection(img,cfg);pname=app.projector_window('Living Pookalam - Projection',stable)
 cap=cv2.VideoCapture(cfg['camera_index']);field=np.float32(cfg['projector_field_camera']);floor=np.float32(cfg['floor_boundary_camera']);Hfield=cv2.getPerspectiveTransform(field,np.float32([[0,0],[pw,0],[pw,ph],[0,ph]]));Hfloor=cv2.getPerspectiveTransform(floor,np.float32([[0,0],[640,0],[640,640],[0,640]]));Hfloorproj=Hfield@np.linalg.inv(Hfloor)
 if progress:progress('Learning stable scene — 10 seconds remaining')
 scene_base,floor_base=app.learn_baseline(cap,field,Hfloor,stop_event,debug=debug_event.is_set())
 if scene_base is None:cap.release();return
 if img is not None:artwork=cv2.resize(img,(640,640));vision={'mask':np.full((640,640),255,np.uint8),'center':(320,320),'radius':315,'confidence':1.0};source='UPLOADED DESIGN'
 else:vision=detect_pookalam(floor_base);artwork=vision['artwork'];source=f"PHYSICAL POOKALAM {vision['confidence']:.0%}"
 def discovery_progress(step,total,remaining,label):
  if progress:progress(f'{label} — phase {step+1}/{total} — {remaining:.1f}s remaining')
 run_discovery(pname,(pw,ph),vision,artwork,seconds=6,stop=stop_event,on_progress=discovery_progress)
 if stop_event.is_set():cap.release();return
 if progress:progress('Pookalam ready — interactive experience running')
 fx=EffectsEngine(pw,ph,artwork,Hfloorproj);fx.design_mask=vision['mask'];fx.cx,fx.cy=vision['center'];fx.radius=vision['radius'];kernel=np.ones((5,5),np.uint8);tick=time.perf_counter();frames=0;fps=0
 while not stop_event.is_set():
  ok,frame=cap.read()
  if not ok:continue
  debug=debug_event.is_set();frames+=1;now=time.perf_counter()
  if now-tick>=1:fps=frames/(now-tick);frames=0;tick=now
  rectified=cv2.warpPerspective(frame,Hfloor,(640,640));rdiff,rmask=app.difference(rectified,floor_base);rmask=cv2.morphologyEx(rmask,cv2.MORPH_OPEN,kernel);contours,_=cv2.findContours(rmask,cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE);floor_debug=rectified.copy();hits=0
  for q in contours:
   if cv2.contourArea(q)<500:continue
   x,y,w,h=cv2.boundingRect(q);fx.trigger(x+w/2,y+h/2,'floor');hits+=1;cv2.rectangle(floor_debug,(x,y),(x+w,y+h),(0,255,0),2)
  fx_floor=fx.render_floor(artwork.copy());warped=cv2.warpPerspective(fx_floor,Hfloorproj,(pw,ph));mask=cv2.warpPerspective(np.full((640,640),255,np.uint8),Hfloorproj,(pw,ph));effect=stable.copy();effect[mask>0]=warped[mask>0];cv2.imshow(pname,effect)
  if debug:
   view=frame.copy();cv2.polylines(view,[field.astype(np.int32)],True,(0,255,255),2);cv2.polylines(view,[floor.astype(np.int32)],True,(0,255,0),2);cv2.putText(view,f'DEBUG | {source} | FPS {fps:.1f} | FLOOR {hits}',(15,30),0,.6,(0,0,255),2);cv2.imshow('Debug - Camera',view);cv2.imshow('Debug - Floor Live',floor_debug);cv2.imshow('Debug - Pookalam Source',artwork);m=np.zeros_like(artwork);cv2.circle(m,vision['center'],vision['radius'],(0,255,255),2);cv2.imshow('Debug - Pookalam Detection',m)
  else:app.debug_close()
  cv2.waitKey(1)
 cap.release();app.debug_close();cv2.destroyAllWindows()
app.interaction_loop=interaction_with_effects

def project_optional(self):
 if self.worker and self.worker.is_alive():return
 self.stop.clear();img=None if self.image is None else cv2.cvtColor(np.array(self.image),cv2.COLOR_RGB2BGR);self.set_state('Preparing experience...',True)
 def report(text):self.after(0,lambda:self.set_state(text,True))
 def work():
  try:app.interaction_loop(img,self.stop,self.debug,report)
  except Exception as e:self.after(0,lambda:app.messagebox.showerror('Interactive Pookalam',str(e)))
  finally:self.after(0,lambda:self.set_state('Experience stopped'))
 self.worker=threading.Thread(target=work,daemon=True);self.worker.start()
app.App.project=project_optional
if __name__=='__main__':app.main()
