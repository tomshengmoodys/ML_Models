from glob import glob as gg
import json
import logging
import os
import pandas as pd
import shutil
import tempfile


class Scenario:
    def __init__(self, scenario_info):
        self.name = scenario_info.get('name')
        self.as_of_date = pd.to_datetime(scenario_info.get('asOfDate'))
        self.weight = scenario_info.get('weight')


class ModelRunParameters:
    def __init__(self, model_run_parameter_json, file_path):
        self.path = file_path
        self.json = model_run_parameter_json
        self.name = model_run_parameter_json.get('name')
        self.model_factors = model_run_parameter_json['datasets'].get('modelFactors', [])
        self.input_data = {data['category']: data['attributes'] for data in
                           model_run_parameter_json['datasets'].get('inputData', {})}
        self.output_data = {data['category']: data['attributes'] for data in
                            model_run_parameter_json['datasets'].get('outputData', {})}
        self.supporting_data = {data['category']: data['attributes'] for data in
                                model_run_parameter_json['datasets'].get('supportingData', {})}
        self.scenarios = [Scenario(s) for s in model_run_parameter_json['settings'].get('scenarios', [])]
        self.output_s3_paths = model_run_parameter_json['settings']['outputPaths']
        self.input_s3_path = model_run_parameter_json['settings']['inputPath']
        self.log_s3_path = model_run_parameter_json['settings']['logPath']
        self.run_date = pd.to_datetime(model_run_parameter_json['settings']['runDate'])
        self.reporting_date = pd.to_datetime(model_run_parameter_json['settings']['reportingDate'])


