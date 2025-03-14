import base64
import io
import sqlite3
import pandas as pd
from dash import Dash, dcc, html, dash_table, Input, Output, State
import math
from io import BytesIO
import openpyxl
from openpyxl.utils import get_column_letter

app = Dash(__name__)

# ---------------- Hilfsfunktionen ----------------

def convert_timedelta_to_decimal(td):
    """Konvertiert einen Timedelta in den Anteil eines Tages.
       Falls td NaT ist, wird None zurückgegeben."""
    if pd.isnull(td):
        return None
    return td.total_seconds() / 86400

def decimal_to_hms(decimal_val):
    """
    Konvertiert einen Dezimalwert (Bruchteil eines Tages) in das Format h:mm:ss.
    Ist der Wert leer oder NaN, wird ein leerer String zurückgegeben.
    """
    if pd.isnull(decimal_val):
        return ""
    total_seconds = decimal_val * 86400
    total_seconds = int(round(total_seconds))
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    seconds = total_seconds % 60
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}"

# Umrechnung von h:mm:ss in einen Dezimalwert (Anteil eines Tages)
def hms_to_decimal(hms_str):
    try:
        parts = hms_str.split(':')
        if len(parts) != 3:
            return 0.0
        hours = float(parts[0])
        minutes = float(parts[1])
        seconds = float(parts[2])
        total_seconds = hours * 3600 + minutes * 60 + seconds
        return total_seconds / 86400
    except Exception:
        return 0.0

def parse_contents(contents, filename):
    """
    Dekodiert den Base64-String und liest mit pandas das Excel-Blatt "data" ein.
    Dabei werden broadcasting_time und visibility in Dezimalzahlen (Tagesanteil) umgewandelt,
    falls sie als Timedelta eingelesen wurden.
    """
    content_type, content_string = contents.split(',')
    decoded = base64.b64decode(content_string)
    try:
        df = pd.read_excel(
            io.BytesIO(decoded),
            sheet_name="data",
            engine="openpyxl",
            converters={
                'season': lambda x: str(int(x.toordinal() - pd.Timestamp("1899-12-30").toordinal()))
                        if isinstance(x, pd.Timestamp) else str(int(x)) if isinstance(x, (int, float)) else str(x)
            }
        )
        if 'broadcasting_time' in df.columns and pd.api.types.is_timedelta64_dtype(df['broadcasting_time']):
            df['broadcasting_time'] = df['broadcasting_time'].apply(convert_timedelta_to_decimal)
        if 'visibility' in df.columns and pd.api.types.is_timedelta64_dtype(df['visibility']):
            df['visibility'] = df['visibility'].apply(convert_timedelta_to_decimal)
        if 'apt' in df.columns and pd.api.types.is_timedelta64_dtype(df['apt']):
            df['apt'] = df['apt'].apply(convert_timedelta_to_decimal)            
        if 'program_duration' in df.columns and pd.api.types.is_timedelta64_dtype(df['program_duration']):
            df['program_duration'] = df['program_duration'].apply(convert_timedelta_to_decimal)           
        if 'start_time_program' in df.columns and pd.api.types.is_timedelta64_dtype(df['start_time_program']):
            df['start_time_program'] = df['start_time_program'].apply(convert_timedelta_to_decimal)  
        if 'end_time_program' in df.columns and pd.api.types.is_timedelta64_dtype(df['end_time_program']):
            df['end_time_program'] = df['end_time_program'].apply(convert_timedelta_to_decimal)  
        if 'start_time_item' in df.columns and pd.api.types.is_timedelta64_dtype(df['start_time_item']):
            df['start_time_item'] = df['start_time_item'].apply(convert_timedelta_to_decimal)
        if 'season' in df.columns:
            df['season'] = df['season'].apply(lambda x: str(int(x)) if isinstance(x, (float, int)) else str(x))
                           
        return df
    except Exception as e:
        print(f"Fehler beim Einlesen von {filename}: {e}")
        return None

