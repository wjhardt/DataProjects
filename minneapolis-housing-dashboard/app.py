"""
Minneapolis Housing Market Dashboard
=====================================
Interactive visualization of property value appreciation across
Minneapolis neighborhoods (2016–2025).

Data sources:
  - Minneapolis Open Data: Assessor's Parcel Data (open.minneapolismn.gov)
  - Minneapolis Neighborhood GeoJSON boundaries
  - Minneapolis Area Association of Realtors market reports

Run with:  streamlit run app.py
"""

import json
from pathlib import Path

import folium
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from branca.colormap import LinearColormap
from streamlit_folium import st_folium

# ─── Page config ─────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Minneapolis Housing Market Dashboard",
    page_icon="🏠",
    layout="wide",
    initial_sidebar_state="expanded",
)

DATA_DIR = Path(__file__).parent / "data"

# ─── Community groupings ──────────────────────────────────────────────────────
COMMUNITY_COLORS = {
    "Southwest": "#2196F3",
    "Calhoun-Isles": "#9C27B0",
    "Nokomis": "#4CAF50",
    "Longfellow": "#FF9800",
    "Northeast": "#F44336",
    "North": "#795548",
    "Powderhorn": "#00BCD4",
    "University": "#FF5722",
    "Downtown": "#607D8B",
}

SW_NEIGHBORHOODS = [
    "Linden Hills", "Fulton", "Armatage", "Kenny",
    "Lynnhurst", "Windom", "Tangletown", "Kingfield",
]


# ─── Data loading ─────────────────────────────────────────────────────────────
@st.cache_data
def load_data():
    df = pd.read_csv(DATA_DIR / "neighborhood_values.csv")
    with open(DATA_DIR / "neighborhoods.geojson") as f:
        geojson = json.load(f)
    return df, geojson


# ─── Helper functions ─────────────────────────────────────────────────────────
def format_currency(val: float) -> str:
    if val >= 1_000_000:
        return f"${val/1_000_000:.2f}M"
    return f"${val:,.0f}"


def growth_color(pct: float) -> str:
    """Return a color hex based on growth percentage."""
    if pct >= 60:
        return "#1a237e"
    if pct >= 45:
        return "#1565c0"
    if pct >= 30:
        return "#1976d2"
    if pct >= 15:
        return "#42a5f5"
    if pct >= 0:
        return "#90caf9"
    return "#ef9a9a"


