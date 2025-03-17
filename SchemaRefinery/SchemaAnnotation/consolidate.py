import os
import pandas as pd
from typing import Dict, Tuple, List

try:
    from utils import (pandas_functions as upf,
					   print_functions as prf)
except ModuleNotFoundError:
    from SchemaRefinery.utils import (pandas_functions as upf,
									  print_functions as prf)

def consolidate_annotations(consolidate_annotation_files: List[str],
                            cleanup: bool,
                            output_file: str) -> str:
    """
    Consolidates annotations from different annotation files into a single file.
    
    Parameters
    ----------
    consolidate_annotation_files: List[str]:
        List of files of annotations to consolidate.
    cleanup: bool
        If the final file will or not have duplicates. Advised for the use of match schemas annotations.
    output_file: str
        Path to the directory where output files will be saved.

    Returns
    -------
    str
        Path to the annotations file.
    """

    # Create dataframes out of the first 2 files in the list
    prf.print_message('Format tsv files for merging...', 'info')

    with open(output_file, 'w') as f:
        f.write("")

    # Check if all files exist
    for i in range(len(consolidate_annotation_files)):
        if os.path.getsize(consolidate_annotation_files[i]) == 0:
            prf.print_message(f'The file number {i+1} is empty.', 'error')
            sys.exit()
    
    first_df = pd.read_csv(consolidate_annotation_files[0], delimiter='\t', dtype=str, index_col=False)
    second_df = pd.read_csv(consolidate_annotation_files[1], delimiter='\t', dtype=str, index_col=False)
    


##### MUDARRRRRRRRR
    first_0_filtered = first_df[first_df.iloc[:, 0] != 'Not Matched'].sort_values(by=first_df.columns[0])
    second_0_filtered = second_df[(second_df.iloc[:, 0] != 'Not Matched')].sort_values(by=second_df.columns[0])
    first_1_filtered = first_df[(first_df.iloc[:, 1] != 'Not Matched')].sort_values(by=first_df.columns[1])
    second_1_filtered = second_dfs[(second_df.iloc[:, 1] != 'Not Matched')].sort_values(by=second_df.columns[1])


    prf.print_message('Merging first 2 files...', 'info')
    # Compare the first columns of both files
    if first_0_filtered.iloc[:, 0].equals(second_0_filtered.iloc[:, 0]):
        prf.print_message('First columns are a match', 'info')
        upf.merge_files_by_column_values(consolidate_annotation_files[0],
                                            consolidate_annotation_files[1],
                                            0,
                                            0,
                                            output_file)
    # Compare the first column of the first file and the second one of the second file
    elif first_0_filtered.iloc[:, 0].equals(second_1_filtered.iloc[:, 1]):
        prf.print_message('First and second columns are a match', 'info')
        upf.merge_files_by_column_values(consolidate_annotation_files[0],
                                            consolidate_annotation_files[1],
                                            0,
                                            1,
                                            output_file)
    # Compare the second column of the first file and the first one of the second file
    elif first_1_filtered.iloc[:, 1].equals(second_0_filtered.iloc[:, 0]):
        prf.print_message('Second and first columns are a match', 'info')
        upf.merge_files_by_column_values(consolidate_annotation_files[0],
                                            consolidate_annotation_files[1],
                                            1,
                                            0,
                                            output_file)
    # Compare the second columns of both files
    elif first_1_filtered.iloc[:, 1].equals(second_1_filtered.iloc[:, 1]):
        prf.print_message('Second columns are a match', 'info')
        upf.merge_files_by_column_values(consolidate_annotation_files[0],
                                            consolidate_annotation_files[1],
                                            1,
                                            1,
                                            output_file)
    else:
        prf.print_message('No columns are a match', 'info')

    # Merge the remaining files
    if len(consolidate_annotation_files) > 2:
        prf.print_message('Merging the remaining files...', 'info')
        for i in range(2, len(consolidate_annotation_files)):
            pf.print_message(f"Merging file: {i}/{len(consolidate_annotation_files)}", "info", end='\r', flush=True)
            old_df = pd.read_csv(output_file, delimiter='\t', dtype=str, index_col=False)
            new_df = pd.read_csv(consolidate_annotation_files[i], delimiter='\t', dtype=str, index_col=False)
            
            old_0_filtered = old_df[(old_df.iloc[:, 0] != 'Not Matched')].sort_values(by=old_df.columns[0])
            new_0_filtered = new_df[(new_df.iloc[:, 0] != 'Not Matched')].sort_values(by=new_df.columns[0])
            old_1_filtered = old_df[(old_df.iloc[:, 1] != 'Not Matched')].sort_values(by=old_df.columns[1])
            new_1_filtered = new_df[(new_df.iloc[:, 1] != 'Not Matched')].sort_values(by=new_df.columns[1])


            # Compare the first columns of both files
            if old_0_filtered.iloc[:, 0].equals(new_0_filtered.iloc[:, 0]):
                upf.merge_files_by_column_values(output_file,
                                                    consolidate_annotation_files[i],
                                                    0,
                                                    0,
                                                    output_file)
            # Compare the first column of the first file and the second one of the second file
            elif old_0_filtered.iloc[:, 0].equals(new_1_filtered.iloc[:, 1]):
                upf.merge_files_by_column_values(output_file,
                                                    consolidate_annotation_files[i],
                                                    0,
                                                    1,
                                                    output_file)
            # Compare the second column of the first file and the first one of the second file
            elif old_1_filtered.iloc[:, 1].equals(new_0_filtered.iloc[:, 0]):
                upf.merge_files_by_column_values(output_file,
                                                    consolidate_annotation_files[i],
                                                    1,
                                                    0,
                                                    output_file)
            # Compare the second columns of both files
            elif old_1_filtered.iloc[:, 1].equals(new_1_filtered.iloc[:, 1]):
                upf.merge_files_by_column_values(output_file,
                                                    consolidate_annotation_files[i],
                                                    1,
                                                    1,
                                                    output_file)

    # If cleanup TRUE dedeup the final file
    if cleanup:
        prf.print_message('Deduplicating the final file...', 'info')
        ann_df = pd.read_csv(output_file, delimiter='\t', dtype=str, index_col=False)
        ann_df.sort_values(by=ann_df.columns[0], ascending=False, inplace=True)
        ann_df.drop_duplicates(subset=ann_df.columns[0], inplace=True)
        ann_df.to_csv(output_file, sep="\t", index=False)

    return output_file