def update_database(df, mode, first_file):
    """
    Schreibt den DataFrame in die SQLite-Datenbank "data.db".
    Bei der ersten Datei wird je nach Modus "replace" oder "append" verwendet.
    Für weitere Dateien wird immer angehängt.
    """
    db_path = 'data.db'
    conn = sqlite3.connect(db_path)
    if first_file:
        if_exists_option = "replace" if mode == "replace" else "append"
    else:
        if_exists_option = "append"
    df.to_sql("data", conn, if_exists=if_exists_option, index=False)
    conn.close()

def get_aggregated_data():
    """
    Aggregation für TV/OTT & Social Media (Video):
      - Filter: media = 'TV/OTT' oder (media = 'Social Media' und post_type = 'Video')
      - Gruppierung nach hr_basis
      - Kennzahlen:
            • COUNT(DISTINCT bid) als distinct_bid
            • SUM(visibility) als sum_visibility
            • SUM(broadcasting_time) (nur für Zeilen, bei denen tool leer ist) als sum_broadcasting_time
    Anschließend werden die Zeitwerte ins Format h:mm:ss konvertiert.
    """
    db_path = 'data.db'
    conn = sqlite3.connect(db_path)
    query = """
    SELECT 
        TRIM(hr_basis) AS hr_basis,
        COUNT(DISTINCT bid) AS distinct_bid,
        SUM(visibility) AS sum_visibility,
        SUM(CASE WHEN tool IS NULL OR tool = '' THEN broadcasting_time ELSE 0 END) AS sum_broadcasting_time
    FROM data
    WHERE (media = 'TV/OTT' OR (media = 'Social Media' AND post_type = 'Video'))
    GROUP BY TRIM(hr_basis);
    """
    df = pd.read_sql(query, conn)
    conn.close()
    if not df.empty:
        df['sum_visibility'] = df['sum_visibility'].apply(decimal_to_hms)
        df['sum_broadcasting_time'] = df['sum_broadcasting_time'].apply(decimal_to_hms)
    return df

def get_aggregated_data_opposite():
    """
    Aggregation für Print, Online & Social Media (nicht Video):
      - Filter: media IN ('Print', 'Online', 'Social Media') und post_type <> 'Video'
      - Gruppierung nach hr_basis
      - Kennzahlen:
            • COUNT(DISTINCT bid) als distinct_bid
            • SUM(mentions) als sum_mentions
    """
    db_path = 'data.db'
    conn = sqlite3.connect(db_path)
    query = """
    SELECT 
        TRIM(hr_basis) AS hr_basis,
        COUNT(DISTINCT bid) AS distinct_bid,
        SUM(mentions) AS sum_mentions
    FROM data
    WHERE media IN ('Print', 'Online', 'Social Media')
      AND post_type <> 'Video'
    GROUP BY TRIM(hr_basis);
    """
    df = pd.read_sql(query, conn)
    conn.close()
    return df

# ---------------- Layout mit Tabs ----------------

