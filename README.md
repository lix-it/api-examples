# Lix API Examples
These examples are designed to demonstrate how to use the Lix API. The examples show you how to query the API on your machine and store the results for processing.

All scripts are fault-tolerant, meaning if your internet connection drops or the API is slow, the script will continue to run and store the results in the database. If you restart the script, it will continue from where it left off.

For full API documentation check out https://lix-it.com/docs

# Environment

## Python

[Poetry](https://python-poetry.org/) is used to manage the dependencies and Python versions.

### Set up venv
```bash
poetry install
poetry shell
```

# How to use the examples
This repository is organised into two components, the `examples` package and the `export` package. The `examples` package contains the code to query the Lix API and the `export` package contains example code to export the results from the SQLite database to a CSV file.

1. Run the migrate command on the script you want to use. This will create the database and tables as an SQLite file in the root directory of the project.
2. Load the input data into the SQLite database. 
3. Run the export command on the script you want to use. This will export the data from the SQLite database to a CSV file.

## Loading data
To load the data into the SQLite database you will need to run the import script. This changes with each script. For each script you will need to ensure that you have a file with the correct layout

You can also load the data into the SQLite table yourself:

More information on SQLite importing here https://www.sqlite.org/cli.html#importing_files_as_csv_or_other_formats