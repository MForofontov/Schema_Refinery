import os
import concurrent.futures
from typing import Dict, List, Tuple, Optional, Union
from itertools import repeat

try:
    from utils import (
                        sequence_functions as sf,
                        blast_functions as bf,
                        linux_functions as lf,
                        file_functions as ff,
                        alignments_functions as af,
                        iterable_functions as itf,
    )
except ModuleNotFoundError:
    from SchemaRefinery.utils import (
                                    sequence_functions as sf,
                                    blast_functions as bf,
                                    linux_functions as lf,
                                    file_functions as ff,
                                    alignments_functions as af,
                                    iterable_functions as itf,
    )

def get_schema_files(schema_directory: str) -> Tuple[Dict[str, str], Dict[str, str]]:
    """
    Identify all of the FASTA files in the schema directory and its 'short' subdirectory.

    Parameters
    ----------
    schema_directory : str
        Path to the directory containing schema FASTA files.

    Returns
    -------
    Tuple[Dict[str, str], Dict[str, str]]
        A tuple containing two dictionaries:
        - The first dictionary maps loci names to their file paths in the schema directory.
        - The second dictionary maps loci names to their file paths in the 'short' subdirectory.
    """
    # Identify all of the FASTA files in the schema directory
    fasta_files_dict: Dict[str, str] = {
        loci.split('.')[0]: os.path.join(schema_directory, loci)
        for loci in os.listdir(schema_directory)
        if os.path.isfile(os.path.join(schema_directory, loci)) and loci.endswith('.fasta')
    }
    
    # Identify all of the FASTA files in the 'short' subdirectory
    short_folder: str = os.path.join(schema_directory, 'short')
    fasta_files_short_dict: Dict[str, str] = {
        loci.split('.')[0].split('_')[0]: os.path.join(short_folder, loci)
        for loci in os.listdir(short_folder)
        if os.path.isfile(os.path.join(short_folder, loci)) and loci.endswith('.fasta')
    }
    
    return fasta_files_dict, fasta_files_short_dict

def run_blasts_match_schemas(query_translations_paths: Dict[str, str], blast_db_files: str,
                             blast_folder: str, bsr: float, cpu: int):
    # Get Path to the blastp executable
    get_blastp_exec: str = lf.get_tool_path('blastp')
    
    # Get the maximum length of the IDs for better prints
    max_id_length: int = len(max(query_translations_paths.keys(), key=len))
    
    # Run BLASTp
    print("Running BLASTp...")
    blastp_results_folder: str = os.path.join(blast_folder, 'blastp_results')
    ff.create_directory(blastp_results_folder)
    
    # Run BLASTp between all BLASTn matches (rep vs all its BLASTn matches).
    bsr_values: Dict[str, Dict[str, float]] = {}
    best_bsr_values: Dict[str, Tuple[str, float]] = {}
    total_blasts: int = len(query_translations_paths)
    i: int = 1
    
    with concurrent.futures.ProcessPoolExecutor(max_workers=cpu) as executor:
        for res in executor.map(bf.run_blastdb_multiprocessing,
                                repeat(get_blastp_exec),
                                repeat(blast_db_files),
                                query_translations_paths.values(),
                                query_translations_paths.keys(),
                                repeat(blastp_results_folder)):
            # Get the alignments
            filtered_alignments_dict: Dict[str, Dict[str, Dict[str, float]]]
            filtered_alignments_dict, _, _, _ = af.get_alignments_dict_from_blast_results(res[1], 0, True, False, True, True, False)

            # Since BLAST may find several local alignments, choose the largest one to calculate BSR.
            for query, subjects_dict in filtered_alignments_dict.items():
                # Get the loci name
                loci: str = query.split('_')[0]
                # Create the dict of the query
                bsr_values.setdefault(query, {})
                for subject_id, results in subjects_dict.items():
                    # Highest score (First one)
                    subject_score: float = next(iter(results.values()))['score']
                    # Calculate BSR value
                    bsr_value: float = bf.compute_bsr(subject_score, self_score_dict[query])
                    # Check if the BSR value is higher than the threshold
                    if bsr_value >= bsr:
                        # Round BSR values if they are superior to 1.0 to 1 decimal place
                        if bsr_value > 1.0:
                            bsr_value = round(bsr_value, 1)
                        # Save all of the different matches that this query had and their BSR values
                        bsr_values[query].update({subject_id: bsr_value})
                    else:
                        continue
                    # Check if the BSR value is the best for the locus
                    current_best_bsr: Optional[Tuple[str, float]] = best_bsr_values.get(loci)
                    # If there is a previous BSR value for the locus, check if the current BSR value is higher
                    if current_best_bsr and bsr_value > current_best_bsr[1]:
                        best_bsr_values[loci] = (subject_id, bsr_value)
                    else:
                        best_bsr_values[loci] = (subject_id, bsr_value)

            print(f"\rRunning BLASTp for cluster representatives matches: {res[0]} - {i}/{total_blasts: <{max_id_length}}", end='', flush=True)
            i += 1

    return best_bsr_values

