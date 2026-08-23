import json,subprocess,threading,time
from pathlib import Path
import tkinter as tk
from tkinter import filedialog,messagebox
from PIL import Image,ImageTk
import cv2,numpy as np
from auto_calibration import run as auto_run
VERSION='3.3.0';ROOT=Path(__file__).resolve().parent;CONFIG=ROOT/'calibration.json'
# Load the existing application implementation, preserving all GUI/runtime methods.
_exec=(ROOT/'main_legacy.py')
if _exec.exists():exec(_exec.read_text(),globals())
else:
 # fallback is intentionally explicit if a packaging migration is incomplete
 raise RuntimeError('main_legacy.py missing; update package requires legacy runtime')

def auto_calibrate(self):
 if self.worker and self.worker.is_alive():return
 cams=cameras()
 if not cams:messagebox.showerror('Auto Calibration','No camera found');return
 idx=cams[0];self.stop.clear();self.set_state('Auto calibration: projecting fiducial markers...',True)
 def work():
  cap=cv2.VideoCapture(idx)
  try:
   _,_,pw,ph=projector_geometry();win=projector_window('LP Auto Calibration',np.full((ph,pw,3),255,np.uint8))
   def project(im):cv2.imshow(win,cv2.resize(im,(pw,ph)));cv2.waitKey(1)
   result=auto_run(cap,project,(pw,ph),stop=self.stop)
   if result is None:raise RuntimeError('Could not reliably detect all four projected markers')
   old=json.loads(CONFIG.read_text()) if CONFIG.exists() else {'camera_index':idx}
   old.update(result);old['camera_index']=idx
   # Floor boundary defaults to the detected circular Pookalam bounding square only when absent; manual calibration remains available for precise setup.
   if 'floor_boundary_camera' not in old:old['floor_boundary_camera']=result['projector_field_camera']
   CONFIG.write_text(json.dumps(old,indent=2))
   self.after(0,lambda:self.set_state(f"Auto calibration complete — quality {result['quality']:.0%}"))
  except Exception as e:self.after(0,lambda:messagebox.showerror('Auto Calibration',str(e)))
  finally:cap.release();cv2.destroyWindow('LP Auto Calibration')
 self.worker=threading.Thread(target=work,daemon=True);self.worker.start()

# Patch the GUI class after loading the stable runtime.
_old_init=App.__init__
def _init(self,*a,**k):
 _old_init(self,*a,**k);self.side_btn('Auto Calibrate','Detect projector field automatically',self.auto_calibrate,BLUE,'white')
App.__init__=_init;App.auto_calibrate=auto_calibrate
if __name__=='__main__':App().mainloop()
