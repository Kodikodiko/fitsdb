import streamlit as st
import pandas as pd
import altair as alt
from sqlalchemy import func
from datetime import datetime, date
from pathlib import Path
import socket
import uuid
import os
import sys

from database import SessionLocal, FitsFile

# --- Page Configuration ---
st.set_page_config(
    page_title="FITS File Search",
    page_icon="🔭",
    layout="wide",
)

# --- Helper Functions & Data Loading ---

@st.cache_resource
def get_db_session():
    return SessionLocal()

@st.cache_data
def get_client_info() -> dict:
    try:
        mac_int = uuid.getnode()
        mac_address = ':'.join(f'{mac_int:012x}'[i:i+2] for i in range(0, 12, 2))
        return {'hostname': socket.gethostname(), 'mac': mac_address}
    except Exception:
        return {'hostname': 'unknown', 'mac': '00:00:00:00:00:00'}

@st.cache_data
def get_all_clients(_db_session_id):
    db = get_db_session()
    clients = db.query(FitsFile.client_hostname, FitsFile.client_mac).distinct().all()
    return {mac: hostname for hostname, mac in clients if mac}

db = get_db_session()
current_client = get_client_info()
all_clients_map = get_all_clients(id(db))
if current_client['mac'] not in all_clients_map:
    all_clients_map[current_client['mac']] = current_client['hostname']

@st.cache_data
def get_date_range(_db_session_id):
    min_date_db, max_date_db = db.query(func.min(FitsFile.date_obs), func.max(FitsFile.date_obs)).first()
    return min_date_db or date.today(), max_date_db or date.today()

default_min_date, default_max_date = get_date_range(id(db))

# --- State Management ---

@st.cache_data
def get_filter_options(_db_session_id, selected_clients_macs):
    """Queries the DB for distinct, sorted lists of filter options."""
    db = get_db_session()
    query = db.query(FitsFile)
    if selected_clients_macs:
        query = query.filter(FitsFile.client_mac.in_(selected_clients_macs))

    # Query for distinct, non-null, non-empty values and sort them
    object_names = sorted([r[0] for r in query.with_entities(FitsFile.object_name).distinct().all() if r[0] and r[0] != 'Unknown'])
    observatories = sorted([r[0] for r in query.with_entities(FitsFile.observatory).distinct().all() if r[0] and r[0] != 'Unknown'])
    exptimes = sorted([r[0] for r in query.with_entities(FitsFile.exptime).distinct().all() if r[0] is not None])
    
    return object_names, observatories, exptimes

# --- State Management ---

def initialize_state():
    """Initializes session state for filters if they don't exist."""
    # Multi-select filters
    if 'object_names' not in st.session_state: st.session_state.object_names = []
    if 'observatories' not in st.session_state: st.session_state.observatories = []
    if 'exptimes' not in st.session_state: st.session_state.exptimes = []
    
    # Other filters from original app
    if 'date_range' not in st.session_state: st.session_state.date_range = (default_min_date, default_max_date)
    if 'min_altitude' not in st.session_state: st.session_state.min_altitude = 0
    if 'max_altitude' not in st.session_state: st.session_state.max_altitude = 90
    if 'selected_file' not in st.session_state: st.session_state.selected_file = None
    if 'selected_clients' not in st.session_state:
        st.session_state.selected_clients = [] # No client selected by default
    if 'object_click_filter' not in st.session_state: 
        st.session_state.object_click_filter = None

def clear_all_filters():
    """Resets all filters to their default values."""
    st.session_state.object_names = []
    st.session_state.observatories = []
    st.session_state.exptimes = []
    st.session_state.date_range = (default_min_date, default_max_date)
    st.session_state.min_altitude = 0
    st.session_state.max_altitude = 90
    st.session_state.selected_file = None
    st.session_state.selected_clients = [] # No client selected by default
    st.session_state.object_click_filter = None
    # Dataframe selections are cleared automatically on rerun

initialize_state()

