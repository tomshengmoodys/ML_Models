# Getting Familiar with the Model Framework

## Model Run Parameters

An important input for the model is the model run parameters file, [`modelRunParameter.json`](../test/sample-test/modelRunParameter.json). Among other things, this file defines your model's input, output, and supporting data sets. It also keeps a reference to the S3 keys where you can download your data files, and upload your results. This file is fetched from the provided s3 key (or file path, in local mode) early in the model creation procedure. A helper class is provided throughout the code by way of the Model member variable `model_run_parameters` to obviate the need for json key lookup/error handling. However, if you require the original JSON, you can access it via the `model_run_parameters.json` attribute.

## Getting your input files

Model files must be fetched from S3 (or local folder) manually. A helper method, `IOSession.getSourceInputFiles()` is provided for this purpose. With successful authentication using cappy (see `Model.__init__()`), the helper method will attempt to fetch all files from S3 that are specified in modelRunParameter.json under data inputs. Required and optional files can be specified by arguments.

## Running locally vs on Domino

Two run modes are supported- local and S3 modes. Either is available to you when running locally on your computer. On Domino however, the default mode will be S3. This is because the model registry by default will pass the `-s` flag as a parameter. When running manually on Domino, it is possible to use the `-L` flag, but be careful to specify file paths where Domino can find them (e.g., `/repos/`, `/mnt,`, `/tmp/`, etc.) as they will be different than when run locally on your own computer.

## Cross-platform compatibility

At all times CAP developers should strive for cross-platform compatibility. For instance, if you are running a C/C++ binary as your core model, make sure to include builds for Windows and Linux, as this will hasten debugging time. Domino is a great platform for running code in the cloud, but debugging and interactive sessions will be more powerful and accessible on a local machine, and it is important that yoru code can run on a machine potentially not running Linux.

## Next up

After you have your model running locally, it's time to [get started with Domino](2_domino.md)!