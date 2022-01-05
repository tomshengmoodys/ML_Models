import os
import pandas as pd


def createCsv(df, file_name, **kwargs):
    """Safely write csv from data frame, overwriting if exists. kwargs must be acceptable inputs to .DataFrame.to_csv"""
    try:
        os.remove(file_name)
    except:
        pass
    os.makedirs(os.path.dirname(file_name), exist_ok=True)
    df.to_csv(file_name, **kwargs)


def createComparisonCsv(benchmark_df, output_df, output_file_name, ignore_column_case=True):
    """Generate a side-by-side comparison csv file out of two data frames"""
    if ignore_column_case:
        benchmark_df.rename(str.lower, axis='columns')
        output_df.rename(str.lower, axis='columns')
    comparison_df = pd.DataFrame()
    for column in benchmark_df:
        comparison_df[f'{column}_benchmark'] = benchmark_df[column]
        comparison_df[f'{column}_test_output'] = output_df.get(column, 'missing column in output')
    extra_output_columns = output_df.columns.difference(benchmark_df.columns)
    for column in extra_output_columns:
        comparison_df[column] = 'extra column in output'
    createCsv(comparison_df, output_file_name, index=False)


def getDifference(benchmark_df, output_df, ignore_column_case=True):
    """Return an array of the differences between two data frames"""
    wrong = []
    if ignore_column_case:
        benchmark_df.rename(str.lower, axis='columns')
        output_df.rename(str.lower, axis='columns')
    missing_columns = list(benchmark_df.columns.difference(output_df.columns))
    extra_columns = list(output_df.columns.difference(benchmark_df.columns))
    missing_indices = list(benchmark_df.index.difference(output_df.index))
    extra_indices = list(output_df.index.difference(benchmark_df.index))
    if missing_columns:
        wrong.append(f'Columns missing in output: {missing_columns}')
    if extra_columns:
        wrong.append(f'Extra columns in output: {extra_columns}')
    if missing_indices:
        wrong.append(f'Indices missing in output: {missing_indices}')
    if extra_indices:
        wrong.append(f'Extra indices in output: {extra_indices}')
    for index, benchmark_row in benchmark_df.iterrows():
        try:
            output_row = output_df.iloc[index]
        except IndexError:
            continue
        for column in benchmark_df.columns:
            benchmark_value = benchmark_row.get(column)
            output_value = output_row.get(column)
            if output_value is None:
                continue  # For cases where column not found in output
            if pd.isna(output_value) and pd.isna(benchmark_value):
                continue  # Because NaN == NaN for our purposes here
            if output_value != benchmark_value:
                wrong.append(f'Row {index} column {column} value {output_row[column]} does not equal benchmark of {benchmark_row[column]}')
    return wrong
