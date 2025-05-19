# app.py – Haupt-Einstiegspunkt für den IRIS-Extrapolator
from dash import Dash
from layout import create_layout
from callbacks import register_callbacks

app = Dash(__name__, title="IRIS-Extrapolator", suppress_callback_exceptions=True)
server = app.server  # wichtig für Deployment z. B. mit gunicorn
app.layout = create_layout()
register_callbacks(app)

if __name__ == '__main__':
    app.run(debug=True, host="0.0.0.0", port=8050)

