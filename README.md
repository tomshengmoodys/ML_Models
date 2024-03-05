# CAP Model Starter

##############

This repository is an example model to help with standardization of Moody's internal CAP models. The basic boilerplate and framework code is included to get you started quickly. This model includes an example R script which will be called by the Python wrapper, and demonstrates proper ImpairmentStudio-style file I/O.

## Getting Started

Check out the [quick start guide](quickstart/0_getting_started.md) to get your model running faster.

## Project Structure

```bash
./
├── bin/
│   ├── example_r_model_script.R # Main example model R script
│   └── run_model.R              # Exqample R script wrapper for model code
├── cap/
│   ├── config/
│   │   ├── config.py            # Main configuration script
│   │   ├── local.ini            # For environment configuration
│   │   ├── logging.ini          # Default logging parameters
│   │   └── model-conf-*.ini     # local.ini configs for various environments. local.ini will be overwritten by one of these as part of the build process
│   └── model/
│       ├── instrumenterror.py   # Module for creating and maniputlating IS standard instrumentError files
│       ├── iosession.py         # Interface for handling file I/O and S3 communications
│       ├── model.py             # Main model setup, run, and cleanup methods (overwrite here)
│       └── run.py               # Program entry script (see run scripts section below)
├── data/                        # Directory for storing static data files and accessor scripts (required for example)
├── mapping/
│   └── mapping.py               # Common mapping and data frame manipulation helper functions
├── meta/                        # Folder to store model registry JSON and related model metadata
├── quickstart/                  # Helpful resources for getting started. Should be removed before model deployment
├── tests/
│   ├── /*                       # Test case folders (see proper format below)
│   ├── regression.ini           # List end-to-end (regression) test cases to run with unit tests here
│   ├── helpers.py               # Helpful test methods
│   ├── test_regression.py       # Automatically run regression tests listed in regression.ini
│   └── test_*.py                # Automated tests and test cases for modules
├── .circleci/
│   └── config.yml               # CircleCI continuous integration configuration file
├── .dominoignore                # Similar to .gitignore, used by domino to manage files to track between runs
├── .gitignore                   # Used by git to determine which files to track
└── README.md                    # This file
```

## Prerequisites

The main Python script (cap/model/run.py) relies on some external Python libraries. In order to run it you will need to have Python 3.x installed with required libraries. Additionally, some R dependencies are required to run the provided example.

```bash
# Python prerequisites
pip install https://github.com/moodysanalytics/cappy.git # moodyscappy
pip install pandas
pip install pytest

# R dependencies
argparser
log4r
XML
plyr
```

To install moodyscappy library locally, follow instructions [here](https://github.com/moodysanalytics/cappy#installation).

### Script run Parameters

The end to end python wrapper script includes cap model integration code and can run against S3 bucket.
`cap/model/run.py` is the main entry file.

```bash
python ./cap/model/run.py -h
usage: run.py [-h] [-d]
              [-l {NOTSET,DEBUG,INFO,WARNING,ERROR,CRITICAL,DISABLED}]
              [-r] [-k] [-o CUSTOM_CONFIG_PATH | -c CUSTOM_CONFIG_PATH]
              (-s MODEL_PARAMS_S3_KEY | -L TEST_FOLDER_PATH)
              (-j JWT | -u USERNAME PASSWORD)

Arguments:
  -h,                     --help                          Show help message and exit
  -d,                     --usedefaults                   Do not overwrite system env variables with included configuration files
  -k,                     --keeptemp                      Do not clear temp directories and files after model run
  -l,                     --loglevel                      Set log level. Options: NOTSET, DEBUG, [INFO], WARNING, ERROR, CRITICAL, DISABLED
  -o CUSTOM_CONFIG_PATH,  --overwrite CUSTOM_CONFIG_PATH  Overwrite configurations with custom configuration file
  -c CUSTOM_CONFIG_PATH,  --config CUSTOM_CONFIG_PATH     Add custom configurations without overwriting system variables
  -s MODEL_PARAMS_S3_KEY, --s3 MODEL_PARAMS_S3_KEY        Run model with data hosted on S3 (default behavior)
  -L TEST_FOLDER_PATH,    --local TEST_FOLDER_PATH        Run model with data from local test folder
  -j JWT,                 --jwt JWT                       Log in using JSON web token
  -u USERNAME PASSWORD,   --unpw USERNAME PASSWORD        Log in using username and password
  -t JWT,                 --proxyjwt JWT                  Use proxy user JWT for API access
  -p USERNAME PASSWORD,   --proxyunpw USERNAME PASSWORD   Use proxy username and password for API access
```

### Examples

```bash
# Run example model on local data, using a JWT for authentication
python ./cap/model/run.py -j <jwt_token> -L <path_to_local_modelRunParameters.json>

# Run example model on S3 data, using username and password, keeping temp files, and setting log level to WARNING
python ./cap/model/run.py -u <username> <password> -s <path_to_s3_modelRunParameters.json> -k -l WARNING

# Run example model on local data, providing a proxy JWT for some other potential purpose
python ./cap/model/run.py -j <jwt_token> -t <proxy_jwt_token> -L <path_to_local_modelRunParameters.json>

```

### Test Folder Structure

A valid test folder must follow this structure to be sumbitted to the model service (local mode only).

```bash
test_folder/
├── benchmark/               # Contains benchmarks to compare (file names must match expected outputs) (REQUIRED FOR REGRESSION ONLY)
├── input_csv/               # Folder containing all input CSV files
└── modelRunParameter.json   # Name not important, but must follow CAP model parameter format
```

 A sample test case is provided at `tests/sample-test`. To run it locally, from the package directory, run:

```bash
python ./cap/model/run.py -u <username> <password> -L ./tests/sample-test/modelRunParameter.json
```

The same test can be run on s3 by running (must use credentials with s3 bucket access to bank1305):

```bash
python ./cap/model/run.py -u <username> <password> -s model-intg/cap-model-starter/sample-test/modelRunParameter.json
```

An output folder will be generated at runtime.

#### Run Example R Model Script Directly

Modeler can directly run Rscript to test model code through local files. If your model cannot interface directly with Python (e.g., it must be run by calling subprocess command), it is recommended that you further wrap your R script or binary with its own run script (in R, bash, or other) for testing purposes.

```bash
Rscript <path/to/run_model.R> -p <localModelRunParameter.json> -l <module_path>
```

## Running the tests

You will need to set the following environment variables in order to run the regression tests:

```bash
E2E_TEST_UN =          # QA User
E2E_TEST_PW =          # QA User password
E2E_TEST_PROXY_UN =    # Proxy User, if required for your model
E2E_TEST_PROXY_PW =    # Proxy User password, if required for your model
```

Test cases must follow the folder structure listed above, and the name of the regression test folder must be specified in `regression.ini`

```bash
pytest                                        # Run all unit and regression tests
python -m unittest -v -b                      # Run all unit and regression tests (alternate)
python -m unittest -v -b test_regression.py   # Run only regression tests listed in regression.ini
```
