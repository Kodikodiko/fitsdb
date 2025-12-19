import streamlit as st
import pandas as pd
import altair as alt
from datetime import datetime, date
from pathlib import Path
import socket
import uuid
import os
import sys
import json

# --- Page Configuration ---
st.set_page_config(
    page_title="FITS File Search (Static)",
    page_icon="🔭",
    layout="wide",
)

st.title("🔭 FITS File Catalog (Static Mode)")
st.write("This app reads data from a local `fits_data.parquet` file.")
st.info("To update the data, run `python export_data.py` in your terminal and refresh this page.")


# --- Helper Functions & Data Loading ---

@st.cache_data
def load_data(parquet_path='fits_data.parquet'):
    """Loads data from the Parquet file."""
    if not os.path.exists(parquet_path):
        st.error(f"Error: Data file '{parquet_path}' not found.")
        st.warning("Please run `python export_data.py` in your terminal to generate the data file, then refresh this page.")
        return pd.DataFrame()
    try:
        df = pd.read_parquet(parquet_path)
        # Ensure date_obs is a datetime object
        df['date_obs'] = pd.to_datetime(df['date_obs'])
        return df
    except Exception as e:
        st.error(f"Failed to read Parquet file: {e}")
        return pd.DataFrame()

@st.cache_data
def get_client_info() -> dict:
    """Gets local client info (hostname, MAC)."""
    try:
        mac_int = uuid.getnode()
        mac_address = ':'.join(f'{mac_int:012x}'[i:i+2] for i in range(0, 12, 2))
        return {'hostname': socket.gethostname(), 'mac': mac_address}
    except Exception:
        return {'hostname': 'unknown', 'mac': '00:00:00:00:00:00'}

@st.cache_data
def get_all_clients(df: pd.DataFrame):
    """Gets all unique clients from the DataFrame."""
    if df.empty or 'client_mac' not in df.columns:
        return {}
    clients = df[['client_hostname', 'client_mac']].drop_duplicates().dropna()
    return {mac: hostname for mac, hostname in clients.itertuples(index=False)}

# Load the main dataframe
fits_data = load_data()

