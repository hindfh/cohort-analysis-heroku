'''
 # @ Create Time: 2022-06-09 16:29:03.834081
'''

import pathlib
import pandas as pd
import datetime as dt

def load_data(data_file: str) -> pd.DataFrame:
    '''
    Load data from /data directory
    '''
    PATH = pathlib.Path(__file__).parent
    DATA_PATH = PATH.joinpath("data").resolve()
    return pd.read_csv(DATA_PATH.joinpath(data_file), delimiter=',', encoding = "ISO-8859-1")
    
data = load_data("data.csv")

data.isnull().sum().sort_values(ascending=False)

# Drop unnecessary columns and null values
data = data.drop(['InvoiceNo', 'StockCode', 'Description'], axis=1)
data = data.dropna()

print("Range Quantity \t\t:", data.Quantity.min(), " to ", data.Quantity.max())
print("Range UnitPrice \t:", data.UnitPrice.min(), " to ", data.UnitPrice.max())

# Remove negative value in Quantity, UnitPrice columns
data = data[data.Quantity > 0]
data = data[data.UnitPrice > 0]

data.isnull().sum().sort_values(ascending=False)

# convert InvoiceDate to Date data type
data['InvoiceDate'] = pd.to_datetime(data['InvoiceDate'], format='%m/%d/%Y %H:%M')

# remove the time from InvoiceDate
data['InvoiceDate'] = data['InvoiceDate'].dt.date

cleaned_data = data.copy()

# # Cohort Analysis
# Create the Cohort
def get_month(x): return dt.datetime(x.year, x.month, 1)
cleaned_data['InvoiceMonth'] = cleaned_data['InvoiceDate'].apply(get_month)# Create InvoiceMonth column
grouping = cleaned_data.groupby('CustomerID')['InvoiceMonth']# Group by CustomerID and select the InvoiceDay value
cleaned_data['CohortMonth'] = grouping.transform('min')# Assign a minimum InvoiceDay value to the dataset

#Extract integer values from data
def get_date_int(df, column):
    year = df[column].dt.year
    month = df[column].dt.month
    day = df[column].dt.day
    return year, month, day

invoice_year, invoice_month, _ = get_date_int(cleaned_data, 'InvoiceMonth')# Get the integers for date parts from the `InvoiceMonth` column
cohort_year, cohort_month, _ = get_date_int(cleaned_data, 'CohortMonth')# Get the integers for date parts from the `CohortMonth` column

years_diff = invoice_year - cohort_year # Calculate difference in years
months_diff = invoice_month - cohort_month # Calculate difference in months

cleaned_data['CohortIndex'] = years_diff * 12 + months_diff + 1 # Extract the difference in months from all previous values

# # Dash
from dash import Dash, dcc, html, Input, Output
import plotly.express as px

app = Dash(__name__, title="MyCSVLoaderApp")

# Declare server for Heroku deployment. Needed for Procfile.
server = app.server

countries = cleaned_data['Country'].unique()

# App layout
app.layout = html.Div([
    html.H1("cohort analysis Dashboards with Dash", style={'text-align': 'center'}),
    dcc.Dropdown(
        id="slct_country",
        options=[{'label': i, 'value': i} for i in countries],
        multi=False,
        value=countries[0],
        style={'width': "40%", 'align': 'center'}
        ),
    dcc.Graph(id='my_heatmap'),
])

# Connect the Plotly graphs with Dash Components
@app.callback(
    Output('my_heatmap', 'figure'),
    Input('slct_country', 'value')
)

def update_graph(option_slctd):
    country_choosen_data = cleaned_data[cleaned_data['Country'] == option_slctd]
    
    ## count monthly active customers from each cohort
    grouping = country_choosen_data.groupby(['CohortMonth', 'CohortIndex'])
    cohort_data = grouping['CustomerID'].apply(pd.Series.nunique)#Count the number of unique values per customer ID
    cohort_data = cohort_data.reset_index()
    cohort_counts = cohort_data.pivot(index='CohortMonth', columns='CohortIndex', values='CustomerID')

    # Retention Rate
    cohort_sizes = cohort_counts.iloc[:,0]#divide each column by value of the first(cohort sizes) to find retention rate
    retention = cohort_counts.divide(cohort_sizes, axis=0)
    retention.round(2) * 100
    
    fig = px.imshow(retention, text_auto='.0%', color_continuous_scale='Blues', zmax=0.5, zmin=0.0)

    return fig


if __name__ == "__main__":
    app.run_server(debug=False)
