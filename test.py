# Install required libraries
import dash
from dash import dcc, html
import pandas as pd
import geopandas as gpd
import plotly.express as px
import plotly.graph_objects as go
import seaborn as sns
import matplotlib.pyplot as plt
import numpy as np

# File paths
eci_data_path = "dataset/multidimensional_eci_data.csv"
trade_data_path = "dataset/Export COMPET_.csv"
exposure_data_path = "dataset/Fig2a-avg_exposure.csv"
shapefile_path = "map/ne_110m_admin_0_countries.shp"

# Step 1: Load datasets
eci_data = pd.read_csv(eci_data_path)
trade_data = pd.read_csv(trade_data_path)
exposure_data = pd.read_csv(exposure_data_path)
world = gpd.read_file(shapefile_path)

# Step 2: Process ECI data for 2019
eci_2019 = eci_data[eci_data['variable'] == 'eci_trade'][['country', 'x2019']].rename(columns={'x2019': 'eci_trade'})
eci_2019 = eci_2019.dropna()

# Step 3: Filter trade data for selected indicators
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

# Step 4: Process exposure data (country-specific self-exposure)
exposure_data.set_index('Unnamed: 0', inplace=True)
self_exposure = exposure_data.stack().reset_index()
self_exposure = self_exposure[self_exposure['Unnamed: 0'] == self_exposure['level_1']]
self_exposure = self_exposure.rename(columns={'Unnamed: 0': 'country', 0: 'self_exposure'})[['country', 'self_exposure']]

# Step 5: Merge datasets
merged_data = eci_2019.merge(trade_agg, on='country', how='left')
merged_data = merged_data.merge(self_exposure, on='country', how='left')

# Step 6: Merge with shapefile data for mapping
world = world.merge(merged_data, left_on='ADM0_A3', right_on='country', how='left')

# Step 7: Create the Dash App
app = dash.Dash(__name__)

# Choropleth map visualization
choropleth_fig = px.choropleth(
    world,
    geojson=world.geometry,
    locations=world.index,
    color='eci_trade',
    color_continuous_scale='Viridis',
    title='Economic Complexity Index (ECI) and Trade Indicators by Country',
    hover_name='ADM0_A3',
    hover_data={
        'eci_trade': True,
        'quantity_market_share': ':.4f',
        'self_exposure': ':.4f'
    }
)

# Add bubble markers for trade values and exposure
world['quantity_market_share_clean'] = world['quantity_market_share'].replace([np.inf, -np.inf], np.nan).fillna(0).apply(lambda x: max(x, 0))
choropleth_fig.add_trace(go.Scattergeo(
    lon=world.geometry.centroid.x,
    lat=world.geometry.centroid.y,
    mode='markers',
    marker=dict(
        size=world['quantity_market_share_clean'] * 10,
        color=world['self_exposure'],
        colorscale='Reds',
        showscale=True,
        colorbar=dict(title="Self-Exposure"),
        opacity=0.8,
        line=dict(width=1, color='black')
    ),
    text=world.apply(
        lambda row: f"Country: {row['ADM0_A3']}<br>Trade Value: {row['quantity_market_share_clean']:.4f}<br>Exposure: {row['self_exposure']:.4f}",
        axis=1
    ),
    hoverinfo='text'
))

# App layout
app.layout = html.Div([
    html.H1("Economic Complexity, Trade, and Exposure Visualization"),
    dcc.Graph(
        id="choropleth",
        figure=choropleth_fig
    )
])

# Run the app
if __name__ == "__main__":
    app.run_server(debug=True, host="0.0.0.0", port=8050)
