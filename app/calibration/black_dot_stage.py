"""Physical-floor camera/projector calibration stage."""
from __future__ import annotations
import time
import tkinter as tk
import cv2
import numpy as np
from PIL import Image, ImageTk
from app.calibration.staged import _detect_projector_rectangle
from app.calibration.floor_space import build_floor_calibration, transform

MARGIN = 0.12
DOT_RADIUS_FRACTION = 0.065
GEOMETRY_NAMES = ["FLOOR CORNER 1", "FLOOR CORNER 2", "FLOOR CORNER 3", "FLOOR CORNER 4"]
DEFAULT_FLOOR_WIDTH_MM = 2000.0
DEFAULT_FLOOR_HEIGHT_MM = 1500.0


def _white_field(self):
    self.clear(); self.canvas.configure(bg="white")
    self.canvas.create_rectangle(0, 0, self.w, self.h, fill="white", outline="white")
    self.canvas.create_text(self.w/2, self.h*.48, text="CALIBRATING PROJECTOR SPACE", fill="#111111", font=("Segoe UI",26,"bold"))
    self.canvas.create_text(self.w/2, self.h*.54, text="FULL WHITE FIELD • CAMERA OBSERVATION", fill="#333333", font=("Segoe UI",14,"bold"))


def _black_dot(self, index):
    self.clear(); self.canvas.configure(bg="white")
    self.canvas.create_rectangle(0,0,self.w,self.h,fill="white",outline="white")
    points=[(self.w*MARGIN,self.h*MARGIN),(self.w*(1-MARGIN),self.h*MARGIN),(self.w*(1-MARGIN),self.h*(1-MARGIN)),(self.w*MARGIN,self.h*(1-MARGIN))]
    x,y=points[index]; r=min(self.w,self.h)*DOT_RADIUS_FRACTION
    self.canvas.create_oval(x-r,y-r,x+r,y+r,fill="black",outline="black")
    self.canvas.create_oval(x-r*.16,y-r*.16,x+r*.16,y+r*.16,fill="white",outline="white")
    arm=r*1.45
    for a,b in [((x-arm,y),(x+r,y)),((x-r,y),(x+arm,y)),((x,y-arm),(x,y+r)),((x,y-r),(x,y+arm))]: self.canvas.create_line(*a,*b,fill="black",width=5)
    self.canvas.create_text(self.w/2,self.h*.48,text=f"FLOOR CORNER • TARGET {index+1}",fill="black",font=("Segoe UI",26,"bold"))
    self.canvas.create_text(self.w/2,self.h*.54,text="BLACK ON WHITE • ACQUIRE → PINPOINT → LOCK",fill="#222222",font=("Segoe UI",14,"bold"))


def _detect_black_dot(frame, expected_xy, radius):
    if frame is None or frame.size==0: return None
    h,w=frame.shape[:2]; cx,cy=int(expected_xy[0]),int(expected_xy[1]); r=max(30,int(radius))
    x0,x1=max(0,cx-r),min(w,cx+r); y0,y1=max(0,cy-r),min(h,cy+r); roi=frame[y0:y1,x0:x1]
    if roi.size==0: return None
    gray=cv2.cvtColor(roi,cv2.COLOR_BGR2GRAY)
    threshold=int(np.clip(np.percentile(gray,12)+12,35,120))
    mask=cv2.threshold(gray,threshold,255,cv2.THRESH_BINARY_INV)[1]
    mask=cv2.morphologyEx(mask,cv2.MORPH_OPEN,np.ones((5,5),np.uint8)); mask=cv2.morphologyEx(mask,cv2.MORPH_CLOSE,np.ones((9,9),np.uint8))
    contours,_=cv2.findContours(mask,cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE)
    if not contours:return None
    expected_area=np.pi*(r*.28)**2; candidates=[]
    for c in contours:
        area=cv2.contourArea(c)
        if area<max(40.,expected_area*.15):continue
        m=cv2.moments(c)
        if not m["m00"]:continue
        px=x0+m["m10"]/m["m00"]; py=y0+m["m01"]/m["m00"]; distance=float(np.hypot(px-cx,py-cy))
        if distance<=r*.85:candidates.append((distance,area,(px,py)))
    return min(candidates,key=lambda item:(item[0],-item[1]))[2] if candidates else None


def _projector_points(proj):
    return np.float32([(proj.w*MARGIN,proj.h*MARGIN),(proj.w*(1-MARGIN),proj.h*MARGIN),(proj.w*(1-MARGIN),proj.h*(1-MARGIN)),(proj.w*MARGIN,proj.h*(1-MARGIN))])


