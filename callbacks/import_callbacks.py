from dash import html, Output, Input, State, exceptions
import pandas as pd
import sqlite3
import os
from helpers import parse_contents, update_database, get_aggregated_data, get_aggregated_data_opposite, PARQUET_CACHE

def register_import_callbacks(app):
    @app.callback(
        [
            Output("status", "children"),
            Output("aggregated-table-1", "data"),
            Output("aggregated-table-1", "columns"),
            Output("aggregated-table-2", "data"),
            Output("aggregated-table-2", "columns")
        ],
        Input("upload-data", "contents"),
        State("upload-data", "filename"),
        State("mode-radio", "value"),
        prevent_initial_call=True
    )
    def update_on_upload(list_of_contents, list_of_names, mode):
        if not list_of_contents:
            return "", [], [], [], []

        status_messages = []
        first_file = True

        # 1) Importiere und schreibe alle Dateien (replace/append)
        for contents, filename in zip(list_of_contents, list_of_names):
            if not filename.lower().startswith("report"):
                status_messages.append(f"Datei {filename} übersprungen (Name beginnt nicht mit 'report').")
                continue

            # parse_contents: schneller Einzellesezugriff per pandas.read_excel + to_timedelta :contentReference[oaicite:0]{index=0}
            try:
                df = parse_contents(contents, filename)
            except Exception as e:
                status_messages.append(f"❌ Fehler beim Lesen von {filename}: {e}")
                continue

            try:
                update_database(df, mode, first_file)  # Bulk-Insert mit PRAGMA+chunksize :contentReference[oaicite:1]{index=1}
                status_messages.append(f"✅ {filename} importiert ({len(df)} Zeilen).")
                first_file = False
            except Exception as e:
                status_messages.append(f"❌ Fehler beim Import von {filename}: {e}")
                continue

        db_path = "data.db"
        # 2) Alle weiteren SQL-Schritte mit EINER Connection im WAL-Mode
        with sqlite3.connect(db_path, timeout=30) as conn:
            # wir setzen read_uncommitted einmalig hier (falls nötig)
            # conn.execute("PRAGMA read_uncommitted = 1;")

            # 1) Video-Tabelle erstellen (C-optimiert)
            conn.execute("DROP TABLE IF EXISTS video;")
            conn.execute("""
                CREATE TABLE video AS
                SELECT *
                FROM data
                WHERE media = 'TV/OTT'
                    OR (media = 'Social Media' AND LOWER(post_type) = 'video');
            """)
            # direkt die Anzahl holen, ohne Pandas
            video_count = conn.execute("SELECT COUNT(*) FROM video;").fetchone()[0]
            status_messages.append(f"Tabelle 'video': {video_count} Zeilen.")

            # 2) Non-Video-Tabelle erstellen
            conn.execute("DROP TABLE IF EXISTS non_video;")
            conn.execute("""
                CREATE TABLE non_video AS
                SELECT *
                FROM data
                WHERE media IN ('Print','Online','Social Media')
                AND (post_type IS NULL OR post_type = '' OR LOWER(post_type) <> 'video');
            """)
            nonvideo_count = conn.execute("SELECT COUNT(*) FROM non_video;").fetchone()[0]
            status_messages.append(f"Tabelle 'non_video': {nonvideo_count} Zeilen.")

            # 3) Fehlende broadcasting_time zählen
            missing_bt = conn.execute("""
                SELECT COUNT(*)
                FROM data
                WHERE (media = 'TV/OTT'
                        OR (media = 'Social Media' AND LOWER(post_type) = 'video'))
                AND broadcasting_time IS NULL;
            """).fetchone()[0]
            if missing_bt:
                status_messages.append(f"⚠️ {missing_bt} Zeilen ohne broadcasting_time.")


        # 3) Aggregierte Daten für die beiden Tables
        try:
            df_agg1 = get_aggregated_data()
            data1 = df_agg1.to_dict("records")
            cols1 = [{"name": c, "id": c} for c in df_agg1.columns]
        except:
            data1, cols1 = [], []

        try:
            df_agg2 = get_aggregated_data_opposite()
            data2 = df_agg2.to_dict("records")
            cols2 = [{"name": c, "id": c} for c in df_agg2.columns]
        except:
            data2, cols2 = [], []

        # 4) Ergebnis-Status in der UI
        return (
            html.Div([html.Div(msg) for msg in status_messages]),
            data1, cols1,
            data2, cols2
        )




    @app.callback(
        Output("clear-db-status", "children"),
        Input("clear-db-button", "n_clicks"),
        prevent_initial_call=True
    )
    def clear_database(n_clicks):
        if not n_clicks:
            raise exceptions.PreventUpdate

        db_path = "data.db"
        # 1) Alle Tabellen droppen
        with sqlite3.connect(db_path, timeout=30) as conn:
            tables = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table';"
            ).fetchall()
            for (tbl,) in tables:
                conn.execute(f"DROP TABLE IF EXISTS `{tbl}`;")

           # 2) VACUUM, um das File zu schrumpfen
            conn.execute("VACUUM;")

        # 2) Parquet-Cache löschen
        try:
            os.remove(PARQUET_CACHE)
        except FileNotFoundError:
            pass

        return "✅ Alle Tabellen wurden geleert."