def build_choropleth_map(
    df_year: pd.DataFrame,
    geojson: dict,
    metric: str,
    selected_communities: list[str],
    year: int,
    base_year: int,
) -> folium.Map:
    """Build a Folium choropleth map for the given year and metric."""

    # Minneapolis center
    m = folium.Map(
        location=[44.9375, -93.2950],
        zoom_start=12,
        tiles="CartoDB positron",
        prefer_canvas=True,
    )

    # Merge data with geojson lookup
    data_lookup = df_year.set_index("neighborhood").to_dict("index")

    # Determine color scale
    if metric == "absolute":
        values = df_year["median_value"].dropna()
        vmin, vmax = values.min(), values.max()
        colormap = LinearColormap(
            ["#fffde7", "#fff176", "#ffca28", "#ff8f00", "#e65100"],
            vmin=vmin, vmax=vmax,
            caption="Median Assessed Value ($)",
        )

        def get_value(name):
            return data_lookup.get(name, {}).get("median_value", 0)

        def tooltip_metric(name):
            v = get_value(name)
            return f"<b>Median Value:</b> {format_currency(v)}"

    else:  # percent growth
        values = df_year["cumulative_growth_pct"].dropna()
        vmin, vmax = max(values.min(), -5), min(values.max(), 100)
        colormap = LinearColormap(
            ["#ffebee", "#ffcdd2", "#ef9a9a", "#42a5f5", "#1565c0", "#0d47a1"],
            vmin=vmin, vmax=vmax,
            caption=f"Cumulative Growth Since {base_year} (%)",
        )

        def get_value(name):
            return data_lookup.get(name, {}).get("cumulative_growth_pct", 0)

        def tooltip_metric(name):
            v = get_value(name)
            city = data_lookup.get(name, {}).get("city_cumulative_growth_pct", 0)
            vs = data_lookup.get(name, {}).get("vs_city_avg", 0)
            sign = "+" if vs >= 0 else ""
            return (
                f"<b>Growth since {base_year}:</b> {v:.1f}%<br>"
                f"<b>vs City Avg ({city:.1f}%):</b> {sign}{vs:.1f}%"
            )

    # Add GeoJSON layer with styling
    for feature in geojson["features"]:
        name = feature["properties"]["neighborhood"]
        community = feature["properties"]["community"]

        if selected_communities and community not in selected_communities:
            opacity = 0.08
            fill_opacity = 0.05
            color = "#cccccc"
            fill_color = "#eeeeee"
        else:
            val = get_value(name)
            fill_color = colormap(val) if val else "#eeeeee"
            opacity = 0.7
            fill_opacity = 0.65
            color = "#555555"

        info = data_lookup.get(name, {})
        med_val = info.get("median_value", 0)
        growth = info.get("cumulative_growth_pct", 0)
        city_growth = info.get("city_cumulative_growth_pct", 0)
        vs_city = info.get("vs_city_avg", 0)
        stock = info.get("housing_stock", "N/A")
        prop_count = info.get("property_count", "N/A")
        comm = info.get("community", "N/A")

        sign = "+" if vs_city >= 0 else ""
        micro_trend = (
            "OUTPACING city avg" if vs_city >= 5
            else "LAGGING city avg" if vs_city <= -5
            else "Tracking city avg"
        )
        trend_color = "#1b5e20" if vs_city >= 5 else "#b71c1c" if vs_city <= -5 else "#e65100"

        tooltip_html = f"""
        <div style="font-family: Arial, sans-serif; min-width: 240px; max-width: 300px;">
            <div style="background:#1565c0; color:white; padding:8px 12px; border-radius:6px 6px 0 0;">
                <b style="font-size:14px;">{name}</b>
                <span style="font-size:11px; margin-left:6px; opacity:0.85;">{comm}</span>
            </div>
            <div style="padding:10px 12px; background:#fafafa; border:1px solid #ddd; border-top:none; border-radius:0 0 6px 6px;">
                <table style="width:100%; font-size:12px; border-collapse:collapse;">
                    <tr>
                        <td style="padding:3px 0; color:#555;">Median Value ({year})</td>
                        <td style="padding:3px 0; text-align:right; font-weight:bold; color:#1565c0;">
                            {format_currency(med_val)}
                        </td>
                    </tr>
                    <tr>
                        <td style="padding:3px 0; color:#555;">Growth since {base_year}</td>
                        <td style="padding:3px 0; text-align:right; font-weight:bold;">
                            {growth:.1f}%
                        </td>
                    </tr>
                    <tr>
                        <td style="padding:3px 0; color:#555;">vs City Avg</td>
                        <td style="padding:3px 0; text-align:right; font-weight:bold; color:{trend_color};">
                            {sign}{vs_city:.1f}%
                        </td>
                    </tr>
                    <tr>
                        <td style="padding:3px 0; color:#555;">Properties</td>
                        <td style="padding:3px 0; text-align:right;">{prop_count:,}</td>
                    </tr>
                    <tr>
                        <td colspan="2" style="padding:5px 0 3px 0; color:#555; font-size:11px;">
                            <b>Housing Stock:</b><br>{stock}
                        </td>
                    </tr>
                    <tr>
                        <td colspan="2" style="padding:5px 0 0 0; text-align:center;">
                            <span style="background:{trend_color}; color:white; padding:2px 8px;
                                  border-radius:10px; font-size:11px; font-weight:bold;">
                                {micro_trend}
                            </span>
                        </td>
                    </tr>
                </table>
            </div>
        </div>
        """

        folium.GeoJson(
            feature,
            style_function=lambda f, fc=fill_color, op=opacity, fop=fill_opacity, c=color: {
                "fillColor": fc,
                "color": c,
                "weight": 1.5,
                "fillOpacity": fop,
                "opacity": op,
            },
            highlight_function=lambda f: {
                "weight": 3,
                "color": "#333",
                "fillOpacity": 0.85,
            },
            tooltip=folium.Tooltip(tooltip_html, sticky=True),
        ).add_to(m)

    colormap.add_to(m)

    # Add Minneapolis city boundary label
    folium.Marker(
        location=[44.9778, -93.2650],
        icon=folium.DivIcon(
            html="""<div style="font-size:11px; color:#555; font-weight:bold;
                         background:rgba(255,255,255,0.7); padding:2px 5px;
                         border-radius:3px;">Minneapolis</div>""",
            icon_size=(100, 20),
        ),
    ).add_to(m)

    return m