class IOSession:
    def __init__(self, cap_session, mrp_json_path, local_mode):
        self.logger = logging.getLogger(__name__)
        self.local_mode = local_mode
        self.cap_session = cap_session

        self.local_temp_directory = os.path.abspath(tempfile.mkdtemp())
        self.logger.debug(f'Created local temp directory: {self.local_temp_directory}')
        self.model_run_parameters = self.getModelRunParameters(mrp_json_path)
        self.local_directories = self.create_io_directories()

        if local_mode:
            test_folder = os.path.abspath(os.path.dirname(mrp_json_path))
            self.input_path = os.path.join(test_folder, 'input_csv')
            self.test_folder_output = os.path.join(test_folder, 'output')
            self.initializeDirectory(self.test_folder_output)
        else:
            self.input_path = self.model_run_parameters.input_s3_path

    def create_io_directories(self):
        """Create local directories for every input/output/log directory in modelRunParameter.json settings"""
        local_directories = {'outputPaths': {}}
        local_directories['logPath'] = self.initializeDirectory(os.path.join(self.local_temp_directory, 'logPath'))
        local_directories['inputPath'] = self.initializeDirectory(os.path.join(self.local_temp_directory, 'inputPath'))
        for file in self.model_run_parameters.output_s3_paths:
            path = self.initializeDirectory(os.path.join(self.local_temp_directory, 'outputPaths', file))
            local_directories['outputPaths'].update({file: path})
        return local_directories

    def _downloadObject(self, download_key, local_file_path, on_error='log', is_multipart=False):
        """Fetch object or multipart objects from S3 key"""
        download_key_string = f'part files in {download_key}' if is_multipart else download_key
        file_name = os.path.splitext(os.path.basename(local_file_path))[0]
        try:
            # Disable cap_session logging if on_error='ignore'
            cap_session_logger_disabled = self.cap_session.logger.disabled
            self.cap_session.logger.disabled = on_error == 'ignore' or cap_session_logger_disabled
            if is_multipart:
                self.cap_session.s3_download_part_files(download_key, local_file_path)
            else:
                self.cap_session.s3_download_file(download_key, local_file_path)
            self.cap_session.logger.disabled = cap_session_logger_disabled  # Reset cap_session.logger
            self.logger.info(f'Successfully downloaded {download_key_string} to {local_file_path}')
            return {file_name: local_file_path}
        except Exception as e:
            self.cap_session.logger.disabled = cap_session_logger_disabled  # Reset cap_session.logger
            self.logger.debug(e, exc_info=True)
            if on_error == 'raise':
                self.logger.error(f'Error downloading {download_key_string} to {local_file_path}')
                raise
            elif on_error == 'ignore':
                pass
            else:
                self.logger.warning(f'Error downloading {download_key_string} to {local_file_path}')
            return {}

    def deleteTempDirectories(self, on_error='log'):
        """Remove top level temp directory"""
        try:
            shutil.rmtree(self.local_temp_directory)
            self.logger.info(f'Successfuly deleted temporary directory: {self.local_temp_directory}')
        except Exception as e:
            self.logger.debug(e, exc_info=True)
            if on_error == 'raise':
                self.logger.error(f'Error deleting temporary directory: {self.local_temp_directory}')
                raise
            elif on_error == 'ignore':
                pass
            else:
                self.logger.warning(f'Error deleting temporary directory: {self.local_temp_directory}')

    def _uploadFile(self, local_file_path, upload_key, on_error='log'):
        """Upload local file object to S3 bucket associated with cap_session tenant"""
        try:
            # Disable cap_session logging if on_error='ignore'
            cap_session_logger_disabled = self.cap_session.logger.disabled
            self.cap_session.logger.disabled = on_error == 'ignore' or cap_session_logger_disabled
            self.cap_session.s3_upload_file(local_file_path, upload_key)
            self.cap_session.logger.disabled = cap_session_logger_disabled  # Reset cap_session.logger
            self.logger.info(f'Successfully uploaded {os.path.basename(local_file_path)} to {upload_key}')
        except Exception as e:
            self.cap_session.logger.disabled = cap_session_logger_disabled  # Reset cap_session.logger
            self.logger.debug(e, exc_info=True)
            if on_error == 'raise':
                self.logger.error(f'Error uploading {local_file_path} to {upload_key}')
                raise
            elif on_error == 'ignore':
                pass
            else:
                self.logger.warning(f'Error uploading {local_file_path} to {upload_key}')

    def initializeDirectory(self, directory):
        """Create or overwrite (clear) specified directory"""
        self.logger.debug(f'Clearing directory {directory}')
        shutil.rmtree(directory, ignore_errors=True)
        os.makedirs(directory, exist_ok=True)
        return directory

    def _safeCopyFile(self, from_file, to_file, on_error='log'):
        """
        Copy a local file to a new directory, regardless whether given directory exists
        :return: dictionary of form {file_name_wo_ext: file_path}
        """
        os.makedirs(os.path.dirname(to_file), exist_ok=True)
        file_name = os.path.splitext(os.path.basename(to_file))[0]
        try:
            shutil.copyfile(from_file, to_file)
            self.logger.info(f'Successfully copied {from_file} to {to_file}')
            return {file_name: to_file}
        except Exception as e:
            self.logger.debug(e, exc_info=True)
            if on_error == 'raise':
                self.logger.error(f'Error copying {from_file} to {to_file}')
                raise
            elif on_error == 'ignore':
                pass
            else:
                self.logger.warning(f'Error copying {from_file} to {to_file}')
            return {}

    def _createFileDict(self, directory):
        """
        Creates a dictionary of files in a given directory
        :param directory: path to a directory to create dictionary from
        :return: dictionary of form {file_name_wo_ext: file_path}
        """
        file_dict = {}
        try:
            for file in os.listdir(directory):
                file_name = os.path.splitext(file)[0]
                file_path = os.path.join(directory, file)
                if os.path.isfile(file_path):
                    file_dict.update({file_name: file_path})
        except FileNotFoundError as e:
            self.logger.warning(f'Not found: {directory}')
            self.logger.debug(e, exc_info=True)
        return file_dict

    def createFileDicts(self, directory):
        """
        Creates a list of dictionaries of files in a given directory
        :param directory: path to a directory to create dictionaries from
        :return: list of one or more dictionaries of form {file_name_wo_ext: file_path}
        :rtype: list(dict)
        """
        file_dicts = [{}]
        all_paths = gg(os.path.join(os.path.abspath(directory), '**'), recursive=True)
        all_files = [path for path in all_paths if os.path.isfile(path)]
        for file in all_files:
            file_dict = file_dicts[-1]
            file_name = os.path.splitext(os.path.basename(file))[0]
            file_path = os.path.abspath(file)
            if file_name in file_dict:
                file_dicts.append({})
                file_dict = file_dicts[-1]
            file_dict[file_name] = file_path
        return file_dicts if file_dicts != [{}] else []

    def getModelRunParameters(self, mrp_json_path):
        """
        Fetch modelRunParameter.json (named whatever) from given local path or S3 key
        :param mrp_json_path: S3 key or absolute local path to modelRunParamter.json file (file name irrelevant)
        :return: iosession.ModelRunParameters object
        """
        model_run_parameters_path = os.path.join(self.local_temp_directory, os.path.basename(mrp_json_path))
        if self.local_mode:
            file = self._safeCopyFile(mrp_json_path, model_run_parameters_path, on_error='raise')
        else:
            file = self._downloadObject(mrp_json_path, model_run_parameters_path, on_error='raise')
        with open(model_run_parameters_path, 'r') as f:
            model_run_parameters_json = json.load(f)
        self.logger.debug(f'Contents of {os.path.basename(mrp_json_path)}:\n{model_run_parameters_json}')
        return ModelRunParameters(model_run_parameters_json, file)

    def getSourceInputFiles(self, require=[], optional=[]):
        """
        Fetch model input files specified in MRP from given local path or S3 bucket
        :param require: List of files that will raise an error if missing
        :param optional: List of files that will not raise or log an error if missing
        :note: args are optional. Errors will by default be logged only
        :return: dictionary of form {file_name_wo_ext: local_file_path}
        """
        source_input_directory = self.local_directories.get('inputPath')
        os.makedirs(source_input_directory, exist_ok=True)
        file_names = [f'{fn}.csv' for fn in {**self.model_run_parameters.input_data, **self.model_run_parameters.supporting_data}]
        input_files = {}
        for file_name in file_names:
            local_file_path = os.path.join(source_input_directory, file_name)
            if file_name in require:
                on_error = 'raise'
            elif file_name in optional:
                on_error = 'ignore'
            else:
                on_error = 'log'
            if self.local_mode:
                remote_file_path = os.path.join(self.input_path, file_name)
                file = self._safeCopyFile(remote_file_path, local_file_path, on_error=on_error)
            else:
                remote_file_path = f'{self.input_path}/{file_name}'
                file = self._downloadObject(remote_file_path, local_file_path, on_error=on_error)
            input_files.update(file)
        return input_files

    def uploadFiles(self, files, scenario_name=None, on_error='log'):
        """
        Upload files in a manner consistent with ImpairmentStudio expectations
        :note: if file name is found in MRP outputPaths, the correct outputPath will be used
        :note: if scenario is given, scenarioPartition will be added to the output path
        :note: if file name is not found in MRP outputPaths, file will be uploaded to logPath
        :note: if run in local mode, will upload to local test folder output in similar manner to above
        """
        for file, file_path in files.items():
            ext = os.path.splitext(file_path)[1]
            out_path = self.model_run_parameters.output_s3_paths.get(file)
            if self.local_mode:
                if out_path and scenario_name:
                    dest_path = os.path.join(self.test_folder_output, file, f'scenarioPartition={scenario_name}', f'data{ext}')
                elif out_path:
                    dest_path = os.path.join(self.test_folder_output, file, f'data{ext}')
                else:
                    dest_path = os.path.join(self.test_folder_output, 'log', os.path.basename(file_path))
                self._safeCopyFile(file_path, dest_path, on_error=on_error)
            else:
                if out_path and scenario_name:
                    s3_key = f'{out_path}/scenarioPartition={scenario_name}/data{ext}'
                elif out_path:
                    s3_key = f'{out_path}/data{ext}'
                else:
                    s3_key = f'{self.model_run_parameters.log_s3_path}/{os.path.basename(file_path)}'
                self._uploadFile(file_path, s3_key, on_error=on_error)

    def writeFileObjectToDisk(self, file_object, file_name, directory=None):
        """
        Write a file object to disk, optionally specifying a directory.
        :param file_object: file object to write
        :param file_name: file name to write (will be appended to directory)
        :param directory: directory to place file, defaulting to temp logPath
        :return: full file path to written file
        """
        # TODO: Make more generic?
        directory = directory or self.local_directories['logPath']
        file_path = os.path.join(directory, file_name)
        with open(file_path, 'wb') as f:
            self.logger.info(f'Writing file: {file_name}')
            f.write(file_object)
        return file_path

    def copyTempFilesToDominoWorkSpace(self):
        # TODO: Create this method
        pass