# Only proceed if data is loaded successfully
if not fits_data.empty:
    current_client = get_client_info()
    all_clients_map = get_all_clients(fits_data)
    if current_client['mac'] not in all_clients_map:
        all_clients_map[current_client['mac']] = current_client['hostname']

    @st.cache_data
    def get_date_range(df: pd.DataFrame):
        """Gets the min and max observation date from the DataFrame."""
        if df.empty or 'date_obs' not in df.columns:
            return date.today(), date.today()
        min_date_val = df['date_obs'].min().date()
        max_date_val = df['date_obs'].max().date()
        return min_date_val, max_date_val

    default_min_date, default_max_date = get_date_range(fits_data)

    @st.cache_data
    def get_filter_options(df: pd.DataFrame, selected_clients_macs):
        """Gets filter options from the DataFrame based on selected clients."""
        filtered_df = df
        if selected_clients_macs:
            # Ensure 'client_mac' column exists before filtering
            if 'client_mac' in df.columns:
                filtered_df = df[df['client_mac'].isin(selected_clients_macs)]

        object_names = sorted([name for name in filtered_df['object_name'].dropna().unique() if name != 'Unknown'])
        observatories = sorted([name for name in filtered_df['observatory'].dropna().unique() if name != 'Unknown'])
        exptimes = sorted(filtered_df['exptime'].dropna().unique())
        
        return object_names, observatories, exptimes

    def initialize_state():
        if 'object_names' not in st.session_state: st.session_state.object_names = []
        if 'observatories' not in st.session_state: st.session_state.observatories = []
        if 'exptimes' not in st.session_state: st.session_state.exptimes = []
        if 'date_range' not in st.session_state or st.session_state.date_range[0] != default_min_date or st.session_state.date_range[1] != default_max_date:
            st.session_state.date_range = (default_min_date, default_max_date)
        if 'min_altitude' not in st.session_state: st.session_state.min_altitude = 0
        if 'max_altitude' not in st.session_state: st.session_state.max_altitude = 90
        if 'selected_file' not in st.session_state: st.session_state.selected_file = None
        if 'selected_clients' not in st.session_state: st.session_state.selected_clients = []
        if 'object_click_filter' not in st.session_state: st.session_state.object_click_filter = None

    def clear_all_filters():
        st.session_state.object_names = []
        st.session_state.observatories = []
        st.session_state.exptimes = []
        st.session_state.date_range = (default_min_date, default_max_date)
        st.session_state.min_altitude = 0
        st.session_state.max_altitude = 90
        st.session_state.selected_file = None
        st.session_state.selected_clients = []
        st.session_state.object_click_filter = None

    initialize_state()

    is_object_filtered_by_click = st.session_state.object_click_filter is not None

    with st.sidebar:
        st.header("Search Filters")
        st.multiselect("Clients", options=list(all_clients_map.keys()), key='selected_clients', format_func=lambda mac: f"{all_clients_map.get(mac, 'Unknown')} ({mac[-5:]})")
        object_opts, obs_opts, exptime_opts = get_filter_options(fits_data, st.session_state.selected_clients)
        st.multiselect("Object Names", options=object_opts, key='object_names', disabled=is_object_filtered_by_click, help="Disabled when an object is selected from the results table." if is_object_filtered_by_click else "")
        st.multiselect("Observatories", options=obs_opts, key='observatories')
        st.multiselect("Exposure Times (s)", options=exptime_opts, key='exptimes')
        st.date_input("Observation Date Range", key='date_range', min_value=default_min_date, max_value=default_max_date)
        st.subheader("Altitude Filter")
        st.number_input("Minimum Altitude", key='min_altitude', min_value=0, max_value=90)
        st.number_input("Maximum Altitude", key='max_altitude', min_value=0, max_value=90)
        st.button("Clear All Filters", on_click=clear_all_filters, use_container_width=True)

    # --- Main Content ---
    df = fits_data.copy()

    # Apply filters from sidebar
    if is_object_filtered_by_click:
        df = df[df['object_name'] == st.session_state.object_click_filter]
    if st.session_state.selected_clients:
        df = df[df['client_mac'].isin(st.session_state.selected_clients)]
    if st.session_state.object_names and not is_object_filtered_by_click:
        df = df[df['object_name'].isin(st.session_state.object_names)]
    if st.session_state.observatories:
        df = df[df['observatory'].isin(st.session_state.observatories)]
    if st.session_state.exptimes:
        df = df[df['exptime'].isin(st.session_state.exptimes)]
    if 'altitude' in df.columns and df['altitude'].notna().any() and (st.session_state.min_altitude > 0 or st.session_state.max_altitude < 90):
        df = df[df['altitude'].between(st.session_state.min_altitude, st.session_state.max_altitude)]
    if len(st.session_state.date_range) == 2:
        start_date, end_date = st.session_state.date_range
        start_datetime = datetime.combine(start_date, datetime.min.time())
        end_datetime = datetime.combine(end_date, datetime.max.time())
        df = df[df['date_obs'].between(start_datetime, end_datetime)]

    try:
        if is_object_filtered_by_click:
            col1, col2 = st.columns([3, 1])
            with col1:
                st.info(f"Filtered on object: **{st.session_state.object_click_filter}**")
            with col2:
                if st.button("Clear Object Filter", use_container_width=True):
                    st.session_state.object_click_filter = None
                    st.rerun()

        st.info(f"Found **{len(df)}** matching files.")

        if not df.empty:
            with st.expander("Show Statistics for Search Results", expanded=True):
                total_exposure_seconds = df['exptime'].sum()
                total_nights = pd.to_datetime(df['date_obs']).dt.date.nunique()
                df_date_aware = df.copy()
                df_date_aware['date_obs_dt'] = pd.to_datetime(df_date_aware['date_obs'])
                today_tz_unaware = datetime.now()

                last_full_month_end = today_tz_unaware.replace(day=1, hour=0, minute=0, second=0, microsecond=0) - pd.Timedelta(days=1)
                last_full_month_start = last_full_month_end.replace(day=1)
                comparison_month_start = last_full_month_start - pd.DateOffset(years=1)
                comparison_month_end = last_full_month_end - pd.DateOffset(years=1)

                nights_last_month = df_date_aware[(df_date_aware['date_obs_dt'] >= last_full_month_start) & (df_date_aware['date_obs_dt'] <= last_full_month_end)]['date_obs_dt'].dt.date.nunique()
                nights_comp_month = df_date_aware[(df_date_aware['date_obs_dt'] >= comparison_month_start) & (df_date_aware['date_obs_dt'] <= comparison_month_end)]['date_obs_dt'].dt.date.nunique()
                delta_nights = nights_last_month - nights_comp_month
                exp_last_month = df_date_aware[(df_date_aware['date_obs_dt'] >= last_full_month_start) & (df_date_aware['date_obs_dt'] <= last_full_month_end)]['exptime'].sum()
                exp_comp_month = df_date_aware[(df_date_aware['date_obs_dt'] >= comparison_month_start) & (df_date_aware['date_obs_dt'] <= comparison_month_end)]['exptime'].sum()
                delta_exp = exp_last_month - exp_comp_month
                
                distinct_objects_df = df['object_name'].value_counts().reset_index()
                distinct_objects_df.columns = ['Object Name', 'File Count']
                observatory_counts = df['observatory'].fillna('Unknown').value_counts()

                if not df_date_aware.empty:
                    df_date_aware['month'] = df_date_aware['date_obs_dt'].dt.to_period('M').dt.to_timestamp()
                    fits_by_month = df_date_aware.groupby('month').size().reset_index(name='fits_count')
                    exposure_by_month = (df_date_aware.groupby('month')['exptime'].sum() / 3600).round(1).reset_index(name='exposure_hours')
                    min_month, max_month = df_date_aware['month'].min(), df_date_aware['month'].max()
                    all_months_range = pd.date_range(start=min_month, end=max_month, freq='MS')
                    all_months_df = pd.DataFrame({'month': all_months_range})
                    fits_df_chart = pd.merge(all_months_df, fits_by_month, on='month', how='left').fillna(0)
                    fits_df_chart['fits_count'] = fits_df_chart['fits_count'].astype(int)
                    exposure_df_chart = pd.merge(all_months_df, exposure_by_month, on='month', how='left').fillna(0)
                else:
                    fits_df_chart, exposure_df_chart = pd.DataFrame({'month': [], 'fits_count': []}), pd.DataFrame({'month': [], 'exposure_hours': []})

                col1, col2, col3, col4, col5 = st.columns(5)
                with col1: st.metric("Total Distinct Objects", len(distinct_objects_df))
                with col2: st.metric("Total Exposure Time", f"{total_exposure_seconds / 3600:.1f} h")
                with col3: st.metric("Total Nights", total_nights)
                with col4: st.metric(f"Nights ({last_full_month_start.strftime('%b %Y')})", value=nights_last_month, delta=f"{delta_nights} vs prior year")
                with col5: st.metric(f"Exposure ({last_full_month_start.strftime('%b %Y')}) [h]", value=f"{exp_last_month / 3600:.1f}", delta=f"{(delta_exp / 3600):.1f}h vs prior year")
                st.divider()

                chart_col1, chart_col2, chart_col3 = st.columns(3)
                with chart_col1:
                    st.markdown("###### FITS files per month")
                    if not fits_df_chart.empty:
                        chart = alt.Chart(fits_df_chart).mark_bar().encode(x=alt.X('month:T', axis=alt.Axis(title=None, format='%b%y')), y=alt.Y('fits_count:Q', axis=alt.Axis(title='Count'))).properties(height=200)
                        st.altair_chart(chart, use_container_width=True)
                with chart_col2:
                    st.markdown("###### Total Exposure Time per Month (h)")
                    if not exposure_df_chart.empty:
                        chart = alt.Chart(exposure_df_chart).mark_bar().encode(x=alt.X('month:T', axis=alt.Axis(title=None, format='%b%y')), y=alt.Y('exposure_hours:Q', axis=alt.Axis(title='Hours'))).properties(height=200)
                        st.altair_chart(chart, use_container_width=True)
                with chart_col3:
                    st.markdown("###### FITS files per observatory")
                    if not observatory_counts.empty:
                        observatory_df = observatory_counts.reset_index()
                        observatory_df.columns = ['observatory', 'count']
                        chart = alt.Chart(observatory_df).mark_bar().encode(x=alt.X('observatory:N', sort='-y', axis=alt.Axis(title=None, labelAngle=0)), y=alt.Y('count:Q', axis=alt.Axis(title='Count'))).properties(height=200)
                        st.altair_chart(chart, use_container_width=True)

                with st.expander("Objects found in current search"):
                    st.dataframe(distinct_objects_df, use_container_width=True)

            st.header("Search Results")
            st.write("Click on a row in the table below to select a file.")
            display_columns = ["filename", "object_name", "date_obs", "exptime", "altitude", "observatory", "client_hostname"]
            df_display = df[display_columns].copy()
            df_display['date_obs'] = pd.to_datetime(df_display['date_obs']).dt.strftime('%d.%m.%Y %H:%M:%S')
            df_display['exptime'] = df_display['exptime'].map('{:,.1f}s'.format)
            if 'altitude' in df_display.columns:
                df_display['altitude'] = df_display['altitude'].map('{:.2f}°'.format) if df['altitude'].notna().any() else 'N/A'
            st.dataframe(df_display, use_container_width=True, hide_index=True, on_select="rerun", selection_mode="single-row", key="results_df")
            
            selection = st.session_state.get("results_df", {}).get("selection", {})
            if selection and selection.get("rows"):
                selected_row_index = selection["rows"][0]
                selected_object_name = df.iloc[selected_row_index]['object_name']
                if st.session_state.object_click_filter != selected_object_name:
                    st.session_state.object_click_filter = selected_object_name
                    st.rerun()

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

            st.header("FITS Header Inspector")
            file_options = df['filepath'].tolist()
            if 'selected_file' not in st.session_state or st.session_state.selected_file not in file_options:
                st.session_state.selected_file = None
            st.selectbox("Or select a file here to view its header:", options=file_options, key='selected_file', format_func=lambda x: Path(x).name if x else "...", index=None)
            
            if st.session_state.selected_file:
                header_data_str = df[df['filepath'] == st.session_state.selected_file]['header_dump'].iloc[0]
                try:
                    # The header dump was stored as a string, so we need to parse it back into a dict
                    header_data = json.loads(header_data_str.replace("'", "\""))
                    st.json(header_data)
                except (json.JSONDecodeError, TypeError):
                    st.text(header_data_str) # Show as raw text if it's not a valid JSON string
            else:
                st.write("Select a file from the list above to see its header.")
                
    except Exception as e:
        st.error(f"An error occurred: {e}")
        st.exception(e)

