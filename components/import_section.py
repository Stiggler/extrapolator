from dash import dcc, html, dash_table

def import_tab():
    return dcc.Tab(label="Import", children=[
        html.H1("Excel Daten Import Tool"),
        html.Div([
            html.Label("Import-Modus:"),
            dcc.RadioItems(
                id="mode-radio",
                options=[
                    {"label": "Append", "value": "append"},
                    {"label": "Replace", "value": "replace"}
                ],
                value="replace",
                labelStyle={'display': 'inline-block', 'margin-right': '10px'}
            )
        ], style={'margin-bottom': '10px'}),
        dcc.Upload(
            id="upload-data",
            children=html.Div(["Drag & Drop oder ", html.A("Dateien auswählen")]),
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
                'color': 'white',
                'background': '#73b8e6',
                'margin-bottom': '20px'
            }
        ),
        html.Div(id="status", style={'margin-bottom': '20px'}),
        html.H2("Importübersicht"),
        html.Div([
            html.Div([
                html.H3("Import Bewegtbild"),
                dash_table.DataTable(
                    id="aggregated-table-1",
                    columns=[],
                    data=[],
                    style_table={'overflowX': 'auto'},
                    style_cell={'textAlign': 'left'},
                    style_header={
                        'backgroundColor': '#73b8e6',
                        'color': 'white'
                    }
                )
            ], style={'width': '33%', 'display': 'inline-block', 'vertical-align': 'top', 'margin-right': '20px'}),
            html.Div([
                html.H3("Import Nicht-Bewegtbild"),
                dash_table.DataTable(
                    id="aggregated-table-2",
                    columns=[],
                    data=[],
                    style_table={'overflowX': 'auto'},
                    style_cell={'textAlign': 'left'},
                    style_header={
                        'backgroundColor': '#73b8e6',
                        'color': 'white'
                    }
                )
            ], style={'width': '48%', 'display': 'inline-block', 'vertical-align': 'top'})
        ])
    ])
