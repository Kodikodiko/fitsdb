import streamlit as st
import pandas as pd
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

def initialize_state():
    """Initializes session state for filters if they don't exist."""
    if 'object_name' not in st.session_state: st.session_state.object_name = ""
    if 'date_range' not in st.session_state: st.session_state.date_range = (default_min_date, default_max_date)
    if 'min_exptime' not in st.session_state: st.session_state.min_exptime = 0.0
    if 'min_altitude' not in st.session_state: st.session_state.min_altitude = 0
    if 'max_altitude' not in st.session_state: st.session_state.max_altitude = 90
    if 'selected_file' not in st.session_state: st.session_state.selected_file = None
    if 'selected_clients' not in st.session_state:
        st.session_state.selected_clients = [current_client['mac']] if current_client['mac'] in all_clients_map else []
    # DO NOT initialize widget state like this: 'results_df'

def clear_all_filters():
    """Resets all filters to their default values."""
    st.session_state.object_name = ""
    st.session_state.date_range = (default_min_date, default_max_date)
    st.session_state.min_exptime = 0.0
    st.session_state.min_altitude = 0
    st.session_state.max_altitude = 90
    st.session_state.selected_file = None
    st.session_state.selected_clients = [current_client['mac']] if current_client['mac'] in all_clients_map else []
    # To clear a dataframe's selection, we need to re-render it with an empty selection list,
    # which will happen automatically on the next run after filters change.
    # We cannot assign to st.session_state.results_df directly.

initialize_state()

# --- UI Rendering ---

st.title("🔭 FITS File Catalog Search")
st.write("Use the filters in the sidebar to search the catalog of indexed FITS files.")

with st.sidebar:
    st.header("Search Filters")
    st.multiselect(
        "Clients", options=list(all_clients_map.keys()), key='selected_clients',
        format_func=lambda mac: f"{all_clients_map.get(mac, 'Unknown')} ({mac[-5:]})",
        help="Select one or more clients. Defaults to the current machine."
    )
    st.text_input("Object Name (case-insensitive)", key='object_name')
    st.date_input("Observation Date Range", key='date_range', min_value=default_min_date, max_value=default_max_date)
    st.number_input("Minimum Exposure Time (seconds)", key='min_exptime', min_value=0.0, step=1.0)
    st.subheader("Altitude Filter")
    st.number_input("Minimum Altitude", key='min_altitude', min_value=0, max_value=90)
    st.number_input("Maximum Altitude", key='max_altitude', min_value=0, max_value=90)
    st.button("Clear All Filters", on_click=clear_all_filters, use_container_width=True)

# --- Main Content ---

query = db.query(FitsFile)
if st.session_state.selected_clients:
    query = query.filter(FitsFile.client_mac.in_(st.session_state.selected_clients))
if st.session_state.object_name:
    query = query.filter(FitsFile.object_name.ilike(f"%{st.session_state.object_name}%"))
if st.session_state.min_exptime > 0:
    query = query.filter(FitsFile.exptime >= st.session_state.min_exptime)
if st.session_state.min_altitude > 0 or st.session_state.max_altitude < 90:
    query = query.filter(FitsFile.altitude.between(st.session_state.min_altitude, st.session_state.max_altitude))
if len(st.session_state.date_range) == 2:
    start_date, end_date = st.session_state.date_range
    start_datetime = datetime.combine(start_date, datetime.min.time())
    end_datetime = datetime.combine(end_date, datetime.max.time())
    query = query.filter(FitsFile.date_obs.between(start_datetime, end_datetime))

try:
    df = pd.read_sql(query.statement, query.session.bind)
    st.info(f"Found **{len(df)}** matching files from **{len(st.session_state.selected_clients)}** selected client(s).")

    if not df.empty:
        st.header("Search Results")
        st.write("Click on a row in the table below to select a file.")
        display_columns = ["filename", "object_name", "date_obs", "exptime", "altitude", "observatory", "client_hostname"]
        
        df_display = df[display_columns].copy()
        df_display['date_obs'] = pd.to_datetime(df_display['date_obs']).dt.strftime('%d.%m.%Y %H:%M:%S')
        df_display['exptime'] = df_display['exptime'].map('{:,.2f}s'.format)
        df_display['altitude'] = df_display['altitude'].map('{:.2f}°'.format) if df['altitude'].notna().any() else 'N/A'
        
        st.dataframe(
            df_display, use_container_width=True, hide_index=True,
            on_select="rerun", selection_mode="single-row", key="results_df"
        )

        # --- File Opener Section ---
        selection = None
        if "results_df" in st.session_state:
            selection = st.session_state.results_df.selection

        if selection and selection["rows"]:
            selected_row_index = selection["rows"][0]
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
                            st.error(f"File not found at path: {filepath_to_open}")
                        except Exception as e:
                            st.error(f"Failed to open file: {e}")
                    else:
                        st.warning(f"File opening is only supported on Windows. Your OS: {sys.platform}")
            st.divider()

        # --- Header Inspector ---
        st.header("FITS Header Inspector")
        file_options = df['filepath'].tolist()
        if st.session_state.selected_file not in file_options:
            st.session_state.selected_file = None

        st.selectbox(
            "Or select a file here to view its header:",
            options=file_options,
            key='selected_file',
            format_func=lambda x: Path(x).name if x else "...",
        )
        
        if st.session_state.selected_file:
            header_data = df[df['filepath'] == st.session_state.selected_file]['header_dump'].iloc[0]
            st.json(header_data)
        else:
            st.write("Select a file from the list above to see its header.")
            
    # This else block runs if df is empty
    else:
        # If the dataframe is empty, there can be no selection.
        # We don't need to do anything here regarding 'results_df' state.
        st.session_state.selected_file = None


except Exception as e:
    st.error(f"An error occurred: {e}")
    st.exception(e)
