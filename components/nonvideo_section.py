from dash import dcc, html, dash_table

def nonvideo_tab():
    return dcc.Tab(label="Nicht-Bewegtbild", children=[
        dcc.Tabs([
            dcc.Tab(label="Hochrechnung", value="hochrechnung_nbv", children=[
                html.H1("Nicht-Bewegtbild – Hochrechnung"),
                html.Div([
                    html.Div([
                        html.H3("MM-Dimensionen (Non-Video)"),
                        dcc.Dropdown(id='mm-dimensions2', multi=True, placeholder="Wählen Sie MM-Dimensionen...",
                                    options=[{'label': col, 'value': col} for col in [
                                        'media', 'region', 'country', 'broadcaster', 'channel', 'genre', 'sports',
                                        'competition', 'season', 'event', 'venue', 'event_country', 'channel_type',
                                        'post_type', 'owned_channel', 'discipline', 'j1', 'j2', 'j3', 'j4', 'j5',
                                        'hr1', 'hr2', 'hr3', 'hr4', 'hr5']])
                    ], style={'width': '48%', 'display': 'inline-block', 'padding-right': '2%'}),
                    html.Div([
                        html.H3("EA-Dimensionen (Non-Video)"),
                        dcc.Dropdown(id='ea-dimensions2', multi=True, placeholder="Wählen Sie EA-Dimensionen...",
                                    options=[{'label': col, 'value': col} for col in [
                                        'company', 'sponsor', 'tool', 'personal_sponsorship', 'tool_location']])
                    ], style={'width': '48%', 'display': 'inline-block'})
                ]),
                html.Br(),
                html.Button("Berechne Prozentwerte Non-Video", id="calculate-percentages2_nbv"),
                html.Button("Extrapolate Non-Video", id="extrapolate-nonvideo", style={'margin-left': '10px'}),
                html.Div(  id="extrapolate-nonvideo-status",
                        style={'display':'inline-block','margin-left':'10px'}),
                html.Button("Update Percentages", id="update-percentages-nbv", style={'margin-left': '10px'}),
                html.Div(id="update-nonvideo-percentages-status", style={'display': 'inline-block', 'margin-left': '10px'}),
                html.Div(id="nonvideo-percentages-status"),
                html.Div([
                    html.Button("🗑️ Zeile löschen", id="delete-nonvideo-percentages-rows"),
                    html.Button("Select all", id="select-all-nonvideo-rows", style={'margin-left': '6px'}),
                    html.Button("Deselect all", id="deselect-all-nonvideo-rows", style={'margin-left': '6px'}),
                    html.Button("📋 Zeilen duplizieren", id="duplicate-nonvideo-percentages-rows", style={'margin-left': '20px'}),
                    html.Label("Feld:"),
                    dcc.Dropdown(
                        id="field-selector-nonvideo",
                        options=[],  # wird per Callback befüllt
                        placeholder="Feld auswählen",
                        style={'width': '150px', 'display': 'inline-block', 'margin-left': '10px'}
                    ),
                    html.Label("Wert:"),
                    dcc.Input(
                        id="field-value-nonvideo",
                        type="text",
                        style={'width': '150px', 'margin-left': '10px'}
                    ),
                    html.Button("Wert übernehmen", id="apply-field-value-nonvideo", style={'margin-left': '10px'})
                ], style={'margin-top': '10px', 'display': 'flex', 'flex-wrap': 'wrap', 'gap': '10px'}),

                # DataTable mit Mehrfachauswahl, Filter und Sort
                dash_table.DataTable(
                    id="nonvideo-percentages-table",
                    columns=[],  # wird per Callback befüllt
                    data=[],
                    editable=True,
                    row_selectable="multi",
                    selected_rows=[],
                    filter_action="native",
                    sort_action="native",
                    style_table={'overflowX': 'auto'}
                )


            ]),
            dcc.Tab(label="Ergebnisse", value="ergebnisse_nbv", children=[
                html.H1("Nicht-Bewegtbild – Ergebnisse"),
                html.Div([
                    html.Div([
                        html.H3("MM-Dimensionen Ergebnisse"),
                        dcc.Dropdown(
                            id='mm-dimensions-results',
                            multi=True,
                            placeholder="Wählen Sie MM-Dimensionen für Ergebnisse...",
                            options=[{'label': col, 'value': col} for col in [
                                'media', 'region', 'country', 'broadcaster', 'channel', 'genre', 'sports',
                                'competition', 'season', 'event', 'venue', 'event_country',
                                'j1', 'j2', 'j3', 'j4', 'j5', 'hr1', 'hr2', 'hr3', 'hr4', 'hr5']]
                        )
                    ], style={'width': '48%', 'display': 'inline-block'}),
                    html.Div([
                        html.H3("EA-Dimensionen Ergebnisse"),
                        dcc.Dropdown(
                            id='ea-dimensions-results',
                            multi=True,
                            placeholder="Wählen Sie EA-Dimensionen für Ergebnisse...",
                            options=[{'label': col, 'value': col} for col in [
                                'company', 'sponsor', 'tool', 'personal_sponsorship', 'tool_location']]
                        )
                    ], style={'width': '48%', 'display': 'inline-block'})
                ]),
                html.Div([
                    html.H3("Filter hr_basis"),
                    dcc.Dropdown(
                        id='hr-basis-filter',
                        options=[
                            {'label': 'Alle', 'value': 'all'},
                            {'label': 'Basis', 'value': 'Basis'},
                            {'label': 'HR', 'value': 'HR'}
                        ],
                        value='all',
                        clearable=False
                    )
                ], style={'width': '30%', 'margin-top': '10px'}),
                html.Button("Berechne Ergebnisse Non-Video", id="calculate-results-nonvideo", style={'margin-top': '10px'}),
                html.Div(id="nonvideo-results-status", style={'margin-top': '10px'}),
                dash_table.DataTable(
                    id="nonvideo-results-table",
                    columns=[],
                    data=[],
                    style_table={'overflowX': 'auto'},
                    style_cell={'textAlign': 'left'}
                ),
                dcc.Graph(id="nonvideo-pie"),
                html.Button("Export Nicht-Bewegtbild", id="export-nonvideo-button", style={'margin-top': '10px'}),
                dcc.Download(id="download1")
            ]),
            dcc.Tab(label="Basecheck", value="basecheck_nbv", children=[
                html.H1("Nicht-Bewegtbild – Basecheck"),
                html.Div([
                    html.Div([
                        html.H3("MM-Dimensionen"),
                        dcc.Dropdown(
                            id="mm-dimensions-basecheck-nbv",
                            multi=True,
                            placeholder="Wählen Sie MM-Dimensionen...",
                            options=[{'label': col, 'value': col} for col in [
                                'media', 'region', 'country', 'broadcaster', 'channel', 'genre',
                                'sports', 'competition', 'season', 'event', 'venue', 'event_country',
                                'post_type', 'owned_channel', 'j1', 'j2', 'j3', 'j4', 'j5',
                                'hr1', 'hr2', 'hr3', 'hr4', 'hr5']]
                        )
                    ], style={'width': '50%'}),
                    html.Button("Berechne Basecheck", id="calculate-basecheck-nbv", style={'margin-top': '10px'})
                ]),
                html.Div(id="basecheck-status-nbv", style={'margin-top': '10px'}),
                dash_table.DataTable(
                    id="basecheck-table-nbv",
                    columns=[],
                    data=[],
                    merge_duplicate_headers=True,
                    style_table={'overflowX': 'auto'},
                    style_cell={'textAlign': 'left'}
                )
            ])

        ], id="nicht-bewegtbild-subtabs", value="hochrechnung_nbv")
    ])
