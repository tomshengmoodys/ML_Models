from mapping import mapping
from moodyscappy import Cappy
import instrumenterror
import iosession
import json
import logging
import os
import subprocess


class Model:
    """
    Main model class.

    :param credentials: Dictionary with valid javaScript web token or username and password
    :param proxy_credentials: Dictionary with valid javaScript web token or username and password
    :param model_run_parameters_path: S3 key or local path to model run parameters configuration file (e.g., modelRunParameter.json)
    :param local_mode: (Boolean) True if model_run_parameters_path is stored in an s3 bucket, else False if a file stored locally
    """

    def __init__(self, credentials, proxy_credentials, model_run_parameters_path, local_mode=False):
        # Create module's logger and session managers
        self.logger = logging.getLogger(__name__)
        self.logger.info(f'Running in local mode: {local_mode}')
        self.cap_session = Cappy(**credentials, errors='raise')
        self.io_session = iosession.IOSession(self.cap_session, model_run_parameters_path, local_mode)
        self.model_run_parameters = self.io_session.model_run_parameters
        self.instrument_error = instrumenterror.getErrorHandler()
        if proxy_credentials:
            self.proxy_cap_session = Cappy(**proxy_credentials, errors='log')

    def run(self):
        ################## DELETE BELOW THIS LINE AND WRITE YOUR OWN MODEL RUN SCRIPT ##################
        try:
            # If anything fails here, it will be caught and logged appropriately
            self.logger.info(f'Running model: {self.model_run_parameters.name}')

            # Fetch the input files specified in model run parameters from S3 and store in a temp directory
            input_files = self.io_session.getSourceInputFiles(require=['instrumentReference.csv'], optional=['portfolioReference.csv'])
            instrument_reference_path = input_files.get('instrumentReference')

            # Read a CSV using mapping helper function (helpfully handles dtypes that pandas struggles with, and is case-insensitive)
            dtypes = {'reportingdate': 'datetime64[ns]', 'foreclosed': 'bool'}
            instrument_reference = mapping.readCsvWithCorrectDtypes(instrument_reference_path, dtypes)

            # Create a new modelRunParameter.json file with local directories in settings
            # It is strongly recommended to not do this unless your model code actually needs it
            new_mrp = self.createLocalModelRunParameters()

            # Run PIT Converter script
            this_directory_path = os.path.abspath(os.path.dirname(__file__))
            r_script_path = os.path.join(this_directory_path, '..', '..', 'bin', 'run_model.R')
            subprocess.run(['Rscript', r_script_path, '-p', new_mrp, '-l', os.path.dirname(os.path.dirname(r_script_path))], stdout=subprocess.PIPE)

            # Upload input, output, and intermediate files back to S3 (or test folder if running in local mode)
            all_files = self.io_session.createFileDicts(self.io_session.local_temp_directory)
            for file_dict in all_files:
                self.io_session.uploadFiles(file_dict)

            # By example, raise an exception and see it in instrumentError output
            raise Exception('Oops something went wrong!')

        except Exception as e:
            # Log exception and add a row in instrumentError mapping
            self.logger.error('An exception occurred while running the model')
            self.logger.error(e, exc_info=True)
            self.instrument_error.entry(e)

        finally:
            # Create and upload instrumentError, if any entries were made
            output_directory = os.path.join(self.io_session.local_directories['outputPaths'].get('instrumentError'))
            error_columns = self.model_run_parameters.output_data.get('instrumentError', instrumenterror.DEFAULT_COLUMNS)
            instrument_error = self.instrument_error.createInstrumentErrorFile(output_directory, columns=error_columns)
            self.io_session.uploadFiles(instrument_error)

        ################## DELETE ABOVE THIS LINE AND WRITE YOUR OWN MODEL RUN SCRIPT ##################

    def createLocalModelRunParameters(self): # TODO: Delete this function if you are not going to use it
        """Copy modelRunParameter.json, replacing input/output/log paths with local temp directories"""
        new_mrp = self.model_run_parameters.json.copy()
        new_mrp['settings'] = new_mrp.get('settings', {})
        new_mrp['settings'].update(self.io_session.local_directories)
        new_mrp_path = os.path.join(self.io_session.local_temp_directory, 'localModelRunParameters.json')
        with open(new_mrp_path, 'w') as f:
            json.dump(new_mrp, f)
        return new_mrp_path

    def cleanUp(self, log_file=None, keep_temp=False):
        """Delete temp directories and upload logfile and batch id file"""
        if not keep_temp:
            self.io_session.deleteTempDirectories()
        if log_file:
            self.io_session.uploadFiles({'log': log_file})
