"""Runtime compatibility launcher for optional artwork and reliable debug toggling."""
import threading
import cv2
import numpy as np
import main as app

app.VERSION = '2.6.1'
_original_build_projection = app.build_projection


def build_projection_optional(img, cfg):
    if img is None:
        _, _, pw, ph = app.projector_geometry()
        return np.zeros((ph, pw, 3), dtype=np.uint8)
    return _original_build_projection(img, cfg)


app.build_projection = build_projection_optional

# Close every debug window immediately when Debug is switched OFF.
_original_toggle_debug = app.App.toggle_debug

def toggle_debug_reliable(self):
    _original_toggle_debug(self)
    if not self.debug.is_set():
        app.debug_close()
        # Force HighGUI to process pending window-destroy messages.
        cv2.waitKey(1)


app.App.toggle_debug = toggle_debug_reliable


def project_optional(self):
    if self.worker and self.worker.is_alive():
        return
    self.stop.clear()
    img = None if self.image is None else cv2.cvtColor(np.array(self.image), cv2.COLOR_RGB2BGR)
    if img is None:
        self.set_state('No reference image selected — starting interactive mode with neutral projection', True)
    else:
        self.set_state('Learning stable scene for 10 seconds — keep clear', True)

    def work():
        try:
            app.interaction_loop(img, self.stop, self.debug)
        except Exception as e:
            self.after(0, lambda: app.messagebox.showerror('Interactive Pookalam', str(e)))
        finally:
            self.after(0, lambda: self.set_state('Experience stopped'))

    self.worker = threading.Thread(target=work, daemon=True)
    self.worker.start()


app.App.project = project_optional

if __name__ == '__main__':
    app.main()
