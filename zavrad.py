import dash
import dash_core_components as dcc
import dash_html_components as html
import dash_bootstrap_components as dbc
import numpy as np
import plotly.graph_objs as go
import datetime
from dash.dependencies import Input, Output
from pymongo import MongoClient

import config

global data, data_dbm, driver_dbm, driver_trips, sorted_vr, speed, chosen_data, lat, lon, network_class
current_tab = 'tab-1'

cluster = MongoClient('mongodb://' + config.username + ':' + config.password + '@' + config.ip + ':' + config.port +
                      '/automotive_data?authSource=admin')
db = cluster['automotive_data']
trips_col = db['trips']
obd_col = db['obd_data']
drivers_col = db['drivers']

app = dash.Dash(__name__, external_stylesheets=[dbc.themes.PULSE])
app.title = 'Vizualizacija mobilnog signala'
server = app.server

opisi = {
    'dbm': html.Div([
        html.P('dBm je oznaka za razinu snage izračunatu u decibelima na 1 milivat (1 mW). Koristi se u '
               'radiokomunikacijskim i optičkim komunikacijama umjesto vata (W) zbog lakšeg prikaza s obzirom da '
               'vrlo velik raspon brojevnih vrijednosti snaga prebacuju u mali raspon brojevnih vrijednosti razina s '
               'kojima je lakše baratati i računati.'),
        html.P('Formula je: P(dBm) = 10 log(P(W) / 1mW'),
        html.P('Mobilni se signal računa u decibelima. Snaga signala nalazi se u rasponu između otprilike -30 dBm pa '
               'sve do -110 dBm. Što je broj veći (odnosno, bliže nuli) signal je jači. U praksi, sve iznad -85 dBm '
               'smatra se kvalitetnim signalom.'),
        html.P('Za 4G mrežu, koja je danas najzastupljenija, vrijedi sljedeća okvirna skala:'),
        html.P('[0 dBm, −80 dBm] ->	Odličan;  '
               '[-80 dBm, −90 dBm] -> Vrlo dobar;    '
               '[-90 dBm, −100 dBm]	-> Dobar;    '
               '[-100 dBm, −110 dBm] ->	OK;   '
               '[-110 dBm, −120 dBm] ->	Slab;   '
               '[-120 dBm, −130 dBm] ->	Nepostojeć')
    ],
        style={
            'font-size': '15pt'
        }),

    'asuLevel': html.Div([
        html.P('ASU ili "Arbitrary Strength Unit" je cijebrojna vrijednost koja nema mjernu jedinicu '
               'te koja odgovara snazi priljnenog mobilnog signala. Iz vrijednosti ASU-a je vrlo '
               'lagano izračunati stvarnu vrijednost jačine signala izmjerenog u dBm.'
               'Formule za ovaj izračun se razlikuju za različite mreže.'),
        html.P('Formula za GSM (2G) iznosi: dBm = 2 x ASU - 113, gdje je ASU '
               'vrijednost u intervalu od 0.31 do 99. Ovdje 99 označava nepoznatu '
               'vrijednost.'),
        html.P('Formula za UMTS (3G) iznosti: dbm = ASU - 115, gdje je ASU vrijednost '
               'u intervalu od 0.90 do 255. Ovdje 225 označava nepoznatu vrijednost.'),
        html.P('Formula za LTE (4G) iznost: (ASU - 143) < dBm < (ASU - 140), gdje je '
               'ASU vrijednost u interval od 0 do 97. Na dijagramu ispod, uglavnom '
               'prevladava 4G mreža, pa je zato ovaj interval najzastupljeniji'),
        html.P('Kod Android uređaja, GSM formula se često zna koristiti i za UMTS '
               'mrežu.'),
        html.P('Alati poput "Network Signal Info mogu direktno pokazati snagu signala '
               'u decibelima, a isto tako i u ASU vrijednosti.')
    ],
        style={
            'font-size': '15pt'
        }),
    'level': html.Div([
        html.P('Level je apstraktna vrijednost koja označava sveukupnu kvalitetu signala.'),
        html.P('Prikazuje se kao cjelobrojna vrijednost u intervalu od 0 do 4, gdje je 0 najlošija vrijednost te '
               'predstavlja jako loš ili nepostojeć signal, dok je 4 najbolja vrijednost te označava odličnu '
               'kvalitetu signala.')
    ]),
    'timingAdvance': html.Div([])
}

