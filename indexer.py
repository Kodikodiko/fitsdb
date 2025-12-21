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


def extract_and_convert_coords(header: fits.Header) -> tuple[float | None, float | None, SkyCoord | None]:
    """Extracts RA/DEC from FITS header and converts to decimal degrees."""
    ra_str = header.get('RA') or header.get('OBJCTRA')
    dec_str = header.get('DEC') or header.get('OBJCTDEC')
    try:
        if ra_str and dec_str:
            # Ensure values are strings for SkyCoord
            coords = SkyCoord(str(ra_str), str(dec_str), unit=(u.hourangle, u.deg), frame='icrs')
            # Explicitly cast to Python floats to prevent numpy type issues with SQLAlchemy
            return float(coords.ra.deg), float(coords.dec.deg), coords
    except (ValueError, TypeError, AttributeError) as e:
        # VERBOSE LOGGING: Print the error and the problematic values
        tqdm.write(f"Coordinate parse error: {e}. RA: '{ra_str}', DEC: '{dec_str}'")
        pass
    return None, None, None


def calculate_altitude(header: fits.Header, location: EarthLocation, coords: SkyCoord | None) -> float | None:
    """
    Calculates the altitude of the observed object.
    """
    try:
        if coords is None:
            return None
        date_obs_str = header.get('DATE-OBS')
        if not date_obs_str:
            return None
        time = Time(date_obs_str, format='isot', scale='utc')
        altaz_frame = AltAz(obstime=time, location=location)
        obj_altaz = coords.transform_to(altaz_frame)
        return float(obj_altaz.alt.deg)
    except (ValueError, KeyError, TypeError) as e:
        tqdm.write(f"Altitude calculation error: {e} for object {header.get('OBJECT')}")
        return None


def process_fits_file(file_path: Path, client_info: dict, scan_root: str) -> str:
    """
    Reads a FITS file, extracts metadata, and upserts it into the database.
    This function is designed to be thread-safe by managing its own DB session.
    """
    db = SessionLocal()
    try:
        with fits.open(file_path, 'readonly', memmap=False) as hdul:
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
                except (ValueError, TypeError):
                    pass

            # --- Coordinates and Altitude ---
            ra_deg, dec_deg, coords = extract_and_convert_coords(header)
            
            site_lat = header.get('SITELAT') or header.get('LATITUDE')
            site_lon = header.get('SITELON') or header.get('LONGITUD')
            location = DEFAULT_LOCATION
            if site_lat and site_lon:
                try:
                    location = EarthLocation.from_geodetic(lon=str(site_lon), lat=str(site_lat))
                except (u.UnitConversionError, ValueError):
                    pass
            
            altitude = calculate_altitude(header, location, coords)

            # --- Prepare DB record ---
            # Ensure all values are JSON serializable
            header_dict = {}
            for k, v in header.items():
                if isinstance(v, (str, int, float, bool)) or v is None:
                    header_dict[k] = v
                else:
                    header_dict[k] = repr(v) # Use repr for non-standard types

            header_dump = json.dumps(header_dict)

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
            record.ra_deg = ra_deg
            record.dec_deg = dec_deg
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
        # VERBOSE LOGGING: Print the main processing error
        tqdm.write(f"!!! CRITICAL ERROR processing {file_path.name}: {e}")
        return f"Error processing {file_path.name}"
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