def match_schemas(query_schema: str, subject_schema: str, output_directory: str, bsr: float,
                  translation_table: int, cpu: int, run_mode: str):
    # Query schema files
    query_files: Dict[str, str]
    query_files_short: Dict[str, str]
    query_files, query_files_short = get_schema_files(query_schema)
    # Subject schema files
    subject_files: Dict[str, str]
    subject_files_short: Dict[str, str]
    subject_files, subject_files_short = get_schema_files(subject_schema)
    # Choose what files to use for the BLAST search
    query_fastas: Dict[str, str] = query_files if run_mode.split('_')[0] == 'alleles' else query_files_short
    subject_fastas: Dict[str, str] = subject_files_short if run_mode.split('_')[-1] == 'rep' else subject_files
    # Create the output directory
    blast_folder: str = os.path.join(output_directory, 'Blast')
    ff.create_directory(blast_folder)
    query_translation_folder: str = os.path.join(output_directory, 'Query_Translation')
    ff.create_directory(query_translation_folder)
    
    len_query_fastas: int = len(query_fastas)
    len_subject_fasta: int = len(subject_fastas)
    # Process query FASTA files
    query_translation_dict: Dict[str, str] = {}
    query_ids: Dict[str, List[str]] = {}
    query_translations_paths: Dict[str, str] = {}
    for query_loci, path in query_fastas.items():
        print(f"\rTranslated query loci FASTA: {i}/{len_query_fastas}", end='', flush=True)
        i += 1
        # Get the fasta sequences for the query
        fasta_dict: Dict[str, str] = sf.fetch_fasta_dict(path, False)
        # Save the IDs of the alleles
        query_ids.setdefault(query_loci, []).append([allele_id for allele_id in fasta_dict.keys()])
        # Create translation file path
        query_fasta_translation = os.path.join(query_translation_folder, f"{query_loci}-translation.fasta")
        # Translate sequences and update translation dictionary
        query_translations_paths[query_loci] = query_fasta_translation
        trans_dict, _, _ = sf.translate_seq_deduplicate(fasta_dict,
                                                        query_fasta_translation,
                                                        None,
                                                        0,
                                                        False,
                                                        translation_table,
                                                        False)
        # Update the query translation dictionary
        query_translation_dict.update(trans_dict)
    
    # Process subject FASTA files
    subject_translation_dict: Dict[str, str] = {}
    subject_ids: Dict[str, List[str]] = {}
    subject_translations_paths: Dict[str, str] = {}
    master_file_path: str = os.path.join(blast_folder, 'master_file.fasta')
    for subject_loci, path in subject_fastas.items():
        print(f"\rTranslated subject loci FASTA: {i}/{len_subject_fasta}", end='', flush=True)
        i += 1
        # Get the fasta sequences for the query
        fasta_dict: Dict[str, str] = sf.fetch_fasta_dict(path, False)
        # Save the IDs of the alleles
        subject_ids.setdefault(subject_loci, []).append([allele_id for allele_id in fasta_dict.keys()])
        # Create translation file path
        subject_fasta_translation = os.path.join(query_translation_folder, f"{subject_loci}-translation.fasta")
        # Translate sequences and update translation dictionary
        subject_translations_paths[subject_loci] = subject_fasta_translation
        trans_dict, _, _ = sf.translate_seq_deduplicate(fasta_dict,
                                                        subject_fasta_translation,
                                                        None,
                                                        0,
                                                        False,
                                                        translation_table,
                                                        False)
        # Write the sequences to the master file
        with open(master_file_path) as master:
            for id_, sequence in trans_dict.items():
                master.write(f">{id_}\n{sequence}\n")

        # Update the subject translation dictionary
        subject_translation_dict.update(trans_dict)
    
    # Create BLAST database

    # Create BLAST database
    blastdb_path: str = os.path.join(blast_folder, 'blastdb')
    ff.create_directory(blastdb_path)
    blast_db_files: str = os.path.join(blastdb_path, 'genbank_protein_db')
    makeblastdb_exec: str = lf.get_tool_path('makeblastdb')
    bf.make_blast_db(makeblastdb_exec, master_file_path, blast_db_files, 'prot')

    # Run BLAST
    best_bsr_values = run_blasts_match_schemas(query_translations_paths, blast_db_files, blast_folder, bsr, cpu)