# --- UI Rendering ---

st.title("🔭 FITS File Catalog Search")
st.write("Use the filters in the sidebar to search the catalog of indexed FITS files.")

# --- Click-to-filter state ---
is_object_filtered_by_click = st.session_state.object_click_filter is not None

with st.sidebar:
    st.header("Search Filters")
    st.multiselect(
        "Clients", options=list(all_clients_map.keys()), key='selected_clients',
        format_func=lambda mac: f"{all_clients_map.get(mac, 'Unknown')} ({mac[-5:]})",
        help="Select one or more clients. The filters below will update based on your selection."
    )

    # Get filter options based on selected clients
    object_opts, obs_opts, exptime_opts = get_filter_options(id(db), st.session_state.selected_clients)

    st.multiselect(
        "Object Names", 
        options=object_opts, 
        key='object_names',
        disabled=is_object_filtered_by_click,
        help="Disabled when an object is selected from the results table." if is_object_filtered_by_click else ""
    )
    st.multiselect("Observatories", options=obs_opts, key='observatories')
    st.multiselect("Exposure Times (s)", options=exptime_opts, key='exptimes', help="Select specific exposure times.")

    st.date_input("Observation Date Range", key='date_range', min_value=default_min_date, max_value=default_max_date)
    
    st.subheader("Altitude Filter")
    st.number_input("Minimum Altitude", key='min_altitude', min_value=0, max_value=90)
    st.number_input("Maximum Altitude", key='max_altitude', min_value=0, max_value=90)
    st.button("Clear All Filters", on_click=clear_all_filters, use_container_width=True)

# --- Main Content ---

# Base query
query = db.query(FitsFile)

# Handle click-to-filter for object
if is_object_filtered_by_click:
    query = query.filter(FitsFile.object_name == st.session_state.object_click_filter)

# Apply filters from sidebar
if st.session_state.selected_clients:
    query = query.filter(FitsFile.client_mac.in_(st.session_state.selected_clients))
if st.session_state.object_names and not is_object_filtered_by_click: # Only apply if not click-filtered
    query = query.filter(FitsFile.object_name.in_(st.session_state.object_names))
if st.session_state.observatories:
    query = query.filter(FitsFile.observatory.in_(st.session_state.observatories))
if st.session_state.exptimes:
    query = query.filter(FitsFile.exptime.in_(st.session_state.exptimes))
if st.session_state.min_altitude > 0 or st.session_state.max_altitude < 90:
    query = query.filter(FitsFile.altitude.between(st.session_state.min_altitude, st.session_state.max_altitude))