def build_trend_chart(
    df: pd.DataFrame,
    neighborhoods: list[str],
    metric: str,
    base_year: int,
) -> go.Figure:
    """Build a line chart showing value trends over time."""
    df_filtered = df[df["neighborhood"].isin(neighborhoods)].copy()
    df_city = df[df["neighborhood"] == neighborhoods[0]][["year", "city_median_value",
                                                           "city_cumulative_growth_pct"]].copy()

    if metric == "absolute":
        y_col = "median_value"
        y_label = "Median Assessed Value ($)"
        title = "Median Property Value Over Time"
        city_y = "city_median_value"
        city_label = "City Average"
        tickformat = "$,.0f"
    else:
        y_col = "cumulative_growth_pct"
        y_label = f"Cumulative Growth Since {base_year} (%)"
        title = f"Cumulative Appreciation Since {base_year}"
        city_y = "city_cumulative_growth_pct"
        city_label = "City Average"
        tickformat = ".1f%"

    fig = go.Figure()

    # Add city average line
    fig.add_trace(go.Scatter(
        x=df_city["year"],
        y=df_city[city_y],
        name=city_label,
        line=dict(color="#999999", width=2, dash="dash"),
        mode="lines",
    ))

    # Color palette
    palette = px.colors.qualitative.Set1

    for i, nbhd in enumerate(neighborhoods):
        df_nbhd = df_filtered[df_filtered["neighborhood"] == nbhd]
        color = palette[i % len(palette)]

        fig.add_trace(go.Scatter(
            x=df_nbhd["year"],
            y=df_nbhd[y_col],
            name=nbhd,
            line=dict(color=color, width=2.5),
            mode="lines+markers",
            marker=dict(size=6),
            hovertemplate=(
                f"<b>{nbhd}</b><br>"
                "Year: %{x}<br>"
                + (f"Value: $%{{y:,.0f}}<extra></extra>" if metric == "absolute"
                   else f"Growth: %{{y:.1f}}%<extra></extra>")
            ),
        ))

    fig.update_layout(
        title=dict(text=title, font=dict(size=16)),
        xaxis=dict(title="Year", tickmode="linear", dtick=1, tickangle=-45),
        yaxis=dict(
            title=y_label,
            tickformat="$,.0f" if metric == "absolute" else ".0f",
            tickprefix="" if metric != "absolute" else "",
            ticksuffix="%" if metric == "percent" else "",
        ),
        legend=dict(orientation="v", yanchor="top", y=1, xanchor="left", x=1.01),
        plot_bgcolor="#fafafa",
        paper_bgcolor="white",
        hovermode="x unified",
        margin=dict(l=10, r=180, t=50, b=60),
        height=380,
    )

    # Add shaded COVID period
    fig.add_vrect(
        x0=2020, x1=2021,
        fillcolor="#ffebee", opacity=0.5, layer="below",
        line_width=0,
        annotation_text="COVID-19",
        annotation_position="top left",
        annotation_font_size=10,
        annotation_font_color="#c62828",
    )

    return fig


