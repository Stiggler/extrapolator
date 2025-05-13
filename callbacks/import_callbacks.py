from dash import html, Output, Input, State
import pandas as pd
import sqlite3
from helpers import parse_contents, update_database, get_aggregated_data, get_aggregated_data_opposite


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
        State("mode-radio", "value")
    )
    def update_on_upload(list_of_contents, list_of_names, mode):
        if list_of_contents is not None:
            status_messages = []
            first_file = True
            for contents, filename in zip(list_of_contents, list_of_names):
                if not filename.lower().startswith("report"):
                    status_messages.append(f"Datei {filename} übersprungen (Name beginnt nicht mit 'report').")
                    continue
                df = parse_contents(contents, filename)
                if df is None:
                    status_messages.append(f"Fehler beim Verarbeiten von {filename}.")
                    continue
                update_database(df, mode, first_file)
                first_file = False
                status_messages.append(f"Datei {filename} importiert.")

            # Tabelle video
            db_path = "data.db"
            conn = sqlite3.connect(db_path)
            df_video = pd.read_sql("""
                SELECT * FROM data
                WHERE (media = 'TV/OTT' OR (media = 'Social Media' AND post_type IN ('Video')))
            """, conn)
            conn.close()

            conn = sqlite3.connect(db_path)
            df_video.to_sql("video", conn, if_exists="replace", index=False)
            conn.close()
            status_messages.append(f"Tabelle 'video' erstellt: {len(df_video)} Zeilen gespeichert.")

            # Tabelle non_video
            conn = sqlite3.connect(db_path)
            df_non_video = pd.read_sql("""
                SELECT * FROM data
                WHERE media IN ('Print', 'Online', 'Social Media')
                  AND (post_type IS NULL OR post_type = '' OR post_type NOT IN ('Video'))
            """, conn)
            conn.close()

            conn = sqlite3.connect(db_path)
            df_non_video.to_sql("non_video", conn, if_exists="replace", index=False)
            conn.close()
            status_messages.append(f"Tabelle 'non_video' erstellt: {len(df_non_video)} Zeilen gespeichert.")

            # Aggregation für UI
            df_agg1 = get_aggregated_data()
            data1 = df_agg1.to_dict("records") if not df_agg1.empty else []
            columns1 = [{"name": col, "id": col} for col in df_agg1.columns] if not df_agg1.empty else []

            df_agg2 = get_aggregated_data_opposite()
            data2 = df_agg2.to_dict("records") if not df_agg2.empty else []
            columns2 = [{"name": col, "id": col} for col in df_agg2.columns] if not df_agg2.empty else []

            return html.Div([html.Div(msg) for msg in status_messages]), data1, columns1, data2, columns2

        return "", [], [], [], []
