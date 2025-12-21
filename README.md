# FITSDB

A high-speed, searchable catalog for your astronomical FITS files with a modern web interface.

## About The Project

FITSDB is a Python-based system designed to solve the problem of managing thousands of FITS files spread across local or network drives. It consists of two main components:

1.  A **high-speed, parallel indexer** that recursively scans directories, extracts metadata from FITS headers, and populates a central PostgreSQL database.
2.  An **interactive web application** built with Streamlit that allows for powerful filtering, searching, and inspection of the cataloged files.

## Features

-   **High-Speed Concurrent Indexing**: Utilizes multiple worker threads to scan and process thousands of files in minutes, not hours.
-   **Interactive Web UI**: A clean and modern interface for searching and exploring your data.
-   **Advanced Filtering**: Filter your files by:
    -   Client machine (where the files were indexed)
    -   Object Name (multi-select)
    -   Observatory (multi-select)
    -   Exposure Time (multi-select)
    -   Date Range
    -   Altitude Range
-   **Data Visualizations**:
    -   **Galactic Sky Map**: A powerful scatter plot that visualizes the distribution of your observed objects in galactic coordinates (Longitude and Latitude). This view helps map your observations against the plane of the Milky Way and supports interactive filtering by observatory.
    -   **Statistical Charts**: Get a quick overview of your observation habits with monthly charts for FITS count and total exposure time, plus a summary of observations per observatory.
-   **Result Statistics**: Get a quick overview of the objects found in your search results with an expandable statistics panel.
-   **Header Inspector**: View the full FITS header of any file directly in the web UI.
-   **File Opener**: On Windows, open a FITS file in its default application directly from the search results.

---

## Setup & Installation

Follow these steps to get the application running.

### 1. Configure Environment

The application uses a `.env` file to manage database credentials. Create a file named `.env` in the root of the project directory.

Copy the following template into your `.env` file and replace the values with your PostgreSQL connection details.

```env
# .env file
DB_USER=your_postgres_user
DB_PASSWORD=your_postgres_password
DB_HOST=localhost
DB_PORT=5432
DB_NAME=fitsdb
```

### 2. Install Dependencies

This command will install all necessary Python libraries, including the new `tqdm` for the progress bar.

```bash
pip install -r requirements.txt
```

### 3. Initialize the Database

This crucial step creates the required tables in your database. If you are upgrading, this will reset the database, deleting old data to apply the new schema.

**WARNING:** This command deletes any existing `fits_files` table and its data.

```bash
python database.py --reset
```

---

## How to Use

### 1. Index Your FITS Files

Run the indexer script, pointing it to the directory containing your FITS files. Use the optional `--workers` flag to specify how many parallel threads to use.

The optimal number of workers depends on your system's hardware, particularly the speed of your storage (I/O) and the number of CPU cores.
- For **fast local storage (SSDs)**, a higher number of workers can be effective.
- For **slower network drives**, the process is often limited by network speed (I/O bound), so a very high number of workers may not increase performance.

A good starting point is a value between **8 and 16**. You can experiment to find the best value for your specific setup.

**Example for a network drive `Z:`:**
```bash
python indexer.py "Z:\__RAW_IMAGES" --workers 16
```

#### Understanding the Progress Bar

The script will display a real-time progress bar that looks like this:
`1068/23562 [01:47<40:31,  9.25file/s]`

-   `1068/23562`: Shows the number of files processed so far out of the total number of files found.
-   `[01:47<40:31]`: Indicates the elapsed time (`01:47`) and the estimated time remaining (`40:31`) at the current processing speed.
-   `9.25file/s`: The current indexing speed in files per second.

The `W` at the end of the line on Windows indicates that the console is in a legacy mode and may not support all modern characters, but it does not affect the process.

### 2. Run the Web Application

This project provides two ways to run the web interface, depending on your needs.

#### Option A: Live Database Mode (`app.py`)

This is the primary application that connects directly to the PostgreSQL database. It's ideal for a live environment where you are actively indexing new files and want to see the latest data immediately.

**To run:**
```bash
streamlit run app.py
```

#### Option B: Static File Mode (`app2.py`)

This version is designed for easy sharing and deployment (e.g., on Streamlit Community Cloud) without needing a live database connection. It reads all its data from a single `fits_data.parquet` file.

This is a 2-step process to run:

**1. Export Data from Database**
Run the export script to query your database and create the `fits_data.parquet` file. You must do this every time you want to update the data in the static app.
```bash
python export_data.py
```

**2. Run the Static App**
Now, run the `app2.py` version of the application.
```bash
streamlit run app2.py
```

This will launch the web app, which will have the same features as the live version but will be reading from the data snapshot you just created.