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
                html.Div(id="nonvideo-percentages-status"),
                html.Div(id="extrapolate-nonvideo-status"),
                dash_table.DataTable(
                    id="nonvideo-percentages-table",
                    columns=[],
                    data=[],
                    editable=False,
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
                html.Div("Platzhalter – spätere Erweiterung möglich.")
            ])
        ], id="nicht-bewegtbild-subtabs", value="hochrechnung_nbv")
    ])
