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
This repository is organised into two streams, `guides` and `use cases`. The `guides` stream demonstrates how to use the Lix API to query the capabilities of the API using simple scripts. The `use cases` stream demonstrates how to use the Lix API to query the API for specific use cases, like people enrichment, company finding, or lead generation at scale.

All the scripts assume you are running them from the root directory of the project.

## Running guides
Guides are simple scripts that demonstrate how to use the Lix API to query the capabilities of the API.

The `examples/guides` package contains the code to query the Lix API. All the responses will be saved to the /data directory.

## Running use cases
Use cases store the data in a database and have associated scripts to export the data to a CSV file.

The `examples/use_cases` package contains the code to query the Lix API and save the data into an SQLite database. The `examples/use_cases/export` package contains example code to export the results from the SQLite database to a CSV file.

1. Run the migrate command on the script you want to use. This will create the database and tables as an SQLite file in the root directory of the project.
2. Load the input data into the SQLite database. 
3. Run the export command on the script you want to use. This will export the data from the SQLite database to a CSV file.

### Loading data
To load the data into the SQLite database you will need to run the import script. This changes with each script. For each script you will need to ensure that you have a file with the correct layout

You can also load the data into the SQLite table yourself:

More information on SQLite importing here https://www.sqlite.org/cli.html#importing_files_as_csv_or_other_formats