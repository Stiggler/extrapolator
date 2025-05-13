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
            html.Button("Prozentwerte", id="calculate-percentages"),
            html.Button("Extrapolate", id="extrapolate", style={'margin-left': '10px'}),
            html.Button("Update Percentages", id="update-percentages", style={'margin-left': '10px'}),
            html.Div(id="percentages-status"),
            html.Div(id="update-percentages-status"),
            html.Div(id="extrapolate-status"),
            dash_table.DataTable(
                id="percentages-table",
                columns=[],
                data=[],
                editable=True,
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
                    style_table={'overflowX': 'auto'},
                    style_cell={'textAlign': 'left'}
                )
            ])
        ], id="bewegtbild-subtabs", value="hochrechnung")
    ])
