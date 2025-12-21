import streamlit as st
import pandas as pd
import altair as alt
from datetime import datetime, date
from pathlib import Path
import os
import sys
import json
from astropy.coordinates import SkyCoord
from astropy.units import deg, hourangle

# --- Page Configuration ---
st.set_page_config(
    page_title="FITS File Visualizer",
    page_icon="🔭",
    layout="wide",
)

# --- Helper Functions & Data Loading ---

@st.cache_data
def load_data():
    """Loads data from the Parquet file and caches it."""
    try:
        # Load data from the specified parquet file
        df = pd.read_parquet("fits_data.parquet")
        # Ensure date_obs is a datetime object, coercing errors
        df['date_obs'] = pd.to_datetime(df['date_obs'], errors='coerce')
        # Drop rows where date_obs could not be parsed
        df.dropna(subset=['date_obs'], inplace=True)
        return df
    except FileNotFoundError:
        st.error("Error: 'fits_data.parquet' not found. Make sure the Parquet file is in the same directory as the app.")
        return pd.DataFrame() # Return empty dataframe on error
    except Exception as e:
        st.error(f"An error occurred while loading the Parquet file: {e}")
        return pd.DataFrame()

# Load the main dataframe
df_main = load_data()

# --- Early exit if data loading failed ---
if df_main.empty:
    st.warning("The dataset is empty. Please check the data source.")
    st.stop()

# --- Get Filter Options from DataFrame ---
@st.cache_data
def get_filter_options_from_df(_df):
    """Gets distinct, sorted lists of filter options from the main DataFrame."""
    if _df.empty:
        return [], [], [], date.today(), date.today()
        
    object_names = sorted([name for name in _df['object_name'].unique() if name and name not in ['Unknown', 'flatwizard']])
    observatories = sorted([obs for obs in _df['observatory'].unique() if obs and obs != 'Unknown'])
    exptimes = sorted([et for et in _df['exptime'].unique() if et is not None])
    min_date = _df['date_obs'].min().date()
    max_date = _df['date_obs'].max().date()
    return object_names, observatories, exptimes, min_date, max_date

object_opts, obs_opts, exptime_opts, default_min_date, default_max_date = get_filter_options_from_df(df_main)


# --- State Management ---

def initialize_state():
    """Initializes session state for filters if they don't exist."""
    if 'object_names' not in st.session_state: st.session_state.object_names = []
    if 'observatories' not in st.session_state: st.session_state.observatories = []
    if 'exptimes' not in st.session_state: st.session_state.exptimes = []
    if 'date_range' not in st.session_state: st.session_state.date_range = (default_min_date, default_max_date)
    if 'min_altitude' not in st.session_state: st.session_state.min_altitude = 0
    if 'max_altitude' not in st.session_state: st.session_state.max_altitude = 90
    if 'selected_file' not in st.session_state: st.session_state.selected_file = None
    if 'object_click_filter' not in st.session_state: st.session_state.object_click_filter = None

def clear_all_filters():
    """Resets all filters to their default values."""
    st.session_state.object_names = []
    st.session_state.observatories = []
    st.session_state.exptimes = []
    st.session_state.date_range = (default_min_date, default_max_date)
    st.session_state.min_altitude = 0
    st.session_state.max_altitude = 90
    st.session_state.selected_file = None
    st.session_state.object_click_filter = None

initialize_state()

# --- UI Rendering ---

st.title("🔭 FITS File Catalog Visualizer")
st.write("This app visualizes FITS header data from a Parquet file. Use the filters to explore the data.")

# --- Click-to-filter state ---
is_object_filtered_by_click = st.session_state.object_click_filter is not None

with st.sidebar:
    st.header("Search Filters")

    st.multiselect(
        "Object Names",
        options=object_opts,
        key='object_names',
        disabled=is_object_filtered_by_click,
        help="Filter by object name. Disabled when an object is selected from the results table." if is_object_filtered_by_click else ""
    )
    st.multiselect("Observatories", options=obs_opts, key='observatories')
    st.multiselect("Exposure Times (s)", options=exptime_opts, key='exptimes')
    st.date_input("Observation Date Range", key='date_range', min_value=default_min_date, max_value=default_max_date)

    st.subheader("Altitude Filter")
    st.number_input("Minimum Altitude", key='min_altitude', min_value=0, max_value=90)
    st.number_input("Maximum Altitude", key='max_altitude', min_value=0, max_value=90)
    st.button("Clear All Filters", on_click=clear_all_filters, use_container_width=True)


# --- Main Content: Filtering the DataFrame ---

df = df_main.copy()

# Handle click-to-filter for object
if is_object_filtered_by_click:
    df = df[df['object_name'] == st.session_state.object_click_filter]

# Apply filters from sidebar
if st.session_state.object_names and not is_object_filtered_by_click:
    df = df[df['object_name'].isin(st.session_state.object_names)]
if st.session_state.observatories:
    df = df[df['observatory'].isin(st.session_state.observatories)]
if st.session_state.exptimes:
    df = df[df['exptime'].isin(st.session_state.exptimes)]
