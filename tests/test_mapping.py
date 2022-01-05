import os
import pandas as pd
import sys
import unittest
TEST_DIRECTORY = os.path.dirname(os.path.abspath(__file__))
PACKAGE_DIRECTORY = os.path.dirname(TEST_DIRECTORY)
sys.path.extend([TEST_DIRECTORY, PACKAGE_DIRECTORY])
from mapping import mapping


class TestReadCsvWithCorrectDtypes(unittest.TestCase):


    def setUp(self):
        self.test_csv_path = os.path.join(TEST_DIRECTORY, 'test_files', 'testMapping1.csv')


    def test_usecols_works(self):
        columns = {'float', 'float_int', 'uppercase_column'}
        test_df = mapping.readCsvWithCorrectDtypes(self.test_csv_path, usecols=columns)
        assert {*test_df.columns} == {'float', 'float_int', 'UPPERCASE_COLUMN'}


    def test_dtype_mapping_works_for_nan_supported_types(self):
        dtype_mapping = {
            'float': 'float64',
            'float_int': 'float64',
            'object': 'object',
            'object_float': 'object',
            'object_int': 'object',
            'date': 'datetime64[ns]',
            'object_date': 'object',
            'UPPERCASE_COLUMN': 'object'
        }
        test_df = mapping.readCsvWithCorrectDtypes(self.test_csv_path, dtypes=dtype_mapping)
        for column, dtype in dtype_mapping.items():
            assert test_df[column].dtype == dtype


    def test_dtype_mapping_works_for_bool(self):
        dtype_mapping = {
            'bool': 'bool',
            'mixed_bool': 'bool'
        }
        correct = {
            'bool': [True, True, True, False, False, False, False, False, False],
            'mixed_bool': [True, True, True, True, None, False, False, False, False]
        }
        test_df = mapping.readCsvWithCorrectDtypes(self.test_csv_path, dtypes=dtype_mapping)
        for column, array in correct.items():
            assert False not in [x is y for x, y in zip(test_df[column], array)]


    def test_dtype_mapping_works_for_int(self):
        dtype_mapping = {
            'int': 'int64',
            'int_float': 'int64'
        }
        correct = {
            'int': [1, 2, 3, 4, pd.np.NaN, pd.np.NaN, 7, 8, 9],
            'int_float': [1, 2, 3, 4, pd.np.NaN, pd.np.NaN, 7, 8, 9]
        }
        test_df = mapping.readCsvWithCorrectDtypes(self.test_csv_path, dtypes=dtype_mapping)
        for column, array in correct.items():
            assert False not in [x is y for x, y in zip(test_df[column], array)]


if __name__ == '__main__':
    unittest.main()
