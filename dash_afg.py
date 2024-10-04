import dash
import dash_bootstrap_components as dbc
from dash import dcc, html, dash_table
from dash.dependencies import Input, Output
import plotly.express as px
import pandas as pd
import os

# Initialize the Dash app with a Bootstrap theme
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.DARKLY])
server = app.server

# Paths to the relevant folders
DATA_PATH = 'data/Afghanistan.csv'
#FORECAST_PATH = 'models/TiDE/predictions/sampling/'
#FORECAST_HTML_PATH = 'docs/figures/operative/TiDE/default/'
#ISO3_PATH = 'data/raw/ACLED_coverage_ISO3.csv'

# Load initial data
data = pd.read_csv(DATA_PATH)
data['event_date'] = pd.to_datetime(data['event_date'], format='%Y-%m-%d')
data = data[data['event_date'] > pd.to_datetime('2020-01-01')]
data = data[data['event_date'] < pd.to_datetime('2022-01-01')]
# Event Raw Data
event_data = pd.read_csv('data/Afg.csv')
available_event_dates = sorted(event_data['event_date'].unique())
default_event_date = '2021-08-15'

# Extract available dates and other options
available_dates = sorted(data['event_date'].unique())
default_date = available_dates[-1]

# Column dropdown options
unavailable_cols = ['event_date', 'country', 'ISO_3', 'capital_lat', 'capital_lon', 'month', 'quarter', 'week']
unavailable_table_cols = ['country', 'month', 'quarter', 'week']
column_options = [{'label': col, 'value': col} for col in data.columns if col not in unavailable_cols]
vi_avg_column_options = [{'label': 'Violence index 1 Year moving average', 'value': col} for col in ['violence index_moving_avg'] if col not in unavailable_cols]

# Navbar layout
navbar = dbc.NavbarSimple(
    children=[
        dbc.NavItem(dbc.NavLink("Monitoring", href="/monitoring")),
        #dbc.NavItem(dbc.NavLink("Forecasting", href="/forecasting")),
    ],
    brand="Dashboard",
    brand_href="/",
    color="primary",
    dark=True,
)

# Monitoring layout
monitoring_layout = html.Div([
    html.H1('Monitoring Dashboard'),
    html.Div(className='container', children=[
        html.H2('Afghanistan Events Over Time'),
        dcc.Dropdown(id='map-date', options=[{'label': date, 'value': date} for date in available_event_dates], value=default_event_date, clearable=False, className='dcc-dropdown'),
        dcc.Graph(id='event-map', className='dcc-graph'),
        html.H2('Afghanistan Data Over Time'),
        dcc.Dropdown(id='evolution-column', options=column_options, value='violence index', clearable=False, className='dcc-dropdown'),
        dcc.Graph(id='line-plot', className='dcc-graph'),
        html.H2('Afghanistan Weekly Stats by Date'),
        dcc.Dropdown(id='plot-date', options=[{'label': date, 'value': date} for date in available_dates], value=default_date, clearable=False, className='dcc-dropdown'),
        dash_table.DataTable(id='data-table',
            style_data={'color': 'white','backgroundColor': 'rgb(50, 50, 50)'},
            style_header={'backgroundColor': 'rgb(30, 30, 30)', 'color': 'white', 'fontWeight': 'bold'},
            style_cell={'height': 'auto', 'minWidth': '90px', 'width': '180px', 'maxWidth': '180px', 'whiteSpace': 'normal'}
        ),
    ]),
])

# Forecasting layout
forecasting_layout = html.Div([
    html.H1('Forecasting Dashboard'),
    html.H3('Select forecasted week:'),
    dcc.Slider(id='forecast-slider', min=0, max=11, step=1, value=0, marks={i: f'Forecast {i+1}' for i in range(12)}),
    html.H3('Select outcome level:'),
    dcc.Slider(id='percentile-slider', min=0, max=100, step=1, value=50, marks={i: str(i) for i in range(0, 101, 10)}),
    dcc.Graph(id='forecast-bar-plot', className='dcc-graph'),
    html.H3('Select number of countries:'),
    dcc.Slider(id='num-forecasted-countries', min=10, max=160, step=10, value=10, marks={i: str(i) for i in range(10, 160, 10)}),
    dcc.Graph(id='forecast-world-map', className='dcc-graph'),
    html.H2('Select Country Forecasts'),
    dcc.Dropdown(id='forecast-country', options=[{'label': c, 'value': c} for c in sorted(data['country'].unique())], value='Afghanistan', clearable=False, className='dcc-dropdown'),
    html.Iframe(id='forecast-line-plot', style={'width': '100%', 'height': '600px'}),
])

# Main layout
app.layout = html.Div([
    dcc.Location(id="url"),
    navbar,
    html.Div(id="page-content")
])

# Page routing callback
@app.callback(Output('page-content', 'children'), [Input('url', 'pathname')])
def display_page(pathname):
    if pathname == '/forecasting':
        return forecasting_layout
    else:
        return monitoring_layout  # Default to monitoring


