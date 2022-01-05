import os
import pandas as pd
import sys
import unittest
TEST_DIRECTORY = os.path.dirname(os.path.abspath(__file__))
PACKAGE_DIRECTORY = os.path.dirname(TEST_DIRECTORY)
sys.path.extend([TEST_DIRECTORY, PACKAGE_DIRECTORY])
from cap.model import instrumenterror
# import cap.model.instrumenterror as another_import # for testing globalness
from pandas.util.testing import assert_frame_equal

DEFAULT_COLUMNS = ['errormessage', 'instrumentidentifier', 'errorcode', 'modulecode', 'analysisidentifier', 'scenarioidentifier', 'portfolioidentifier']
DEFAULT_NAME = 'model_root'
DEFAULT_ERROR_CODE = 100
DEFAULT_ERROR_MESSAGE = 'An unknown exception has occurred'
DEFAULT_MODULE_CODE = 'MA Structured Analytics'

class TestJoinDataFrame(unittest.TestCase):


    def setUp(self):
        self.test_join_df = pd.DataFrame({
            'analysisIdentifier': [10],
            'instrumentIdentifier': [1],
            'portfolioIdentifier': [7],
            'scenarioidentifier': [13],
            'errorcode': [24],
            'errorMessage': ['test error message'],
            'moduleCode': [18],
            'new_column': ['why would I ever need this?']
        })


    def test_empty_df_doesnt_break_it(self):
        instrument_error = instrumenterror.getErrorHandler('test_empty_df_doesnt_break_it')
        instrument_error.entry(err_msg='cannot compute', err_code=42)
        original_df = instrument_error._df.copy()
        instrument_error.joinDataFrame(pd.DataFrame(columns=instrument_error._df.columns))
        assert_frame_equal(original_df, instrument_error._df)


    def test_index_is_reset(self):
        instrument_error = instrumenterror.getErrorHandler('test_index_is_reset')
        instrument_error.entry(err_msg='cannot compute', err_code=42)
        instrument_error.joinDataFrame(self.test_join_df)
        assert [*instrument_error._df.index] == [0, 1]


    def test_keep_extra_columns(self):
        instrument_error = instrumenterror.getErrorHandler('test_keep_extra_columns')
        instrument_error.entry(err_msg='cannot compute', err_code=42)
        instrument_error.joinDataFrame(self.test_join_df, keep_alt_cols=True)
        assert 'new_column' in instrument_error._df.columns


    def test_dont_keep_extra_columns(self):
        instrument_error = instrumenterror.getErrorHandler('test_dont_keep_extra_columns')
        instrument_error.entry(err_msg='cannot compute', err_code=42)
        instrument_error.joinDataFrame(self.test_join_df, keep_alt_cols=False)
        assert 'new_column' not in instrument_error._df.columns


    def test_case_insensitivity(self):
        instrument_error = instrumenterror.getErrorHandler('test_case_insensitivity')
        original_df = instrument_error._df.copy()
        instrument_error.entry(err_msg='cannot compute', err_code=42)
        instrument_error.joinDataFrame(self.test_join_df)
        assert {*instrument_error._df.columns} == {*original_df.columns}


    def test_global_availability_after_join(self):
        instrument_error = instrumenterror.getErrorHandler('test_global_availability_after_join')
        instrument_error.entry(err_msg='cannot compute', err_code=42)
        instrument_error.joinDataFrame(self.test_join_df)
        get_it_again = instrumenterror.getErrorHandler('test_global_availability_after_join')
        assert_frame_equal(get_it_again._df, instrument_error._df)
        get_it_again.entry(err_msg='cannot compute again', err_code=44)
        assert_frame_equal(get_it_again._df, instrument_error._df)


    def test_dont_modify_input_data_frame(self):
        instrument_error = instrumenterror.getErrorHandler('test_dont_modify_input_data_frame')
        instrument_error.entry(err_msg='cannot compute', err_code=42)
        original_df = self.test_join_df.copy()
        instrument_error.joinDataFrame(self.test_join_df)
        assert_frame_equal(original_df, self.test_join_df)


    def test_instrument_error_empty_ok(self):
        instrument_error = instrumenterror.getErrorHandler('test_instrument_error_empty_ok')
        assert len(instrument_error._df.index) == 0
        instrument_error.joinDataFrame(self.test_join_df)
        assert len(instrument_error._df.index) == 1


    def test_prepend_flag_works(self):
        instrument_error = instrumenterror.getErrorHandler('test_prepend_flag_works')
        instrument_error.entry(err_msg='cannot compute', err_code=42)
        assert [*instrument_error._df['errorCode']] == [42]
        instrument_error.joinDataFrame(self.test_join_df)
        assert [*instrument_error._df['errorCode']] == [42, 24]
        instrument_error.joinDataFrame(self.test_join_df, prepend=True)
        assert [*instrument_error._df['errorCode']] == [24, 42, 24]


    def test_returning_self_still_available_globally(self):
        instrument_error = instrumenterror.getErrorHandler('test_prepend_flag_works')
        instrument_error.entry(err_msg='cannot compute', err_code=42)
        returned_handler = instrument_error.joinDataFrame(self.test_join_df)
        returned_handler.entry(err_msg='cannot compute', err_code=24)
        new_handler =  instrumenterror.getErrorHandler('test_prepend_flag_works')
        new_handler.entry(err_msg='cannot compute', err_code=33)
        assert returned_handler is instrument_error
        assert returned_handler is new_handler
        assert new_handler is instrument_error
        assert_frame_equal(returned_handler._df, instrument_error._df)
        assert_frame_equal(returned_handler._df, new_handler._df)
        assert_frame_equal(new_handler._df, instrument_error._df)


if __name__ == '__main__':
    unittest.main()
