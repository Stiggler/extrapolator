from dash import Output, Input, State, dcc
import pandas as pd
import sqlite3
from io import BytesIO
import openpyxl
from openpyxl.utils import get_column_letter

def register_nonvideo_callbacks(app):

    @app.callback(
        [
            Output("nonvideo-percentages-status", "children"),
            Output("nonvideo-percentages-table", "data"),
            Output("nonvideo-percentages-table", "columns")
        ],
        Input("calculate-percentages2_nbv", "n_clicks"),
        State("mm-dimensions2", "value"),
        State("ea-dimensions2", "value")
    )
    def calculate_nonvideo_percentages(n_clicks, mm_dims, ea_dims):
        if not n_clicks:
            return "", [], []

        group_by_all = (mm_dims or []) + (ea_dims or [])
        if not group_by_all:
            return "Bitte wählen Sie mindestens eine Dimension aus.", [], []

        db_path = "data.db"
        conn = sqlite3.connect(db_path)
        df_nonvideo = pd.read_sql("SELECT * FROM non_video", conn)
        conn.close()

        if df_nonvideo.empty:
            return "Die Tabelle non_video ist leer.", [], []

        df_basis = df_nonvideo[df_nonvideo['hr_basis'] == 'Basis']
        overall_bid_count = df_basis['bid'].nunique()

        df_basis["weight_ratio"] = df_basis.apply(
            lambda r: r["ave_weighted"] / r["ave_100"] if r["ave_100"] > 0 else 0, axis=1
        )
        overall_avg_weighting = df_basis["weight_ratio"].mean() * 100

        if ea_dims:
            avg_weighting_df = df_basis.groupby(ea_dims, as_index=False)["weight_ratio"].mean()
            avg_weighting_df.rename(columns={"weight_ratio": "avg_weighting_factor"}, inplace=True)
            avg_weighting_df["avg_weighting_factor"] = avg_weighting_df["avg_weighting_factor"] * 100
        else:
            avg_weighting_df = None

        if mm_dims:
            bid_mm_df = df_basis.groupby(mm_dims, as_index=False)['bid'].nunique()
            bid_mm_df.rename(columns={'bid': 'bid_mm_kombo'}, inplace=True)
        else:
            bid_mm_df = pd.DataFrame()

        ea_hits_df = df_basis.groupby(group_by_all, as_index=False)['bid'].nunique()
        ea_hits_df.rename(columns={'bid': 'ea_hits'}, inplace=True)

        if mm_dims:
            df_hr = df_nonvideo[df_nonvideo['hr_basis'] == 'HR']
            bid_mm_hr_df = df_hr.groupby(mm_dims, as_index=False)['bid'].nunique()
            bid_mm_hr_df.rename(columns={'bid': 'bid_mm_kombo_hr'}, inplace=True)
        else:
            bid_mm_hr_df = pd.DataFrame()

        df_groups = df_basis[group_by_all].drop_duplicates().reset_index(drop=True)

        if mm_dims:
            df_result = pd.merge(df_groups, bid_mm_df, on=mm_dims, how='left')
        else:
            df_result = df_groups.copy()

        df_result = pd.merge(df_result, ea_hits_df, on=group_by_all, how='left')
        if mm_dims:
            df_result = pd.merge(df_result, bid_mm_hr_df, on=mm_dims, how='left')

        df_result["overall_bid_count"] = overall_bid_count

        if ea_dims:
            df_result = pd.merge(df_result, avg_weighting_df, on=ea_dims, how='left')
        else:
            df_result["avg_weighting_factor"] = overall_avg_weighting

        df_result["hit_percentage"] = df_result.apply(
            lambda row: (row["ea_hits"] / row["bid_mm_kombo"] * 100) if (row.get("bid_mm_kombo", 0) > 0) else 0,
            axis=1
        )

        df_result["ids_for_HR"] = df_result["bid_mm_kombo_hr"] * df_result["hit_percentage"]/100
        df_result["ids_for_HR"] = df_result["ids_for_HR"].apply(lambda x: round(x) if pd.notna(x) else 0)

        mentions_df = df_basis.groupby(group_by_all, as_index=False)['mentions'].sum()
        mentions_df.rename(columns={'mentions': 'sum_mentions'}, inplace=True)
        df_result = pd.merge(df_result, mentions_df, on=group_by_all, how='left')
        df_result["avg_mentions"] = df_result.apply(
            lambda row: max(round(row["sum_mentions"] / row["ea_hits"]), 1) if row["ea_hits"] > 0 else 1, axis=1
        )

        df_result = df_result[df_result["ea_hits"] > 0]

        for col in ["bid_mm_kombo", "bid_mm_kombo_hr", "ea_hits"]:
            if col in df_result.columns:
                df_result[col] = df_result[col].fillna(0).apply(lambda x: format(int(x), ",d"))
        df_result["hit_percentage"] = df_result["hit_percentage"].apply(lambda x: f"{x:.2f}")
        df_result["overall_bid_count"] = df_result["overall_bid_count"].fillna(0).apply(lambda x: format(int(x), ",d"))
        df_result["avg_weighting_factor"] = df_result["avg_weighting_factor"].apply(lambda x: f"{x:.2f}")
        df_result["ids_for_HR"] = df_result["ids_for_HR"].apply(lambda x: format(int(x), ",d"))
        df_result["avg_mentions"] = df_result["avg_mentions"].apply(lambda x: format(int(x), ",d"))

        columns = [{"name": col, "id": col} for col in df_result.columns]
        data = df_result.to_dict("records")

        conn = sqlite3.connect(db_path)
        df_result.to_sql("percent_non_video", conn, if_exists="replace", index=False)
        conn.close()

        status_msg = f"Basecheck Non-Video: {len(df_result)} Gruppen gefunden. (Distinct bid Gesamt: {overall_bid_count:,})"
        return status_msg, data, columns

    @app.callback(
        Output("extrapolate-nonvideo-status", "children"),
        Input("extrapolate-nonvideo", "n_clicks"),
        State("mm-dimensions2", "value"),
        State("ea-dimensions2", "value")
    )
    def extrapolate_nonvideo(n_clicks, mm_dims2, ea_dims2):
        if not n_clicks:
            return ""

        db_path = "data.db"
        try:
            conn = sqlite3.connect(db_path)
            df_percent = pd.read_sql("SELECT * FROM percent_non_video", conn)
            df_nonvideo = pd.read_sql("SELECT * FROM non_video", conn)
            conn.close()
        except Exception as e:
            return f"Fehler beim Laden der Tabellen: {e}"

        if df_percent.empty:
            return "Die Tabelle percent_non_video ist leer."
        if df_nonvideo.empty:
            return "Die Tabelle non_video ist leer."

        if not mm_dims2:
            return "Keine MM-Dimensionen ausgewählt."

        result_rows = []

        for idx, percent_row in df_percent.iterrows():
            ids_for_hr = 0
            try:
                ids_for_hr = int(float(str(percent_row.get("ids_for_HR", 0)).replace(",", ".")))
            except:
                pass

            if ids_for_hr <= 0:
                continue

            df_candidates = df_nonvideo[df_nonvideo["hr_basis"].str.upper() == "HR"].copy()

            for dim in mm_dims2:
                val_in_percent = str(percent_row.get(dim, ""))
                df_candidates = df_candidates[df_candidates[dim].astype(str) == val_in_percent]

            if df_candidates.empty:
                continue

            import uuid
            import random

            pr_values = df_candidates["pr_value"].fillna(0)
            max_pr = pr_values.max()
            normalized = pr_values / max_pr if max_pr > 0 else pr_values
            alpha = 0.7
            weights = alpha * normalized + (1 - alpha)

            if len(df_candidates) >= ids_for_hr:
                sampled = df_candidates.sample(n=ids_for_hr, weights=weights, replace=False)
            else:
                sampled = df_candidates.sample(n=ids_for_hr, weights=weights, replace=True)

            for row in sampled.to_dict("records"):
                new_row = row.copy()

                if ea_dims2:
                    for ea in ea_dims2:
                        if ea in percent_row:
                            new_row[ea] = percent_row[ea]

                try:
                    new_row["mentions"] = int(float(str(percent_row["avg_mentions"]).replace(",", ".")))
                except:
                    new_row["mentions"] = 1

                new_row["ave_100"] = new_row.get("pr_value")

                try:
                    aw_val = float(str(percent_row['avg_weighting_factor']).replace(",", "."))
                except:
                    aw_val = 0.0
                new_row["ave_weighting_factor"] = aw_val

                try:
                    pr_val = float(new_row["pr_value"]) if new_row["pr_value"] is not None else 0.0
                    new_row["ave_weighted"] = pr_val * (aw_val / 100)
                except:
                    new_row["ave_weighted"] = 0.0

                new_row["hr_basis"] = "HR"
                new_row["bid"] = str(uuid.uuid4())

                result_rows.append(new_row)

        if not result_rows:
            return "Keine HR-Zeilen extrapoliert."

        df_hr_nonvideo = pd.DataFrame(result_rows)
        try:
            conn = sqlite3.connect(db_path)
            df_hr_nonvideo.to_sql("hr_non_bewegt", conn, if_exists="replace", index=False)
            conn.close()
            msg = (
                f"HR Non-Video-Daten extrapoliert: {len(df_hr_nonvideo)} neue Zeilen "
                f"(Summe ids_for_HR = {df_percent['ids_for_HR'].sum()})."
            )
        except Exception as e:
            msg = f"Fehler beim Speichern in 'hr_non_bewegt': {e}"

        return msg
    @app.callback(
        [
            Output("nonvideo-results-status", "children"),
            Output("nonvideo-results-table", "data"),
            Output("nonvideo-results-table", "columns"),
            Output("nonvideo-pie", "figure")
        ],
        Input("calculate-results-nonvideo", "n_clicks"),
        State("mm-dimensions-results", "value"),
        State("ea-dimensions-results", "value"),
        State("hr-basis-filter", "value")
    )
    def calculate_nonvideo_results(n_clicks, mm_dims_res, ea_dims_res, hr_basis_filter):
        if not n_clicks:
            return "", [], [], {}

        db_path = "data.db"
        conn = sqlite3.connect(db_path)
        df_non_video = pd.read_sql("SELECT * FROM non_video", conn)
        df_hr_non_video = pd.read_sql("SELECT * FROM hr_non_bewegt", conn)
        conn.close()

        df_combined = pd.concat([df_non_video, df_hr_non_video], ignore_index=True)

        if hr_basis_filter != "all":
            df_combined = df_combined[df_combined["hr_basis"] == hr_basis_filter]

        group_by_cols = (mm_dims_res or []) + (ea_dims_res or [])
        if not group_by_cols:
            return "Bitte wählen Sie mindestens eine Dimension für die Ergebnisberechnung aus.", [], [], {}

        agg_df = df_combined.groupby(group_by_cols, as_index=False).agg({
            "mentions": "sum",
            "ave_100": "sum",
            "ave_weighted": "sum"
        })

        agg_df["Summe mentions"] = agg_df["mentions"].round(0)
        agg_df["Summe ave_100"] = agg_df["ave_100"].round(0)
        agg_df["Summe ave_weighted"] = agg_df["ave_weighted"].round(0)
        agg_df = agg_df.drop(columns=["mentions", "ave_100", "ave_weighted"])

        text_columns = [{"name": col, "id": col, "type": "text"} for col in group_by_cols]
        numeric_columns = [
            {"name": "Summe mentions", "id": "Summe mentions", "type": "numeric"},
            {"name": "Summe ave_100", "id": "Summe ave_100", "type": "numeric"},
            {"name": "Summe ave_weighted", "id": "Summe ave_weighted", "type": "numeric"}
        ]
        columns = text_columns + numeric_columns
        data = agg_df.to_dict("records")

        import plotly.express as px
        pie_df = df_combined.groupby("hr_basis", as_index=False).agg({"ave_weighted": "sum"})
        fig = px.pie(pie_df, names="hr_basis", values="ave_weighted",
                     title="Verteilung von Summe ave_weighted nach hr_basis")

        status_msg = f"Ergebnisse berechnet: {len(agg_df)} Gruppen gefunden."
        return status_msg, data, columns, fig

    # UNTER deinen anderen Callbacks:
    @app.callback(
        Output("download1", "data"),
        Input("export-nonvideo-button", "n_clicks"),
        prevent_initial_call=True
    )
    def export_nonvideo_to_excel(n_clicks):
        if not n_clicks:
            return None

        conn = sqlite3.connect("data.db")
        df_non_video = pd.read_sql("SELECT * FROM non_video", conn)
        df_hr_non_video = pd.read_sql("SELECT * FROM hr_non_bewegt", conn)
        conn.close()

        df_export = pd.concat([df_non_video, df_hr_non_video], ignore_index=True)

        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df_export.to_excel(writer, index=False, sheet_name="data")
            worksheet = writer.sheets["data"]
            for i, col in enumerate(df_export.columns):
                col_letter = get_column_letter(i + 1)
                if col.lower() in ["pr_value", "ave_100", "ave_weighted"]:
                    for cell in worksheet[col_letter][1:]:
                        cell.number_format = '#,##0'
                elif col.lower() in ["broadcasting_time", "visibility", "apt", "start_time_program", "end_time_program", "start_time_item"]:
                    for cell in worksheet[col_letter][1:]:
                        cell.number_format = 'h:mm:ss'
        output.seek(0)
        return dcc.send_bytes(output.getvalue(), "nonvideo_report.xlsx")

    @app.callback(
        [
            Output("basecheck-status-nbv", "children"),
            Output("basecheck-table-nbv", "data"),
            Output("basecheck-table-nbv", "columns")
        ],
        Input("calculate-basecheck-nbv", "n_clicks"),
        State("mm-dimensions-basecheck-nbv", "value"),
        prevent_initial_call=True
    )
    def calculate_nonvideo_basecheck(n_clicks, dimensions):
        if not dimensions:
            return "Bitte wählen Sie mindestens eine Dimension aus.", [], []

        conn = sqlite3.connect("data.db")
        df = pd.read_sql("SELECT * FROM non_video", conn)
        conn.close()

        if df.empty or "hr_basis" not in df.columns:
            return "Keine gültigen Daten in 'non_video' gefunden.", [], []

        grouped = df.groupby(dimensions + ["hr_basis"], as_index=False).agg({
            "bid": pd.Series.nunique
        })

        pivot_bid = grouped.pivot_table(index=dimensions, columns="hr_basis", values="bid", fill_value=0).add_prefix("distinct_bid_").reset_index()

        columns = []
        for col in pivot_bid.columns:
            if col.startswith("distinct_bid_"):
                basis = col.replace("distinct_bid_", "")
                columns.append({"name": ["distinct_bid", basis], "id": col})
            else:
                columns.append({"name": [col, ""], "id": col})

        data = pivot_bid.to_dict("records")
        return f"{len(pivot_bid)} Gruppen gefunden.", data, columns