def _page_calibrate(self):
    self.page_title("Calibration","Physical floor is the master coordinate system. Camera and projector are calibrated to the same four floor corners.")
    top=tk.Frame(self.main,bg="#090711"); top.pack(fill="x")
    self.calib_status=tk.StringVar(value="READY"); self.calib_detail=tk.StringVar(value="Enter the physical usable floor rectangle, then run the camera → floor → projector calibration.")
    tk.Label(top,textvariable=self.calib_status,bg="#090711",fg="#ffd24a",font=("Segoe UI",14,"bold")).pack(anchor="w")
    tk.Label(top,textvariable=self.calib_detail,bg="#090711",fg="#9c95aa",font=("Segoe UI",9)).pack(anchor="w",pady=(2,8))
    dimensions=tk.Frame(self.main,bg="#090711"); dimensions.pack(fill="x",pady=(0,8))
    tk.Label(dimensions,text="FLOOR WIDTH (mm)",bg="#090711",fg="#9c95aa",font=("Segoe UI",9,"bold")).pack(side="left")
    self.floor_width_var=tk.StringVar(value=str(self.state.get("floor_width_mm",DEFAULT_FLOOR_WIDTH_MM)))
    tk.Entry(dimensions,textvariable=self.floor_width_var,width=10,bg="#171526",fg="#f4f1fa",insertbackground="#f4f1fa",relief="flat").pack(side="left",padx=(8,18))
    tk.Label(dimensions,text="FLOOR HEIGHT (mm)",bg="#090711",fg="#9c95aa",font=("Segoe UI",9,"bold")).pack(side="left")
    self.floor_height_var=tk.StringVar(value=str(self.state.get("floor_height_mm",DEFAULT_FLOOR_HEIGHT_MM)))
    tk.Entry(dimensions,textvariable=self.floor_height_var,width=10,bg="#171526",fg="#f4f1fa",insertbackground="#f4f1fa",relief="flat").pack(side="left",padx=(8,18))
    tk.Label(dimensions,text="The four projected black dots are the physical corners of this usable rectangle.",bg="#090711",fg="#9c95aa",font=("Segoe UI",9)).pack(side="left")
    actions=tk.Frame(self.main,bg="#090711"); actions.pack(fill="x",pady=(0,8))
    self.button(actions,"◎  CALIBRATE FLOOR",self.start_calibration,True).pack(side="left",padx=(0,5)); self.button(actions,"▦  PROJECTOR GRID",self.projector_grid).pack(side="left",padx=5); self.button(actions,"■  STOP CALIBRATION",self.stop_calibration).pack(side="left",padx=5); self.button(actions,"CLEAR MAP",self.clear_calibration).pack(side="left",padx=5)
    body=tk.Frame(self.main,bg="#090711"); body.pack(fill="both",expand=True)
    left=tk.Frame(body,bg="#171526",highlightthickness=1,highlightbackground="#2b2540"); left.pack(side="left",fill="both",expand=True,padx=(0,5)); self.calib_preview=tk.Label(left,bg="#020204"); self.calib_preview.pack(fill="both",expand=True,padx=8,pady=8)
    right=tk.Frame(body,bg="#171526",width=320,highlightthickness=1,highlightbackground="#2b2540"); right.pack(side="right",fill="y",padx=(5,0)); right.pack_propagate(False)
    tk.Label(right,text="PHYSICAL FLOOR CALIBRATION",bg="#171526",fg="#f4f1fa",font=("Segoe UI",11,"bold")).pack(anchor="w",padx=16,pady=14)
    self.calib_labels=[]
    for i,name in enumerate(GEOMETRY_NAMES):
        var=tk.StringVar(value=f"{i+1}   {name}   WAITING"); lab=tk.Label(right,textvariable=var,bg="#171526",fg="#9c95aa",font=("Consolas",9,"bold")); lab.pack(anchor="w",padx=16,pady=7); self.calib_labels.append((var,lab))
    self.calib_progress=tk.StringVar(value="FLOOR SPACE"); tk.Label(right,textvariable=self.calib_progress,bg="#171526",fg="#8b35ff",font=("Segoe UI",21,"bold")).pack(anchor="w",padx=16,pady=8)
    self.calib_error=tk.StringVar(value="Camera→floor: PENDING • Projector→floor: PENDING"); tk.Label(right,textvariable=self.calib_error,bg="#171526",fg="#9c95aa",font=("Consolas",9),wraplength=285,justify="left").pack(anchor="w",padx=16)