driver_options = []
drivers = drivers_col.find()

j = 0
for d in drivers:
    j += 1
    gender = 'M' if d['gender'] == 'male' else 'Ž'
    driver_options.append({'label': d['vehicle'] + ' ( ' + gender + ' )', 'value': d['androidId']})


def calculate_colors(sent_data):
    data_colors = []

    if chosen_data == 'dbm' or chosen_data == 'asuLevel':
        for el in sent_data:
            if el == 0:
                data_colors.append('white')
            elif el > -80:
                data_colors.append('green')
            elif el > -90:
                data_colors.append('limegreen')
            elif el > -100:
                data_colors.append('gold')
            elif el > -110:
                data_colors.append('orange')
            else:
                data_colors.append('red')

    if chosen_data == 'level':
        for el in sent_data:
            if el == 4:
                data_colors.append('green')
            elif el == 3:
                data_colors.append('limegreen')
            elif el == 2:
                data_colors.append('gold')
            elif el == 1:
                data_colors.append('orange')
            else:
                data_colors.append('red')

    return data_colors


app.layout = html.Div([
    html.Br(),
    html.Header([
        html.H1(children='Vizualizacija mobilnog signala',
                style={
                    'textAlign': 'center',
                    # 'background-image': 'url(https://image.freepik.com/free-vector/digital-mobile-telecommunication-tower'
                    #                     '-network-connection-background_1017-25469.jpg)',
                    # 'width': '626px',
                    # 'height': '357px'
                }
                )
    ]),

    html.Br(),
    html.Br(),

    html.Div([
        html.Div([
            html.H2(children='Izaberite vozača',
                    style={
                        'textAlign': 'center'
                    }),

            dcc.Dropdown(
                id='dropdown-drivers',
                options=driver_options,
            ),
        ],
            style={
                'width': '35%',
                'margin-left': '10%'
            }
        ),

    ]),

    html.Br(),

    html.Div(id='dd-drivers-output'),

    html.Br(),
    html.Br(),

    html.Div([
        html.Div(id='dd-output-container'),

        html.Br(),
        html.Br(),

        html.Div(id='tabs-content')
    ],
        style={
            'width': '90%',
            'height': '1400px',
            'margin-left': '5%'
        })
],
    style={
        'width': '100%',
        'height': '100%'
    })


@app.callback(Output('dd-drivers-output', 'children'), Input('dropdown-drivers', 'value'))
def render_content(value):
    global data, driver_trips

    trips = trips_col.find()
    driver_trips = []

    trip_options = []

    for trip in trips:
        if trip['mobileDeviceInfo']['androidId'] == value:
            start_time = trip['tripStartTimestamp'] / 1000.0
            start_time = datetime.datetime.fromtimestamp(start_time).strftime('%Y-%m-%d %H:%M:%S')
            trip_options.append({'label': start_time, 'value': trip['tripId']})
            driver_trips.append(trip['tripId'])

    data_names = []
    i = 0

    for key in opisi.keys():
        i += 1
        data_names.append({'label': str(i) + ". " + key, 'value': key})

    div = html.Div([
        html.Div([
            html.H2(children='Izaberite vožnju',
                    style={
                        'textAlign': 'center'
                    }),

            dcc.Dropdown(
                id='dropdown',
                options=trip_options
            ),
        ],
            style={
                'width': '35%',
                'margin-left': '10%'
            }
        ),

        html.Div([
            html.H2(children='Izaberite podatak mobilnog signala',
                    style={
                        'textAlign': 'center'
                    }),

            dcc.Dropdown(
                id='dropdown2',
                options=data_names
            ),

        ],
            style={
                'width': '35%',
                'margin-left': '10%'
            }
        ),
    ],
        style={
            'display': 'flex'
        }),
    return div


