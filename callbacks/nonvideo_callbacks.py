# nonvideo_callbacks.py
from dash import Input, Output, State, exceptions, dcc
import pandas as pd
import sqlite3
import uuid
import zipfile
from io import BytesIO
import random
import openpyxl
from openpyxl.utils import get_column_letter
import plotly.express as px
from math import ceil


def register_nonvideo_callbacks(app):
    print("🔧 register_nonvideo_callbacks() wurde aufgerufen")
    # 1) Calculate percent values (Hochrechnung Non-Video)
    @app.callback(
        [
            Output("nonvideo-percentages-status", "children"),
            Output("nonvideo-percentages-table", "data"),
            Output("nonvideo-percentages-table", "columns")
        ],
        Input("calculate-percentages2_nbv", "n_clicks"),
        State("mm-dimensions2", "value"),
        State("ea-dimensions2", "value"),
        prevent_initial_call=True
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

        # Basis-Daten
        df_basis = df_nonvideo[df_nonvideo['hr_basis'] == 'Basis']
        overall_bid_count = df_basis['bid'].nunique()

        # Gewichtungs-Factor
        df_basis['weight_ratio'] = df_basis.apply(
            lambda r: (r['ave_weighted'] / r['ave_100']) if r['ave_100'] > 0 else 0,
            axis=1
        )
        overall_avg_weighting = df_basis['weight_ratio'].mean() * 100

        # EA-Dimension Mittelwerte
        if ea_dims:
            avg_weighting_df = (
                df_basis.groupby(ea_dims, as_index=False)['weight_ratio']
                        .mean()
                        .rename(columns={'weight_ratio': 'avg_weighting_factor'})
            )
            avg_weighting_df['avg_weighting_factor'] *= 100
        else:
            avg_weighting_df = None

        # MM-Dimension Bid Counts
        if mm_dims:
            bid_mm_df = (
                df_basis.groupby(mm_dims, as_index=False)['bid']
                        .nunique()
                        .rename(columns={'bid': 'bid_mm_kombo'})
            )
        else:
            bid_mm_df = pd.DataFrame()

        # EA Hits
        ea_hits_df = (
            df_basis.groupby(group_by_all, as_index=False)['bid']
                    .nunique()
                    .rename(columns={'bid': 'ea_hits'})
        )

        # MM HR-Basis
        if mm_dims:
            df_hr = df_nonvideo[df_nonvideo['hr_basis'] == 'HR']
            bid_mm_hr_df = (
                df_hr.groupby(mm_dims, as_index=False)['bid']
                     .nunique()
                     .rename(columns={'bid': 'bid_mm_kombo_hr'})
            )
        else:
            bid_mm_hr_df = pd.DataFrame()

        # Grund-Kombinationen
        df_groups = df_basis[group_by_all].drop_duplicates().reset_index(drop=True)

        # Merge Schritt-für-Schritt
        df_result = df_groups.copy()
        if mm_dims:
            df_result = pd.merge(df_result, bid_mm_df, on=mm_dims, how='left')
        df_result = pd.merge(df_result, ea_hits_df, on=group_by_all, how='left')
        if mm_dims:
            df_result = pd.merge(df_result, bid_mm_hr_df, on=mm_dims, how='left')
        df_result['overall_bid_count'] = overall_bid_count
        if ea_dims and avg_weighting_df is not None:
            df_result = pd.merge(df_result, avg_weighting_df, on=ea_dims, how='left')
        else:
            df_result['avg_weighting_factor'] = overall_avg_weighting

        # Berechnungen
        df_result['hit_percentage'] = df_result.apply(
            lambda row: (row['ea_hits'] / row['bid_mm_kombo'] * 100)
                        if row.get('bid_mm_kombo', 0) > 0 else 0,
            axis=1
        )
        df_result['ids_for_HR'] = (
            df_result['bid_mm_kombo_hr'] * df_result['hit_percentage'] / 100
        ).round(0)

        # avg_mentions
        mentions_df = (
            df_basis.groupby(group_by_all, as_index=False)['mentions']
            .sum()
            .rename(columns={'mentions':'sum_mentions'})
        )
        df_result = pd.merge(df_result, mentions_df, on=group_by_all, how='left')
        df_result['avg_mentions'] = df_result.apply(
            lambda row: max(round(row['sum_mentions'] / row['ea_hits']), 1)
                        if row['ea_hits']>0 else 1,
            axis=1
        )
        df_result = df_result[df_result['ea_hits'] > 0]

        # Formatierung
        for col in ['bid_mm_kombo','bid_mm_kombo_hr','ea_hits','ids_for_HR','sum_mentions']:
            if col in df_result.columns:
                df_result[col] = df_result[col].fillna(0).astype(int).map('{:,}'.format)
        df_result['hit_percentage'] = df_result['hit_percentage'].map('{:.2f}'.format)
        df_result['avg_weighting_factor'] = df_result['avg_weighting_factor'].map('{:.2f}'.format)

        # Columns & data
        columns = [{'name': c, 'id': c} for c in df_result.columns]
        data = df_result.to_dict('records')

        # Save percent_non_video
        conn = sqlite3.connect(db_path)
        df_result.to_sql('percent_non_video', conn, if_exists='replace', index=False)
        conn.close()

        status_msg = (
            f"Basecheck Non-Video: {len(df_result)} Gruppen gefunden. "
            f"(Distinct bid gesamt: {overall_bid_count:,})"
        )
        return status_msg, data, columns


    @app.callback(
        Output("extrapolate-nonvideo-status", "children"),
        Input("extrapolate-nonvideo", "n_clicks"),
        State("mm-dimensions2", "value"),
        State("ea-dimensions2", "value"),
        prevent_initial_call=True
    )
    def extrapolate_nonvideo(n_clicks, mm_dims2, ea_dims2):
        if not n_clicks:
            raise exceptions.PreventUpdate

        db_path = "data.db"
        # 1) Laden der Prozent- und Non-Video-Tabellen
        with sqlite3.connect(db_path, timeout=30) as conn:
            df_percent  = pd.read_sql("SELECT * FROM percent_non_video", conn)
            df_nonvideo = pd.read_sql("SELECT * FROM non_video", conn)

        if df_percent.empty:
            return "❌ Tabelle percent_non_video ist leer."
        if df_nonvideo.empty:
            return "❌ Tabelle non_video ist leer."
        if not mm_dims2:
            return "⚠️ Keine MM-Dimensionen ausgewählt."

        # 2) Debug-Zähler
        total_requested = 0
        total_produced  = 0
        skipped_zero_id = 0
        skipped_no_cand = 0

        # 3) Sampling-Loop
        result_rows = []
        alpha = 0.7
        scale = 1.5  # Skalierungsfaktor

        for _, pr in df_percent.iterrows():
            # a) ids_for_hr sauber parsen (Tausender entfernen)
            ids_str    = str(pr.get("ids_for_HR", 0))
            ids_digits = "".join(ch for ch in ids_str if ch.isdigit())
            try:
                base_ids = int(ids_digits) if ids_digits else 0
            except:
                base_ids = 0

            # b) Skalieren & Aufrunden
            ids_for_hr = ceil(base_ids * scale)

            # c) Zero-Check
            if ids_for_hr <= 0:
                skipped_zero_id += 1
                continue
            total_requested += ids_for_hr

            # d) Kandidaten filtern
            df_cand = df_nonvideo[df_nonvideo['hr_basis'].str.upper() == 'HR'].copy()
            for dim in mm_dims2:
                val = str(pr.get(dim, '')).strip()
                df_cand = df_cand[df_cand[dim].astype(str).str.strip() == val]
            if df_cand.empty:
                skipped_no_cand += 1
                continue

            # e) Gewichte
            pr_vals    = df_cand['pr_value'].fillna(0)
            max_pr     = pr_vals.max()
            normalized = pr_vals / max_pr if max_pr>0 else pr_vals
            weights    = alpha * normalized + (1 - alpha)

            # f) Channel-Guarantee-Sampling
            mandatory = []
            remaining = ids_for_hr
            channels  = df_cand['channel'].dropna().unique()
            for ch in channels:
                if remaining <= 0:
                    break
                sub = df_cand[df_cand['channel'] == ch]
                if sub.empty:
                    continue
                sel = sub.sample(
                    n=1,
                    weights=weights.loc[sub.index],
                    replace=True
                )
                mandatory.append(sel)
                remaining -= 1

            # g) Restliches Sampling
            rest = pd.DataFrame()
            if remaining > 0:
                rest = df_cand.sample(
                    n=remaining,
                    weights=weights,
                    replace=len(df_cand) < remaining
                )

            # h) Final zusammenführen
            sampled = pd.concat(mandatory + [rest], ignore_index=True)
            total_produced += len(sampled)

            # i) Baue result_rows
            for row in sampled.to_dict('records'):
                new = row.copy()
                # EA-Dimensionen übernehmen
                for ea in ea_dims2 or []:
                    if ea in pr:
                        new[ea] = pr[ea]
                # mentions
                try:
                    new['mentions'] = int(float(str(pr['avg_mentions']).replace(',', '.')))
                except:
                    new['mentions'] = 1
                # ave_100, ave_weighting_factor, ave_weighted
                new['ave_100']              = new.get('pr_value', 0)
                try:
                    aw = float(str(pr.get('avg_weighting_factor', 0)).replace(',', '.'))
                except:
                    aw = 0.0
                new['ave_weighting_factor'] = aw
                new['ave_weighted']         = float(new.get('pr_value', 0)) * (aw/100)
                # HR-Kennung und neue BID
                new['hr_basis'] = 'HR'
                new['bid']      = str(uuid.uuid4())
                result_rows.append(new)

        # 4) Debug-Report bei 0 Zeilen
        if not result_rows:
            return (f"⚠️ Keine HR-Zeilen. Angefordert={total_requested}, "
                    f"zero_id={skipped_zero_id}, no_cand={skipped_no_cand}")

        # 5) Schreiben in DB
        df_hr = pd.DataFrame(result_rows)
        try:
            with sqlite3.connect(db_path, timeout=30) as conn:
                df_hr.to_sql('hr_non_bewegt', conn, if_exists='replace', index=False)
        except Exception as e:
            return f"❌ Speichern fehlgeschlagen: {e}"

        # 6) Finaler Debug-Report
        return (f"✅ Fertig. Angefordert={total_requested}, Generiert={total_produced}, "
                f"zero_id={skipped_zero_id}, no_cand={skipped_no_cand}")
        

    # 3) Calculate results
    @app.callback(
        [
            Output('nonvideo-results-status','children'),
            Output('nonvideo-results-table','data'),
            Output('nonvideo-results-table','columns'),
            Output('nonvideo-pie','figure')
        ],
        Input('calculate-results-nonvideo','n_clicks'),
        State('mm-dimensions-results','value'),
        State('ea-dimensions-results','value'),
        State('hr-basis-filter','value'),
        prevent_initial_call=True
    )
    def calculate_nonvideo_results(n_clicks, mm_dims_res, ea_dims_res, hr_basis_filter):
        if not n_clicks:
            raise exceptions.PreventUpdate
        conn = sqlite3.connect('data.db')
        df_nv = pd.read_sql('SELECT * FROM non_video', conn)
        df_hr_nv = pd.read_sql('SELECT * FROM hr_non_bewegt', conn)
        conn.close()
        df_all = pd.concat([df_nv, df_hr_nv], ignore_index=True)
        if hr_basis_filter!='all':
            df_all = df_all[df_all['hr_basis']==hr_basis_filter]
        group_by_cols = (mm_dims_res or []) + (ea_dims_res or [])
        if not group_by_cols:
            return 'Bitte wählen Sie ...', [], [], {}
        agg = df_all.groupby(group_by_cols, as_index=False).agg({
            'mentions':'sum','ave_100':'sum','ave_weighted':'sum'
        })
        agg['Summe mentions'] = agg['mentions'].round(0)
        agg['Summe ave_100'] = agg['ave_100'].round(0)
        agg['Summe ave_weighted'] = agg['ave_weighted'].round(0)
        agg = agg.drop(columns=['mentions','ave_100','ave_weighted'])
        cols = (
            [{'name':c,'id':c,'type':'text'} for c in group_by_cols]
            +[{'name':'Summe mentions','id':'Summe mentions','type':'numeric'},
             {'name':'Summe ave_100','id':'Summe ave_100','type':'numeric'},
             {'name':'Summe ave_weighted','id':'Summe ave_weighted','type':'numeric'}]
        )
        fig = px.pie(
            df_all.groupby('hr_basis',as_index=False).agg({'ave_weighted':'sum'}),
            names='hr_basis',values='ave_weighted',title='Verteilung Summe ave_weighted'
        )
        return f"Ergebnisse berechnet: {len(agg)} Gruppen.", agg.to_dict('records'), cols, fig



# 4a) Zeilenanzahl-Info neben dem Export-Button
    @app.callback(
        Output("nonvideo-export-info", "children"),
        Input("nicht-bewegtbild-subtabs", "value"),
        prevent_initial_call=False
    )
    def update_nonvideo_export_info(active_tab):
        # Zähle nur, wenn wir im Hochrechnungs-Tab sind (Value = "hochrechnung_nbv")
        if active_tab != "ergebnisse_nbv":
            return ""
        conn = sqlite3.connect("data.db")
        c1 = conn.execute("SELECT COUNT(*) FROM non_video").fetchone()[0]
        c2 = conn.execute("SELECT COUNT(*) FROM hr_non_bewegt").fetchone()[0]
        conn.close()
        total = c1 + c2
        return f"Zeilen in non_video: {c1:,}, hr_non_bewegt: {c2:,} → Gesamt: {total:,}"


    # 4b) Export mit optionalem Split per MM-Dimension
    @app.callback(
        Output("download1", "data"),
        Input("export-nonvideo-button", "n_clicks"),
        State("export-mm-dims-nbv", "value"),
        prevent_initial_call=True
    )
    def export_nonvideo_to_excel(n_clicks, split_dims):
        if not n_clicks:
            raise exceptions.PreventUpdate

        # Daten laden
        conn = sqlite3.connect("data.db")
        df_nv = pd.read_sql("SELECT * FROM non_video", conn)
        df_hr = pd.read_sql("SELECT * FROM hr_non_bewegt", conn)
        conn.close()
        df = pd.concat([df_nv, df_hr], ignore_index=True)

        # Kein Split: einfache Excel
        if not split_dims:
            buf = BytesIO()
            with pd.ExcelWriter(buf, engine="openpyxl") as w:
                df.to_excel(w, index=False, sheet_name="data")
            buf.seek(0)
            return dcc.send_bytes(buf.getvalue(), "nonvideo_report.xlsx")

        # Split: ZIP mit je einer Excel pro Kombination
        zip_buf = BytesIO()
        with zipfile.ZipFile(zip_buf, mode="w") as zf:
            # Alle einzigartigen Dim-Kombos
            combos = df[split_dims].drop_duplicates()
            for _, key_row in combos.iterrows():
                # Filter für diese Kombination
                mask = True
                parts = []
                for dim in split_dims:
                    val = key_row[dim]
                    mask &= (df[dim] == val)
                    parts.append(f"{dim}-{val}")
                sub = df[mask]

                # Excel-Buffer bauen
                excel_buf = BytesIO()
                with pd.ExcelWriter(excel_buf, engine="openpyxl") as w:
                    sub.to_excel(w, index=False, sheet_name="data")
                excel_buf.seek(0)

                # Dateiname aus den Dim-Werten
                fname = "_".join(parts) + ".xlsx"
                zf.writestr(fname, excel_buf.read())

        zip_buf.seek(0)
        return dcc.send_bytes(zip_buf.getvalue(), "nonvideo_exports.zip")


    # 5) Basecheck Non-Video
    @app.callback(
        [
            Output('basecheck-status-nbv','children'),
            Output('basecheck-table-nbv','data'),
            Output('basecheck-table-nbv','columns')
        ],
        Input('calculate-basecheck-nbv','n_clicks'),
        State('mm-dimensions-basecheck-nbv','value'),
        prevent_initial_call=True
    )
    def calculate_nonvideo_basecheck(n_clicks, dimensions):
        if not dimensions:
            return 'Bitte wählen Sie mindestens eine Dimension aus.', [], []
        conn = sqlite3.connect('data.db')
        df = pd.read_sql('SELECT * FROM non_video', conn)
        conn.close()
        if df.empty or 'hr_basis' not in df.columns:
            return 'Keine gültigen Daten in non_video gefunden.', [], []
        grouped = df.groupby(dimensions+['hr_basis'], as_index=False).agg({'bid':'nunique'})
        pivot = grouped.pivot_table(index=dimensions, columns='hr_basis', values='bid', fill_value=0)
        pivot = pivot.add_prefix('distinct_bid_').reset_index()
        cols = []
        for col in pivot.columns:
            if col.startswith('distinct_bid_'):
                base = col.replace('distinct_bid_','')
                cols.append({'name':['distinct_bid', base], 'id':col})
            else:
                cols.append({'name':[col,''], 'id':col})
        return f"{len(pivot)} Gruppen gefunden.", pivot.to_dict('records'), cols

    # 6) Table row operations
    @app.callback(
        Output('nonvideo-percentages-table','selected_rows', allow_duplicate=True),
        Input('select-all-nonvideo-rows','n_clicks'),
        State('nonvideo-percentages-table','data'),
        prevent_initial_call=True
    )
    def select_all_nonvideo_rows(n_clicks, data):
        return list(range(len(data))) if data else []

    @app.callback(
        Output('nonvideo-percentages-table','selected_rows', allow_duplicate=True),
        Input('deselect-all-nonvideo-rows','n_clicks'),
        prevent_initial_call=True
    )
    def deselect_all_nonvideo_rows(n_clicks):
        return []

    @app.callback(
        Output('nonvideo-percentages-table','data', allow_duplicate=True),
        Input('delete-nonvideo-percentages-rows','n_clicks'),
        State('nonvideo-percentages-table','data'),
        State('nonvideo-percentages-table','selected_rows'),
        prevent_initial_call=True
    )
    def delete_nonvideo_rows(n_clicks, data, selected_rows):
        if not data or not selected_rows:
            return data
        return [r for i,r in enumerate(data) if i not in selected_rows]

    @app.callback(
        Output('nonvideo-percentages-table','data', allow_duplicate=True),
        Input('duplicate-nonvideo-percentages-rows','n_clicks'),
        State('nonvideo-percentages-table','data'),
        State('nonvideo-percentages-table','selected_rows'),
        prevent_initial_call=True
    )
    def duplicate_nonvideo_rows(n_clicks, data, selected_rows):
        if not data or not selected_rows:
            return data
        valid = [i for i in selected_rows if 0<=i<len(data)]
        return data + [data[i].copy() for i in valid]

    @app.callback(
        Output('nonvideo-percentages-table','data', allow_duplicate=True),
        Input('apply-field-value-nonvideo','n_clicks'),
        State('nonvideo-percentages-table','data'),
        State('nonvideo-percentages-table','selected_rows'),
        State('field-selector-nonvideo','value'),
        State('field-value-nonvideo','value'),
        prevent_initial_call=True
    )
    def apply_field_value_nonvideo(n_clicks, data, selected_rows, field, value):
        if not data or not selected_rows or not field:
            return data
        for i in [i for i in selected_rows if 0<=i<len(data)]:
            data[i][field] = value
        return data

    @app.callback(
        Output('field-selector-nonvideo','options', allow_duplicate=True),
        Input('nonvideo-percentages-table','columns'),
        prevent_initial_call='initial_duplicate'
    )
    def update_field_selector_nonvideo(columns):
        return [{'label':c.get('name',c.get('id')),'value':c.get('id')} for c in (columns or [])]

    @app.callback(
        Output('update-nonvideo-percentages-status','children'),
        Input('update-percentages-nbv','n_clicks'),
        State('nonvideo-percentages-table','data'),
        prevent_initial_call=True
    )
    def update_percentages_nonvideo(n_clicks, data):
        if not data:
            return "❌ Keine Daten zum Speichern."
        try:
            db_path = 'data.db'
            df = pd.DataFrame(data)
            conn = sqlite3.connect(db_path)
            df.to_sql('percent_non_video', conn, if_exists='replace', index=False)
            conn.close()
            return f"✅ Prozentwertetabelle erfolgreich gespeichert ({len(df)} Zeilen)."
        except Exception as e:
            return f"❌ Fehler beim Speichern: {e}"
        

    # 4c) Parquet-Export anstelle von Excel
    @app.callback(
        Output("download-parquet", "data"),
        Input("export-nonvideo-parquet-button", "n_clicks"),
        State("export-mm-dims-nbv", "value"),
        prevent_initial_call=True
    )
    def export_nonvideo_to_parquet(n_clicks, split_dims):
        if not n_clicks:
            raise exceptions.PreventUpdate

        # Daten laden
        conn = sqlite3.connect("data.db")
        df_nv = pd.read_sql("SELECT * FROM non_video", conn)
        df_hr = pd.read_sql("SELECT * FROM hr_non_bewegt", conn)
        conn.close()
        df = pd.concat([df_nv, df_hr], ignore_index=True)

        # Single Parquet
        if not split_dims:
            buf = BytesIO()
            df.to_parquet(buf, index=False, engine="pyarrow")
            buf.seek(0)
            return dcc.send_bytes(buf.getvalue(), "nonvideo.parquet")

        # Optional: split per MM-Dimension und ZIP mehrere Parquets
        import zipfile
        zip_buf = BytesIO()
        with zipfile.ZipFile(zip_buf, mode="w") as zf:
            combos = df[split_dims].drop_duplicates()
            for _, key_row in combos.iterrows():
                mask = True
                parts = []
                for dim in split_dims:
                    val = key_row[dim]
                    mask &= (df[dim] == val)
                    parts.append(f"{dim}-{val}")
                sub = df[mask]
                parquet_buf = BytesIO()
                sub.to_parquet(parquet_buf, index=False, engine="pyarrow")
                parquet_buf.seek(0)
                fname = "_".join(parts) + ".parquet"
                zf.writestr(fname, parquet_buf.read())
        zip_buf.seek(0)
        return dcc.send_bytes(zip_buf.getvalue(), "nonvideo_parquets.zip")
