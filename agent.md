# Project: FITS File Catalog and Search Application

## 1. Project Goal

The primary objective is to create a comprehensive system for cataloging astronomical FITS files from a local filesystem into a central PostgreSQL database. The system must also provide an interactive web-based graphical user interface (GUI) for searching, filtering, and inspecting the cataloged files.

## 2. Core Architecture & Technology Stack

-   **Backend Language:** Python 3.10+
-   **Database:** PostgreSQL
-   **ORM:** SQLAlchemy
-   **Astronomical Data Processing:** Astropy
-   **Web GUI Framework:** Streamlit
-   **Data Manipulation:** Pandas
-   **Database Driver:** `psycopg2-binary`
-   **Client Identification:** `netifaces`, `socket`, `platform`

## 3. Database Setup

### 3.1. Connection Details

The application must connect to a pre-existing PostgreSQL database with the following credentials:

-   **see .env file!**

### 3.2. Data Model (`database.py`)

A single table named `fits_files` is required to store the metadata. The table schema should be defined using SQLAlchemy ORM.

**Table: `fits_files`**

| Column Name | Data Type | Constraints / Description |
| :--- | :--- | :--- |
| `id` | Integer | Primary Key, Auto-incrementing |
| `filepath` | String | Unique. The absolute path to the FITS file on the client machine. |
| `filename` | String | The name of the FITS file. |
| `object_name` | String | Indexed for fast text searching. The astronomical object name from the header. |
| `date_obs` | DateTime | The observation date and time from the header. |
| `exptime` | Float | The exposure time in seconds. |
| `altitude` | Float | The calculated altitude (elevation) of the object at the time of observation. |
| `observatory` | String | The name of the observatory from the header. |
| `header_dump` | JSONB | A complete dump of the FITS header in JSON format. |
| `client_hostname` | String | The hostname of the client machine that indexed the file. |
| `client_ip` | String | The IP address of the client machine. |
| `client_os` | String | The operating system of the client machine (e.g., "Windows"). |
| `client_mac` | String | The MAC address of the client's primary network interface for unique identification. |

**Indexes:**
- A case-insensitive index should be created on the `object_name` column to improve search performance.

## 4. Indexer Script (`indexer.py`)

This is a command-line script responsible for populating the database.

-   **Functionality:**
    -   It must accept a single command-line argument: the root directory to scan for FITS files.
    -   It must recursively traverse all subdirectories of the given root path.
    -   It must identify files with `.fits` or `.fit` extensions.
    -   For each file found, it performs the following:
        1.  **Read Header:** Use `astropy.io.fits` to open the file and read its primary header.
        2.  **Extract Metadata:** Parse key-value pairs like `OBJECT`, `DATE-OBS`, `EXPTIME`, and `OBSERVAT`.
        3.  **Calculate Altitude:**
            -   Use the observation time and object coordinates.
            -   Get the observatory's location (latitude/longitude) from the FITS header if available.
            -   If not available, use a default location.
            -   Use `astropy.coordinates` to perform the calculation to get the object's altitude.
        4.  **Gather Client Info:** Programmatically determine the `hostname`, `ip`, `os`, and `mac address` of the machine running the script.
        5.  **Database Operation:**
            -   Check if a record with the same `filepath` already exists.
            -   If it exists, update the existing record.
            -   If it does not exist, insert a new record.
            -   All database operations for a single file should be within a transaction to ensure atomicity.
    -   **Error Handling:**
        -   The script must gracefully handle errors, such as corrupt FITS files or database connection issues, log the error, and continue processing other files.
        -   It must correctly handle data type mismatches between Python (e.g., NumPy types like `np.float64`) and the database.
    -   **User Feedback:** The script should print progress to the console (e.g., "Processing file X/Y...").

## 5. Web Search GUI (`app.py`)

This script launches a web application using Streamlit for user interaction.

-   **Layout:** A two-column layout with a sidebar for controls and a main area for results.

-   **Sidebar Controls:**
    -   **Client Filter:** A dropdown menu to filter results by the client that indexed them. It should list all unique clients from the database and an "All Clients" option. The default selection should be the current client running the app.
    -   **Object Name Filter:** A text input field for case-insensitive searching on the `object_name`.
    -   **Altitude Filter:** Two numeric input fields for `Min Altitude` and `Max Altitude`, allowing users to specify a range from 0 to 90 degrees.
    -   **Exposure Time Filter:** A numeric input for `Min Exposure Time` in seconds.
    -   **Date Filter:** A date range selector, allowing the user to pick a start and end date. The date format must be `dd.mm.yyyy`.
    -   **Clear All Filters Button:** A button that resets all filter controls to their default state and re-runs the query.

-   **Main Area Display:**
    -   **Results Table:**
        -   The primary view is a table (DataFrame) displaying the filtered results from the database.
        -   Key columns like `filename`, `object_name`, `date_obs`, `exptime`, `altitude`, and `filepath` should be visible.
    -   **File Interaction:** When a user clicks a row in the results table, the application should attempt to open the `filepath` from that row using the operating system's default associated program for `.fits` files (e.g., `os.startfile` on Windows).
    -   **FITS Header Inspector:**
        -   A dropdown or select box should appear above or below the results table, populated with the `filename` of each result.
        -   When a file is selected from this dropdown, its full FITS header (from the `header_dump` JSONB column) should be displayed in a formatted, readable way (e.g., using `st.json`).

-   **Behavior:**
    -   The results table should update automatically whenever a filter value is changed.
    -   The application must handle database connection errors gracefully and display an informative message to the user.

## 6. Project Files

The final project should consist of the following files:

-   `requirements.txt`: A file listing all Python dependencies (e.g., `sqlalchemy`, `astropy`, `streamlit`, `pandas`, `psycopg2-binary`, `netifaces`).
-   `database.py`: Contains the SQLAlchemy database engine setup and the `FitsFile` ORM model definition.
-   `indexer.py`: The command-line script for scanning and indexing files.
-   `app.py`: The Streamlit application for the search GUI.
-   `agent.md`: This file, documenting all project requirements.
