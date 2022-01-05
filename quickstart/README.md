# CAP Model Starter

This project provides a basic template for running a custom R model for CAP in domino, which can be easily extended to other run configurations.

## Getting Started

Check out the [quick start guide](0_getting_started.md) to get your model running faster.

## CAP Structure

```bash
cap/
├── config/
│   ├── config.py             # Main configuration script
│   ├── local.ini             # For environment configuration
│   ├── logging.ini           # Default logging parameters
│   └── model-conf-*.ini      # local.ini configs for various environments. local.ini will be overwritten by one of these as part of the build process
├── model/
│   ├── instrumenterror.py    # Module for creating and maniputlating IS standard instrumentError files
│   ├── iosession.py          # Interface for handling file io and s3 communications
│   ├── model.py              # Main Model logic goes in the run() method
│   └── run.py                # Program entry script (see run scripts section below)
├── quickstart/               # Helpful tutorials to get your model running faster
└── README.md                 # This file
```

## Using the CAP Model Starter

The following classes and methods are meant to be a "jumping off point" for creating your own CAP models to be run on domino. Many of the boilerplate tasks (authentication, file io, etc.) are taken care of, but there is no expectation that it will work for all use-cases. Therefore feel free to modify the code as necessary. Happy modeling!

### Overview of runtime process

When `cap/model/run.py` is called, the following happens:

1. Input arguments are parsed
2. Configuration script processes all config files present, as well as any configs passed as input to model.
3. CAP session is authenticated. If provided, proxy user CAP session is also authenticated.
4. Model run parameters are fetched from either S3 or local file.
5. The Model's `run()` method is called.
6. The Model's `cleanup()` method is called.
7. Exit code 0 is returned for success, and 1 for failure.

### Configuration

* Log settings can be adjusted in `cap/config/logging.ini`.
* It is recommended to adjust environment settings in `cap/config/local.ini`.
* Additional configurations should be added to the `config` directory and `config.py` updated.
* It is possible to add environment variables directly from the domino dashboard.
* The `-c` and `-o` flags can be used to adjust configurations at runtime.

### Defining a custom Model

* Custom model code should be implemented in the `run()` method in `cap/model/model.py`
* Custom cleanup code should be added to the `cleanup()` method in `cap/model/model.py`. By default, temp files will be deleted and the logfile uploaded.
* Helper classes `io_session` and `cap_session` are provided as attributes of the `Model` class. These are described in their own sections.

### Calling non-Python code (e.g., R, C++)

If the model requires non-Python code to be run, it is recommended to use Python's [`subprocess`](https://docs.python.org/3/library/subprocess.html) module to call the executable or interpreter relevant arguments from within the `Model.run()` method in `cap/model/model.py`:

```python
import subprocess
import ctypes
...

class Model:
    ...

    def run(self):
        ...

        # Run an external R script
        r = subprocess.run(['Rscript', 'path/to/script.R', 'arg1', '...etc'], stdout=subprocess.PIPE)

        # Run a C/C++ executable
        c = subprocess.run(['path/to/executable', 'arg1', '...etc'], stdout=subprocess.PIPE)

        # Run a C/C++ library function (from .dll, .so, etc.)
        c = ctypes.windll.library.cpp_function(args) # windows
        c = ctypes.CDLL('./library.so').cpp_function(args) # Linux
```

Note that if you are running executables, behavior may differ between domino and your local system. If you are developing in a Windows environment or need to ensure cross-platform compatibility, make sure to check what platform you are on before trying to call an executable. The Python Standard Library includes many helpful utilities for running external code:

