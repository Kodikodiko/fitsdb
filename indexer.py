import os
import argparse
import json
from pathlib import Path
from datetime import datetime
import socket
import platform
import uuid
import time

from astropy.io import fits
from astropy.coordinates import SkyCoord, EarthLocation, AltAz
from astropy.time import Time
from astropy import units as u
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from database import SessionLocal, FitsFile

# --- Constants ---
# Default observatory location (Leopold Figl Observatory, Austria)
# Used if FITS header does not contain site coordinates.
DEFAULT_LOCATION = EarthLocation(lat=48.129*u.deg, lon=16.024*u.deg, height=940*u.m)

# --- Helper Functions ---

def get_client_info() -> dict:
    """Gathers information about the client machine."""
    try:
        # MAC address as a stable unique ID
        mac_int = uuid.getnode()
        mac_address = ':'.join(f'{mac_int:012x}'[i:i+2] for i in range(0, 12, 2))
        
        return {
            'hostname': socket.gethostname(),
            'os': f"{platform.system()} {platform.release()}",
            'mac': mac_address
        }
    except Exception:
        # Fallback in case of any errors
        return {
            'hostname': 'unknown',
            'os': 'unknown',
            'mac': '00:00:00:00:00:00'
        }


def calculate_altitude(header: fits.Header, location: EarthLocation) -> float | None:
    """
    Calculates the altitude of the observed object.
    """
    try:
        ra_str = header.get('RA') or header.get('OBJCTRA')
        dec_str = header.get('DEC') or header.get('OBJCTDEC')
        if ra_str is None or dec_str is None:
            return None

        coords = SkyCoord(ra_str, dec_str, unit=(u.hourangle, u.deg))
        date_obs_str = header.get('DATE-OBS')
        if not date_obs_str:
            return None
        time = Time(date_obs_str, format='isot', scale='utc')
        altaz_frame = AltAz(obstime=time, location=location)
        obj_altaz = coords.transform_to(altaz_frame)
        return float(obj_altaz.alt.deg)
    except (ValueError, KeyError, TypeError) as e:
        print(f"  - Warning: Could not calculate altitude. Error: {e}")
        return None


def process_fits_file(db: Session, file_path: Path, client_info: dict):
    """
    Reads a FITS file, extracts metadata, and upserts it into the database.
    """
    print(f"Processing: {file_path.name}")
    try:
        with fits.open(file_path) as hdul:
            header = hdul[0].header

            # --- Extract Metadata ---
            filepath_str = str(file_path.resolve())
            object_name = header.get('OBJECT', 'Unknown')
            date_obs_str = header.get('DATE-OBS')
            exptime = float(header.get('EXPTIME') or header.get('EXPOSURE', 0.0))
            observatory = header.get('OBSERVAT') or header.get('TELESCOP', 'Unknown')
            date_obs = None
            if date_obs_str:
                try:
                    date_obs = datetime.fromisoformat(date_obs_str)
                except ValueError:
                    print(f"  - Warning: Could not parse DATE-OBS '{date_obs_str}'. Skipping date.")

            # --- Calculate Altitude ---
            site_lat = header.get('SITELAT') or header.get('LATITUDE')
            site_lon = header.get('SITELON') or header.get('LONGITUD')
            location = DEFAULT_LOCATION
            if site_lat and site_lon:
                try:
                    location = EarthLocation.from_geodetic(lon=site_lon, lat=site_lat)
                except (u.UnitConversionError, ValueError):
                    print(f"  - Warning: Could not parse site coordinates. Using default.")
            
            altitude = calculate_altitude(header, location)

            # --- Prepare DB record ---
            header_dump = json.loads(json.dumps({k: str(v) for k, v in header.items()}))
            
            existing_file = db.query(FitsFile).filter(FitsFile.filepath == filepath_str).first()

            if existing_file:
                print("  - File exists. Updating record.")
                record = existing_file
            else:
                print("  - New file. Creating record.")
                record = FitsFile(filepath=filepath_str, filename=file_path.name)
                db.add(record)

            # Update all fields
            record.object_name = object_name
            record.date_obs = date_obs
            record.exptime = exptime
            record.altitude = altitude
            record.observatory = observatory
            record.header_dump = header_dump
            # Add client info
            record.client_hostname = client_info['hostname']
            record.client_os = client_info['os']
            record.client_mac = client_info['mac']
            
            db.commit()

    except FileNotFoundError:
        print(f"  - Error: File not found.")
    except OSError as e:
        print(f"  - Error: Could not read file (possibly corrupt). Skipping. Details: {e}")
    except SQLAlchemyError as e:
        print(f"  - Error: Database operation failed. Rolling back. Details: {e}")
        db.rollback()
    except Exception as e:
        print(f"  - An unexpected error occurred: {e}")
        db.rollback()


