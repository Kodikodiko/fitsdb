# FITS File Catalog and Search Application

This application provides a system to index FITS files from a local directory into a PostgreSQL database and a web-based GUI to search the catalog.

## Setup and Usage

Follow these steps to set up and run the application.

### 1. Install Dependencies

First, ensure you have Python 3.10+ installed. Then, install the required Python packages using the `requirements.txt` file.

```bash
pip install -r requirements.txt
```

### 2. Create Database Tables

The `database.py` script can be run directly to create the necessary `fits_files` table in your PostgreSQL database. Make sure your database is running and accessible with the credentials specified in `database.py`.

```bash
python database.py
```
This command will connect to the database and create the table schema if it doesn't already exist.

### 3. Index Your FITS Files

Run the `indexer.py` script, providing the path to the root directory containing your FITS (`.fits`, `.fit`) files. The script will recursively scan the directory, extract metadata, and populate the database.

Replace `/path/to/your/fits/files` with the actual path to your data. For example, if your files are in the current directory `T_CrB`, you would run:

```bash
python indexer.py ./T_CrB
```
or
```bash
python indexer.py "c:\Users\stefan\Documents\antares\T_CrB"
```

The indexer will print its progress and any warnings or errors encountered.

### 4. Run the Search Application

Once your files are indexed, you can launch the Streamlit web application.

```bash
streamlit run app.py
```

This command will start a local web server and open the search interface in your default web browser. You can then use the filters in the sidebar to search your cataloged files.
