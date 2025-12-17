# Agent Technical Briefing: FITSDB Project

## 1. Project Goal

The primary objective is to create a high-performance system for cataloging astronomical FITS files into a PostgreSQL database and providing an interactive web GUI for searching, filtering, and inspecting the catalog. This document outlines the technical architecture and operational workflow.

## 2. Core Architecture & Technology Stack

-   **Backend Language:** Python 3.10+
-   **Database:** PostgreSQL
-   **Web GUI Framework:** Streamlit
-   **ORM:** SQLAlchemy
-   **Data Processing:** Pandas
-   **Astronomical Data:** Astropy
-   **Concurrency:** `concurrent.futures.ThreadPoolExecutor`
-   **Progress Indication:** `tqdm`
-   **DB Driver:** `psycopg2-binary`
-   **Configuration:** `python-dotenv`

## 3. Component Overview

-   `database.py`: Defines the database schema using SQLAlchemy ORM and provides a script for table creation and reset.
-   `indexer.py`: A high-performance, concurrent command-line script for populating the database.
-   `app.py`: A Streamlit application that serves the interactive web GUI.
-   `requirements.txt`: Lists all Python dependencies.
-   `.env`: A file (to be created by the user) for storing database credentials.

## 4. Database Schema (`database.py`)

### 4.1. Connection

Connection details are loaded from a `.env` file in the project root. The file must contain `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT`, and `DB_NAME`.

### 4.2. `fits_files` Table Model

The schema is defined in the `FitsFile` class.

| Column Name | Data Type | Constraints / Description |
| :--- | :--- | :--- |
| `id` | Integer | Primary Key |
| `filepath` | String | Unique. The absolute, resolved path to the FITS file. |
| `filename` | String | The base name of the FITS file. |
| `object_name` | String | Indexed. The astronomical object name from the header. |
| `date_obs` | DateTime | The observation date and time. |
| `exptime` | Float | The exposure time in seconds. |
| `altitude` | Float | The calculated altitude of the object at observation time. |
| `observatory` | String | The name of the observatory. |
| `header_dump`| JSONB | A complete JSON dump of the FITS header. |
| `scan_root` | String | The original root directory path passed to the indexer. |
| `client_hostname`| String | The hostname of the client machine that indexed the file. |
| `client_os` | String | The operating system of the client machine. |
| `client_mac` | String | Indexed. The MAC address of the client machine for unique identification. |

## 5. Indexer Script (`indexer.py`)

The indexer is designed for high-speed, parallel processing.

-   **Architecture:**
    -   The `run_indexer` function first performs a fast file discovery using `os.walk`.
    -   It then creates a `concurrent.futures.ThreadPoolExecutor` to manage a pool of worker threads.
    -   Tasks (`process_fits_file`) are submitted to the executor for each file.
    -   `tqdm` is used to create a progress bar that updates as tasks are completed, providing an accurate ETA.
-   **Thread Safety:**
    -   The `process_fits_file` function is thread-safe. It creates and closes its own SQLAlchemy `SessionLocal()` for each file it processes, preventing session conflicts between threads.
-   **Command-Line Arguments:**
    -   `directory`: (Positional) The root directory path to scan.
    -   `--workers` or `-w`: (Optional) The number of concurrent worker threads to use. Defaults to 8. The optimal value is highly dependent on the I/O bottleneck of the target `directory`. For slow network drives, the process is I/O bound, and a smaller number of workers (e.g., 4-8) may be optimal. For fast local SSDs, the process can become CPU-bound, and a higher number (e.g., 16-32) can be beneficial. Advise the user to experiment.
-   **Progress Bar Interpretation (`tqdm`):**
    -   The output `1068/23562 [01:47<40:31,  9.25file/s]` should be parsed as:
        -   `1068/23562`: `processed_items/total_items`.
        -   `[01:47<40:31]`: `[elapsed_time < remaining_time]`.
        -   `9.25file/s`: The current processing rate in items per second.
    -   A `W` suffix on Windows indicates a legacy console and can be ignored.

## 6. Web Search GUI (`app.py`)

The Streamlit GUI provides a dynamic interface for data exploration.

-   **Filtering:**
    -   The sidebar contains filters for clients, date range, and altitude.
    -   **Dynamic Multi-Select Filters:** For `Object Names`, `Observatories`, and `Exposure Times`. These are populated by querying the distinct values present in the database, scoped to the currently selected client(s). This provides a "one-click" filtering experience.
-   **Statistics:**
    -   An expandable section below the main result count displays statistics for the current search results, including a count of distinct objects and a table of their names and file counts.

---

## 7. Operational Workflow (Sequence of Commands)

To set up and run the project from a fresh state, execute the following commands in sequence in the project's root directory.

### Step 1: Configure Environment

Create a `.env` file in the project root with the PostgreSQL database credentials.

**Template for `.env`:**
```env
DB_USER=your_user
DB_PASSWORD=your_password
DB_HOST=localhost
DB_PORT=5432
DB_NAME=fitsdb
```

### Step 2: Install Dependencies

Install all required Python packages from `requirements.txt`.

```bash
pip install -r requirements.txt
```

### Step 3: Initialize Database

Run the database script with the `--reset` flag to create a clean table schema. **This command is destructive and will erase existing data.**

```bash
python database.py --reset
```

### Step 4: Run the Indexer

Execute the indexer script. Provide the path to the FITS files and specify the number of workers for parallel processing.

**Example:**
```bash
python indexer.py "C:\path\to\your\fits_files" --workers 16
```

### Step 5: Launch the Web Application

Start the Streamlit web server to launch the GUI. The application will open in a new browser tab.

```bash
streamlit run app.py
```