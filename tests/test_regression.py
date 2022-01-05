from datetime import datetime
from moodyscappy import Cappy
import glob
import itertools
import json
import logging
import os
import pandas as pd
import shutil
import subprocess
import sys
import unittest
import warnings


# Adding package directory necessary for some imports to work in local mode. List local imports below
TEST_DIRECTORY = os.path.dirname(os.path.abspath(__file__))
PACKAGE_DIRECTORY = os.path.dirname(TEST_DIRECTORY)
MAPPING_DIRECTORY = os.path.join(PACKAGE_DIRECTORY, 'mapping')
CAP_DIRECTORY = os.path.join(PACKAGE_DIRECTORY, 'cap')
MODEL_DIRECTORY = os.path.join(CAP_DIRECTORY, 'model')
CONFIG_DIRECTORY = os.path.join(CAP_DIRECTORY, 'config')
sys.path.extend([PACKAGE_DIRECTORY, TEST_DIRECTORY, MODEL_DIRECTORY, MAPPING_DIRECTORY, CONFIG_DIRECTORY, CAP_DIRECTORY])
from cap.config import config
from tests import helpers

# Configuration files
TEST_CONFIG_FILE = os.path.join(TEST_DIRECTORY, 'regression.ini')
LOGGING_CONFIG_FILE = os.path.join(CONFIG_DIRECTORY, 'logging.ini')
QA_CONFIG_FILE = os.path.join(CONFIG_DIRECTORY, 'model-conf-qa.ini')

# CLI run parameters
LOG_LEVEL = ['-l', 'DEBUG']
CONFIG_OVERWRITE = ['-o', QA_CONFIG_FILE]

# Digits to compare for float64 dtypes
EPSILON = 10

# Get usernames and passwords from environment variables
USER_NAME = os.environ.get('E2E_TEST_UN')
PASSWORD = os.environ.get('E2E_TEST_PW')
PROXY_USER_NAME = os.environ.get('E2E_TEST_PROXY_UN')
PROXY_PASSWORD = os.environ.get('E2E_TEST_PROXY_PW')


class Regression(unittest.TestCase):

    def setUp(self):
        # Suppress boto3 unclosed socket warnings (known bug, see: https://github.com/kennethreitz/requests/issues/3912)
        warnings.simplefilter("ignore", ResourceWarning)

    @classmethod
    def addTestCase(cls, test_directory, user_info, proxy_user_info, cap_session):
        """Create a unit test case for each test listed in regression.ini"""

        def e2eTest(self):
            if None in user_info:
                self.skipTest('No E2E_TEST_UN or E2E_TEST_PW found in environment variables')
            start_time = datetime.now()
            test = EndToEndTestCase(test_directory, user_info, proxy_user_info, cap_session)
            exit_code = test.run()
            results = test.checkOutput()
            results.append(exit_code == 0)
            if exit_code != 0:
                test.log.error(f'Model returned exit code: {exit_code}')
            all_tests_passed = len(list(filter(lambda x: not x, results))) == 0
            try:
                success_msg = f'All tests passed.'
                err_msg = f'One or more tests failed. For details, refer to test.log file.'
                self.assertTrue(all_tests_passed, err_msg)
                test.log.info(success_msg)
            except Exception as e:
                test.log.error(e)
                raise
            finally:
                run_time = datetime.now() - start_time
                test.log.info(f'Time to test completion: {run_time}')
                test.cleanUp()
        setattr(cls, f'test_e2e_{os.path.basename(test_directory)}', e2eTest)