# Callback for event map
@app.callback(
    [Output('event-map', 'figure')],  # Expecting a list or tuple of outputs
    [Input('map-date', 'value')]
)

def update_event_map(selected_date):
    # Filter data for the selected date
    filtered_df = event_data[event_data['event_date'] == selected_date]

    # Group by latitude, longitude, and event_type
    grouped = filtered_df.groupby(['latitude', 'longitude', 'event_type']).agg(
        count=('event_type', 'size'),  # Count the number of events in the group
        fatalities=('fatalities', 'sum'),  # Sum the fatalities for each group
        actor1=('actor1', lambda x: ', '.join(sorted(set(x)))),  # Concatenate unique actor1 values
        admin1=('admin1', lambda x: ', '.join(sorted(set(x)))),  # Concatenate unique admin1 values
        admin2=('admin2', lambda x: ', '.join(sorted(set(x)))),  # Concatenate unique admin2 values
        sub_event_type=('sub_event_type', lambda x: ', '.join(sorted(set(x))))   # Concatenate unique admin2 values
    ).reset_index()

    # Generate map with Plotly Express
    fig = px.scatter_mapbox(grouped,
                            lat='latitude',
                            lon='longitude',
                            size='count',  # Circle size based on count
                            color='event_type',  # Color based on event_type
                            hover_name='event_type',
                            hover_data={'count': True, 'event_type': False, 'latitude': False, 'longitude': False, 'sub_event_type': True, 'actor1': True, 'fatalities':True, 'admin1': True, 'admin2': True},
                            zoom=5,
                            opacity=0.5,
                            template='plotly_dark')

    # Update map style
    fig.update_layout(mapbox_style="carto-positron", margin={"r": 0, "t": 0, "l": 0, "b": 0})

    return [fig]


# Callback for line plot and data table
@app.callback(
    [Output('line-plot', 'figure'),
     Output('data-table', 'data'),
     Output('data-table', 'columns')],
    [Input('evolution-column', 'value'),
     Input('plot-date', 'value')]
)

def update_line_plot_and_table(selected_column, plot_date):
    # Create the line plot showing the evolution of the selected column for each country
    line_fig = px.line(data, x='event_date', y=selected_column, template='plotly_dark',
                  title=f'{selected_column} over time for Afghanistan')
    
    # Add the second line for the second column
    if selected_column == 'violence index':
        line_fig.add_scatter(x=data['event_date'], y=data['violence index_moving_avg'], mode='lines',
                            name='Violence index 1 Year moving average',
                            line=dict(color='purple'))  # Customize the color as needed

       
    # Find the y-value (selected_column value) at the plot_date
    y_value = data.loc[data['event_date'] == plot_date, selected_column].values[0]
    # Add a scatter trace for the marker at the specific point
    line_fig.add_scatter(x=[plot_date], y=[y_value], mode='markers',
                            marker=dict(color='white', size=10, symbol='circle'),
                            name=f'date selected')
    
    y_value = data.loc[data['event_date'] == '2020-05-01', selected_column].values[0]
    line_fig.add_scatter(x=['2020-04-29'], y=[y_value], mode='markers',
                            marker=dict(color='yellow', size=15, symbol='star'),
                            name='Trump withdrawal announcement')
    
    y_value = data.loc[data['event_date'] == '2021-02-19', selected_column].values[0]
    line_fig.add_scatter(x=['2021-02-14'], y=[y_value], mode='markers',
                            marker=dict(color='green', size=15, symbol='star'),
                            name='Biden moves withdrawal')
    
    y_value = data.loc[data['event_date'] == '2021-05-07', selected_column].values[0]
    line_fig.add_scatter(x=['2021-05-01'], y=[y_value], mode='markers',
                            marker=dict(color='orange', size=15, symbol='star'),
                            name='Withdrawal begins')
    
    y_value = data.loc[data['event_date'] == '2021-08-13', selected_column].values[0]
    line_fig.add_scatter(x=['2021-08-15'], y=[y_value], mode='markers',
                            marker=dict(color='red', size=15, symbol='star'),
                            name='Taliban enter Kabul')
    
    # Prepare the table data for the selected countries
    table_data = []
    latest_values = data.loc[data['event_date'] == plot_date].to_dict('records')[0]
    table_data.append(latest_values)

    new_table_data = []
    for col in data.columns:
        if col in unavailable_table_cols:
            continue
        new_row = {'Country': col}
        new_row['Afghanistan'] = table_data[0][col]
        new_table_data.append(new_row)
    
    columns_default = [{'name':'Country', 'id':'Country'}]
    columns = [{'name':'Afghanistan', 'id':'Afghanistan'}]
    columns = columns_default + columns

    return line_fig, new_table_data, columns
    


# Start the app
if __name__ == '__main__':
    app.run_server(debug=False)
