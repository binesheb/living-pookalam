"""Living Pookalam application entry point."""
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from app import __version__
from app.calibration.manual_corners import calibrate_manual_corners
from app.calibration.floor_space import build_floor_calibration
from app.core.config import load_profile, load_runtime_config, save_runtime_config
from app.core.runtime import RuntimeState
from app.perception.camera import discover_cameras, test_camera
app=FastAPI(title="Living Pookalam",version=__version__); state=RuntimeState(); manual_calibration=None; floor_calibration=None
class CameraSelection(BaseModel): index:int=Field(ge=0,le=99)
class Point(BaseModel): x:float; y:float
class ManualCornerRequest(BaseModel):
    points:list[Point]=Field(min_length=4,max_length=4); physical_width_mm:float=Field(gt=0); physical_height_mm:float=Field(gt=0)
class ProjectorCalibrationRequest(BaseModel):
    camera_floor_points:list[Point]=Field(min_length=4,max_length=4)
    projector_reference_camera_points:list[Point]=Field(min_length=4,max_length=4)
    physical_width_mm:float=Field(gt=0); physical_height_mm:float=Field(gt=0)
@app.on_event("startup")
def startup(): state.start()
@app.get("/health")
def health():
    p=load_profile(); return {"status":"ok","running":state.running,"version":__version__,"profile":p.get("id","unknown")}
@app.get("/api/v1/state")
def runtime_state(): return {"running":state.running,"active_scene":state.active_scene,"last_event":state.last_event,"started_at":state.started_at.isoformat() if state.started_at else None}
@app.get("/api/v1/cameras")
def cameras(max_index:int=10): return {"selected_index":load_runtime_config()["camera_index"],"cameras":discover_cameras(min(max(max_index,1),50))}
@app.post("/api/v1/cameras/test")
def camera_test(selection:CameraSelection): return test_camera(selection.index)
@app.post("/api/v1/cameras/select")
def select_camera(selection:CameraSelection):
    r=test_camera(selection.index)
    if not r.get("ok"): raise HTTPException(400,r.get("error","Camera test failed"))
    c=load_runtime_config(); c["camera_index"]=selection.index; save_runtime_config(c); return {"ok":True,"selected_index":selection.index,"camera":r}
@app.get("/api/v1/calibration/manual")
def get_manual_calibration(): return {"calibration":manual_calibration.as_dict() if manual_calibration else None,"corner_order":["top_left","top_right","bottom_right","bottom_left"]}
@app.post("/api/v1/calibration/manual")
def save_manual_calibration(request:ManualCornerRequest):
    global manual_calibration
    try: manual_calibration=calibrate_manual_corners([[p.x,p.y] for p in request.points],request.physical_width_mm,request.physical_height_mm)
    except ValueError as e: raise HTTPException(400,str(e)) from e
    return {"ok":True,"calibration":manual_calibration.as_dict()}
@app.post("/api/v1/calibration/projector")
def save_projector_calibration(request:ProjectorCalibrationRequest):
    global floor_calibration
    try:
        floor_calibration=build_floor_calibration([[p.x,p.y] for p in request.camera_floor_points],[[p.x,p.y] for p in request.projector_reference_camera_points],request.physical_width_mm,request.physical_height_mm)
    except ValueError as e: raise HTTPException(400,str(e)) from e
    return {"ok":True,"floor_to_projector":floor_calibration.floor_to_projector.tolist(),"projector_to_floor":floor_calibration.projector_to_floor.tolist(),"max_error_mm":floor_calibration.max_error_mm}
def run():
    import uvicorn; uvicorn.run("app.main:app",host="0.0.0.0",port=8080,reload=False)
if __name__=="__main__": run()
