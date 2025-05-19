from dash import dcc, html, dash_table

def video_tab():
    return dcc.Tab(label="Bewegtbild", children=[
                dcc.Tabs([
                    dcc.Tab(label="Hochrechnung", value="hochrechnung", children=[
            html.H1("Bewegtbild – Hochrechnung"),
            html.Div([
                html.Div([
                    html.H3("MM-Dimensionen"),
                    dcc.Dropdown(id='mm-dimensions', multi=True, placeholder="Wählen Sie MM-Dimensionen...",
                                options=[
                                    {'label': col, 'value': col} for col in [
                                        'media', 'region', 'country', 'broadcaster', 'channel', 'genre', 'sports',
                                        'competition', 'season', 'event', 'venue', 'event_country', 'post_type',
                                        'owned_channel', 'discipline', 'j1', 'j2', 'j3', 'j4', 'j5', 'hr1', 'hr2',
                                        'hr3', 'hr4', 'hr5']
                                ])
                ], style={'width': '48%', 'display': 'inline-block', 'padding-right': '2%'}),
                html.Div([
                    html.H3("EA-Dimensionen"),
                    dcc.Dropdown(id='ea-dimensions', multi=True, placeholder="Wählen Sie EA-Dimensionen...",
                                options=[
                                    {'label': col, 'value': col} for col in [
                                        'company', 'sponsor', 'tool', 'personal_sponsorship', 'tool_location']
                                ])
                ], style={'width': '48%', 'display': 'inline-block'})
            ]),
            html.Br(),
            html.Div([
                html.Button("🗑️ Zeile löschen", id="delete-percentages-rows", style={'font-size': '12px', 'padding': '4px 8px'}),
                html.Button("Select all", id="select-all-visible-rows", style={'font-size': '12px', 'padding': '4px 8px'}),
                html.Button("Deselect all", id="deselect-all-rows", style={'font-size': '12px', 'padding': '4px 8px', 'margin-left': '6px'}),
                html.Button("📋 Zeilen duplizieren", id="duplicate-percentages-rows", style={'margin-right': '20px'}),
                html.Label("Feld:"),
                dcc.Dropdown(id="field-selector", placeholder="Feld auswählen", style={'width': '150px', 'display': 'inline-block'}),
                html.Label("Wert:"),
                dcc.Input(id="field-value", type="text", style={'width': '150px', 'margin-left': '10px'}),
                html.Button("Wert übernehmen", id="apply-field-value", style={'margin-left': '10px'})
            ], style={'margin-top': '10px', 'display': 'flex', 'flex-wrap': 'wrap', 'gap': '10px'}),
            html.Button("Prozentwerte", id="calculate-percentages", style={'margin-top': '10px'}),
            html.Button("Extrapolate", id="extrapolate", style={'margin-left': '10px'}),
            html.Button("Update Percentages", id="update-percentages", style={'margin-left': '10px'}),
            html.Div(id="percentages-status"),
            html.Div(id="update-percentages-status"),
            html.Div(id="extrapolate-status"),
            html.Div([
                html.Button("📤 Exportieren", id="export-percentages-button", style={'font-size': '12px', 'padding': '4px 8px'}),
                dcc.Download(id="download-percentages"),
                dcc.Upload(
                    id="import-percentages-upload",
                    children=html.Button("📥 Importieren", style={'font-size': '12px', 'padding': '4px 8px', 'margin-left': '6px'}),
                    multiple=False,
                    accept=".xlsx"
                )
            ], style={'margin-top': '10px', 'display': 'flex', 'gap': '10px'}),

            html.Div(id="import-percentages-status", style={"font-size": "12px", "margin-top": "4px", "margin-left": "6px"}),

            dash_table.DataTable(
                id="percentages-table",
                columns=[],
                data=[],
                editable=True,
                row_selectable="multi",
                selected_rows=[],
                 filter_action="native",         # ✅ Filter aktivieren
                sort_action="native",           # ✅ Sortieren aktivieren      
                style_table={'overflowX': 'auto'}
            )
        ])
,
            dcc.Tab(label="Ergebnisse", value="ergebnisse", children=[
                html.H1("Bewegtbild – Ergebnisse"),
                html.Div([
                    html.Div([
                        html.H3("MM-Dimensionen Ergebnisse"),
                        dcc.Dropdown(
                            id='mm-dimensions-results-video',
                            multi=True,
                            placeholder="Wählen Sie MM-Dimensionen für Ergebnisse...",
                            options=[{'label': col, 'value': col} for col in [
                                'media', 'region', 'country', 'broadcaster', 'channel', 'genre', 'sports',
                                'competition', 'season', 'event', 'venue', 'event_country',
                                'hr1', 'hr2', 'hr3', 'hr4', 'hr5']]
                        )
                    ], style={'width': '48%', 'display': 'inline-block'}),
                    html.Div([
                        html.H3("EA-Dimensionen Ergebnisse"),
                        dcc.Dropdown(
                            id='ea-dimensions-results-video',
                            multi=True,
                            placeholder="Wählen Sie EA-Dimensionen für Ergebnisse...",
                            options=[{'label': col, 'value': col} for col in [
                                'company', 'sponsor', 'tool', 'personal_sponsorship', 'tool_location']]
                        )
                    ], style={'width': '48%', 'display': 'inline-block'})
                ]),
                html.Button("Berechne Ergebnisse", id="calculate-results", style={'margin-top': '10px'}),
                html.Button("Tabelle", id="calculate-results2", style={'margin-left': '10px'}),
                html.Button("Export", id="export-button", style={'margin-left': '10px'}),
                html.Div(id="results-status", style={'margin-top': '10px'}),
                dcc.Download(id="download"),
                dash_table.DataTable(
                    id="results-table",
                    columns=[],
                    data=[],
                    style_table={'overflowX': 'auto'},
                    style_cell={'textAlign': 'left'}
                )
            ]),
            dcc.Tab(label="Basecheck", value="basecheck", children=[
                html.H1("Bewegtbild – Basecheck"),
                html.Div([
                    html.H3("MM-Dimensionen (Basecheck)"),
                    dcc.Dropdown(
                        id='mm-dimensions-basecheck',
                        multi=True,
                        placeholder="Wählen Sie MM-Dimensionen...",
                        options=[{'label': col, 'value': col} for col in [
                            'media', 'region', 'country', 'broadcaster', 'channel', 'genre', 'sports',
                            'competition', 'season', 'event', 'venue', 'event_country', 'post_type',
                            'owned_channel', 'discipline', 'j1', 'j2', 'j3', 'j4', 'j5', 'hr1', 'hr2',
                            'hr3', 'hr4', 'hr5']]
                    )
                ]),
                html.Button("Berechne Basecheck", id="calculate-basecheck", style={'margin-top': '10px'}),
                html.Div(id="basecheck-status", style={'margin-top': '10px'}),
                dash_table.DataTable(
                    id="basecheck-table",
                    columns=[],
                    data=[],
                    merge_duplicate_headers=True,
                    style_table={'overflowX': 'auto'},
                    style_cell={'textAlign': 'left'}
                )
            ])
        ], id="bewegtbild-subtabs", value="hochrechnung")
    ])
