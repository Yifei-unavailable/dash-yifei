# Import required libraries
import dash
from dash import dcc, html, Input, Output
import pandas as pd
import geopandas as gpd
import plotly.express as px
import plotly.graph_objects as go

# File paths
eci_data_path = "dataset/multidimensional_eci_data.csv"
trade_data_path = "dataset/Export COMPET_.csv"
exposure_data_path = "dataset/Fig2a-avg_exposure.csv"
shapefile_path = "map/ne_110m_admin_0_countries.shp"

# Load datasets
eci_data = pd.read_csv(eci_data_path)
trade_data = pd.read_csv(trade_data_path)
exposure_data = pd.read_csv(exposure_data_path)
world = gpd.read_file(shapefile_path)

# Process ECI data for 2019
eci_2019 = eci_data[eci_data['variable'] == 'eci_trade'][['country', 'x2019']].rename(columns={'x2019': 'eci_trade'})
eci_2019 = eci_2019.dropna()

# Filter trade data for selected indicators
quantity_indicator = "Adjusted export market share - Quantity (delta log)"
quarters_2018 = ['2018q1', '2018q2', '2018q3', '2018q4']

trade_data = trade_data[
    (trade_data['Indicator'] == quantity_indicator) &
    (trade_data['Partner'] == 'World') &
    (trade_data['Attribute 1'] == 'All')
].copy()

for col in quarters_2018:
    trade_data[col] = pd.to_numeric(trade_data[col], errors='coerce')

trade_data['avg_quantity_2018'] = trade_data[quarters_2018].mean(axis=1)
trade_agg = trade_data.groupby('Economy ISO3')['avg_quantity_2018'].mean().reset_index()
trade_agg = trade_agg.rename(columns={'Economy ISO3': 'country', 'avg_quantity_2018': 'quantity_market_share'})

# Process exposure data (country-specific self-exposure)
exposure_data.set_index('Unnamed: 0', inplace=True)
self_exposure = exposure_data.stack().reset_index()
self_exposure = self_exposure[self_exposure['Unnamed: 0'] == self_exposure['level_1']]
self_exposure = self_exposure.rename(columns={'Unnamed: 0': 'country', 0: 'self_exposure'})[['country', 'self_exposure']]

# Merge datasets
merged_data = eci_2019.merge(trade_agg, on='country', how='left')
merged_data = merged_data.merge(self_exposure, on='country', how='left')

# Merge with shapefile data for mapping
world = world.merge(merged_data, left_on='ADM0_A3', right_on='country', how='left')

# Initialize Dash app
app = dash.Dash(__name__)
app.title = "Global Economic Visualizations"

# Layout
app.layout = html.Div([
    html.H1("Economic Complexity and Trade Visualizations", style={"textAlign": "center"}),

    dcc.Dropdown(
        id="metric-dropdown",
        options=[
            {"label": "Economic Complexity Index (ECI)", "value": "eci_trade"},
            {"label": "Trade Market Share", "value": "quantity_market_share"},
            {"label": "Self Exposure", "value": "self_exposure"}
        ],
        value="eci_trade",
        placeholder="Select a metric",
        style={"width": "50%", "margin": "auto"}
    ),
    
    dcc.Graph(id="choropleth-map")
])

# Callback to update the map
@app.callback(
    Output("choropleth-map", "figure"),
    [Input("metric-dropdown", "value")]
)
def update_map(selected_metric):
    fig = px.choropleth(
        world,
        geojson=world.geometry,
        locations=world.index,
        color=selected_metric,
        color_continuous_scale="Viridis",
        hover_name="ADM0_A3",
        hover_data={
            "eci_trade": True,
            "quantity_market_share": ":.4f",
            "self_exposure": ":.4f"
        },
        title=f"Global Visualization: {selected_metric}"
    )

    # Fix overlapping legends
    fig.update_layout(
        margin={"r": 0, "t": 50, "l": 0, "b": 0},
        coloraxis_colorbar=dict(title=selected_metric, thickness=15, x=0.85, y=0.5),
        geo=dict(showcountries=True, showcoastlines=True, fitbounds="locations")
    )

    return fig

# Run the app
if __name__ == "__main__":
    app.run_server(debug=True)