@app.callback(Output('dd-output-container', 'children'),
              [Input('dropdown', 'value'), Input('dropdown2', 'value')])
def render_content(value1, value2):
    global data, data_dbm, sorted_vr, speed, chosen_data, current_tab, lat, lon, network_class, driver_trips, driver_dbm

    if value1 and value2:

        chosen_data = value2

        vr = {}

        data = []
        data_dbm = []

        network_class = []
        speed = []

        lat = []
        lon = []

        obd = obd_col.find({'tripId': value1})

        test = []

        for o in obd:
            try:
                # Ako ovdje pukne, ne dodaji ga u polja
                test.append(o['signalData'][chosen_data])
                test.append(o['obdData']['SPEED'])
                test.append(o['signalData']['networkClass'])
                test.append(o['signalData']['dbm'])
                test.append(o['locationData']['latitude'])
                test.append(o['locationData']['longitude'])
                if o['signalData']['dbm'] != 0:
                    data.append(o['signalData'][chosen_data])
                    s = o['timestamp'] / 1000.0
                    vr[datetime.datetime.fromtimestamp(s).strftime('%Y-%m-%d %H:%M:%S.%f')] = o['signalData'][
                        chosen_data]
                    speed.append(o['obdData']['SPEED'])
                    network_class.append(o['signalData']['networkClass'])
                    data_dbm.append(o['signalData']['dbm'])
                    lat.append(o['locationData']['latitude'])
                    lon.append(o['locationData']['longitude'])

            except KeyError:
                print("Error on: ", j, value1)

        sorted_vr = {}
        for key in sorted(vr):
            sorted_vr[key] = vr[key]

        mean = 'Aritmetička sredina za ovu vožnju je ' + str(np.mean(data))
        median = 'Medijan za ovu vožnju je ' + str(np.median(data))
        std = 'Standardna devijacija za ovu vožnju je ' + str(np.std(data))

        div = html.Div([

            html.Div([
                html.H3(children=opisi[value2],
                        style={
                            'textAlign': 'center',
                            'padding': '10px 10px 10px 10px'
                        }
                        ),
            ]
            ),

            html.Br(),

            html.Div([
                html.H3(children=mean,
                        style={
                            'textAlign': 'center',
                            'font-size': '15pt'
                        }
                        ),

                html.H3(children=median,
                        style={
                            'textAlign': 'center',
                            'font-size': '15pt'
                        }
                        ),
                html.H3(children=std,
                        style={
                            'textAlign': 'center',
                            'font-size': '15pt'
                        }
                        )
            ],
                style={
                    'padding': '10px 10px 10px 10px'
                }),

            html.Br(),
            html.Br(),

            dcc.Tabs(id="tabs", value=current_tab, children=[
                dcc.Tab(label='Linijski dijagram ovisnosti podataka o vremenu', value='tab-1'),
                dcc.Tab(label='Dijagram ovisnosti podataka o brzini vožnje', value='tab-2'),
                dcc.Tab(label='Prikaz na karti za odabranu vožnju', value='tab-3'),
                dcc.Tab(label='Prikaz na karti za sve vožnje odabranog vozača', value='tab-4')
            ])
        ])
        return div

    return []


