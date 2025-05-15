from dash import Output, Input, State, dcc, callback_context, ctx, dash_table
import dash
import pandas as pd
import sqlite3
import re
from helpers import decimal_to_hms


def register_video_callbacks(app):

    @app.callback(
        [
            Output("percentages-status", "children"),
            Output("percentages-table", "data"),
            Output("percentages-table", "columns"),
            Output("field-selector", "options")
        ],
        Input("calculate-percentages", "n_clicks"),
        State("mm-dimensions", "value"),
        State("ea-dimensions", "value")
    )
    def calculate_percentages(n_clicks, mm_dims, ea_dims):
        if not n_clicks:
            return "", [], [], []
        group_by_cols = (mm_dims or []) + (ea_dims or [])
        if not group_by_cols:
            return "Bitte wählen Sie mindestens eine Dimension aus.", [], []

        group_by_clause = ", ".join(group_by_cols)
        join_condition = " AND ".join([f"v2.{dim} = v.{dim}" for dim in mm_dims]) if mm_dims else "1=1"

        query = f"""
        SELECT 
             {group_by_clause},
             COUNT(DISTINCT bid) AS count_bid,
             SUM(mentions) AS sum_mentions,
             SUM(visibility) AS sum_visibility,
             (
               SELECT SUM(CASE WHEN tool IS NULL OR tool = '' THEN broadcasting_time ELSE 0 END)
               FROM video AS v2
               WHERE v2.hr_basis = 'Basis' AND {join_condition}
             ) AS sum_broadcasting_time
        FROM video AS v
        WHERE hr_basis = 'Basis'
        GROUP BY {group_by_clause}
        """
        if ea_dims:
            having_conditions = " AND ".join([f"({dim} IS NULL OR {dim} = '')" for dim in ea_dims])
            query += f"\nHAVING NOT ({having_conditions})"

        conn = sqlite3.connect("data.db")
        df_raw = pd.read_sql(query, conn)
        conn.close()
        if df_raw.empty:
            return "Keine Daten gefunden.", [], [], []


        df = df_raw.copy()
        df['sum_mentions'] = df['sum_mentions'].fillna(0).astype(int)
        df['sum_visibility_raw'] = df['sum_visibility']
        df['sum_broadcasting_time_raw'] = df['sum_broadcasting_time']
        df['sum_visibility'] = df['sum_visibility_raw'].apply(decimal_to_hms)
        df['sum_broadcasting_time'] = df['sum_broadcasting_time_raw'].apply(decimal_to_hms)
        df['visibility_share'] = df.apply(
            lambda row: f"{(row['sum_visibility_raw'] / row['sum_broadcasting_time_raw'] * 100):.2f}%"
            if row['sum_broadcasting_time_raw'] else "N/A", axis=1
        )
        df['avg_mention'] = df.apply(
            lambda row: row['sum_visibility_raw'] / row['sum_mentions'] if row['sum_mentions'] != 0 else 0, axis=1
        )
        df['avg_mention'] = df['avg_mention'].apply(decimal_to_hms)

        final_cols = group_by_cols + [
            "sum_mentions", "avg_mention", "sum_visibility", "sum_broadcasting_time", "visibility_share"
        ]
        final_df = df[final_cols]
        columns = [{"name": col, "id": col, "editable": col in ["visibility_share", "avg_mention"]} for col in final_df.columns]
        data = final_df.to_dict("records")

        conn = sqlite3.connect("data.db")
        final_df.to_sql("percent", conn, if_exists="replace", index=False)
        conn.close()

        field_options = [{"label": col["name"], "value": col["id"]} for col in columns]
        return "Berechnung erfolgreich.", data, columns, field_options




    @app.callback(
        Output("update-percentages-status", "children"),
        Input("update-percentages", "n_clicks"),
        State("percentages-table", "data")
    )
    def update_percentages_db(n_clicks, table_data):
        if not n_clicks:
            return ""
        df = pd.DataFrame(table_data)
        conn = sqlite3.connect("data.db")
        df.to_sql("percent", conn, if_exists="replace", index=False)
        conn.close()
        return "Tabelle 'percent' wurde aktualisiert."

    @app.callback(
        Output("extrapolate-status", "children"),
        Input("extrapolate", "n_clicks"),
        State("mm-dimensions", "value")
    )
    def extrapolate_hr(n_clicks, mm_dims):
        if not n_clicks:
            return ""
        if not mm_dims:
            return "Bitte wählen Sie mindestens eine MM-Dimension für die Hochrechnung aus."

        db_path = "data.db"
        conn = sqlite3.connect(db_path)
        df_video = pd.read_sql("SELECT * FROM video WHERE hr_basis = 'HR'", conn)
        df_percent = pd.read_sql("SELECT * FROM percent", conn)
        conn.close()

        if df_video.empty:
            return "Keine HR-Daten in der Tabelle video gefunden."
        if df_percent.empty:
            return "Keine Daten in der Tabelle percent gefunden."

        df_merged = pd.merge(df_video, df_percent, on=mm_dims, suffixes=("_video", "_percent"))
        if "visibility_share_percent" not in df_merged.columns:
            return "Spalte 'visibility_share_percent' fehlt in den aggregierten Daten."

        df_merged["visibility_share"] = df_merged["visibility_share_percent"]


        def convert_visibility_share(val):
            try:
                if isinstance(val, str) and "%" in val:
                    return float(val.strip('%')) / 100.0
                elif isinstance(val, (int, float)):
                    return float(val)
                else:
                    return 0.0
            except Exception:
                return 0.0

        df_merged["visibility_share_factor"] = df_merged["visibility_share"].apply(convert_visibility_share)
        df_merged["visibility"] = df_merged["visibility_share_factor"] * df_merged["broadcasting_time"]

        def hms_to_decimal(hms_str):
            try:
                parts = re.split(":", hms_str)
                if len(parts) != 3:
                    return 0.0
                hours, minutes, seconds = map(float, parts)
                return (hours * 3600 + minutes * 60 + seconds) / 86400
            except Exception:
                return 0.0

        df_merged["avg_mention_numeric"] = df_merged["avg_mention"].apply(hms_to_decimal)
        df_merged["mentions"] = df_merged.apply(
            lambda row: int(row["visibility"] / row["avg_mention_numeric"]) if row["avg_mention_numeric"] > 0 else 1,
            axis=1
        )

        df_merged.drop(columns=["visibility_share_factor", "avg_mention_numeric"], inplace=True)

        conn = sqlite3.connect(db_path)
        df_merged.to_sql("hr_bewegt", conn, if_exists="replace", index=False)
        conn.close()

        return f"Extrapolation abgeschlossen: {len(df_merged)} Zeilen wurden in 'hr_bewegt' erstellt."

    @app.callback(
        [Output("results-status", "children"),
         Output("results-table", "data"),
         Output("results-table", "columns")],
        [Input("calculate-results", "n_clicks"),
         Input("calculate-results2", "n_clicks")],
        [State("mm-dimensions-results-video", "value"),
         State("ea-dimensions-results-video", "value")]
    )
    def combined_results(n_clicks1, n_clicks2, mm_dims, ea_dims):
        ctx = dash.callback_context
        if not ctx.triggered:
            return "", [], []

        triggered_id = ctx.triggered[0]['prop_id'].split('.')[0]
        db_path = "data.db"

        if triggered_id == "calculate-results":
            conn = sqlite3.connect(db_path)
            df_video = pd.read_sql("SELECT * FROM video", conn)
            df_hr = pd.read_sql("SELECT * FROM hr_bewegt", conn)
            conn.close()

            if "sponsor_percent" in df_hr.columns:
                df_hr["sponsor"] = df_hr["sponsor_percent"]
                df_hr.drop(columns=["sponsor_percent"], inplace=True)
            if "tool_percent" in df_hr.columns:
                df_hr["tool"] = df_hr["tool_percent"]
                df_hr.drop(columns=["tool_percent"], inplace=True)

            df_final = pd.concat([df_video, df_hr], ignore_index=True)

            try:
                df_final["sponsoring_value_cpt"] = (df_final["visibility"] * df_final["reach"] * 86400 / 1000 * 10 * 1000000) / 30
                df_final["sponsorship_contacts"] = (df_final["visibility"] * df_final["reach"] * 86400 / 30)
                df_final["ave_100"] = (df_final["visibility"] * 86400) * (df_final["advertising_price_TV"] / 30)
                df_final["sponsoring_value_cpt"] = df_final["sponsoring_value_cpt"].fillna(0).apply(lambda x: int(x))
                df_final["ave_100"] = df_final["ave_100"].fillna(0).apply(lambda x: int(x))
            except Exception as e:
                return f"Fehler bei der Berechnung von sponsoring_value_cpt: {e}", [], []

            conn = sqlite3.connect(db_path)
            df_final.to_sql("video_final", conn, if_exists="replace", index=False)
            conn.close()

            return f"Neue Tabelle 'video_final' erstellt: {len(df_final)} Zeilen, Sponsoring_Value_CPT aktualisiert.", [], []

        elif triggered_id == "calculate-results2":
            group_by_cols = (mm_dims or []) + (ea_dims or [])
            if not group_by_cols:
                return "Bitte wählen Sie mindestens eine Dimension aus.", [], []

            conn = sqlite3.connect(db_path)
            df = pd.read_sql("SELECT * FROM video_final", conn)
            conn.close()

            if df.empty:
                return "Die Tabelle video_final ist leer.", [], []

            df = df[df['hr_basis'].isin(['Basis', 'HR'])]

            grouped_vis = df.groupby(group_by_cols + ['hr_basis'], as_index=False)['visibility'].sum()
            pivot_vis = grouped_vis.pivot_table(index=group_by_cols, columns='hr_basis', values='visibility', fill_value=0).reset_index()
            pivot_vis.rename(columns={'Basis': 'sum_visibility_basis', 'HR': 'sum_visibility_hr'}, inplace=True)

            grouped_extra = df.groupby(group_by_cols + ['hr_basis'], as_index=False).agg({
                'bid': pd.Series.nunique,
                'ave_100': 'sum'
            })
            pivot_bid = grouped_extra.pivot_table(index=group_by_cols, columns='hr_basis', values='bid', fill_value=0).reset_index()
            pivot_bid.rename(columns={'Basis': 'bid_count_basis', 'HR': 'bid_count_hr'}, inplace=True)
            pivot_ave = grouped_extra.pivot_table(index=group_by_cols, columns='hr_basis', values='ave_100', fill_value=0).reset_index()
            pivot_ave.rename(columns={'Basis': 'sum_ave_100_basis', 'HR': 'sum_ave_100_hr'}, inplace=True)

            final_df = pivot_vis.merge(pivot_bid, on=group_by_cols, how='outer') \
                                .merge(pivot_ave, on=group_by_cols, how='outer')

            final_df["sum_visibility_basis"] = final_df["sum_visibility_basis"].apply(decimal_to_hms)
            final_df["sum_visibility_hr"] = final_df["sum_visibility_hr"].apply(decimal_to_hms)
            final_df["bid_count_basis"] = final_df["bid_count_basis"].apply(lambda x: format(int(x), ",d"))
            final_df["bid_count_hr"] = final_df["bid_count_hr"].apply(lambda x: format(int(x), ",d"))
            final_df["sum_ave_100_basis"] = final_df["sum_ave_100_basis"].apply(lambda x: format(int(x), ",d"))
            final_df["sum_ave_100_hr"] = final_df["sum_ave_100_hr"].apply(lambda x: format(int(x), ",d"))

            columns = [{"name": col, "id": col} for col in final_df.columns]
            data = final_df.to_dict("records")
            return f"Ergebnisse berechnet: {len(final_df)} Gruppen gefunden.", data, columns

        return "", [], []


    from dash import dcc  # sicherstellen, dass dcc importiert ist
    from io import BytesIO
    import openpyxl
    from openpyxl.utils import get_column_letter

    @app.callback(
        Output("download", "data"),
        Input("export-button", "n_clicks"),
        prevent_initial_call=True
    )
    def export_video_to_excel(n_clicks):
        if not n_clicks:
            return None

        conn = sqlite3.connect("data.db")
        df = pd.read_sql("SELECT * FROM video_final", conn)
        conn.close()

        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name="data")
            worksheet = writer.sheets["data"]
            for i, col in enumerate(df.columns):
                col_letter = get_column_letter(i + 1)
                if col.lower() in ["pr_value", "ave_100", "ave_weighted", "sponsoring_value_cpt"]:
                    for cell in worksheet[col_letter][1:]:
                        cell.number_format = '#,##0'
                elif col.lower() in ["broadcasting_time", "visibility", "apt", "start_time_program", "end_time_program", "start_time_item"]:
                    for cell in worksheet[col_letter][1:]:
                        cell.number_format = 'h:mm:ss'
        output.seek(0)
        return dcc.send_bytes(output.getvalue(), "video_final.xlsx")



    @app.callback(
        Output("percentages-table", "data", allow_duplicate=True),
        [
            Input("add-percentages-row", "n_clicks"),
            Input("duplicate-percentages-rows", "n_clicks")
        ],
        State("percentages-table", "data"),
        State("percentages-table", "columns"),
        State("percentages-table", "selected_rows"),
        prevent_initial_call=True
    )
    def modify_percentages_table(n_add, n_duplicate, data, columns, selected_rows):
        from dash import callback_context
        triggered = callback_context.triggered_id
        if data is None:
            data = []

        if triggered == "add-percentages-row":
            new_row = {col["id"]: "" for col in columns}
            data.append(new_row)
        elif triggered == "duplicate-percentages-rows" and selected_rows:
            duplicated = [data[i].copy() for i in selected_rows]
            data += duplicated

        return data


    @app.callback(
        Output("percentages-table", "data", allow_duplicate=True),
        Input("apply-field-value", "n_clicks"),
        State("percentages-table", "data"),
        State("percentages-table", "selected_rows"),
        State("field-selector", "value"),
        State("field-value", "value"),
        prevent_initial_call=True
    )
    def apply_field_value(n_clicks, data, selected_rows, field, value):
        if not selected_rows or not field:
            return data

        for i in selected_rows:
            data[i][field] = value
        return data


    @app.callback(
        [
            Output("basecheck-status", "children"),
            Output("basecheck-table", "data"),
            Output("basecheck-table", "columns")
        ],
        Input("calculate-basecheck", "n_clicks"),
        State("mm-dimensions-basecheck", "value"),
        prevent_initial_call=True
    )
    def calculate_basecheck(n_clicks, dimensions):
        if not dimensions:
            return "Bitte wählen Sie mindestens eine Dimension aus.", [], []

        conn = sqlite3.connect("data.db")
        df = pd.read_sql("SELECT * FROM video", conn)
        conn.close()

        if df.empty or "hr_basis" not in df.columns:
            return "Keine gültigen Daten in 'video' gefunden.", [], []

        # Gruppierung nach Dimensionen + hr_basis
        grouped = df.groupby(dimensions + ["hr_basis"], as_index=False).agg({
            "bid": pd.Series.nunique,
            "visibility": "sum",
            "broadcasting_time": "sum"
        })

        # Pivotieren
        pivot_bid = grouped.pivot_table(index=dimensions, columns="hr_basis", values="bid", fill_value=0).add_prefix("distinct_bid_").reset_index()
        pivot_vis = grouped.pivot_table(index=dimensions, columns="hr_basis", values="visibility", fill_value=0).add_prefix("visibility_").reset_index()
        pivot_bt  = grouped.pivot_table(index=dimensions, columns="hr_basis", values="broadcasting_time", fill_value=0).add_prefix("broadcasting_time_").reset_index()

        # Zusammenführen
        df_final = pivot_bid.merge(pivot_vis, on=dimensions).merge(pivot_bt, on=dimensions)

        # Zeitfelder umwandeln
        for col in df_final.columns:
            if col.startswith("visibility_") or col.startswith("broadcasting_time_"):
                df_final[col] = df_final[col].apply(decimal_to_hms)

        columns = []
        for col in df_final.columns:
            if col.startswith("distinct_bid_"):
                basis = col.replace("distinct_bid_", "")
                columns.append({"name": ["distinct_bid", basis], "id": col})
            elif col.startswith("visibility_"):
                basis = col.replace("visibility_", "")
                columns.append({"name": ["visibility", basis], "id": col})
            elif col.startswith("broadcasting_time_"):
                basis = col.replace("broadcasting_time_", "")
                columns.append({"name": ["broadcasting_time", basis], "id": col})
            else:
                columns.append({"name": [col, ""], "id": col})

        data = df_final.to_dict("records")

        return f"{len(df_final)} Gruppen gefunden.", data, columns