if st.session_state.min_altitude > 0 or st.session_state.max_altitude < 90:
    df = df[df['altitude'].between(st.session_state.min_altitude, st.session_state.max_altitude)]
if len(st.session_state.date_range) == 2:
    start_date, end_date = st.session_state.date_range
    start_datetime = pd.to_datetime(start_date)
    end_datetime = pd.to_datetime(end_date) + pd.Timedelta(days=1)
    df = df[df['date_obs'].between(start_datetime, end_datetime)]


try:
    # Display filter state if active
    if is_object_filtered_by_click:
        col1, col2 = st.columns([3, 1])
        with col1:
            st.info(f"Filtered on object: **{st.session_state.object_click_filter}**")
        with col2:
            if st.button("Clear Object Filter", use_container_width=True):
                st.session_state.object_click_filter = None
                st.rerun()

    st.info(f"Found **{len(df)}** matching files from your search criteria.")
    
    # Create a DataFrame for the sky plot from the filtered results
    if not df.empty:
        # The new columns ra_deg and dec_deg are already loaded.
        # We just need to drop rows where the coordinates are missing.
        df_coords = df.dropna(subset=['ra_deg', 'dec_deg']).copy()

    # --- Statistics Section ---
    if not df.empty:
        with st.expander("Show Statistics for Search Results", expanded=True):
            # --- Calculations for all metrics ---
            total_exposure_seconds = df['exptime'].sum()
            total_nights = df['date_obs'].dt.date.nunique()
            
            # Data for table and observatory chart
            distinct_objects_df = df['object_name'].value_counts().reset_index()
            distinct_objects_df.columns = ['Object Name', 'File Count']
            observatory_counts = df['observatory'].fillna('Unknown').value_counts()

            # --- Monthly Charts Calculation ---
            df_date_aware = df.copy()
            df_date_aware['month'] = df_date_aware['date_obs'].dt.to_period('M').dt.to_timestamp()
            
            # FITS count per month
            fits_by_month = df_date_aware.groupby('month').size().reset_index(name='fits_count')
            
            # Exposure time per month
            exposure_by_month = (df_date_aware.groupby('month')['exptime'].sum() / 3600).round(1).reset_index(name='exposure_hours')
            
            # Determine the full month range from the filtered data and fill gaps
            if not df_date_aware.empty:
                min_month, max_month = df_date_aware['month'].min(), df_date_aware['month'].max()
                all_months_range = pd.date_range(start=min_month, end=max_month, freq='MS')
                all_months_df = pd.DataFrame({'month': all_months_range})
                
                fits_df = pd.merge(all_months_df, fits_by_month, on='month', how='left').fillna(0)
                fits_df['fits_count'] = fits_df['fits_count'].astype(int)
                
                exposure_df = pd.merge(all_months_df, exposure_by_month, on='month', how='left').fillna(0)
            else:
                fits_df = pd.DataFrame({'month': [], 'fits_count': []})
                exposure_df = pd.DataFrame({'month': [], 'exposure_hours': []})

            # --- UI Layout for Stats ---
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Total Distinct Objects", len(distinct_objects_df))
            with col2:
                st.metric("Total Exposure Time", f"{total_exposure_seconds / 3600:.1f} h")
            with col3:
                st.metric("Total Nights", total_nights)

            st.divider()

            chart_col1, chart_col2, chart_col3 = st.columns(3)
            with chart_col1:
                st.markdown("###### FITS files per month")
                if not fits_df.empty:
                    chart = alt.Chart(fits_df).mark_bar().encode(
                        x=alt.X('month:T', axis=alt.Axis(title=None, format='%b %Y')),
                        y=alt.Y('fits_count:Q', axis=alt.Axis(title='Count'))
                    ).properties(height=200)
                    st.altair_chart(chart, use_container_width=True)
                else:
                    st.caption("No data for this period.")
            
            with chart_col2:
                st.markdown("###### Total Exposure Time per Month (h)")
                if not exposure_df.empty:
                    chart = alt.Chart(exposure_df).mark_bar().encode(
                        x=alt.X('month:T', axis=alt.Axis(title=None, format='%b %Y')),
                        y=alt.Y('exposure_hours:Q', axis=alt.Axis(title='Hours'))
                    ).properties(height=200)
                    st.altair_chart(chart, use_container_width=True)
                else:
                    st.caption("No data for this period.")

            with chart_col3:
                st.markdown("###### FITS files per observatory")
                if not observatory_counts.empty:
                    observatory_df = observatory_counts.reset_index()
                    observatory_df.columns = ['observatory', 'count']
                    chart = alt.Chart(observatory_df).mark_bar().encode(
                        x=alt.X('observatory:N', sort='-y', axis=alt.Axis(title=None, labelAngle=0)),
                        y=alt.Y('count:Q', axis=alt.Axis(title='Count'))
                    ).properties(height=200)
                    st.altair_chart(chart, use_container_width=True)
                else:
                    st.caption("No observatory data.")

            st.divider()

            # --- Celestial Coordinates Scatter Plot ---
            st.markdown("###### Milky Way Structure (Galactic Coordinates)")
            if 'df_coords' in locals() and not df_coords.empty:
                # --- Coordinate Transformation ---
                def get_galactic_coords(row):
                    try:
                        coord = SkyCoord(ra=row['ra_deg']*deg, dec=row['dec_deg']*deg, frame='icrs')
                        return coord.galactic.l.deg, coord.galactic.b.deg
                    except Exception:
                        return None, None
                
                df_coords[['galactic_l', 'galactic_b']] = df_coords.apply(get_galactic_coords, axis=1, result_type='expand')
                df_coords.dropna(subset=['galactic_l', 'galactic_b'], inplace=True)

                if not df_coords.empty:
                    legend_selection = alt.selection_multi(fields=['observatory'], bind='legend')

                    df_filtered_chart = df_coords[
                        ~df_coords['object_name'].isin(['Unknown', 'flatwizard']) &
                        df_coords['object_name'].notna()
                    ]

                    df_galactic_chart = df_filtered_chart.copy()
                    df_galactic_chart['l_wrapped'] = (df_galactic_chart['galactic_l'] + 180) % 360 - 180

                    mw_chart = alt.Chart(df_galactic_chart).mark_circle(size=10).encode(
                        x=alt.X('l_wrapped:Q', scale=alt.Scale(domain=[180, -180]), axis=alt.Axis(title='Galactic Longitude (l) [deg]')),
                        y=alt.Y('galactic_b:Q', scale=alt.Scale(domain=[-90, 90]), axis=alt.Axis(title='Galactic Latitude (b) [deg]')),
                        color=alt.Color('observatory:N', legend=alt.Legend(title="Observatory")),
                        opacity=alt.condition(legend_selection, alt.value(0.7), alt.value(0.1)),
                        tooltip=['object_name', 'observatory', 'l_wrapped', 'galactic_b', 'date_obs']
                    ).add_selection(
                        legend_selection
                    ).properties(
                        height=400
                    ).interactive()
                    
                    st.altair_chart(mw_chart, use_container_width=True)
                else:
                    st.info("No valid celestial coordinates could be calculated from the filtered data.")
            else:
                st.info("No valid celestial coordinates found in the current search results to display the sky plot.")
            
            with st.expander("Objects found in current search"):
                st.dataframe(distinct_objects_df, use_container_width=True)

    # --- Data Table and File Inspector ---
    if not df.empty:
        st.header("Search Results")
        display_columns = ["filename", "object_name", "date_obs", "exptime", "altitude", "observatory"]
        
        df_display = df[display_columns].copy()
        df_display['date_obs'] = df_display['date_obs'].dt.strftime('%d.%m.%Y %H:%M:%S')
        df_display['exptime'] = df_display['exptime'].map('{:,.1f}s'.format)
        df_display['altitude'] = df_display['altitude'].map('{:.2f}°'.format) if df['altitude'].notna().any() else 'N/A'
        
        st.dataframe(
            df_display, use_container_width=True, hide_index=True,
            on_select="rerun", selection_mode="single-row", key="results_df"
        )
        
        selection = st.session_state.get("results_df", {}).get("selection", {})
        if selection and selection.get("rows"):
            selected_row_index = selection["rows"][0]
            selected_object_name = df.iloc[selected_row_index]['object_name']
            
            if st.session_state.object_click_filter != selected_object_name:
                st.session_state.object_click_filter = selected_object_name
                st.rerun()

        # --- Header Inspector ---
        st.header("FITS Header Inspector")
        # Use the filtered dataframe `df` for file selection
        file_options = df['filepath'].tolist()
        
        # Check if a row is selected from the results dataframe
        selection = st.session_state.get("results_df", {}).get("selection", {})
        selected_filepath = None
        if selection and selection.get("rows"):
            selected_row_index = selection["rows"][0]
            selected_filepath = df.iloc[selected_row_index]['filepath']
            # Automatically set the selectbox to the clicked file
            if st.session_state.selected_file != selected_filepath:
                st.session_state.selected_file = selected_filepath

        st.selectbox(
            "Select a file to view its header:",
            options=file_options,
            key='selected_file',
            format_func=lambda x: Path(x).name if x else "...",
            index=file_options.index(st.session_state.selected_file) if st.session_state.selected_file in file_options else 0
        )
        
        if st.session_state.selected_file:
            header_data_str = df[df['filepath'] == st.session_state.selected_file]['header_dump'].iloc[0]
            try:
                # Try to parse the string into a dictionary for nice display
                header_data = json.loads(header_data_str)
                st.json(header_data, expanded=False)
            except (json.JSONDecodeError, TypeError):
                # If it fails, just show the raw string
                st.text(header_data_str)
        else:
            st.info("Select a file to see its header.")
            
    else:
        st.session_state.selected_file = None
        st.warning("No files match the current filter criteria.")

except Exception as e:
    st.error("An unexpected error occurred. See details below.")
    st.exception(e)