app.layout = html.Div([
    dcc.Tabs([
        dcc.Tab(label="Import", children=[
            html.H1("Excel Daten Import Tool"),
            html.Div([
                html.Label("Import-Modus:"),
                dcc.RadioItems(
                    id="mode-radio",
                    options=[
                        {"label": "Append", "value": "append"},
                        {"label": "Replace", "value": "replace"}
                    ],
                    value="append",
                    labelStyle={'display': 'inline-block', 'margin-right': '10px'}
                )
            ], style={'margin-bottom': '20px'}),
            dcc.Upload(
                id="upload-data",
                children=html.Div([
                    "Drag & Drop oder ",
                    html.A("Dateien auswählen")
                ]),
                multiple=True,
                accept=".xlsx",
                style={
                    'width': '100%',
                    'height': '60px',
                    'lineHeight': '60px',
                    'borderWidth': '1px',
                    'borderStyle': 'dashed',
                    'borderRadius': '5px',
                    'textAlign': 'center',
                    'margin-bottom': '20px'
                }
            ),
            html.Div(id="status", style={'margin-bottom': '20px'}),
            html.H2("Aggregierte Datenanzeige"),
            html.Div([
                html.Div([
                    html.H3("TV/OTT & Social Media (Video)"),
                    dash_table.DataTable(
                        id="aggregated-table-1",
                        columns=[],
                        data=[],
                        style_table={'overflowX': 'auto'},
                        style_cell={'textAlign': 'left'}
                    )
                ], style={'width': '48%', 'display': 'inline-block', 'vertical-align': 'top'}),
                html.Div([
                    html.H3("Print, Online & Social Media (nicht Video)"),
                    dash_table.DataTable(
                        id="aggregated-table-2",
                        columns=[],
                        data=[],
                        style_table={'overflowX': 'auto'},
                        style_cell={'textAlign': 'left'}
                    )
                ], style={'width': '48%', 'display': 'inline-block', 'vertical-align': 'top'})
            ])
        ]),
        dcc.Tab(label="Bewegtbild", children=[
            dcc.Tabs([
                dcc.Tab(label="Hochrechnung", children=[
                    html.H1("Bewegtbild – Hochrechnung"),
                    html.Button("DB erstellen", id="create-db-video", style={'backgroundColor': 'blue', 'color': 'white'}),
                    html.Div(id="create-db-status", style={'margin-top': '10px'}),
                    html.Br(),
                    html.Div([
                        html.Div([
                            html.H3("MM-Dimensionen"),
                            dcc.Dropdown(
                                id='mm-dimensions',
                                options=[
                                    {'label': 'media', 'value': 'media'},
                                    {'label': 'region', 'value': 'region'},
                                    {'label': 'country', 'value': 'country'},
                                    {'label': 'broadcaster', 'value': 'broadcaster'},
                                    {'label': 'channel', 'value': 'channel'},
                                    {'label': 'genre', 'value': 'genre'},
                                    {'label': 'sports', 'value': 'sports'},
                                    {'label': 'competition', 'value': 'competition'},
                                    {'label': 'season', 'value': 'season'},
                                    {'label': 'event', 'value': 'event'},
                                    {'label': 'venue', 'value': 'venue'},
                                    {'label': 'event_country', 'value': 'event_country'},
                                    {'label': 'post_type', 'value': 'post_type'},
                                    {'label': 'owned_channel', 'value': 'owned_channel'},
                                    {'label': 'discipline', 'value': 'discipline'},
                                    {'label': 'j1', 'value': 'j1'},
                                    {'label': 'j2', 'value': 'j2'},
                                    {'label': 'j3', 'value': 'j3'},
                                    {'label': 'j4', 'value': 'j4'},
                                    {'label': 'j5', 'value': 'j5'},
                                    {'label': 'hr1', 'value': 'hr1'},
                                    {'label': 'hr2', 'value': 'hr2'},
                                    {'label': 'hr3', 'value': 'hr3'},
                                    {'label': 'hr4', 'value': 'hr4'},
                                    {'label': 'hr5', 'value': 'hr5'}
                                ],
                                multi=True,
                                placeholder="Wählen Sie MM-Dimensionen..."
                            )
                        ], style={'width': '48%', 'display': 'inline-block', 'vertical-align': 'top', 'padding-right': '2%'}),
                        html.Div([
                            html.H3("EA-Dimensionen"),
                            dcc.Dropdown(
                                id='ea-dimensions',
                                options=[
                                    {'label': 'company', 'value': 'company'},
                                    {'label': 'sponsor', 'value': 'sponsor'},
                                    {'label': 'tool', 'value': 'tool'},
                                    {'label': 'personal_sponsorship', 'value': 'personal_sponsorship'},
                                    {'label': 'tool_location', 'value': 'tool_location'}
                                ],
                                multi=True,
                                placeholder="Wählen Sie EA-Dimensionen..."
                            )
                        ], style={'width': '48%', 'display': 'inline-block', 'vertical-align': 'top'})
                    ]),
                    html.Br(),
                    html.Button("Prozentwerte", id="calculate-percentages", style={'backgroundColor': 'green', 'color': 'white'}),
                    html.Div(id="percentages-status", style={'margin-top': '10px'}),
                    html.Br(),
                    html.Button("Extrapolate", id="extrapolate", style={'backgroundColor': 'purple', 'color': 'white'}),
                    html.Div(id="extrapolate-status", style={'margin-top': '10px'}),
                    html.Br(),
                    html.Button("Update Percentages", id="update-percentages", style={'backgroundColor': 'orange', 'color': 'white'}),
                    html.Div(id="update-percentages-status", style={'margin-top': '10px'}),
                    html.Br(),
                    dash_table.DataTable(
                        id="percentages-table",
                        columns=[],  # Diese werden dynamisch gesetzt
                        data=[],     # Diese werden dynamisch gesetzt
                        editable=True,
                        filter_action="native",
                        sort_action="native",
                        sort_mode="multi",
                        style_table={'overflowX': 'auto'},
                        style_cell={'textAlign': 'left'}
                    )
                ]),
                # Im Layout (z. B. im Tab "Ergebnisse") ergänzen:
                dcc.Tab(label="Ergebnisse", children=[
                    html.H1("Bewegtbild – Ergebnisse"),
                    html.Button("Berechne Ergebnisse", id="calculate-results", style={'backgroundColor': 'darkblue', 'color': 'white'}),
                    html.Button("Export", id="export-button", style={'backgroundColor': 'darkgreen', 'color': 'white', 'margin-left': '10px'}),
                    html.Div(id="results-status", style={'margin-top': '10px'}),
                    dcc.Download(id="download"),
                    html.Div("Platzhalter – hier folgen später Charts und weitere Visualisierungen.")
                ])
            ])
        ]),
        dcc.Tab(label="Nicht-Bewegtbild", children=[
            html.H1("Nicht-Bewegtbild"),
            html.Div("Platzhalter – hier folgt in Kürze die Implementierung.")
        ])
    ])
])