@app.callback(Output('tabs-content', 'children'), Input('tabs', 'value'))
def render_content(tab):
    global chosen_data, current_tab, lat, lon, driver_dbm, driver_trips, network_class
    current_tab = tab
    div = None
    if tab == 'tab-1':
        layout = go.Layout(
            height=700
        )

        fig = go.Figure(
            data=go.Scatter(x=list(sorted_vr.keys()), y=list(sorted_vr.values())),
            layout=layout
        )
        div = html.Div(
            children=[
                dcc.Graph(
                    id='world_map',
                    figure=fig
                )
            ]
        )

    elif tab == 'tab-2':
        div = html.Div([
            dcc.Graph(
                id='scatter_chart',
                figure={
                    'data': [
                        go.Scatter(
                            x=speed,
                            y=data,
                            mode='markers'
                        )
                    ],
                    'layout': go.Layout(
                        title=f'Scatter Plot for {chosen_data}',
                        xaxis={'title': 'Brzina vožnje [km/h]'},
                        yaxis={'title': f'{chosen_data}'},
                        hovermode='closest',
                        height=700
                    )
                }
            )
        ])

    elif tab == 'tab-3':
        data_colors = []
        if chosen_data == 'dbm' or chosen_data == 'asuLevel':
            data_colors = calculate_colors(data_dbm)
        elif chosen_data == 'level':
            data_colors = calculate_colors(data)
        map_data = go.Scattermapbox(
            name='RideMap',
            lon=lon,
            lat=lat,
            mode='markers',
            text=[chosen_data + ': ' + str(data[i]) + '<br>' + 'Network class: ' + network_class[i] for i in
                  range(len(data))],
            marker=go.scattermapbox.Marker(
                color=data_colors,
                opacity=1
            )
        )

        layout = go.Layout(
            autosize=True,
            height=700,
            mapbox=dict(
                accesstoken='pk.eyJ1IjoidG1hdGljIiwiYSI6ImNrbXhtamc0eDBxZXUycXBxaG94YmppbmUifQ.L7ulSrlC5mV_TwFD15k6sw',
                bearing=0,
                center=go.layout.mapbox.Center(
                    lat=46.01342639395872,
                    lon=16.400215918042534,
                ),
                pitch=0,
                zoom=9
            )

        )
        fig_data = [map_data]
        fig = go.Figure(data=fig_data, layout=layout)
        div = html.Div(
            children=[
                dcc.Graph(
                    id='zagreb-map',
                    figure=fig
                )
            ]
        )

    elif tab == 'tab-4':
        driver_dbm = []
        driver_chosen = []
        network_class2 = []
        lon2 = []
        lat2 = []

        for t in driver_trips:
            obd = obd_col.find({'tripId': t})
            for o in obd:
                try:
                    if o['signalData']['dbm'] != 0:
                        network_class2.append(o['signalData']['networkClass'])
                        driver_dbm.append(o['signalData']['dbm'])
                        driver_chosen.append(o['signalData'][chosen_data])
                        lat2.append(o['locationData']['latitude'])
                        lon2.append(o['locationData']['longitude'])
                except KeyError:
                    print("Error on: ", j)

        data_colors = []
        if chosen_data == 'dbm' or chosen_data == 'asuLevel':
            data_colors = calculate_colors(driver_dbm)
        elif chosen_data == 'level':
            data_colors = calculate_colors(driver_chosen)

        map_data = go.Scattermapbox(
            name='RideMap',
            lon=lon2,
            lat=lat2,
            mode='markers',
            text=[chosen_data + ': ' + str(driver_chosen[i]) + '<br>' + 'Network class: ' + network_class2[i] for i in
                  range(len(driver_dbm))],
            marker=go.scattermapbox.Marker(
                color=data_colors,
                opacity=0.7
            )
        )

        layout = go.Layout(
            autosize=True,
            height=700,
            mapbox=dict(
                accesstoken='pk.eyJ1IjoidG1hdGljIiwiYSI6ImNrbXhtamc0eDBxZXUycXBxaG94YmppbmUifQ.L7ulSrlC5mV_TwFD15k6sw',
                bearing=0,
                center=go.layout.mapbox.Center(
                    lat=46.01342639395872,
                    lon=16.400215918042534,
                ),
                pitch=0,
                zoom=9
            )

        )
        fig_data = [map_data]
        fig = go.Figure(data=fig_data, layout=layout)
        div = html.Div(
            children=[
                dcc.Graph(
                    id='zagreb-map',
                    figure=fig
                )
            ]
        )

    return div


if __name__ == '__main__':
    app.run_server(port=4050)
