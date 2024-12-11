# Install required libraries
import dash
from dash import dcc, html
import pandas as pd
import geopandas as gpd
import plotly.express as px

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

# Step 3: Process trade data
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

# Step 4: Process exposure data
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

app.layout = html.Div([
    html.H1("Economic Complexity, Trade, and Risk Visualization"),
    dcc.Graph(
        id="choropleth",
        figure=px.choropleth(
            world,
            geojson=world.geometry,
            locations=world.index,
            color='eci_trade',
            color_continuous_scale='Viridis',
            title='ECI, Trade, and Risk Indicators by Country',
            hover_name='ADM0_A3',
            hover_data={
                'eci_trade': True,
                'quantity_market_share': ':.4f',
                'self_exposure': ':.4f'
            }
        )
    )
])

# Run the app
if __name__ == "__main__":
    app.run_server(debug=True, host="0.0.0.0", port=8050)