def _start_calibration(self):
    try:
        width=float(self.floor_width_var.get()); height=float(self.floor_height_var.get())
        if width<=0 or height<=0: raise ValueError
    except (ValueError, AttributeError):
        self.calib_status.set("INVALID FLOOR DIMENSIONS"); self.calib_detail.set("Enter positive physical width and height in millimetres."); return
    self.open_projector(); self.stop_show(); self.open_projector()
    self.calib_index=-2; self.calib_history=[]; self.calib_points=[]; self.calib_started=time.perf_counter(); self.calib_baseline=None if self.frame is None else self.frame.copy(); self.calib_stage="WHITE_FIELD"; self.calib_H=None
    self.floor_width_mm=width; self.floor_height_mm=height
    self.proj.white(); self.calib_status.set("CALIBRATING • WHITE PROJECTOR FIELD"); self.calib_detail.set("Projecting full white. Locating the illuminated projector rectangle before floor-corner acquisition…")
    for i,(var,lab) in enumerate(self.calib_labels):var.set(f"{i+1}   FLOOR CORNER   WAITING");lab.configure(fg="#9c95aa")
    self.calib_progress.set("PROJECTOR SPACE"); self.calib_error.set("Camera→floor: PENDING • Projector→floor: PENDING"); self.projection_quad=None


def _detect_target(self,frame,index):
    if getattr(self,"projection_quad",None) is None or getattr(self,"calib_H",None) is None:return None
    p=_projector_points(self.proj)[index]
    try:expected=cv2.perspectiveTransform(p.reshape(1,1,2),np.linalg.inv(self.calib_H)).reshape(2)
    except np.linalg.LinAlgError:return None
    return _detect_black_dot(frame,expected,max(50,int(min(frame.shape[:2])*.12)))


def _calibration_tick(self):
    if self.calib_index==-1 or self.frame is None:return
    if self.calib_index==-2:
        if time.perf_counter()-self.calib_started<1.2:self.calib_detail.set("WHITE FIELD • allowing camera/projector exposure to settle…");return
        quad=_detect_projector_rectangle(self.frame,self.calib_baseline)
        if quad is None:self.calib_detail.set("WHITE FIELD • searching for the illuminated projector rectangle…");return
        self.projection_quad=np.asarray(quad,dtype=np.float32)
        proj_pts=np.float32([(0,0),(self.proj.w,0),(self.proj.w,self.proj.h),(0,self.proj.h)]); H,_=cv2.findHomography(self.projection_quad,proj_pts,0)
        if H is None:self.calib_detail.set("WHITE FIELD • rectangle found, but initial geometry transform failed");return
        self.calib_H=H.astype(np.float32); self.calib_index=0; self.calib_history=[]; self.proj.target(0)
        self.calib_labels[0][0].set("1   FLOOR CORNER   ACTIVE"); self.calib_labels[0][1].configure(fg="#8b35ff")
        self.calib_status.set("CALIBRATING • PHYSICAL FLOOR CORNERS"); self.calib_detail.set(f"Floor rectangle: {self.floor_width_mm:.0f} × {self.floor_height_mm:.0f} mm. Acquire corner 1 on the real floor…"); self.calib_progress.set("FLOOR CORNER 1 / 4"); return
    p=self.detect_target(self.frame,self.calib_index)
    if p is None:self.calib_history=[];self.calib_detail.set(f"Floor corner {self.calib_index+1}: acquiring projected reference point…");return
    self.calib_history.append(p)
    if len(self.calib_history)>8:self.calib_history.pop(0)
    if len(self.calib_history)<8:self.calib_detail.set(f"Floor corner {self.calib_index+1}: pinpointing centre {len(self.calib_history)}/8…");return
    arr=np.asarray(self.calib_history,np.float32);mean=arr.mean(axis=0);jitter=float(np.max(np.linalg.norm(arr-mean,axis=1)));self.calib_detail.set(f"Floor corner {self.calib_index+1}: centre locked • jitter {jitter:.1f}px")
    if jitter>12:return
    idx=self.calib_index;self.calib_points.append(tuple(mean));self.calib_history=[];self.calib_labels[idx][0].set(f"{idx+1}   FLOOR CORNER   LOCKED");self.calib_labels[idx][1].configure(fg="#32e875")
    if idx<3:
        self.calib_index+=1;self.proj.target(self.calib_index);self.calib_labels[self.calib_index][0].set(f"{self.calib_index+1}   FLOOR CORNER   ACTIVE");self.calib_labels[self.calib_index][1].configure(fg="#8b35ff");self.calib_progress.set(f"FLOOR CORNER {self.calib_index+1} / 4");return
    camera_pts=np.asarray(self.calib_points,np.float32);projector_pts=_projector_points(self.proj)
    try:
        result=build_floor_calibration(camera_pts,projector_pts,self.floor_width_mm,self.floor_height_mm)
    except (ValueError,np.linalg.LinAlgError) as exc:
        self.calib_index=-1;self.calib_status.set("CALIBRATION REJECTED");self.calib_detail.set(f"Floor calibration failed: {exc}");self.calib_error.set("OLD MAP RETAINED");self.proj.black();return
    self.H=result.camera_to_projector
    self.floor_calibration=result
    self.state.update({
        "homography":self.H.tolist(),
        "camera_to_floor_homography":result.camera_to_floor.tolist(),
        "floor_to_camera_homography":result.floor_to_camera.tolist(),
        "projector_to_floor_homography":result.projector_to_floor.tolist(),
        "floor_to_projector_homography":result.floor_to_projector.tolist(),
        "projector_to_camera_homography":result.projector_to_camera.tolist(),
        "projector_width":self.proj.w,"projector_height":self.proj.h,
        "floor_width_mm":result.physical_width_mm,"floor_height_mm":result.physical_height_mm,
        "surface_rectangle_camera":self.projection_quad.tolist(),
        "geometry_from_white":True,"calibration_stage":"FLOOR_CALIBRATION_COMPLETE",
        "geometry_calibration_valid":True,"surface_calibration_valid":True,
        "floor_calibration_valid":True,"camera_floor_error_mm":result.camera_error_mm,
        "projector_floor_error_mm":result.projector_error_mm,
        "reprojection_error":result.max_error_mm,"reprojection_status":"FOUR_POINT_FIT",
    })
    from app.ui.field_ui import save_state
    save_state(self.state)
    self.calib_error.set(f"Camera→floor: {result.camera_error_mm:.2f} mm • Projector→floor: {result.projector_error_mm:.2f} mm")
    self.calib_progress.set("FLOOR CALIBRATION LOCKED")
    self.calib_status.set("PHYSICAL FLOOR CALIBRATION COMPLETE")
    self.calib_detail.set("Floor is now the canonical coordinate system. Camera detection is converted to floor mm, then floor geometry is projected through the calibrated projector map.")
    self.calib_index=-1; self.proj.black()