def build_bar_chart(df_year: pd.DataFrame, metric: str, base_year: int) -> go.Figure:
    """Build a horizontal bar chart ranking neighborhoods by metric."""
    df_sorted = df_year.copy()

    if metric == "absolute":
        col = "median_value"
        xlabel = "Median Assessed Value ($)"
        title = f"Neighborhood Rankings by Median Value"
    else:
        col = "cumulative_growth_pct"
        xlabel = f"Cumulative Growth Since {base_year} (%)"
        title = f"Neighborhood Rankings by Growth Since {base_year}"

    df_sorted = df_sorted.sort_values(col, ascending=True)

    colors = [
        COMMUNITY_COLORS.get(comm, "#607D8B")
        for comm in df_sorted["community"]
    ]

    fig = go.Figure(go.Bar(
        x=df_sorted[col],
        y=df_sorted["neighborhood"],
        orientation="h",
        marker_color=colors,
        text=(
            df_sorted[col].apply(lambda v: format_currency(v))
            if metric == "absolute"
            else df_sorted[col].apply(lambda v: f"{v:.1f}%")
        ),
        textposition="outside",
        hovertemplate=(
            "<b>%{y}</b><br>"
            + ("Value: $%{x:,.0f}<extra></extra>" if metric == "absolute"
               else "Growth: %{x:.1f}%<extra></extra>")
        ),
    ))

    fig.update_layout(
        title=dict(text=title, font=dict(size=15)),
        xaxis=dict(
            title=xlabel,
            tickformat="$,.0f" if metric == "absolute" else ".0f",
            ticksuffix="%" if metric == "percent" else "",
        ),
        yaxis=dict(tickfont=dict(size=11)),
        plot_bgcolor="#fafafa",
        paper_bgcolor="white",
        margin=dict(l=10, r=80, t=50, b=40),
        height=max(380, len(df_sorted) * 26 + 80),
    )

    return fig


def build_micro_trends_table(df_year: pd.DataFrame) -> pd.DataFrame:
    """Identify neighborhoods outpacing/lagging the city average."""
    df = df_year[["neighborhood", "community", "median_value",
                  "cumulative_growth_pct", "city_cumulative_growth_pct",
                  "vs_city_avg", "housing_stock"]].copy()
    df["trend"] = df["vs_city_avg"].apply(
        lambda v: "🚀 Outpacing" if v >= 5 else ("📉 Lagging" if v <= -5 else "≈ Tracking")
    )
    df = df.sort_values("vs_city_avg", ascending=False)
    df["median_value"] = df["median_value"].apply(format_currency)
    df["cumulative_growth_pct"] = df["cumulative_growth_pct"].apply(lambda v: f"{v:.1f}%")
    df["vs_city_avg"] = df["vs_city_avg"].apply(lambda v: f"+{v:.1f}%" if v >= 0 else f"{v:.1f}%")
    df = df.rename(columns={
        "neighborhood": "Neighborhood",
        "community": "Community",
        "median_value": "Median Value",
        "cumulative_growth_pct": "Total Growth",
        "city_cumulative_growth_pct": "City Avg Growth",
        "vs_city_avg": "vs City Avg",
        "housing_stock": "Housing Stock",
        "trend": "Micro-Trend",
    })
    return df.reset_index(drop=True)


