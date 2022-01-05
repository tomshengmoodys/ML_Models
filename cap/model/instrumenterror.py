import logging
import os
import pandas as pd
import sys
import warnings


DEFAULT_COLUMNS = [
    'errorMessage',
    'errorCode',
    'moduleCode',
    'analysisIdentifier',
    'scenarioIdentifier',
    'portfolioIdentifier',
    'instrumentIdentifier'
]

DEFAULT_NAME = 'model_root'

# Default entry parameters
DEFAULT_ERROR_CODE = 100
DEFAULT_MODEL_NAME = None
DEFAULT_ANALYSIS_ID = None
DEFAULT_SCENARIO_ID = None
DEFAULT_PORTFOLIO_ID = None
DEFAULT_INSTRUMENT_ID = None
DEFAULT_ERROR_MESSAGE = 'An unknown exception has occurred'


class InstrumentErrorHandler:
    """Handler for creating and managing instrumentError.csv files"""
    _error_handlers = {}

    def __init__(self, name=DEFAULT_NAME, columns=DEFAULT_COLUMNS, **kwargs):
        self._name = name
        self._df = pd.DataFrame(columns=columns)
        self._logger = logging.getLogger(__name__)
        DEFAULT_MODEL_NAME = os.environ.get('MOODYS_MODEL_NAME')
        self.err_msg = kwargs.get('err_msg', DEFAULT_ERROR_MESSAGE)
        self.err_code = kwargs.get('err_code', DEFAULT_ERROR_CODE)
        self.module_code = kwargs.get('module_code', DEFAULT_MODEL_NAME)
        self.analysis_id = kwargs.get('analysis_id', DEFAULT_ANALYSIS_ID)
        self.scenario_id = kwargs.get('scenario_id', DEFAULT_SCENARIO_ID)
        self.portfolio_id = kwargs.get('portfolio_id', DEFAULT_PORTFOLIO_ID)
        self.instrument_id = kwargs.get('instrument_id', DEFAULT_INSTRUMENT_ID)
        self.allowed_kwargs = [kw for kw in vars(self) if kw[0] != '_']


    def entry(self, err_msg, log=False, **kwargs):
        """
        Create an entry in instrumentError data frame

        :param err_msg: message for the error
        :param log: Boolean flag to optionally log an error
        :param kwargs.instrument_id: instrument ID where the error was generated
        :param kwargs.err_code: alphanumeric code for the error
        :param kwargs.module_code: module name where the error was generated
        :param kwargs.analysis_id: analysis ID where the error was generated
        :param kwargs.scenario_id: scenario ID where the error was generated
        :param kwargs.portfolio_id: portfolio ID where the error was generated
        """
        entry = {
            'errorMessage': err_msg,
            'errorCode': kwargs.get('err_code', self.err_code),
            'moduleCode': kwargs.get('module_code', self.module_code),
            'analysisIdentifier': kwargs.get('analysis_id', self.analysis_id),
            'scenarioIdentifier': kwargs.get('scenario_id', self.scenario_id),
            'portfolioIdentifier': kwargs.get('portfolio_id', self.portfolio_id),
            'instrumentIdentifier': kwargs.get('instrument_id', self.instrument_id)
        }
        self._df = self._df.append(entry, sort=False, ignore_index=True)
        self._logger.error(err_msg) if log else None


    def createInstrumentErrorFile(self, directory, columns=DEFAULT_COLUMNS):
        """
        Write instrumentError.csv file from data frame, optionally joining root handler's data frame.

        :param directory: directory to write file to
        :param columns: columns to output
        :return: dictionary {'instrumentError': file_path} or empty dictionary if no entries in data frame
        """
        df = self._df.copy()
        if len(df.index) == 0:
            return {}
        column_mapper = {column.lower(): column for column in self._df.columns}
        mapped_columns = [column_mapper.get(column.lower(), column) for column in columns]
        df = df.reindex(columns=mapped_columns)
        os.makedirs(directory, exist_ok=True)
        # TODO: Make more fault tolerant. What happens if directory not provided (present in MRP)?
        file_path = os.path.join(directory, 'instrumentError.csv')
        df.to_csv(file_path, index=False, date_format='%Y-%m-%d')
        self._logger.error('One or more error files have been generated')
        return {'instrumentError': file_path}


    def joinDataFrame(self, data_frame, keep_alt_cols=False, prepend=False):
        """
        Join another data frame to self._df case-insensitively, optionally keeping non-mathcing columns
        :param data_frame: data frame to be appended
        :param keep_alt_cols: Don't discard columns that do not match default columns
        :return: calling InstrumentErrorHandler
        """
        data_frame = data_frame.copy()
        df_column_map = {column: column.lower() for column in data_frame.columns}
        self_column_map = {column.lower(): column for column in self._df.columns}
        from_col_to_col_map = {reg_col: self_column_map.get(low_col) for reg_col, low_col in df_column_map.items()}
        rename_columns = {from_col: to_col for from_col, to_col in from_col_to_col_map.items() if to_col is not None}
        extra_columns = [from_col for from_col, to_col in from_col_to_col_map.items() if to_col is None]
        keep_columns = [*extra_columns, *self._df.columns] if keep_alt_cols else self._df.columns
        data_frame = data_frame.rename(columns=rename_columns).reindex(columns=keep_columns)
        to_concat = [data_frame, self._df] if prepend else [self._df, data_frame]
        self._df = pd.concat(to_concat, ignore_index=True, sort=False).reset_index(drop=True)
        return self


    # def join(self):
    #     pass


    # def copy(self, new_name=None, overwrite=False):
    #     """
    #     :param new_name: 
    #     :raises ValueError: if handler with name exists and overwrite flag is not True
    #     """
    #     if new_name in InstrumentErrorHandler._error_handlers and not overwrite:
    #         error_name = new_name if new_name is not None else 'Default'
    #         raise ValueError(f'{error_name} InstrumentErrorHandler already exists. To overwrite, set overwrite=True')
    #     columns = self._df.columns
    #     new_handler = getErrorHandler(new_name, columns)
    #     new_handler.df = self._df.copy()
    #     return new_handler

    def configureDefaults(self, **kwargs):
        """Overwrite current default parameters with soecified kwargs"""

        # Log warning on invalid kwargs
        for kw in [kw for kw in kwargs if kw not in self.allowed_kwargs]:
            self._logger.warning(f'Invalid keyword argument provided to configureDefaults: {kw}')

        self.err_msg = kwargs.get('err_msg', self.err_msg)
        self.err_code = kwargs.get('err_code', self.err_code)
        self.module_code = kwargs.get('module_code', self.module_code)
        self.analysis_id = kwargs.get('analysis_id', self.analysis_id)
        self.scenario_id = kwargs.get('scenario_id', self.scenario_id)
        self.portfolio_id = kwargs.get('portfolio_id', self.portfolio_id)
        self.instrument_id = kwargs.get('instrument_id', self.instrument_id)


def getErrorHandler(name=DEFAULT_NAME, columns=DEFAULT_COLUMNS, **kwargs):
    """
    Method for getting error handlers. Each handler is unique by its given name attribute

    :param name: name by which to get/create error handler
    :param columns: default columns to instantiate data frame with
    :return: error handler with given name, defaulting to root handler if name ommitted
    """
    if name in InstrumentErrorHandler._error_handlers:
        return InstrumentErrorHandler._error_handlers[name]
    else:
        InstrumentErrorHandler._error_handlers[name] = InstrumentErrorHandler(name, columns=columns, **kwargs)
        return InstrumentErrorHandler._error_handlers[name]


def warnOnMultipleImports():
    """
    If instrumenterror.py is imported multiple times
    (e.g., `import instrumenterror` in one module and `from cap.model import instrumenterror` in another)
    the singleton nature of the module will be broken, resulting in inconsistencies for more complex use-cases.
    :warns: UserWarning
    """
    count = 0
    for key in sys.modules:
        if 'instrumenterror' in key:
            count += 1
    if count > 1:
        warnings.warn("instrumenterror module imported in multiple namespaces. This may cause things to break unexpectedly.", UserWarning)


warnOnMultipleImports()