def _tick(self):
    ok,frame=self.cap.read()
    if ok:
        self.frame=frame
        from app.ui.field_ui import segment_pookalam
        _,self.contour,self.confidence=segment_pookalam(frame)
        if self.page=="home" and hasattr(self,"preview"):self.set_preview(frame)
        elif self.page=="detect" and hasattr(self,"detect_preview"):
            debug=frame.copy()
            if self.contour is not None:cv2.drawContours(debug,[self.contour],-1,(190,134,255),4)
            img=cv2.cvtColor(cv2.resize(debug,(900,506)),cv2.COLOR_BGR2RGB);self.detect_photo=ImageTk.PhotoImage(Image.fromarray(img));self.detect_preview.configure(image=self.detect_photo)
        elif self.page=="calibrate" and hasattr(self,"calib_preview"):
            debug=frame.copy()
            if self.calib_index>=0:
                p=self.detect_target(frame,self.calib_index)
                if p:cv2.circle(debug,(int(p[0]),int(p[1])),24,(0,255,0),3)
            elif self.calib_index==-2 and getattr(self,"projection_quad",None) is not None:cv2.polylines(debug,[np.int32(self.projection_quad)],True,(0,255,255),3)
            img=cv2.cvtColor(cv2.resize(debug,(900,506)),cv2.COLOR_BGR2RGB);self.calib_photo=ImageTk.PhotoImage(Image.fromarray(img));self.calib_preview.configure(image=self.calib_photo)
        if self.calib_index!=-1:self.calibration_tick()
    self.root.after(33,self.tick)


def _install_class(cls):
    cls.page_calibrate=_page_calibrate;cls.start_calibration=_start_calibration;cls.detect_target=_detect_target;cls.calibration_tick=_calibration_tick


def _install():
    from app.ui.field_ui import FieldConsole,ProjectionWindow
    ProjectionWindow.white=_white_field;ProjectionWindow.target=_black_dot;FieldConsole.tick=_tick;_install_class(FieldConsole)
    try:
        from app.ui.field_experience_console import FieldExperienceConsole
        _install_class(FieldExperienceConsole)
    except Exception:pass
    try:
        from app.ui.field_product import ProductFieldConsole
        _install_class(ProductFieldConsole)
    except Exception:pass

_install()