# ─── Main app ─────────────────────────────────────────────────────────────────
def main():
    df, geojson = load_data()

    all_years = sorted(df["year"].unique())
    all_communities = sorted(df["community"].unique())
    all_neighborhoods = sorted(df["neighborhood"].unique())

    # ── Sidebar ───────────────────────────────────────────────────────────────
    with st.sidebar:
        st.image(
            "https://upload.wikimedia.org/wikipedia/commons/thumb/9/98/Flag_of_Minneapolis%2C_Minnesota.svg/320px-Flag_of_Minneapolis%2C_Minnesota.svg.png",
            width=120,
        )
        st.markdown("## Minneapolis Housing")
        st.markdown("### Market Dashboard")
        st.caption("Property value appreciation · 2016–2025")
        st.divider()

        st.markdown("#### View Mode")
        metric = st.radio(
            "Appreciation Toggle",
            options=["absolute", "percent"],
            format_func=lambda x: "💰 Absolute Value ($)" if x == "absolute" else "📈 % Growth vs 2016",
            index=1,
            help="Switch between showing raw assessed values or cumulative % growth since 2016",
        )
        st.divider()

        st.markdown("#### Community Filter")
        show_all = st.checkbox("Show all communities", value=False)

        if show_all:
            selected_communities = all_communities
        else:
            selected_communities = st.multiselect(
                "Select communities",
                options=all_communities,
                default=["Southwest", "Calhoun-Isles", "Nokomis"],
                help="Filter neighborhoods by community area. Southwest includes Linden Hills, Fulton, Armatage, etc.",
            )
            if not selected_communities:
                st.warning("Select at least one community")
                selected_communities = ["Southwest"]

        st.divider()

        st.markdown("#### Trend Chart Selection")
        chart_neighborhoods = st.multiselect(
            "Neighborhoods to compare",
            options=all_neighborhoods,
            default=SW_NEIGHBORHOODS[:5] + ["Northeast Minneapolis"],
            help="Select neighborhoods to display in the trend line chart below the map",
        )
        if not chart_neighborhoods:
            chart_neighborhoods = SW_NEIGHBORHOODS[:3]

        st.divider()
        st.markdown("#### About")
        st.caption(
            "Data represents estimated market values from Minneapolis "
            "Assessor records and MAAR sales data, 2016–2025. "
            "Southwest Community includes Linden Hills, Fulton, Armatage, "
            "Kenny, Lynnhurst, Windom, Tangletown, and Kingfield."
        )
        st.caption(
            "**Sources:** Minneapolis Open Data · "
            "Minneapolis Area Association of Realtors"
        )

    # ── Main content ──────────────────────────────────────────────────────────
    st.markdown(
        """
        <h1 style="margin-bottom:0">
            🏠 Minneapolis Housing Market
        </h1>
        <p style="color:#666; font-size:16px; margin-top:4px;">
            Property Value Appreciation · Southwest Neighborhoods · 2016–2025
        </p>
        """,
        unsafe_allow_html=True,
    )

    # ── KPI cards ─────────────────────────────────────────────────────────────
    df_2025 = df[df["year"] == 2025]
    df_2016 = df[df["year"] == 2016]

    sw_2025 = df_2025[df_2025["community"] == "Southwest"]["median_value"].median()
    sw_2016 = df_2016[df_2016["community"] == "Southwest"]["median_value"].median()
    sw_growth = (sw_2025 - sw_2016) / sw_2016 * 100

    city_2025 = df_2025["city_median_value"].mean()
    city_2016 = df_2016["city_median_value"].mean()
    city_growth = (city_2025 - city_2016) / city_2016 * 100

    top_nbhd = df_2025.loc[df_2025["cumulative_growth_pct"].idxmax()]

    kpi1, kpi2, kpi3, kpi4 = st.columns(4)
    kpi1.metric(
        "SW Median Value (2025)",
        format_currency(sw_2025),
        f"+{sw_growth:.0f}% since 2016",
        delta_color="normal",
    )
    kpi2.metric(
        "City Median Value (2025)",
        format_currency(city_2025),
        f"+{city_growth:.0f}% since 2016",
    )
    kpi3.metric(
        "SW vs City Premium",
        f"{(sw_2025/city_2025 - 1)*100:.0f}%",
        "above city median",
        delta_color="off",
    )
    kpi4.metric(
        "Top Appreciating Neighborhood",
        top_nbhd["neighborhood"],
        f"+{top_nbhd['cumulative_growth_pct']:.0f}% since 2016",
    )

    st.divider()

    # ── Time Slider ───────────────────────────────────────────────────────────
    col_slider, col_info = st.columns([3, 1])
    with col_slider:
        selected_year = st.slider(
            "Year",
            min_value=min(all_years),
            max_value=max(all_years),
            value=2025,
            step=1,
            format="%d",
            help="Drag the slider to travel through time and see how values changed year by year",
        )
    with col_info:
        st.markdown(f"""
        <div style="background:#e3f2fd; border-left:4px solid #1565c0;
                    padding:10px 14px; border-radius:4px; margin-top:8px;">
            <div style="font-size:24px; font-weight:bold; color:#1565c0;">{selected_year}</div>
            <div style="font-size:12px; color:#555; margin-top:2px;">
                {'📈 Growth' if metric == 'percent' else '💰 Values'} view
            </div>
        </div>
        """, unsafe_allow_html=True)

    # Filter data for selected year
    df_year = df[df["year"] == selected_year].copy()

    # ── Map + Rankings columns ────────────────────────────────────────────────
    map_col, chart_col = st.columns([3, 2])

    with map_col:
        st.markdown(f"#### Neighborhood Map · {selected_year}")
        base_year = 2016
        folium_map = build_choropleth_map(
            df_year, geojson, metric, selected_communities, selected_year, base_year
        )
        st_folium(folium_map, width="100%", height=500, returned_objects=[])

    with chart_col:
        st.markdown(f"#### Rankings · {selected_year}")
        bar_fig = build_bar_chart(df_year, metric, base_year)
        st.plotly_chart(bar_fig, use_container_width=True)

    st.divider()

    # ── Trend lines ───────────────────────────────────────────────────────────
    st.markdown("#### Appreciation Trends Over Time")

    trend_fig = build_trend_chart(df, chart_neighborhoods, metric, base_year)
    st.plotly_chart(trend_fig, use_container_width=True)

    st.divider()

    # ── Micro-trends table ────────────────────────────────────────────────────
    st.markdown(f"#### Micro-Trend Analysis · {selected_year}")
    st.caption(
        "Neighborhoods labeled **Outpacing** grew more than 5 percentage points faster than the "
        "city average since 2016. These represent the strongest investment micro-trends."
    )

    micro_df = build_micro_trends_table(df_year)

    # Filter to selected communities if not show_all
    if not show_all:
        micro_df_filtered = micro_df[micro_df["Community"].isin(selected_communities)]
    else:
        micro_df_filtered = micro_df

    st.dataframe(
        micro_df_filtered[[
            "Micro-Trend", "Neighborhood", "Community",
            "Median Value", "Total Growth", "vs City Avg", "Housing Stock"
        ]],
        use_container_width=True,
        hide_index=True,
        column_config={
            "Micro-Trend": st.column_config.TextColumn("Micro-Trend", width="small"),
            "Neighborhood": st.column_config.TextColumn("Neighborhood", width="medium"),
            "Community": st.column_config.TextColumn("Community", width="small"),
            "Median Value": st.column_config.TextColumn("Median Value", width="small"),
            "Total Growth": st.column_config.TextColumn("Growth (2016→)", width="small"),
            "vs City Avg": st.column_config.TextColumn("vs City Avg", width="small"),
            "Housing Stock": st.column_config.TextColumn("Housing Stock", width="large"),
        },
    )

    st.divider()

    # ── SW Deep Dive ──────────────────────────────────────────────────────────
    st.markdown("#### Southwest Community Deep Dive")

    sw_neighborhoods = df_year[df_year["community"] == "Southwest"]["neighborhood"].tolist()
    sw_df = df[df["neighborhood"].isin(sw_neighborhoods)].copy()

    sw_fig = px.area(
        sw_df,
        x="year",
        y="median_value",
        color="neighborhood",
        title="Southwest Minneapolis — Median Value by Neighborhood (2016–2025)",
        labels={"median_value": "Median Value ($)", "year": "Year", "neighborhood": "Neighborhood"},
        color_discrete_sequence=px.colors.qualitative.Set2,
    )
    sw_fig.update_layout(
        plot_bgcolor="#fafafa",
        paper_bgcolor="white",
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=-0.35, xanchor="center", x=0.5),
        margin=dict(l=10, r=10, t=50, b=100),
        height=400,
        yaxis_tickformat="$,.0f",
    )
    sw_fig.add_vrect(
        x0=2020, x1=2021, fillcolor="#ffebee", opacity=0.4, layer="below",
        line_width=0,
        annotation_text="COVID-19 dip", annotation_position="top left",
        annotation_font_size=10, annotation_font_color="#c62828",
    )
    st.plotly_chart(sw_fig, use_container_width=True)

    # ── Footer ────────────────────────────────────────────────────────────────
    st.markdown("---")
    st.caption(
        "**Data Sources:** Minneapolis Open Data — Assessor's Parcel Data · "
        "Minneapolis Neighborhood GeoJSON Boundaries · "
        "Minneapolis Area Association of Realtors (MAAR) · "
        "**Note:** Assessed values represent estimated market values from the "
        "Minneapolis City Assessor's Office. Actual sale prices may vary."
    )


if __name__ == "__main__":
    main()