if len(st.session_state.date_range) == 2:
    start_date, end_date = st.session_state.date_range
    start_datetime = datetime.combine(start_date, datetime.min.time())
    end_datetime = datetime.combine(end_date, datetime.max.time())
    query = query.filter(FitsFile.date_obs.between(start_datetime, end_datetime))

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

    df = pd.read_sql(query.statement, query.session.bind)
    st.info(f"Found **{len(df)}** matching files from **{len(st.session_state.selected_clients)}** selected client(s).")

    # --- Statistics Section ---
    if not df.empty:
        with st.expander("Show Statistics for Search Results", expanded=True):
            # --- Calculations for all metrics ---
            total_exposure_seconds = df['exptime'].sum()
            total_nights = pd.to_datetime(df['date_obs']).dt.date.nunique()

            df_date_aware = df.copy()
            df_date_aware['date_obs_dt'] = pd.to_datetime(df['date_obs']).dt.tz_localize(None)
            today_tz_unaware = datetime.now()

            # Define time ranges for top metrics
            last_full_month_end = today_tz_unaware.replace(day=1, hour=0, minute=0, second=0, microsecond=0) - pd.Timedelta(days=1)
            last_full_month_start = last_full_month_end.replace(day=1)
            comparison_month_start = last_full_month_start - pd.DateOffset(years=1)
            comparison_month_end = last_full_month_end - pd.DateOffset(years=1)

            # Calculate comparison metrics for top row
            nights_last_month = df_date_aware[(df_date_aware['date_obs_dt'] >= last_full_month_start) & (df_date_aware['date_obs_dt'] <= last_full_month_end)]['date_obs_dt'].dt.date.nunique()
            nights_comp_month = df_date_aware[(df_date_aware['date_obs_dt'] >= comparison_month_start) & (df_date_aware['date_obs_dt'] <= comparison_month_end)]['date_obs_dt'].dt.date.nunique()
            delta_nights = nights_last_month - nights_comp_month

            exp_last_month = df_date_aware[(df_date_aware['date_obs_dt'] >= last_full_month_start) & (df_date_aware['date_obs_dt'] <= last_full_month_end)]['exptime'].sum()
            exp_comp_month = df_date_aware[(df_date_aware['date_obs_dt'] >= comparison_month_start) & (df_date_aware['date_obs_dt'] <= comparison_month_end)]['exptime'].sum()
            delta_exp = exp_last_month - exp_comp_month
            
            
            # Data for table and observatory chart
            distinct_objects_df = df['object_name'].value_counts().reset_index()
            distinct_objects_df.columns = ['Object Name', 'File Count']
            observatory_counts = df['observatory'].fillna('Unknown').value_counts()

            # --- Monthly Charts Calculation ---
            if not df_date_aware.empty:
                df_date_aware['month'] = df_date_aware['date_obs_dt'].dt.to_period('M').dt.to_timestamp()
                
                # FITS count per month
                fits_by_month = df_date_aware.groupby('month').size().reset_index(name='fits_count')
                
                # Exposure time per month
                exposure_by_month = (df_date_aware.groupby('month')['exptime'].sum() / 3600).round(1).reset_index(name='exposure_hours')
                
                # Determine the full month range from the filtered data and fill gaps
                min_month = df_date_aware['month'].min()
                max_month = df_date_aware['month'].max()
                all_months_range = pd.date_range(start=min_month, end=max_month, freq='MS')
                all_months_df = pd.DataFrame({'month': all_months_range})
                
                fits_df = pd.merge(all_months_df, fits_by_month, on='month', how='left').fillna(0)
                fits_df['fits_count'] = fits_df['fits_count'].astype(int)
                
                exposure_df = pd.merge(all_months_df, exposure_by_month, on='month', how='left').fillna(0)
            else:
                fits_df = pd.DataFrame({'month': [], 'fits_count': []})
                exposure_df = pd.DataFrame({'month': [], 'exposure_hours': []})


            # --- UI Layout ---
            col1, col2, col3, col4, col5 = st.columns(5)
            with col1:
                st.metric("Total Distinct Objects", len(distinct_objects_df))
            with col2:
                st.metric("Total Exposure Time", f"{total_exposure_seconds / 3600:.1f} h")
            with col3:
                st.metric("Total Nights", total_nights)
            with col4:
                st.metric(f"Nights ({last_full_month_start.strftime('%b %Y')})", value=nights_last_month, delta=f"{delta_nights} vs prior year")
            with col5:
                st.metric(f"Exposure ({last_full_month_start.strftime('%b %Y')}) [h]", value=f"{exp_last_month / 3600:.1f}", delta=f"{(delta_exp / 3600):.1f}h vs prior year")

            st.divider()

            chart_col1, chart_col2, chart_col3 = st.columns(3)
            with chart_col1:
                st.markdown("###### FITS files per month")
                if not fits_df.empty:
                    chart = alt.Chart(fits_df).mark_bar().encode(
                        x=alt.X('month:T', axis=alt.Axis(title=None, format='%b%y')),
                        y=alt.Y('fits_count:Q', axis=alt.Axis(title='Count'))
                    ).properties(height=200)
                    st.altair_chart(chart, use_container_width=True)
                else:
                    st.bar_chart(pd.Series(dtype='float64'), height=200)
            
            with chart_col2:
                st.markdown("###### Total Exposure Time per Month (h)")
                if not exposure_df.empty:
                    chart = alt.Chart(exposure_df).mark_bar().encode(
                        x=alt.X('month:T', axis=alt.Axis(title=None, format='%b%y')),
                        y=alt.Y('exposure_hours:Q', axis=alt.Axis(title='Hours'))
                    ).properties(height=200)
                    st.altair_chart(chart, use_container_width=True)
                else:
                    st.bar_chart(pd.Series(dtype='float64'), height=200)

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
                    st.bar_chart(pd.Series(dtype='float64'), height=200)

            with st.expander("Objects found in current search"):
                st.dataframe(distinct_objects_df, use_container_width=True)


    if not df.empty:
        st.header("Search Results")
        st.write("Click on a row in the table below to select a file.")
        display_columns = ["filename", "object_name", "date_obs", "exptime", "altitude", "observatory", "client_hostname"]
        
        df_display = df[display_columns].copy()
        df_display['date_obs'] = pd.to_datetime(df_display['date_obs']).dt.strftime('%d.%m.%Y %H:%M:%S')
        df_display['exptime'] = df_display['exptime'].map('{:,.1f}s'.format)
        df_display['altitude'] = df_display['altitude'].map('{:.2f}°'.format) if df['altitude'].notna().any() else 'N/A'
        
        st.dataframe(
            df_display, use_container_width=True, hide_index=True,
            on_select="rerun", selection_mode="single-row", key="results_df"
        )
        
        # --- Handle row selection for filtering ---
        selection = st.session_state.get("results_df", {}).get("selection", {})
        if selection and selection.get("rows"):
            selected_row_index = selection["rows"][0]
            selected_object_name = df.iloc[selected_row_index]['object_name']
            
            # If the user selected a new object, update the filter and rerun
            if st.session_state.object_click_filter != selected_object_name:
                st.session_state.object_click_filter = selected_object_name
                st.rerun()

        # --- File Opener Section ---
        selection = st.session_state.get("results_df", {}).get("selection", {})
        if selection and selection.get("rows"):
            selected_row_index = selection["rows"][0]
            # Use .iloc on the original dataframe `df` to get the real data
            filepath_to_open = df.iloc[selected_row_index]['filepath']
            filename_to_open = df.iloc[selected_row_index]['filename']
            
            st.divider()
            col1, col2 = st.columns([3, 1])
            with col1:
                st.subheader(f"Open File: `{filename_to_open}`")
                st.caption(filepath_to_open)
            with col2:
                st.write("") # Spacer
                if st.button("Ausgewählte Datei öffnen", use_container_width=True):
                    if sys.platform == "win32":
                        try:
                            os.startfile(filepath_to_open)
                            st.success(f"Sent command to open '{filename_to_open}'.")
                        except FileNotFoundError:
                            st.error(f"File not found at path: {filepath_to_open}. Is the drive mounted correctly?")
                        except Exception as e:
                            st.error(f"Failed to open file: {e}")
                    else:
                        st.warning(f"File opening is only supported on Windows. Your OS: {sys.platform}")
            st.divider()

        # --- Header Inspector ---
        st.header("FITS Header Inspector")
        file_options = df['filepath'].tolist()
        # Ensure the selected file is valid, otherwise reset it
        if st.session_state.selected_file not in file_options:
            st.session_state.selected_file = None

        st.selectbox(
            "Or select a file here to view its header:",
            options=file_options,
            key='selected_file',
            format_func=lambda x: Path(x).name if x else "...",
            index=None # Set default to empty
        )
        
        if st.session_state.selected_file:
            header_data = df[df['filepath'] == st.session_state.selected_file]['header_dump'].iloc[0]
            st.json(header_data)
        else:
            st.write("Select a file from the list above to see its header.")
            
    else:
        st.session_state.selected_file = None

except Exception as e:
    st.error(f"An error occurred: {e}")
    st.exception(e)

