# layout.py
from dash import dcc, html
from components.import_section import import_tab
from components.video_section import video_tab
from components.nonvideo_section import nonvideo_tab

def create_layout():
    return html.Div([
        dcc.Tabs([
            import_tab(),
            video_tab(),
            nonvideo_tab()
        ])
    ])
