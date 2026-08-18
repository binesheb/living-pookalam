"""Windows field console entry point for Live Pookalam."""
from app.ui.camera_bootstrap import install_nonblocking_camera

# Camera discovery must never block the first UI paint.
install_nonblocking_camera()

from app.ui.field_product import launch


if __name__ == "__main__":
    launch()
