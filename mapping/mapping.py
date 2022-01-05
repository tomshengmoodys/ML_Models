import os
import pandas as pd
import shutil


TRUTHY = {True, 'true', '1', '1.0', 1, 1.0}
FALSEY = {False, 'false', '0', '0.0', 0, 0.0}
NULLNA = {None, '', pd.np.NaN, pd.NaT}


def readCsvWithCorrectDtypes(csv_path, dtypes={}, **kwargs):
    """
    Read .csv files with provided datatypes, case-insensitively

    :param csv_path: File path to file to read
    :param dtypes: Dict {column_name: pandas.dtype}
    :param kwargs: Additional kwargs to pass to pandas.read_csv()
    :note: usecol kwarg given additional support for case-insensitivity
    :not supported: .csv files containing duplicate columns (case-insensitive)
    :return: Data frame
    """

    # Get columns from csv and create lowercase mapping for use later
    csv_columns = {column.lower(): column for column in pd.read_csv(csv_path, nrows=0).columns}

    # Create separate mapping data structures for problematic dtypes
    int_columns = {column for column, dtype in dtypes.items() if 'int' in dtype}
    bool_columns = {column for column, dtype in dtypes.items() if 'bool' in dtype}
    date_columns = {column for column, dtype in dtypes.items() if 'datetime64' in dtype}

    # Filter problematic types out of dtypes and set case properly
    dtypes = {column: dtypes[column] for column in ({*dtypes} - int_columns - bool_columns - date_columns)}
    dtypes = {column.lower(): dtype for column, dtype in dtypes.items()}
    dtypes = {csv_columns.get(column): dtype for column, dtype in dtypes.items() if csv_columns.get(column)}

    # If usecols kwarg supplied, set column casing correctly
    usecols = {csv_columns.get(column.lower()) for column in kwargs.get('usecols', [])}
    kwargs['usecols'] = (usecols - {None}) or None

    # Process kwargs and read csv
    kwargs = {'low_memory': False, 'memory_map': True, 'dtype': dtypes, **kwargs}
    df = pd.read_csv(csv_path, **kwargs)

    # Process datetime columns separately, as pd.to_datetime() handles errors better than pd.read_csv()
    for date_column in date_columns:
        df[date_column] = pd.to_datetime(df[date_column], errors='coerce')

    # Process boolean columns separately, as pandas will break if a bool column has NaNs
    for bool_column in bool_columns:
        df[bool_column] = toBoolean(df[bool_column])

    # Process integer columns separately, as pandas will break if an int column has NaNs
    for int_column in int_columns:
        df[int_column] = toInteger(df[int_column])

    # Return data frame, optionally lowercasing columns
    return df


def toBoolean(series):
    series = series.map(str).map(str.lower)
    return [True if val in TRUTHY else False if val in FALSEY else None for val in series]


def toInteger(series):
    new_series = []
    for val in series:
        try:
            x = int(val)
        except ValueError:
            x = pd.np.NaN
        new_series.append(x)
    return pd.Series(new_series, dtype='object')


def createCsvFilesFromDataFrames(data_frame_dict, directory, scenario_name=None, **to_csv_kwargs):
    """
    Create temp files from data frames
    :param data_frame_dict: dict of data frames {name: data_frame}
    :param scenario_name: If given scenario name will be appended to the file name
    :param read_csv_kwargs: Keyword arguments to pass to pandas.DataFrame.to_csv()
    :return: dict of file paths to temp files {name: file_path}
    """
    return_files = {}
    to_csv_kwargs = {'date_format': '%Y-%m-%d', 'index': False, **to_csv_kwargs}
    for name, data_frame in data_frame_dict.items():
        file_name = name + (f'_{scenario_name}' if scenario_name else '') + '.csv'
        file_path = os.path.join(directory, file_name)
        data_frame.to_csv(file_path, **to_csv_kwargs)
        return_files[name] = file_path
    return return_files


def reindexCaseInsensitively(data_frame, reindex_columns):
    to_columns = {column.lower(): column for column in reindex_columns}
    data_frame = data_frame.rename(columns=str.lower).rename(columns=to_columns)
    return data_frame.reindex(columns=reindex_columns, fill_value='')


def mapEnums(df, enum_mapping):
    """ Map the enums of columns in a data frame case-insensitively """
    map_to_original_columns = {column.lower(): column for column in df}
    df = df.rename(columns=str.lower)
    for column, enums in enum_mapping.items():
        enums = {k.lower(): v for k, v in enums.items()}
        df[column.lower()] = df[column.lower()].map(str.lower, na_action='ignore').map(enums, na_action='ignore')
    return df.rename(columns=map_to_original_columns)


def cleanOutputHeaders(files):
    """
    Replace non-standard characters in CSV file columns so pandas can do its thing.

    :param files: dict of {name: path to possibly unreadable (by pandas) file}
    :return: path to cleaned file
    """
    return_files = {}
    map_bad_chars_to_good = {'–': '-'}  # pandas chokes on en-dashes (4 byte utf8 char)
    for name, in_file_path in files.items():
        file, ext = os.path.splitext(in_file_path)
        out_file_path = f'{file}_cleaned{ext}'
        return_files[name] = out_file_path
        with open(in_file_path, 'r', encoding='cp1252') as in_file:
            line = in_file.readline()
            for bad, good in map_bad_chars_to_good.items():
                line = line.replace(bad, good)
            with open(out_file_path, 'w') as out_file:
                out_file.write(line)
                shutil.copyfileobj(in_file, out_file)
    return return_files
