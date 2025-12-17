import os
import argparse
import json
from pathlib import Path
from datetime import datetime
import socket
import platform
import uuid
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

from astropy.io import fits
from astropy.coordinates import SkyCoord, EarthLocation, AltAz
from astropy.time import Time
from astropy import units as u
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from tqdm import tqdm

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
        # This function can be called from multiple threads, printing directly can jumble output.
        # In a more complex app, logging to a file would be better. For now, we return None.
        # print(f"  - Warning: Could not calculate altitude for {header.get('OBJECT', 'Unknown')}. Error: {e}")
        return None


def process_fits_file(file_path: Path, client_info: dict, scan_root: str) -> str:
    """
    Reads a FITS file, extracts metadata, and upserts it into the database.
    This function is designed to be thread-safe by managing its own DB session.
    """
    db = SessionLocal()
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
                    # Could not parse date
                    pass

            # --- Calculate Altitude ---
            site_lat = header.get('SITELAT') or header.get('LATITUDE')
            site_lon = header.get('SITELON') or header.get('LONGITUD')
            location = DEFAULT_LOCATION
            if site_lat and site_lon:
                try:
                    location = EarthLocation.from_geodetic(lon=site_lon, lat=site_lat)
                except (u.UnitConversionError, ValueError):
                    pass # Could not parse coords
            
            altitude = calculate_altitude(header, location)

            # --- Prepare DB record ---
            header_dump = json.loads(json.dumps({k: str(v) for k, v in header.items()}))
            
            existing_file = db.query(FitsFile).filter(FitsFile.filepath == filepath_str).first()

            if existing_file:
                record = existing_file
                status = "Updated"
            else:
                record = FitsFile(filepath=filepath_str, filename=file_path.name)
                db.add(record)
                status = "Created"

            # Update all fields
            record.object_name = object_name
            record.date_obs = date_obs
            record.exptime = exptime
            record.altitude = altitude
            record.observatory = observatory
            record.header_dump = header_dump
            record.scan_root = scan_root
            record.client_hostname = client_info['hostname']
            record.client_os = client_info['os']
            record.client_mac = client_info['mac']
            
            db.commit()
            return f"{status}: {file_path.name}"

    except Exception as e:
        db.rollback()
        return f"Error processing {file_path.name}: {e}"
    finally:
        db.close()


def run_indexer(root_directory: str, max_workers: int):
    """
    Scans a directory for FITS files and indexes them concurrently.
    """
    client_info = get_client_info()
    print("--- Client Information ---")
    print(f"Hostname: {client_info['hostname']}")
    print(f"OS: {client_info['os']}")
    print(f"MAC Address: {client_info['mac']}")
    print("--------------------------")
    
    print(f"Starting indexer for directory: {root_directory}")
    
    extensions = ('.fits', '.fit', '.fts')
    print(f"Phase 1: Recursively searching for files with extensions: {extensions}...")

    try:
        files_to_process = [Path(dirpath) / filename 
                            for dirpath, _, filenames in os.walk(root_directory) 
                            for filename in filenames if filename.lower().endswith(extensions)]
    except Exception as e:
        print(f"An error occurred during file search: {e}")
        return

    total_found = len(files_to_process)
    if total_found == 0:
        print("No matching FITS files found in the specified directory.")
        return

    print(f"Phase 1 Complete: Found {total_found} potential FITS files.")
    print(f"Phase 2: Processing and indexing files with up to {max_workers} concurrent workers...\n")

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Submit all tasks to the executor
        futures = {executor.submit(process_fits_file, fp, client_info, root_directory) for fp in files_to_process}

        # Process results as they complete with a progress bar
        for future in tqdm(as_completed(futures), total=total_found, desc="Indexing Files", unit="file"):
            try:
                result = future.result()
                # Optionally, you can log the result to a file if the output is too noisy.
                # tqdm.write(result) 
            except Exception as e:
                tqdm.write(f"A task generated an exception: {e}")
    
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
    parser.add_argument(
        "-w", "--workers",
        type=int,
        default=8,
        help="Number of concurrent worker threads to use for indexing. Default is 8."
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
        run_indexer(str(scan_directory), max_workers=args.workers)