class EndToEndTestCase:
    """Uploads test files, runs test, downloads and compares outputs"""

    def __init__(self, test_directory, user_info, proxy_user_info, cap_session):
        self.test_directory = test_directory
        self.user_info = user_info
        self.proxy_user_info = proxy_user_info
        self.s3 = cap_session.init_s3_client()
        self.bucket = cap_session.context['s3_bucket']
        self.log_file = os.path.abspath(os.path.join(test_directory, 'test.log'))
        config.configureLogger(config_file=LOGGING_CONFIG_FILE, log_file=self.log_file)
        self.log = logging.getLogger(os.path.basename(test_directory))
        self.log.info(f'Setting up test case in: {test_directory}')

        self.local_output_directory = os.path.join(test_directory, 'output')
        self.local_benchmark_folder = os.path.join(test_directory, 'benchmark')
        self.local_errors_directory = os.path.join(test_directory, 'errors')

        self.mrp_path = self.getModelRunParameters(test_directory)
        self.mrp_json = self.getModelRunParameterJson(self.mrp_path)

        self.s3_log_path = self.mrp_json.get('settings', {}).get('logPath')
        self.s3_input_path = self.mrp_json.get('settings', {}).get('inputPath')
        self.s3_output_paths = self.mrp_json.get('settings', {}).get('outputPaths', {}).values()

    def run(self):
        """clear old test data. upload test files to S3, run model script, and download ouput files"""
        # Clear local and S3 test directories
        self.clearLocalOutputDirecetory()
        self.clearS3Directories()
        # Upload test files to S3
        self.log.info('Uploading local input_csv files and model run parameters')
        input_files = glob.glob(os.path.join(self.test_directory, 'input_csv', '*'))
        uploaded_keys = [self.uploadFile(file, self.s3_input_path) for file in input_files]
        mrp_key = self.uploadFile(self.mrp_path, os.path.dirname(self.s3_input_path))
        # Run test and download result files
        process = self.execute(mrp_key)
        self.results = self.downloadFiles()
        return process.returncode

    def cleanUp(self):
        logging.shutdown()
        self.uploadTestResults()

    def checkOutput(self):
        benchmark_to_result = self.mapBenchmarkToOutputFiles()
        test_results = []
        for benchmark, result in benchmark_to_result.items():
            if os.path.splitext(benchmark)[1].lower() == '.csv':
                test_results.append(self.compareCsvFiles(benchmark, result))
        return test_results

    def compareCsvFiles(self, benchmark_csv, test_csv=None):
        try:
            benchmark_df = pd.read_csv(benchmark_csv)
            benchmark_file_name = benchmark_csv[benchmark_csv.find('benchmark') + 10:]
            test_df = pd.read_csv(test_csv)
            test_file_name = test_csv[test_csv.rfind('output') + 7:]
            pd.util.testing.assert_frame_equal(benchmark_df, test_df, check_less_precise=EPSILON)
            self.log.info(f'Test PASSED: file {test_csv} matches benchmark {benchmark_file_name}')
            return True
        except ValueError:
            self.log.error(f'No output file found for corresponding benchmark: {benchmark_file_name}')
            return False
        except AssertionError:
            self.log.error(f'File: {test_file_name} does not match benchmark file: {benchmark_file_name}')
            differences = helpers.getDifference(benchmark_df, test_df)
            for difference in differences:
                self.log.error(difference)
            diff_file_name = f'{os.path.splitext(benchmark_file_name)[0].replace(os.sep, "_")}_diff.csv'
            diff_file_path = os.path.join(self.local_errors_directory, diff_file_name)
            self.log.error(f'Creating difference file: {diff_file_path}...')
            helpers.createComparisonCsv(benchmark_df, test_df, diff_file_path)
            return False
        except Exception as e:
            self.log.error(f'An unknown exception occurred while processing benchmark: {benchmark_file_name}')
            self.log.error(e)
            return False

    def mapBenchmarkToOutputFiles(self):
        benchmarks = glob.glob(os.path.join(self.local_benchmark_folder, '**'), recursive=True)
        benchmark_files = [path for path in benchmarks if os.path.isfile(path)]
        target_files = [file[file.find('benchmark') + 10:] for file in benchmark_files]
        target_to_benchmark = dict(zip(target_files, benchmark_files))
        benchmark_to_result = {}
        for target, benchmark in target_to_benchmark.items():
            benchmark_to_result[benchmark] = None
            for result in self.results:
                if target in result:
                    benchmark_to_result[benchmark] = result
                    break
        return benchmark_to_result

    def getModelRunParameters(self, test_directory):
        return glob.glob(f'{test_directory}{os.sep}*.json')[0]

    def getModelRunParameterJson(self, mrp_path):
        with open(mrp_path, 'r') as f:
            mrp_json = json.load(f)
        return mrp_json

    def clearLocalOutputDirecetory(self):
        self.log.info(f'Clearing local output directory: {self.local_output_directory}')
        shutil.rmtree(self.local_output_directory, ignore_errors=True)
        self.log.info(f'Clearing local errors directory: {self.local_errors_directory}')
        shutil.rmtree(self.local_errors_directory, ignore_errors=True)
        os.makedirs(self.local_output_directory, exist_ok=True)

    def clearS3Directories(self):
        def clearS3Directory(s3_directory):
            try:
                keys = self.listKeys(s3_directory)
                return [self.s3.delete_object(Bucket=self.bucket, Key=key) for key in keys]
            except Exception as e:
                self.log.error(e)

        clear_s3_paths = [self.s3_input_path, self.s3_log_path, *self.s3_output_paths]
        self.log.info(f'Clearing S3 paths: {clear_s3_paths}')
        return [clearS3Directory(path) for path in clear_s3_paths]

    def uploadFile(self, file, key_path):
        key = f'{key_path}/{os.path.basename(file)}'
        try:
            self.s3.upload_file(Filename=file, Bucket=self.bucket, Key=key)
            return key
        except Exception as e:
            self.log.error(f'Error uploading {file} to {key}')
            self.log.error(e)

    def uploadTestResults(self):
        self.uploadFile(self.log_file, f'{self.s3_log_path}/test_results')
        comparison_files = glob.glob(os.path.join(self.local_errors_directory, '*'), recursive=True)
        comparison_files = [path for path in comparison_files if os.path.isfile(path)]
        for file in comparison_files:
            self.uploadFile(file, f'{self.s3_log_path}/test_results')

    def listKeys(self, prefix):
        return [obj['Key'] for obj in self.s3.list_objects_v2(Bucket=self.bucket, Prefix=prefix).get('Contents', [])]

    def downloadFiles(self):
        def downloadFile(key):
            file_path = os.path.abspath(os.path.join(self.local_output_directory, key))
            try:
                os.makedirs(os.path.dirname(file_path), exist_ok=True)
                self.s3.download_file(Bucket=self.bucket, Key=key, Filename=file_path)
                return file_path
            except:
                self.log.error(f'Error downloading file: {file_path}')
                return ''

        output_keys = list(itertools.chain(*[self.listKeys(path) for path in self.s3_output_paths]))
        log_keys = self.listKeys(self.s3_log_path)
        self.log.info(f'Downloading files: {[*output_keys, *log_keys]}')
        return [downloadFile(key) for key in [*output_keys, *log_keys]]

    def execute(self, s3_path):
        run_path = os.path.join(MODEL_DIRECTORY, 'run.py')
        run_command = ['python', run_path, '-s', s3_path, *self.user_info, *self.proxy_user_info, *CONFIG_OVERWRITE, *LOG_LEVEL]
        print_command = ['python', run_path, '-s', s3_path, '-u **** ****', '-p **** ****' if self.proxy_user_info else '', *CONFIG_OVERWRITE, *LOG_LEVEL]
        self.log.info(f'Executing command: {" ".join(print_command)}')
        return subprocess.run(run_command)


def main():
    user_info = ['-u', USER_NAME, PASSWORD]
    proxy_user_info = ['-p', PROXY_USER_NAME, PROXY_PASSWORD] if PROXY_USER_NAME and PROXY_PASSWORD else []
    config._loadAll(QA_CONFIG_FILE)
    cap_session = Cappy(username=USER_NAME, password=PASSWORD, errors='log')
    test_cases = [*config._getConfigParser(TEST_CONFIG_FILE)['CASES_LIST']]

    for test_case in test_cases:
        test_directory = os.path.join(TEST_DIRECTORY, test_case)
        Regression.addTestCase(test_directory, user_info, proxy_user_info, cap_session)


main()  # Can't be called from if __main__... block
if __name__ == '__main__':
    unittest.main()