# ---------------- Callback: Datenimport und Aggregation ----------------

@app.callback(
    [Output("status", "children"),
     Output("aggregated-table-1", "data"),
     Output("aggregated-table-1", "columns"),
     Output("aggregated-table-2", "data"),
     Output("aggregated-table-2", "columns")],
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
        df_agg1 = get_aggregated_data()
        if not df_agg1.empty:
            columns1 = [{"name": col, "id": col} for col in df_agg1.columns]
            data1 = df_agg1.to_dict("records")
        else:
            columns1 = []
            data1 = []
        df_agg2 = get_aggregated_data_opposite()
        if not df_agg2.empty:
            columns2 = [{"name": col, "id": col} for col in df_agg2.columns]
            data2 = df_agg2.to_dict("records")
        else:
            columns2 = []
            data2 = []
        return html.Div([html.Div(msg) for msg in status_messages]), data1, columns1, data2, columns2
    return "", [], [], [], []

# ---------------- Callback: Neue Tabelle "video" in data.db erstellen ----------------

@app.callback(
    Output("create-db-status", "children"),
    Input("create-db-video", "n_clicks")
)
def create_video_db(n_clicks):
    if not n_clicks:
        return ""
    db_path = "data.db"
    conn = sqlite3.connect(db_path)
    query = """
    SELECT *
    FROM data
    WHERE (media = 'TV/OTT' OR (media = 'Social Media' AND post_type = 'Video'))
    """
    df = pd.read_sql(query, conn)
    conn.close()
    conn = sqlite3.connect(db_path)
    df.to_sql("video", conn, if_exists="replace", index=False)
    conn.close()
    return f"Tabelle 'video' in data.db erstellt: {len(df)} Zeilen wurden gespeichert."

# ---------------- Callback: Prozentwerte berechnen und in Tabelle "percent" speichern ----------------


@app.callback(
    [Output("percentages-status", "children"),
     Output("percentages-table", "data"),
     Output("percentages-table", "columns")],
    Input("calculate-percentages", "n_clicks"),
    State("mm-dimensions", "value"),
    State("ea-dimensions", "value")
)
def calculate_percentages(n_clicks, mm_dims, ea_dims):
    if not n_clicks:
        return "", [], []
    group_by_cols = []
    if mm_dims:
        group_by_cols.extend(mm_dims)
    if ea_dims:
        group_by_cols.extend(ea_dims)
    if not group_by_cols:
        return "Bitte wählen Sie mindestens eine Dimension aus.", [], []
    group_by_clause = ", ".join(group_by_cols)
    if mm_dims:
        join_condition = " AND ".join([f"v2.{dim} = v.{dim}" for dim in mm_dims])
    else:
        join_condition = "1=1"
    
    # Erweiterte Query: Zusätzlich wird COUNT(DISTINCT bid) als count_bid berechnet.
    query = f"""
    SELECT 
         {group_by_clause},
         COUNT(DISTINCT bid) AS count_bid,
         SUM(mentions) AS sum_mentions,
         SUM(visibility) AS sum_visibility,
         (
           SELECT SUM(CASE WHEN tool IS NULL OR tool = '' THEN broadcasting_time ELSE 0 END)
           FROM video AS v2
           WHERE v2.hr_basis = 'Basis'
             AND {join_condition}
         ) AS sum_broadcasting_time
    FROM video AS v
    WHERE hr_basis = 'Basis'
    GROUP BY {group_by_clause}
    """
    if ea_dims:
        having_conditions = " AND ".join([f"({dim} IS NULL OR {dim} = '')" for dim in ea_dims])
        query += f"\nHAVING NOT ({having_conditions})"
    
    db_path = "data.db"
    conn = sqlite3.connect(db_path)
    df_raw = pd.read_sql(query, conn)
    conn.close()
    
    if df_raw.empty:
        return "Keine Daten für die Berechnung gefunden.", [], []
    
    df = df_raw.copy()
    # Formatierung der Kennzahlen:
    df['sum_mentions'] = df['sum_mentions'].fillna(0).astype(int)
    df['sum_visibility_raw'] = df['sum_visibility']
    df['sum_broadcasting_time_raw'] = df['sum_broadcasting_time']
    df['sum_visibility'] = df['sum_visibility_raw'].apply(decimal_to_hms)
    df['sum_broadcasting_time'] = df['sum_broadcasting_time_raw'].apply(decimal_to_hms)
    df['visibility_share'] = df.apply(lambda row: f"{(row['sum_visibility_raw'] / row['sum_broadcasting_time_raw'] * 100):.2f}%"
                                      if row['sum_broadcasting_time_raw'] and row['sum_broadcasting_time_raw'] != 0 
                                      else "N/A", axis=1)
    # Berechnung von avg_mention = sum_visibility_raw / sum_mentions (ohne Rundung)
    df['avg_mention'] = df.apply(lambda row: row['sum_visibility_raw'] / row['sum_mentions'] 
                                  if row['sum_mentions'] != 0 else 0, axis=1)

    # Formatierung avg_mention als h:mm:ss (keine Rundung, alle Dezimalstellen beibehalten)
    df['avg_mention'] = df['avg_mention'].apply(decimal_to_hms)

    # Entferne count_bid aus dem finalen Output
    final_cols = group_by_cols + ["sum_mentions", "avg_mention", "sum_visibility", "sum_broadcasting_time", "visibility_share"]
    final_df = df[final_cols]
    columns = [{"name": col, "id": col, "editable": True if col in ["visibility_share", "avg_mention"] else False} for col in final_df.columns]
    data = final_df.to_dict("records")
    
    # Schreibe die Tabelle "percent" in die Datenbank:
    conn = sqlite3.connect(db_path)
    final_df.to_sql("percent", conn, if_exists="replace", index=False)
    conn.close()
    
    return "Berechnung erfolgreich.", data, columns


# ---------------- Callback: Aktualisierung der bearbeiteten Prozentwerte in der DB ----------------

@app.callback(
    Output("update-percentages-status", "children"),
    Input("update-percentages", "n_clicks"),
    State("percentages-table", "data")
)
def update_percentages_db(n_clicks, table_data):
    if not n_clicks:
        return ""
    df = pd.DataFrame(table_data)
    db_path = "data.db"
    conn = sqlite3.connect(db_path)
    df.to_sql("percent", conn, if_exists="replace", index=False)
    conn.close()
    return "Tabelle 'percent' wurde aktualisiert."

# ---------------- Callback: Hochrehnen ----------------

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
    # Lese alle HR-Zeilen aus der Tabelle video (hr_basis = 'HR')
    df_video = pd.read_sql("SELECT * FROM video WHERE hr_basis = 'HR'", conn)
    # Lese die Tabelle percent (enthält aggregierte Daten, inkl. visibility_share und avg_mention)
    df_percent = pd.read_sql("SELECT * FROM percent", conn)
    conn.close()
    
    if df_video.empty:
        return "Keine HR-Daten in der Tabelle video gefunden."
    if df_percent.empty:
        return "Keine Daten in der Tabelle percent gefunden."
    
    # Merge beider Tabellen anhand der ausgewählten MM-Dimensionen.
    # Dabei erhalten die Spalten aus video den Suffix "_video" und aus percent den Suffix "_percent"
    df_merged = pd.merge(df_video, df_percent, on=mm_dims, suffixes=("_video", "_percent"))
    
    # Überschreibe die Spalte visibility_share: Der Wert aus percent soll übernommen werden.
    df_merged["visibility_share"] = df_merged["visibility_share_percent"]
    
    # Hilfsfunktion zur Umrechnung eines Prozent-Strings in einen Faktor
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

    # Umrechnung: visibility_share als Faktor
    df_merged["visibility_share_factor"] = df_merged["visibility_share"].apply(convert_visibility_share)
    
    # Neue Berechnung: visibility = (visibility_share_factor) * (broadcasting_time aus video)
    # Hier verwenden wir den Wert aus der Spalte "broadcasting_time" (aus video)
    if "broadcasting_time" not in df_merged.columns:
        return "broadcasting_time aus video nicht gefunden."
    df_merged["visibility"] = df_merged["visibility_share_factor"] * df_merged["broadcasting_time"]
    
    # Wichtig: Da avg_mention in der percent-Tabelle als h:mm:ss formatiert vorliegt,
    # müssen wir diesen String wieder in einen numerischen Wert (Anteil eines Tages) umwandeln.
    def hms_to_decimal(hms_str):
        try:
            parts = hms_str.split(':')
            if len(parts) != 3:
                return 0.0
            hours = float(parts[0])
            minutes = float(parts[1])
            seconds = float(parts[2])
            total_seconds = hours * 3600 + minutes * 60 + seconds
            return total_seconds / 86400
        except Exception:
            return 0.0

    # Konvertiere die avg_mention-Spalte in einen numerischen Wert
    df_merged["avg_mention_numeric"] = df_merged["avg_mention"].apply(hms_to_decimal)
    
    # Berechne neue Mentions: mentions = visibility / avg_mention_numeric
    df_merged["mentions"] = df_merged["visibility"] / df_merged["avg_mention_numeric"]
    # Konvertiere in eine Ganzzahl; falls Ergebnis kleiner als 1, setze auf 1
    df_merged["mentions"] = df_merged["mentions"].apply(lambda x: int(x) if x >= 1 else 1)
    
    # Optional: Entferne Hilfsspalten, z. B. visibility_share_factor, avg_mention_numeric und visibility_share_percent
    df_merged.drop(columns=["visibility_share_factor", "avg_mention_numeric", "visibility_share_percent"], inplace=True)
    
    # Schreibe das Ergebnis in die Tabelle "hr_bewegt" in der Datenbank
    conn = sqlite3.connect(db_path)
    df_merged.to_sql("hr_bewegt", conn, if_exists="replace", index=False)
    conn.close()
    
    return f"Extrapolation abgeschlossen: {len(df_merged)} Zeilen wurden in 'hr_bewegt' erstellt."

# ---------------- Ergebnisse ----------------


@app.callback(
    Output("results-status", "children"),
    Input("calculate-results", "n_clicks")
)
def create_video_final(n_clicks):
    if not n_clicks:
        return ""
    db_path = "data.db"
    conn = sqlite3.connect(db_path)
    # Lade die gesamte Tabelle video
    df_video = pd.read_sql("SELECT * FROM video", conn)
    # Lade die gesamte Tabelle hr_bewegt
    df_hr = pd.read_sql("SELECT * FROM hr_bewegt", conn)
    conn.close()
    
    # Für die Tabelle hr_bewegt sollen die Felder sponsor_percent und tool_percent als sponsor bzw. tool verwendet werden.
    if "sponsor_percent" in df_hr.columns:
        df_hr["sponsor"] = df_hr["sponsor_percent"]
        df_hr.drop(columns=["sponsor_percent"], inplace=True)
    if "tool_percent" in df_hr.columns:
        df_hr["tool"] = df_hr["tool_percent"]
        df_hr.drop(columns=["tool_percent"], inplace=True)
    
    # Jetzt vereinigen wir beide DataFrames (Union-All, also vertikal aneinanderhängen)
    df_final = pd.concat([df_video, df_hr], ignore_index=True)
    
    # Schreibe den konsolidierten DataFrame in die neue Tabelle "video_final"
    conn = sqlite3.connect(db_path)
    df_final.to_sql("video_final", conn, if_exists="replace", index=False)
    conn.close()
    
    return f"Neue Tabelle 'video_final' erstellt: {len(df_final)} Zeilen."

# ---------------- Excel export video  ----------------


@app.callback(
    Output("download", "data"),
    Input("export-button", "n_clicks"),
    prevent_initial_call=True
)
def export_to_excel(n_clicks):
    if not n_clicks:
        return None
    db_path = "data.db"
    conn = sqlite3.connect(db_path)
    df = pd.read_sql("SELECT * FROM video_final", conn)
    conn.close()
    
    output = BytesIO()
    # Verwende den ExcelWriter als Kontextmanager
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name="VideoFinal")
        workbook = writer.book
        worksheet = writer.sheets["VideoFinal"]
        
        # Durchlaufe alle Spalten und wende die gewünschte Formatierung an:
        for i, col in enumerate(df.columns):
            col_letter = get_column_letter(i+1)
            # Für "reach": Zahl mit 2 Dezimalstellen
            if col.lower() == "reach":
                for cell in worksheet[col_letter][1:]:  # Überspringe den Header
                    cell.number_format = '0.00'
            # Für "broadcasting_time", "visibility" und "apt": Format h:mm:ss
            elif col.lower() in ["broadcasting_time", "visibility", "apt"]:
                for cell in worksheet[col_letter][1:]:
                    cell.number_format = 'h:mm:ss'
        # writer.save() ist hier nicht zwingend nötig, da der Kontextmanager das Speichern übernimmt.
    output.seek(0)
    # Sende die Bytes als Download zurück
    return dcc.send_bytes(output.getvalue(), "video_final.xlsx")




# ---------------- Main ----------------

if __name__ == '__main__':
    app.run_server(debug=True)
