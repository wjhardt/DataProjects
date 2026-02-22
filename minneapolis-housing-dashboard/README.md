# Minneapolis Housing Market Dashboard

An interactive web application that visualizes property value appreciation
across Minneapolis neighborhoods from 2016 to 2025, with a focus on
identifying micro-trends in Southwest Minneapolis.

## Features

- **Interactive Time Slider** — Scrub from 2016 to 2025 to see how neighborhood values evolved year by year
- **Appreciation Toggle** — Switch between Absolute Value ($) and Percent Growth (%) views
- **Choropleth Map** — Color-coded neighborhood map using Folium/Leaflet
- **Hover Cards** — Rich tooltips showing median value, 10-year growth, vs-city comparison, and housing stock type
- **SW Community Filter** — Sidebar filter for Southwest neighborhoods with multi-community comparison
- **Micro-Trend Table** — Identifies neighborhoods outpacing / tracking / lagging the city average
- **Trend Line Charts** — Compare appreciation curves across selected neighborhoods
- **SW Deep Dive** — Area chart showing all Southwest neighborhoods side-by-side

## Neighborhoods Covered

| Community | Neighborhoods |
|-----------|--------------|
| Southwest | Linden Hills, Fulton, Armatage, Kenny, Lynnhurst, Windom, Tangletown, Kingfield |
| Calhoun-Isles | CARAG, East Calhoun (Bde Maka Ska) |
| Nokomis | Nokomis |
| Longfellow | Longfellow |
| Northeast | Northeast Minneapolis |
| North | Near North, Camden |
| Powderhorn | Powderhorn Park |
| University | Dinkytown |
| Downtown | Downtown West |

## Data Sources

- **Property Assessment Data:** [Minneapolis Open Data — Assessor's Parcel Data](https://opendata.minneapolismn.gov/datasets/assessors-parcel-data)
- **Neighborhood Boundaries:** [Minneapolis Neighborhood GeoJSON](https://opendata.minneapolismn.gov/datasets/neighborhoods)
- **Market Sales Data:** Minneapolis Area Association of Realtors (MAAR) annual reports
- **Reference:** Minneapolis City Assessor's Office estimated market values 2016–2025

## Setup

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Generate data (first time only)
python data/generate_data.py

# 3. Run the dashboard
streamlit run app.py
```

The app will open at `http://localhost:8501`

## Key Findings (2016–2025)

- **Northeast Minneapolis** showed the highest cumulative appreciation (~95%),
  driven by urban infill and proximity to downtown
- **Southwest neighborhoods** (Linden Hills, Tangletown, Kingfield) appreciated
  50–75%, outpacing the city average of ~55%
- **Armatage and Kingfield** are the strongest micro-trends — post-war ramblers
  renovated and attracting young families priced out of Linden Hills
- **North Minneapolis** lagged the city average, growing ~40% vs 55% citywide
- **COVID-19 (2020)** caused a temporary dip, followed by a sharp 2021–2022
  recovery across all neighborhoods

## Project Structure

```
minneapolis-housing-dashboard/
├── app.py                    # Main Streamlit application
├── requirements.txt          # Python dependencies
├── README.md                 # This file
└── data/
    ├── generate_data.py      # Data generation script
    ├── neighborhood_values.csv   # Generated time-series data
    └── neighborhoods.geojson     # Neighborhood polygon boundaries
```