def run_indexer(root_directory: str):
    """
    Scans a directory for FITS files and indexes them.
    """
    client_info = get_client_info()
    print("--- Client Information ---")
    print(f"Hostname: {client_info['hostname']}")
    print(f"OS: {client_info['os']}")
    print(f"MAC Address: {client_info['mac']}")
    print("--------------------------")
    
    print(f"Starting indexer for directory: {root_directory}")
    db = SessionLocal()
    
    extensions = ('.fits', '.fit', '.fts')
    print(f"Phase 1: Recursively searching for files with extensions: {extensions}...")

    files_to_process = []
    try:
        for dirpath, _, filenames in os.walk(root_directory):
            for filename in filenames:
                if filename.lower().endswith(extensions):
                    files_to_process.append(Path(dirpath) / filename)
    except Exception as e:
        print(f"An error occurred during file search: {e}")
        db.close()
        return

    total_found = len(files_to_process)
    if total_found == 0:
        print("No matching FITS files found in the specified directory.")
        db.close()
        return

    print(f"Phase 1 Complete: Found {total_found} potential FITS files.")
    print(f"Phase 2: Processing and indexing files...\n")

    start_time = time.time()

    for i, file_path in enumerate(files_to_process):
        files_processed = i + 1
        print(f"--- Processing file {files_processed}/{total_found} ---")
        process_fits_file(db, file_path, client_info)

        # Alle 100 Dateien eine Schätzung ausgeben
        if files_processed % 100 == 0 and i > 0:
            elapsed_time = time.time() - start_time
            avg_time_per_file = elapsed_time / files_processed
            files_remaining = total_found - files_processed
            eta_seconds = files_remaining * avg_time_per_file
            
            # Umwandlung in Stunden, Minuten, Sekunden
            eta_h = int(eta_seconds // 3600)
            eta_m = int((eta_seconds % 3600) // 60)
            eta_s = int(eta_seconds % 60)

            print("\n" + "="*50)
            print(f"PROGRESS: {files_processed} / {total_found} files indexed.")
            print(f"ESTIMATED TIME REMAINING: {eta_h}h {eta_m}m {eta_s}s")
            print("="*50 + "\n")
    
    db.close()
    print("\nIndexing complete.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Scan a directory and index FITS files into a PostgreSQL database.\n"
                    "If no directory is provided as an argument, the script will prompt for it interactively."
    )
    parser.add_argument(
        "directory",
        nargs="?",
        default=None,
        type=str,
        help="(Optional) The root directory to start scanning for FITS files.",
    )
    args = parser.parse_args()

    scan_directory = args.directory

    if not scan_directory:
        while True:
            try:
                path_input = input("Please enter the root directory to scan: ")
                scan_directory = Path(path_input)
                if scan_directory.is_dir():
                    break
                else:
                    print(f"Error: The path '{scan_directory}' is not a valid directory. Please try again.")
            except KeyboardInterrupt:
                print("\nOperation cancelled by user.")
                exit()

    if not Path(scan_directory).is_dir():
        print(f"Error: Directory '{scan_directory}' not found.")
    else:
        run_indexer(str(scan_directory))