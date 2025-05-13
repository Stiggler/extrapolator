from .import_callbacks import register_import_callbacks
from .video_callbacks import register_video_callbacks
from .nonvideo_callbacks import register_nonvideo_callbacks

def register_callbacks(app):
    register_import_callbacks(app)
    register_video_callbacks(app)
    register_nonvideo_callbacks(app)
