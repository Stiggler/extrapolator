# app.py – Haupt‐Einstiegspunkt für den IRIS-Extrapolator

from dash import Dash
import sqlite3

# 1) Dash-App erstellen mit suppressed exceptions für dynamische Tabs
app = Dash(
    __name__,
    title="IRIS-Extrapolator",
    suppress_callback_exceptions=True
)

# 2) Einmalig SQLite in WAL-Modus schalten (gilt für alle weiteren Verbindungen)
with sqlite3.connect("data.db", timeout=30) as conn:
    conn.execute("PRAGMA journal_mode = WAL;")
    conn.execute("PRAGMA synchronous = NORMAL;")
    conn.execute("PRAGMA locking_mode = EXCLUSIVE;")

# 3) Server‐Objekt für Deployment
server = app.server

# 4) Layout und Callback‐Registrierung
from layout import create_layout
from callbacks import register_callbacks

app.layout = create_layout()
register_callbacks(app)

# 5) App starten
if __name__ == '__main__':
    app.run(debug=True, host="0.0.0.0", port=8050)
