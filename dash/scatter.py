import os
from dash import Dash, dcc, html, Input, Output, ctx
import plotly.express as px
import pandas as pd


current_folder = os.path.dirname(__file__)
iata_coordinates = os.path.join(current_folder, '..', 'data', 'sources', 'iata-icao.csv')
iata_coordinates = os.path.abspath(iata_coordinates)
flights = os.path.join(current_folder, '..', 'data', 'output', 'polish_airports.csv')
flights = os.path.abspath(flights)

df_iata_coordinates = pd.read_csv(iata_coordinates)
df_flights = pd.read_csv(flights)

departure_dropdown = sorted(df_flights['departure_airport'].dropna().unique())
filtered_iata_coordinates = df_iata_coordinates[df_iata_coordinates['iata'].isin(df_flights['arrival_airport'])]
departure_weekday_options = sorted(df_flights['departure_weekday'].dropna().unique())

app = Dash(__name__)

app.layout = html.Div([
    html.H1('Flights from the selected airport and weekday starting from today'),

    dcc.Dropdown(
        id='departure-airport-dropdown',
        options=[{'label': i, 'value': i} for i in departure_dropdown],
        value=departure_dropdown[0],
        clearable=False,
        placeholder='Select departure airport',
    ),

    html.Br(),

    dcc.Dropdown(
            id='departure-weekday-dropdown',
            options=[{'label': i, 'value': i} for i in departure_weekday_options],
            value=departure_weekday_options[0],
            clearable=False
        ),

    html.Br(),

    dcc.RangeSlider(
        id='price-slider',
        min=0,
        max=1000,
        step=1,
        value=[0, 1000],
        tooltip={"placement": "bottom", "always_visible": True}
    ),

    html.Br(),

    dcc.Graph(id='map-graph')
])

@app.callback(
    Output('price-slider', 'min'),
    Output('price-slider', 'max'),
    Output('price-slider', 'value'),
    Output('price-slider', 'marks'),
    Input('departure-airport-dropdown', 'value'),
    Input('departure-weekday-dropdown', 'value')
)
def update_price_slider(selected_departure, selected_departure_weekday):
    filtered_df_flights = df_flights[
        (df_flights['departure_airport'] == selected_departure) &
        (df_flights['departure_weekday'] == selected_departure_weekday)
         ]

    min_price = int(filtered_df_flights['price'].min()) if not filtered_df_flights.empty else 0
    max_price = int(filtered_df_flights['price'].max()) if not filtered_df_flights.empty else 1000
    value = [min_price, max_price]

    marks = {i: str(i) for i in range(min_price, max_price + 1, max(1, (max_price - min_price) // 5))}

    return min_price, max_price, value, marks


@app.callback(
    Output('map-graph', 'figure'),
    Input('departure-airport-dropdown', 'value'),
    Input('departure-weekday-dropdown', 'value'),
    Input('price-slider', 'value')
)
def update_map(selected_departure, selected_departure_weekday, selected_price_range):
    filtered_df_flights = df_flights[
        (df_flights['departure_airport'] == selected_departure) &
        (df_flights['departure_weekday'] == selected_departure_weekday) &
        (df_flights['price'] >= selected_price_range[0]) &
        (df_flights['price'] <= selected_price_range[1])
    ]

    grouped_flights = filtered_df_flights.groupby('arrival_airport').agg(
        num_flights=('arrival_airport', 'count'),
        avg_price=('price', 'mean'),
        min_price=('price', 'min'),
        max_price=('price', 'max')
    ).reset_index()

    filtered_df = pd.merge(
        grouped_flights,
        df_iata_coordinates,
        left_on='arrival_airport',
        right_on='iata',
        how='inner'
    )

    fig = px.scatter_mapbox(
        filtered_df,
        lat='latitude',
        lon='longitude',
        hover_name='iata',
        hover_data={
            'airport': True,
            'num_flights': True,
            'avg_price': ':.0f',
            'min_price': ':.0f',
            'max_price': ':.0f',
            'latitude': False,
            'longitude': False
        },
        color='avg_price',
        color_continuous_scale='Viridis',
        size_max=15,
        zoom=3
    )

    fig.update_layout(
        mapbox_style='carto-positron',
        margin={"r": 0, "t": 0, "l": 0, "b": 0}
    )

    fig.update_traces(marker={'size': 25})

    fig.update_geos(
        fitbounds="locations",
        visible=True
    )

    return fig


if __name__ == '__main__':
    app.run(debug=True)