* [`subprocess`](https://docs.python.org/3/library/subprocess.html)
* [`ctypes`](https://docs.python.org/3.7/library/ctypes.html)
* [`shlex`](https://docs.python.org/3/library/shlex.html#shlex.quote)

### Using `io_session`

The IOSession class provides utilities for file handling. Some methods will behave differently for local runs vs running on S3.

* `createFileDicts()` - Given a directory, create a list of dictionary objects that can be used by `uploadFiles()`
* `deleteTempDirectories()` - Delete all tempdirectories created during run
* `getModelRunParameters()` - Fetch model run parameters from provided s3 key (`-s` flag) or file path (`-L` flag)
* `getSourceInputFiles()` - Fetch input files from s3 keys in model run parameters (`-s` flag) or `test_folder/input_csv/` folder (`-L` flag)
* `uploadFiles()` - Upload files to S3 keys specified in model run parameters(`-s` flag) or copy to `test_folder/output/` folder (`-L` flag)
* `writeFileObjectToDisk()` - Given a file object (e.g., file stream returned from an API call), write it to disk

### Using `cap_session`

The CAPSession class is a wrapper around the moodyscappy library, supplying additional utilities not provided there. It is responsible mainly for authenticating the CAP session and providing retrieved user data to io_session for S3 file handling purposes.

* `renewSession()` - Renew cap session.
* `s3DownloadFile()` - Download files from S3
* `s3UploadFile()` - Upload files to S3
* `s3ListBucket()` - List files in a given S3 bucket

### Using `instrument_error`

The InstrumentErrorHandler class is a handler for creating, tracking, merging, and writing standard ImpairmentStudio instrumentError.csv files. The `instrumenterror` module is modeled after the Python `logging` module and works similarly.

To create or get an existing InstrumentErrorHandler object:

```python
instrument_error = instrumenterror.getErrorHandler()
```

InstrumentErrorHandler has the following methods:

* `entry()` - "Log" an entry in instrument error data frame (will become a row in file when written)
* `configureDefaults()` - Set defaults to simplify entries (i.e., default error code, default scenario, etc.)
* `createInstrumentErrorFile()` - Write the instrumentError.csv file
* `joinDataFrame()` - Join another data frame to this one (for instance if you have pre-filtered errors from an output file)

### Using `mapping` module

The mapping module provides some helpful utilities that are commonly used across Moody's internal models. The raison d'etre for this module is to corrrect for inconsistencies between various aplication input/output files, namely inconsistent column casing. Pandas also has a habit of throwing exceptions on some character inputs, and unhelpfully suppressing them when trying and failing to coerce dtypes on file reads, leading to dtype errors further down the call stack.

The follwoing methods are provided:

* `cleanOutputHeaders()` - Sometimes files contain 4b utf-8 characters that pandas cannot read. This will replace "bad" column chars such as en-dashes and rewrite the file
* `createCsvFilesFromDataFrames()` - Given a dictionary of data frames, write them to temp files and return a dictionary that `io_session.upploadFiles()` can use
* `mapEnums()` - Map enumerated values in the data frame given a dictionary of columns and values to be mapped
* `readCsvWithCorrectDtypes()` - Read CSV files case-insensitively, and coercing columns to dtypes with which pandas sometimes struggles
* `reindexCaseInsensitively()` - Reindex columns without regard to casing
* `toBoolean()` - Coerce a series to booleans
* `toInteger()` - Coerce a series to integers

### Using `model_run_parameters`

The ModelRunParameters class is provided as a model attribute for convenience. It provides cleaner lookup syntax, and obviates the need for error checking against missing JSON keys. However, if the original JSON is required or preferred, it can be accessed through `model_run_parameters.json`. Additionally, the path to the locally saved file can be accessed through `model_run_parameters.path`.

### CAP Authentication

By default, CAP will attempt to authenticate against the QA SSO API. To change this behavior, provide alternate URIs in `local.ini` for `MOODYS_SSO_URL` and `MOODYS_TENANT_URL`.

### Logging

By default, the `logger` object is available in the model module. If you wish to implement a logger in separate module, it is recommended to create it using `your_new_logger = logging.getLogger(__name__)`. Doing so will ensure that new entries will be integrated properly into the existing logging infrastructure.

## Running the Model

To run the model you must call the run.py script located in the model directory with a path (local or S3) to a json file with model run parameters.

### Local mode vs. S3 mode

Two run configurations are possible, depending on user intent. If provided an `-s` flag argument and an S3 key pointing to a JSON file containing model run parameters, the model will be processed based on the input files and data contained within. `io_session.getSourceInputFiles()` will retrieve any files listed in modelRunParameter.json file in the ['settings']['inputPath'] section. `io_session.uploadFiles()` will upload files, by file name, to S3 modelRunParameters based on ['settings']['outputPath'] section. In local mode, (`-L` flag, with `path/to/test_folder/modelRunParameter.json` file), input files will be retrieved from `test_folder/input_csv/` folder. Similarly, files will be output to `test_folder/output/` when using `io_session.uploadFiles()`.

### Running on Domino

By default, when CAP calls the model, it calls with a JWT and S3 key pointing to model run parameters JSON file. The call is equivalent to running the following from local:

```bash
python ./cap/model/run.py -j <jwt_token> -s <s3/key/modelRunParameters.json>
```

### Script run Parameters

```bash
python ./cap/model/run.py -h
usage: run.py [-h] [-d]
              [-l {NOTSET,DEBUG,INFO,WARNING,ERROR,CRITICAL,DISABLED}]
              [-r] [-k] [-o CUSTOM_CONFIG_PATH | -c CUSTOM_CONFIG_PATH]
              (-s MODEL_PARAMS_S3_KEY | -L TEST_FOLDER_PATH)
              (-j JWT | -u USERNAME PASSWORD)

Submit test cases to the CRE-LR API
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

### Usage Examples

```bash
python ./cap/model/run.py -j <jwt_token> -L <path/to/local/modelRunParameters.json>       # Run model on local data, using a JWT
python ./cap/model/run.py -u <username> <password> -s <s3/key/modelRunParameters.json>    # Run model on S3 data, using username and password
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

## Troubleshooting

* If domino is adding empty folders after a run, try adding folders to the .dominoignore file.
