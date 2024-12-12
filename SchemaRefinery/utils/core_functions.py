import os
import concurrent.futures
import pandas as pd
from itertools import repeat
from typing import Dict, Any, List, Tuple, Union, Optional, Set

try:
    from utils import (file_functions as ff,
                       clustering_functions as cf,
                       blast_functions as bf,
                       alignments_functions as af,
                       iterable_functions as itf,
                       linux_functions as lf,
                       graphical_functions as gf,
                       pandas_functions as pf,
                       sequence_functions as sf)
except ModuleNotFoundError:
    from SchemaRefinery.utils import (file_functions as ff,
                                      clustering_functions as cf,
                                      blast_functions as bf,
                                      alignments_functions as af,
                                      iterable_functions as itf,
                                      linux_functions as lf,
                                      graphical_functions as gf,
                                      pandas_functions as pf,
                                      sequence_functions as sf)

def alignment_dict_to_file(blast_results_dict: Dict[str, Dict[str, Dict[str, Dict[str, Any]]]], 
                           file_path: str, write_type: str) -> None:
    """
    Writes alignment data to a file from a nested dictionary structure.

    This function takes a nested dictionary containing alignment data, a file path, and a write type (write or append)
    as input and writes the alignment data to the specified file. It supports the option to add an additional column
    for CDS group information in the output file's header.

    Parameters
    ----------
    blast_results_dict : dict
        A nested dictionary where the first level keys are query IDs, the second level keys are subject IDs, and the
        third level keys are specific alignment IDs, mapping to dictionaries containing alignment data.
    file_path : str
        The path to the file where the alignment data should be written or appended.
    write_type : str
        Specifies whether to create a new file ('w') and write the data or to append ('a') the data to an existing file.

    Returns
    -------
    None
        Writes the alignment data to the specified file based on the provided dictionary structure and parameters.

    Notes
    -----
    - It iterates over the nested dictionary structure to write each piece of alignment data to the file, formatting
    each row as tab-separated values.
    - This function is useful for exporting BLAST alignment results to a file for further analysis or reporting.
    """
    
    # Construct the header for the output file
    header: List[str] = ['Query\t',
                        'Subject\t',
                        'Query_length\t',
                        'Subject_length\t',
                        'Query_start\t',
                        'Query_end\t',
                        'Subject_start\t',
                        'Subject_end\t',
                        'Length\t',
                        'Score\t',
                        'Number_of_gaps\t',
                        'Pident\t',
                        'Prot_BSR\t',
                        'Prot_seq_Kmer_sim\t',
                        'Prot_seq_Kmer_cov\t',
                        'Frequency_in_genomes_query\t',
                        'Frequency_in_genomes_subject\t',
                        'Global_palign_all_min\t',
                        'Global_palign_all_max\t',
                        'Global_palign_pident_min\t',
                        'Global_palign_pident_max\t',
                        'Palign_local_min\t',
                        'Class\n']

    # Write or append to the file
    with open(file_path, write_type) as report_file:
        # Write the header only if the file is being created
        if write_type == 'w':
            report_file.write("".join(header))
        
        # Write all the alignment data
        for query_id, subjects in blast_results_dict.items():
            for subject_id, alignments in subjects.items():
                for alignment_id, alignment_data in alignments.items():
                    # Convert alignment data to a tab-separated string and write to the file
                    report_file.write('\t'.join(map(str, alignment_data.values())) + '\n')


def add_items_to_results(representative_blast_results: Dict[str, Dict[str, Dict[str, Dict[str, Any]]]], 
                         reps_kmers_sim: Dict[str, Dict[str, Tuple[float, float]]], 
                         bsr_values: Dict[str, Dict[str, float]],
                         representative_blast_results_coords_all: Dict[str, Dict[str, Dict[str, List[Tuple[int, int]]]]],
                         representative_blast_results_coords_pident: Dict[str, Dict[str, Dict[str, List[Tuple[int, int]]]]],
                         frequency_in_genomes: Dict[str, int], 
                         allele_ids: List[bool]) -> None:
    """
    Enhances BLAST results with additional metrics and frequencies.

    This function enriches the given BLAST results dictionary with several key metrics and frequencies
    to provide a more comprehensive analysis of the BLAST hits. It adds metrics such as Blast
    Score Ratio (BSR), k-mer similarities and coverage, and frequencies of query and subject CDS in
    schema genomes. It also includes global and local pairwise alignment scores, both in terms of
    coverage and percentage identity, with the ability to focus on specific percentage identity thresholds.

    Parameters
    ----------
    representative_blast_results : Dict[str, Dict[str, Dict[str, Dict[str, Any]]]]
        A dictionary containing BLAST results. Each entry is expected to represent a unique BLAST hit with
        various metrics.
    reps_kmers_sim : Dict[str, Dict[str, Tuple[float, float]]]
        A dictionary mapping pairs of CDS to their k-mer similarity scores.
    bsr_values : Dict[str, Dict[str, float]]
        A dictionary mapping pairs of CDS to their Blast Score Ratio (BSR) values. Can be None if BSR values
        are not available.
    representative_blast_results_coords_all : Dict[str, Dict[str, Dict[str, List[Tuple[int, int]]]]]
        A dictionary containing the coordinates for all BLAST entries, used for calculating global alignment metrics.
    representative_blast_results_coords_pident : Dict[str, Dict[str, Dict[str, List[Tuple[int, int]]]]]
        A dictionary containing the coordinates for BLAST entries above a certain percentage identity threshold,
        used for calculating specific global alignment metrics.
    frequency_in_genomes : Dict[str, int]
        A dictionary summarizing the frequency of each representative cluster within the genomes of the schema,
        enhancing the context of BLAST results.
    allele_ids : List[bool]
        Indicates whether the IDs of loci representatives are included in the `frequency_in_genomes`. If true,
        IDs follow the format `loci1_x`.

    Returns
    -------
    None
        Modifies the representative_blast_results dict inside the main function.

    Notes
    -----
    - The function is designed to work with detailed BLAST results and requires several pre-computed metrics
    and frequencies as input.
    - It is crucial for enhancing the analysis of BLAST results, especially in comparative genomics and
    schema development projects.
    """
    
    def get_kmer_values(reps_kmers_sim: Dict[str, Dict[str, Tuple[float, float]]], 
                        query: str, subject: str) -> Tuple[Union[float, str], Union[float, str]]:
        """
        Retrieves k-mer similarity and coverage values for a specified query and subject pair.

        Parameters
        ----------
        reps_kmers_sim : Dict[str, Dict[str, Tuple[float, float]]]
            A dictionary where keys are query sequence IDs and values are dictionaries with subject
            sequence IDs as keys. Each inner dictionary's values are tuples containing the k-mer
            similarity and coverage values.
        query : str
            The identifier for the query sequence.
        subject : str
            The identifier for the subject sequence.

        Returns
        -------
        sim : float or str
            The k-mer similarity value between the query and subject sequences. Returns 0 if no value is
            found, or '-' if the `reps_kmers_sim` dictionary is empty or not provided.
        cov : float or str
            The coverage value indicating the extent to which the k-mers of the query sequence are present
            in the subject sequence. Returns 0 if no value is found, or '-' if the `reps_kmers_sim` dictionary
            is empty or not provided.
        """
        if reps_kmers_sim:
            if subject in reps_kmers_sim[query]:
                sim: Union[float, str]
                cov: Union[float, str]
                sim, cov = reps_kmers_sim[query][subject]
                sim = round(sim, 2)
                cov = round(cov, 2)
            else:
                sim = 0
                cov = 0
        else:
            sim = '-'
            cov = '-'
        return sim, cov

    def get_bsr_value(bsr_values: Dict[str, Dict[str, float]], 
                      query: str, subject: str) -> float:
        """
        Fetches the BLAST Score Ratio (BSR) for a specified pair of sequences.

        Parameters
        ----------
        bsr_values : Dict[str, Dict[str, float]]
            A dictionary where keys are query sequence IDs and values are dictionaries with subject sequence
            IDs as keys. Each inner dictionary's values are the BSR values.
        query : str
            The identifier for the query sequence.
        subject : str
            The identifier for the subject sequence.

        Returns
        -------
        bsr : float
            The BSR value between the query and subject sequences. Returns 0 if no BSR value is found for the
            given pair. If the BSR value is greater than 1, it is rounded to the nearest whole number. The BSR
            value is rounded by 4 decimal places for consistency.
        """
        bsr: float = bsr_values[query].get(subject, 0)
        if bsr > 1.0:
            bsr = float(round(bsr))
        return round(bsr, 4)

    def calculate_total_length(representative_blast_results_coords: Dict[str, Dict[str, Dict[str, List[Tuple[int, int]]]]], 
                               query: str, subject: str) -> Dict[str, int]:
        """
        Calculates the total aligned length for each reference sequence in a given query-subject pair.

        Parameters
        ----------
        representative_blast_results_coords : Dict[str, Dict[str, Dict[str, List[Tuple[int, int]]]]]
            A nested dictionary where the first level keys are query sequence IDs, the second level keys are
            subject sequence IDs, and the values are dictionaries mapping reference sequence IDs to lists of
            alignment intervals.
        query : str
            The identifier for the query sequence.
        subject : str
            The identifier for the subject sequence.

        Returns
        -------
        total_length : Dict[str, int]
            A dictionary where keys are reference sequence IDs and values are the total aligned length for that
            reference sequence.
        """
        total_length: Dict[str, int] = {}
        for ref, intervals in representative_blast_results_coords[query][subject].items():
            if intervals:
                sorted_intervals: List[Tuple[int, int]] = sorted(intervals, key=lambda x: x[0])
                length: int = sum(interval[1] - interval[0] + 1 for interval in af.merge_intervals(sorted_intervals))
                total_length[ref] = length
            else:
                total_length[ref] = 0
        return total_length

    def calculate_global_palign(total_length: Dict[str, int], 
                                result: Dict[str, Union[int, float]]) -> Tuple[float, float]:
        """
        Calculates the minimum and maximum global pairwise alignment percentages.

        Parameters
        ----------
        total_length : Dict[str, int]
            A dictionary where keys are 'query' and 'subject', and values are the total aligned lengths for the
            query and subject sequences, respectively.
        result : Dict[str, Union[int, float]]
            A dictionary containing the lengths of the query and subject sequences under the keys 'query_length'
            and 'subject_length'.

        Returns
        -------
        global_palign_min : float
            The minimum global pairwise alignment percentage.
        global_palign_max : float
            The maximum global pairwise alignment percentage.
        """
        global_palign_min: float = min(total_length['query'] / result['query_length'],
                                       total_length['subject'] / result['subject_length'])
        global_palign_max: float = max(total_length['query'] / result['query_length'],
                                       total_length['subject'] / result['subject_length'])
        return round(global_palign_min, 4), round(global_palign_max, 4)

    def calculate_local_palign(result: Dict[str, Union[int, float]]) -> float:
        """
        Calculates the minimum local pairwise alignment percentage.

        Parameters
        ----------
        result : Dict[str, Union[int, float]]
            A dictionary containing the result of a BLAST search, including the start and end positions of the alignment
            on both the query and subject sequences, as well as their total lengths.

        Returns
        -------
        local_palign_min : float
            The minimum local pairwise alignment percentage.
        """
        local_palign_min: float = min((result['query_end'] - result['query_start'] + 1) / result['query_length'],
                                      (result['subject_end'] - result['subject_start'] + 1) / result['subject_length'])
        return round(local_palign_min, 4)

    def update_results(representative_blast_results: Dict[str, Dict[str, Dict[str, Dict[str, Any]]]], 
                       query: str, subject: str, entry_id: str, bsr: float, sim: Union[float, str], 
                       cov: Union[float, str], frequency_in_genomes: Dict[str, int],
                       global_palign_all_min: float, global_palign_all_max: float, 
                       global_palign_pident_min: float, global_palign_pident_max: float,
                       local_palign_min: float, allele_ids: List[bool]) -> None:
        """
        Updates the BLAST results for a specific query and subject pair with new data.

        Parameters
        ----------
        representative_blast_results : Dict[str, Dict[str, Dict[str, Dict[str, Any]]]]
            A dictionary containing BLAST results where keys are query IDs, values are dictionaries with subject
            IDs as keys, and each subject dictionary contains dictionaries of entry IDs with their respective data.
        query : str
            The query sequence ID.
        subject : str
            The subject sequence ID.
        entry_id : str
            The ID of the entry to update within the BLAST results.
        bsr : float
            The BSR value to update.
        sim : Union[float, str]
            The similarity value to update.
        cov : Union[float, str]
            The coverage value to update.
        frequency_in_genomes : Dict[str, int]
            A dictionary containing the frequency of the query and subject in genomes.
        global_palign_all_min : float
            The minimum global pairwise alignment percentage.
        global_palign_all_max : float
            The maximum global pairwise alignment percentage.
        global_palign_pident_min : float
            The minimum global pairwise alignment percentage based on Pident threshold.
        global_palign_pident_max : float
            The maximum global pairwise alignment percentage based on Pident threshold.
        local_palign_min : float
            The minimum local pairwise alignment percentage.
        allele_ids : List[bool]
            A list indicating whether to modify the query and/or subject IDs based on loci information.

        Returns
        -------
        None
            This function does not return any value but modifies the `representative_blast_results` dictionary in place.
        """
        if allele_ids[0]:
            query_before: str = query
            query = itf.remove_by_regex(query, '_(\\d+)')
        if allele_ids[1]:
            subject_before: str = subject
            subject = itf.remove_by_regex(subject, '_(\\d+)')
        update_dict: Dict[str, Union[float, str, int]] = {
            'bsr': bsr,
            'kmers_sim': sim,
            'kmers_cov': cov,
            'frequency_in_genomes_query_cds': frequency_in_genomes[query],
            'frequency_in_genomes_subject_cds': frequency_in_genomes[subject],
            'global_palign_all_min' : global_palign_all_min,
            'global_palign_all_max': global_palign_all_max,
            'global_palign_pident_min': global_palign_pident_min,
            'global_palign_pident_max': global_palign_pident_max,
            'local_palign_min': local_palign_min
        }
        if allele_ids[0]:
            query = query_before
        if allele_ids[1]:
            subject = subject_before
        representative_blast_results[query][subject][entry_id].update(update_dict)

    def remove_results(representative_blast_results: Dict[str, Dict[str, Dict[str, Dict[str, Any]]]], 
                       query: str, subject: str, entry_id: str) -> None:
        """
        Removes a specific entry from the BLAST results for a given query and subject pair.

        Parameters
        ----------
        representative_blast_results : Dict[str, Dict[str, Dict[str, Dict[str, Any]]]]
            A dictionary containing BLAST results, structured with query IDs as keys, each mapping to a dictionary
            of subject IDs, which in turn map to dictionaries of entry IDs and their associated data.
        query : str
            The identifier for the query sequence.
        subject : str
            The identifier for the subject sequence.
        entry_id : str
            The identifier of the specific entry to be removed from the results.

        Returns
        -------
        None
            This function does not return any value. It modifies the `representative_blast_results` dictionary in
            place, removing the specified entry.
        """
        del representative_blast_results[query][subject][entry_id]

    def clean_up_results(representative_blast_results: Dict[str, Dict[str, Dict[str, Dict[str, Any]]]], 
                         query: str, subject: str) -> None:
        """
        Cleans up BLAST results for a specific query and subject by removing empty entries.

        Parameters
        ----------
        representative_blast_results : Dict[str, Dict[str, Dict[str, Dict[str, Any]]]]
            A dictionary containing BLAST results, where keys are query IDs, and values are dictionaries with
            subject IDs as keys, each mapping to their respective result entries.
        query : str
            The identifier for the query sequence.
        subject : str
            The identifier for the subject sequence.
        
        Returns
        -------
        None
            This function does not return any value. It modifies the `representative_blast_results` dictionary in
            place, removing the specified entry.
        """
        if not representative_blast_results[query][subject]:
            del representative_blast_results[query][subject]
        if not representative_blast_results[query]:
            del representative_blast_results[query]

    # Iterate over the representative_blast_results dictionary
    for query, subjects_dict in list(representative_blast_results.items()):
        for subject, blastn_results in list(subjects_dict.items()):
            sim, cov = get_kmer_values(reps_kmers_sim, query, subject)
            bsr = get_bsr_value(bsr_values, query, subject)

            total_length = calculate_total_length(representative_blast_results_coords_all, query, subject)
            global_palign_all_min, global_palign_all_max = calculate_global_palign(total_length, blastn_results[1])

            total_length = calculate_total_length(representative_blast_results_coords_pident, query, subject)
            global_palign_pident_min, global_palign_pident_max = calculate_global_palign(total_length, blastn_results[1])
            
            # Iterate over the blastn_results dictionary
            for entry_id, result in list(blastn_results.items()):
                local_palign_min = calculate_local_palign(result)
                # Remove entries with negative local palign values meaning that they are inverse alignments.
                if local_palign_min >= 0:
                    update_results(representative_blast_results, query, subject, entry_id, bsr, sim, cov, frequency_in_genomes, global_palign_all_min, global_palign_all_max, global_palign_pident_min, global_palign_pident_max, local_palign_min, allele_ids)
                else:
                    remove_results(representative_blast_results, query, subject, entry_id)

            clean_up_results(representative_blast_results, query, subject)


def separate_blast_results_into_classes(representative_blast_results: Dict[str, Dict[str, Dict[str, Dict[str, Any]]]], 
                                         constants: Tuple[Any, ...], classes_outcome: List[str]) -> Tuple[str, ...]:
    """
    Separates BLAST results into predefined classes based on specific criteria.

    This function iterates through BLAST results and classifies each result into a specific class
    based on criteria such as global alignment percentage, bit score ratio (bsr), and frequency ratios
    between query and subject CDS in genomes. The classification is done by updating the results
    dictionary with a new key-value pair indicating the class of each BLAST result.

    Parameters
    ----------
    representative_blast_results : Dict[str, Dict[str, Dict[str, Dict[str, Any]]]]
        A nested dictionary where the first level keys are query sequence IDs, the second level keys
        are subject sequence IDs, and the third level keys are unique identifiers for each BLAST
        result. Each BLAST result is a dictionary containing keys such as 'frequency_in_genomes_query_cds',
        'frequency_in_genomes_subject_cds', 'global_palign_all_min', 'bsr', and 'pident'.
    constants : Tuple[Any, ...]
        A collection of constants used in the classification criteria. Specifically, `constants[1]`
        is used as a threshold for the percentage identity (pident) in one of the classification conditions.

    Returns
    -------
    Tuple[str, ...]
        A tuple of class identifiers indicating the order of priority for the classes.

    Notes
    -----
    - The function modifies `representative_blast_results` in place by adding a 'class' key to each
      BLASTN result dictionary.
    - The classification logic is based on a combination of alignment quality metrics and frequency
      ratios, with specific thresholds and conditions determining the class assignment.
    - The function assumes that `constants` provides necessary thresholds for classification and
      that its elements are accessed by index.
    """
    
    def add_class_to_dict(class_name: str) -> None:
        """
        Adds a class identifier to a BLAST result within the representative_blast_results dictionary.

        This helper function is used to update the BLASTN result dictionaries with a 'class' key,
        assigning the specified class identifier based on the classification logic in the outer function.

        Parameters
        ----------
        class_name : str
            The class identifier to be added to the BLASTN result. This should be one of the values
            from the classes_outcome tuple defined in the outer function.

        Notes
        -----
        - This function directly modifies the `representative_blast_results` dictionary from the outer
          scope, specifically adding or updating the 'class' key for a BLASTN result.
        - It is designed to be used only within the `separate_blast_results_into_classes` function.
        """
        representative_blast_results[query][id_subject][id_].update({'class': class_name})

    pident: float = constants[1]
    bsr: float = constants[7]
    size_ratio: float = 1 - constants[8]

    # Loop through the representative BLAST results
    for query, rep_blast_result in representative_blast_results.items():
        for id_subject, matches in rep_blast_result.items():
            for id_, blastn_entry in matches.items():
                # Calculate the frequency ratio
                query_freq: int = blastn_entry['frequency_in_genomes_query_cds']
                subject_freq: int = blastn_entry['frequency_in_genomes_subject_cds']
                
                # If one of the frequencies is 0, set the ratio to 0.1 if the other frequency is 10 times greater
                if query_freq == 0 or subject_freq == 0:
                    freq_ratio: float = 0.1 if query_freq > 10 or subject_freq > 10 else 1
                else:
                    # Calculate the frequency ratio
                    freq_ratio = min(query_freq / subject_freq, subject_freq / query_freq)
                
                # Classify based on global_palign_all_min and bsr
                global_palign_all_min: float = blastn_entry['global_palign_all_min']
                bsr_value: float = blastn_entry['bsr']
                pident_value: float = blastn_entry['pident']
                global_palign_pident_max: float = blastn_entry['global_palign_pident_max']
                
                if global_palign_all_min >= size_ratio:
                    if bsr_value >= bsr:
                        # Add to class '1a' if bsr is greater than or equal to bsr value
                        add_class_to_dict('1a')
                    elif freq_ratio <= 0.1:
                        # Add to class '1b' if frequency ratio is less than or equal to 0.1
                        add_class_to_dict('1b')
                    else:
                        # Add to class '1c' if none of the above conditions are met
                        add_class_to_dict('1c')
                elif 0.4 <= global_palign_all_min < size_ratio:
                    if pident_value >= pident:
                        if global_palign_pident_max >= size_ratio:
                            # Add to class '2a' or '2b' based on frequency ratio
                            add_class_to_dict('2a' if freq_ratio <= 0.1 else '2b')
                        else:
                            # Add to class '3a' or '3b' based on frequency ratio
                            add_class_to_dict('3a' if freq_ratio <= 0.1 else '3b')
                    else:
                        if global_palign_pident_max >= size_ratio:
                            # Add to class '4a' or '4b' based on frequency ratio
                            add_class_to_dict('4a' if freq_ratio <= 0.1 else '4b')
                        else:
                            # Add to class '4c' if none of the above conditions are met
                            add_class_to_dict('4c')
                else:
                    # Add to class '5' for everything that is unrelated
                    add_class_to_dict('5')

    return classes_outcome


def sort_blast_results_by_classes(representative_blast_results, classes_outcome):
    """
    Sorts BLAST results by classes based on the alignment score.
    
    This function organizes BLAST results into a sorted structure according to predefined classes.
    It ensures that for each query, the results are grouped by the class of the alignment, prioritizing
    the classes as specified in the `classes_outcome` list.

    Parameters
    ----------
    representative_blast_results : dict
        A dictionary where each key is a query identifier and each value is another dictionary.
        The inner dictionary's keys are subject identifiers, and values are lists containing
        details of the match, where the second element is a dictionary with the key 'class'
        indicating the class of the alignment.
    classes_outcome : tuple
        A list of possible classes outcomes to sort the BLAST results into. The order in this list
        determines the priority of the classes when organizing the results.

    Returns
    -------
    sorted_blast_dict : dict
        A dictionary structured similarly to `representative_blast_results`, but sorted such that
        all results for a given query are grouped by their class as determined by the highest
        scoring alignment.

    Notes
    -----
    - The function assumes that each match list in the values of `representative_blast_results`
      contains at least one element, which is a dictionary with a 'class' key.
    - It creates a temporary dictionary to first group results by class, then consolidates these
      into the final sorted dictionary to be returned.
    """
    sorted_blast_dict = {}
    temp_dict = {k: {} for k in classes_outcome}

    # Loop through the representative BLAST results
    for query, rep_blast_result in representative_blast_results.items():
        for id_subject, matches in rep_blast_result.items():
            # Class of the alignment with biggest score.
            class_ = matches[1]['class']
            if not temp_dict[class_].get(query):
                temp_dict[class_][query] = {}
            temp_dict[class_][query][id_subject] = matches
    
    for class_, sorted_blast_reps in temp_dict.items():
        for query, rep_blast_result in sorted_blast_reps.items():
            if not sorted_blast_dict.get(query):
                sorted_blast_dict[query] = {}
            for id_subject, matches in rep_blast_result.items():
                    sorted_blast_dict[query][id_subject] = matches
    
    return sorted_blast_dict


def process_classes(representative_blast_results: Dict[str, Dict[str, Dict[str, Any]]], 
                    classes_outcome: Tuple[str, ...], all_alleles: Optional[Dict[str, str]] = None) -> Tuple[
                    Dict[str, Tuple[Optional[str], List[str], List[str], Tuple[str, str], List[str]]],
                    Dict[str, Dict[str, int]], Dict[str, Dict[str, List[Union[int, str]]]],
                    Dict[str, Tuple[set, set]], List[str], Dict[str, List[List[str]]]
                    ]:
    """
    Processes BLAST results to determine class-based relationships and counts.

    This function iterates through representative BLAST results to establish relationships
    between different coding sequences (CDS) and to count occurrences by class. It handles
    allele replacements, prioritizes classes based on a predefined order, and identifies
    important relationships between sequences.

    Parameters
    ----------
    representative_blast_results : Dict[str, Dict[str, Dict[str, Any]]]
        A nested dictionary where the first key is the query sequence ID, the second key is
        the subject sequence ID, and the value is another dictionary containing match details
        including the class of the match.process_classes
    classes_outcome : Tuple[str, ...]
        A list of class identifiers ordered by priority. This order determines which classes are
        considered more significant when multiple matches for the same pair of sequences are found.
    all_alleles : Optional[Dict[str, str]], optional
        A dictionary mapping sequence IDs to their corresponding allele names. If provided, it is
        used to replace allele IDs with loci/CDS names in the processing.

    Returns
    -------
    processed_results : Dict[str, Tuple[Optional[str], List[str], List[str], Tuple[str, str], List[str]]]
        A dictionary containing processed results with keys formatted as "query|subject" and values being tuples
        containing information about the processed sequences, their class, relationships, and additional details.
    count_results_by_class : Dict[str, Dict[str, int]]
        A dictionary containing counts of results by class, with keys formatted as "query|subject" and values being
        dictionaries with class identifiers as keys and counts as values.
    count_results_by_class_with_inverse : Dict[str, Dict[str, List[Union[int, str]]]]
        A dictionary containing counts of results by class, including inverse matches, with keys formatted as
        "query|subject" and values being dictionaries with class identifiers as keys and counts as values.
    reps_and_alleles_ids : Dict[str, Tuple[set, set]]
        A dictionary mapping pairs of query and subject sequences to their unique loci/CDS IDs and alleles IDs.
    drop_mark : List[str]
        A list of sequences that were marked for dropping.
    all_relationships : Dict[str, List[List[str]]]
        A dictionary containing all relationships between sequences, grouped by class.

    Notes
    -----
    - The function dynamically adjusts based on the presence of `all_alleles`, affecting how sequence IDs
    are replaced and processed.
    - It employs a complex logic to handle different scenarios based on class types and the presence or absence of
    alleles in the processed results, including handling allele replacements and determining the importance of
    relationships.
    """
    # Initialize variables
    count_results_by_class: Dict[str, Dict[str, int]] = {}
    count_results_by_class_with_inverse: Dict[str, Dict[str, List[Union[int, str]]]] = {}
    reps_and_alleles_ids: Dict[str, Tuple[set, set]] = {}
    processed_results: Dict[str, Tuple[Optional[str], List[str], List[str], Tuple[str, str], List[str]]] = {}
    all_relationships: Dict[str, List[List[str]]] = {class_: [] for class_ in classes_outcome}
    drop_mark: List[str] = []
    inverse_match: List[str] = []

    # Process the CDS to find what CDS to retain while also adding the relationships between different CDS
    for query, rep_blast_result in representative_blast_results.items():
        for id_subject, matches in rep_blast_result.items():
            class_: str = matches[1]['class']
            all_relationships[class_].append([query, id_subject])
            ids_for_relationship: List[str] = [query, id_subject]
            new_query: str = query
            new_id_subject: str = id_subject

            strings: List[str] = [str(query), str(id_subject), class_]
            if all_alleles:
                replaced_query: Optional[str] = itf.identify_string_in_dict_get_key(query, all_alleles)
                if replaced_query is not None:
                    new_query = replaced_query
                    strings[0] = new_query
                replaced_id_subject: Optional[str] = itf.identify_string_in_dict_get_key(id_subject, all_alleles)
                if replaced_id_subject is not None:
                    new_id_subject = replaced_id_subject
                    strings[1] = new_id_subject

                current_allele_class_index: int = classes_outcome.index(class_)
                # Check if the current loci were already processed
                if not processed_results.get(f"{new_query}|{new_id_subject}"):
                    run_next_step: bool = True
                # If those loci/CDS were already processed, check if the current class is better than the previous one
                elif current_allele_class_index < classes_outcome.index(processed_results[f"{new_query}|{new_id_subject}"][0]):
                    run_next_step = True
                # If not then skip the current alleles
                else:
                    run_next_step = False
            else:
                run_next_step = True

            count_results_by_class.setdefault(f"{new_query}|{new_id_subject}", {})
            if not count_results_by_class[f"{new_query}|{new_id_subject}"].get(class_):
                count_results_by_class[f"{new_query}|{new_id_subject}"].setdefault(class_, 1)
            else:
                count_results_by_class[f"{new_query}|{new_id_subject}"][class_] += 1
            
            if f"{new_query}|{new_id_subject}" not in inverse_match:
                count_results_by_class_with_inverse.setdefault(f"{new_query}|{new_id_subject}", {})
                inverse_match.append(f"{new_id_subject}|{new_query}")
            if f"{new_query}|{new_id_subject}" in inverse_match:
                if not count_results_by_class_with_inverse[f"{new_id_subject}|{new_query}"].get(class_):
                    count_results_by_class_with_inverse[f"{new_id_subject}|{new_query}"].setdefault(class_, ['-', 1])
                elif count_results_by_class_with_inverse[f"{new_id_subject}|{new_query}"][class_][1] == '-':
                    count_results_by_class_with_inverse[f"{new_id_subject}|{new_query}"][class_][1] = 1
                else:
                    count_results_by_class_with_inverse[f"{new_id_subject}|{new_query}"][class_][1] += 1
            else:
                if not count_results_by_class_with_inverse[f"{new_query}|{new_id_subject}"].get(class_):
                    count_results_by_class_with_inverse[f"{new_query}|{new_id_subject}"].setdefault(class_, [1, '-'])
                elif count_results_by_class_with_inverse[f"{new_query}|{new_id_subject}"][class_][0] == '-':
                    count_results_by_class_with_inverse[f"{new_query}|{new_id_subject}"][class_][0] = 1
                else:
                    count_results_by_class_with_inverse[f"{new_query}|{new_id_subject}"][class_][0] += 1
            # Get unique loci/CDS for each query and subject rep and allele.
            reps_and_alleles_ids.setdefault(f"{new_query}|{new_id_subject}", (set(), set()))
            if ids_for_relationship[0] not in reps_and_alleles_ids[f"{new_query}|{new_id_subject}"][0]:
                reps_and_alleles_ids[f"{new_query}|{new_id_subject}"][0].add(ids_for_relationship[0])
            if ids_for_relationship[1] not in reps_and_alleles_ids[f"{new_query}|{new_id_subject}"][1]:
                reps_and_alleles_ids[f"{new_query}|{new_id_subject}"][1].add(ids_for_relationship[1])
    
            if run_next_step:
                # Set all None to run newly for this query/subject combination
                processed_results[f"{new_query}|{new_id_subject}"] = (None, [], [], (new_query, new_id_subject), [])

                if class_ in ['1b', '2a', '3a']:
                    blastn_entry: Dict[str, Any] = matches[list(matches.keys())[0]]
                    # Determine if the frequency of the query is greater than the subject.
                    is_frequency_greater: bool = blastn_entry['frequency_in_genomes_query_cds'] >= blastn_entry['frequency_in_genomes_subject_cds']
                    # Determine if the query or subject should be dropped.
                    query_or_subject: List[str] = [new_id_subject] if is_frequency_greater else [new_query]
                else:
                    query_or_subject = []

                # For the related_matches.tsv file.
                if class_ not in ['4c','5']:
                    # Add asterisk to the query or subject that was dropped.
                    if class_ in ['1b', '2a', '3a']:
                        blastn_entry = matches[list(matches.keys())[0]]
                        # Determine if the frequency of the query is greater than the subject.
                        is_frequency_greater = blastn_entry['frequency_in_genomes_query_cds'] >= blastn_entry['frequency_in_genomes_subject_cds']
                        # Determine if the query or subject should be dropped.
                        dropped: str = new_id_subject if is_frequency_greater else new_query
                        if new_query == dropped:
                            drop_mark.append(new_query)
                            strings[0] += '*' 
                        else:
                            drop_mark.append(new_id_subject)
                            strings[1] += '*'

                processed_results[f"{new_query}|{new_id_subject}"] = (class_,
                                                    ids_for_relationship,
                                                    query_or_subject,
                                                    (new_query, new_id_subject),
                                                    strings)

    return processed_results, count_results_by_class, count_results_by_class_with_inverse, reps_and_alleles_ids, drop_mark, all_relationships


def extract_results(processed_results: Dict[str, Tuple[str, List[str], List[str], Tuple[str, str], List[Any]]], count_results_by_class: Dict[str, Dict[str, int]], 
                    frequency_in_genomes: Dict[str, int], merged_all_classes: Dict[str, List[str]], 
                    dropped_loci_ids: List[str], classes_outcome: List[str]) -> Tuple[Dict[str, List[Any]], Dict[str, Dict[str, Any]]]:
    """
    Extracts and organizes results from process_classes.

    Parameters
    ----------
    processed_results : Dict[str, Dict[str, Any]]
        The processed results data.
    count_results_by_class : Dict[str, Dict[str, int]]
        A dictionary with counts of results by class.
    frequency_in_genomes : Dict[str, int]
        A dictionary containing the frequency of the query and subject in genomes.
    merged_all_classes : Dict[str, List[str]]
        A dictionary containing identifiers to check for a joined condition.
    dropped_loci_ids : List[str]
        A list of possible loci to drop.
    classes_outcome : List[str]
        A list of class outcomes.

    Returns
    -------
    Tuple[Dict[str, List[Any]], Dict[str, Dict[str, Any]]]
        A tuple containing:
        - all_relationships: All relationships between loci and CDS.
        - related_clusters: Dict that groups CDS/loci by ID and that contains strings to write in output file.
    
    Notes
    -----
    - The function iterates over `processed_results` to organize and cluster related CDS/loci based
      on their classification outcomes and the presence in specific clusters.
    - It uses helper functions like `cf.cluster_by_ids` for clustering and `itf.identify_string_in_dict_get_key`
      for identifying if a query or subject ID is present in the clusters.
    """
    def cluster_data(processed_results: Dict[str, Dict[str, Any]]) -> Dict[int, List[str]]:
        """
        Cluster data based on a specific key extracted from the processed results.

        Parameters
        ----------
        processed_results : Dict[str, Dict[str, Any]]
            A dictionary containing the processed results to be clustered.

        Returns
        -------
        Dict[int, List[str]]
            A dictionary where each key is an integer starting from 1, and each value is a cluster of data
            based on the extracted key, excluding entries with specific identifiers.
        """
        key_extractor = lambda v: v[3]
        condition = lambda v: v[0] not in ['4c', '5']

        return {i: cluster for i, cluster in enumerate(cf.cluster_by_ids([key_extractor(v) for v in processed_results.values() if condition(v)]), 1)}

    def choice_data(processed_results: Dict[str, Dict[str, Any]], to_cluster_list: Dict[int, List[str]]) -> Dict[int, List[str]]:
        """
        Select and cluster data based on specific conditions and a list of identifiers to cluster.

        Parameters
        ----------
        processed_results : Dict[str, Dict[str, Any]]
            A dictionary containing the processed results to be selected and clustered.
        to_cluster_list : Dict[int, List[str]]
            A list of identifiers indicating which entries should be considered for clustering.

        Returns
        -------
        Dict[int, List[str]]
            A dictionary where each key is an integer starting from 1, and each value is a cluster of data
            selected based on the given conditions and the to_cluster_list.
        """
        # Extract the key (loci/CDS IDs) from the processed results
        key_extractor = lambda v: v[3]
        # Additional condition for the choice data (* means Dropped loci ID)
        additional_condition = lambda v: '*' in v[4][0] or '*' in v[4][1]

        classes_to_fetch_choice = ['1c', '2b', '3b'] # Classes of choice
        choices_to_cluster = {keys: [] for keys in classes_to_fetch_choice}
        # For each choice class, select every entry ID that are part of the same to_cluster_list and share similiar class.
        for v in processed_results.values():
            for class_ in classes_to_fetch_choice:
                if v[0] == class_ or (itf.identify_string_in_dict_get_key(v[3][0], to_cluster_list) and additional_condition(v)) or (itf.identify_string_in_dict_get_key(v[3][1], to_cluster_list) and additional_condition(v)):
                    if not itf.identify_string_in_dict_get_key(v[3], choices_to_cluster) and not itf.identify_string_in_dict_get_key((v[3][1], v[3][0]), choices_to_cluster):
                        choices_to_cluster[class_].append(key_extractor(v))
                else:
                    continue
        
        clustered_choices = {}
        i = 0
        # Cluster the selected choices
        for cluster_choice in choices_to_cluster.values():
            clustered = cf.cluster_by_ids(cluster_choice)
            for cluster in clustered:
                clustered_choices[i] = cluster
                i += 1

        return clustered_choices

    def process_id(id_: str, to_cluster_list: Dict[int, List[str]], merged_all_classes: Dict[str, List[str]]) -> Tuple[str, str, str]:
        """
        Process an identifier to check its presence in specific lists.

        Parameters
        ----------
        id_ : str
            The identifier to be processed.
        to_cluster_list : Dict[int, List[str]]
            A list of identifiers to check for the presence of id_.
        clusters_to_keep : Dict[str, List[str]]
            A dictionary containing identifiers to check for a joined condition.

        Returns
        -------
        Tuple[str, bool, bool]
            A tuple containing the original id, a boolean indicating if the id is present in the to_cluster_list,
            and a boolean indicating if the id is present in the merged_all_classes under a specific key.
        """
        present: str = itf.identify_string_in_dict_get_key(id_, to_cluster_list)
        joined_id: str = itf.identify_string_in_dict_get_key(id_, merged_all_classes['1a'])
        return id_, present, joined_id

    def check_in_recommendations(id_: str, joined_id: str, recommendations: Dict[str, Dict[str, List[str]]], key: str, categories: List[str]) -> bool:
        """
        Check if an identifier or its joined form is present in a set of recommendations.

        Parameters
        ----------
        id_ : str
            The original identifier to check.
        joined_id : str
            The joined form of the identifier to check.
        recommendations : Dict[str, Dict[str, List[str]]]
            A dictionary of recommendations to search within.
        key : str
            The key within the recommendations to search under.
        categories : List[str]
            A list of categories to consider when searching in the recommendations.

        Returns
        -------
        bool
            True if the identifier or its joined form is present in the recommendations under the specified categories,
            False otherwise.
        """
        return any((joined_id or id_) in itf.flatten_list([v for k, v in recommendations[key].items() if cat in k]) for cat in categories)

    def add_to_recommendations(category: str, id_to_write: str, key: str, recommendations: Dict[str, Dict[str, List[str]]], category_id: str = None) -> None:
        """
        Add an identifier to the recommendations under a specific category.

        Parameters
        ----------
        category : str
            The category under which to add the identifier.
        id_to_write : str
            The identifier to add to the recommendations.
        key : str
            The key within the recommendations to add under.
        recommendations : Dict[str, Dict[str, List[str]]]
            The recommendations dictionary to modify.
        joined_id : str, optional
            The joined form of the identifier, if applicable. Default is None.

        Returns
        -------
        None
            This function does not return any value but modifies the `recommendations` dictionary in place.
        """
        if category_id is not None:  # For joined or choice categories
            recommendations[key].setdefault(f'{category}_{category_id}', set()).add(id_to_write)
        else:  # For keep or drop categories
            recommendations[key].setdefault(category, set()).add(id_to_write)

    def order_dict_by_first_value(data: Dict[str, Tuple[str, List[str], List[str], Tuple[str, str], List[str]]], order: Tuple[str]) -> Dict[str, Tuple[str, List[str], List[str], Tuple[str, str], List[str]]]:
        """
        Order the dictionary by the first value of each tuple according to a specified order tuple.

        Parameters
        ----------
        data : Dict[str, Tuple[str, List[str], List[str], Tuple[str, str], List[str]]]
            The dictionary to be ordered. The dictionary values are tuples containing various elements.
        order : Tuple[str]
            The order tuple specifying the desired order of the first values in the dictionary tuples.

        Returns
        -------
        Dict[str, Tuple[str, List[str], List[str], Tuple[str, str], List[str]]]
            The ordered dictionary.
        """
        # Create a dictionary to map order values to their indices for sorting
        order_index = {value: index for index, value in enumerate(order)}
        
        # Sort the dictionary by the first value of each tuple according to the order tuple
        sorted_data = dict(sorted(data.items(), key=lambda item: order_index.get(item[1][0], len(order))))
        
        return sorted_data

    def find_both_values_in_dict_list(query_id: str, subject_id: str, choice: Dict[str, List[str]]) -> Union[str, None]:
        """
        Find the key where both query_id and subject_id are present in the same list.

        Parameters
        ----------
        query_id : str
            The query identifier to find.
        subject_id : str
            The subject identifier to find.
        choice : Dict[str, List[str]]
            The dictionary containing lists of identifiers.

        Returns
        -------
        str
            The key where both query_id and subject_id are present, or an empty string if not found.
        """
        for key, values in choice.items():
            if query_id in values and subject_id in values:
                return key
        return None

    # Initialize dictionaries to keep track of various results
    related_clusters: Dict[str, List[Any]] = {}  # To keep track of the related clusters
    recommendations: Dict[str, Dict[str, List[str]]] = {}  # To keep track of the recommendations
    dropped_match: Dict[str, List[List[str]]] = {}  # To keep track of the dropped matches
    matched_with_dropped: Dict[str, List[List[str]]] = {}  # To keep track of the matches that matched with dropped
    processed_cases: List[List[str]] = []  # To keep track of the processed cases

    # Filter the processed results by the order of classes
    processed_results = order_dict_by_first_value(processed_results, classes_outcome)

    # Normal run, where IDs are only loci or CDS original IDs.
    to_cluster_list: Dict[int, List[str]] = cluster_data(processed_results)  # All of the cluster of related CDS/loci by ID.
    choice: Dict[int, List[str]] = choice_data(processed_results, to_cluster_list)  # All of the possible cases of choice.

    for results in processed_results.values():
        if results[0] in ['4c', '5', 'Retained_not_matched_by_blastn']:
            continue
        # Get the IDs and check if they are present in the to_cluster_list
        query_id, query_present, joined_query_id = process_id(results[3][0], to_cluster_list, merged_all_classes)
        subject_id, subject_present, joined_subject_id = process_id(results[3][1], to_cluster_list, merged_all_classes)
        
        key: str = query_present if query_present else subject_present

        direct_match_info = f"{count_results_by_class[f'{results[3][0]}|{results[3][1]}'][results[0]]}/{sum(count_results_by_class[f'{results[3][0]}|{results[3][1]}'].values())}"
        related_clusters.setdefault(key, []).append(results[4]
                                                    + [direct_match_info]
                                                    + [str(frequency_in_genomes[results[3][0]])]
                                                    + [str(frequency_in_genomes[results[3][1]])]
                                                    )

        recommendations.setdefault(key, {})
        # Checks to make, so that we can add the ID to the right recommendations.
        if_same_joined: bool = (joined_query_id == joined_subject_id) if joined_query_id and joined_subject_id else False
        if_joined_query: bool = check_in_recommendations(query_id, joined_query_id, recommendations, key, ['Joined'])
        if_joined_subject: bool = check_in_recommendations(subject_id, joined_subject_id, recommendations, key, ['Joined'])
        if_query_in_choice: bool = check_in_recommendations(query_id, joined_query_id, recommendations, key, ['Choice'])
        if_subject_in_choice: bool = check_in_recommendations(subject_id, joined_subject_id, recommendations, key, ['Choice'])
        if_query_dropped: bool = (joined_query_id or query_id) in dropped_loci_ids
        if_subject_dropped: bool = (joined_subject_id or subject_id) in dropped_loci_ids

        choice_id: str = find_both_values_in_dict_list(query_id, subject_id, choice) # Find the choice ID (both query and subject in the same list)

        # What IDs to add to the Keep, Drop and Choice.
        query_to_write: str = joined_query_id or query_id
        subject_to_write: str = joined_subject_id or subject_id
        
        joined_query_to_write: str = query_id
        joined_subject_to_write: str = subject_id

        # Check if the pair was not processed yet
        if [query_id, subject_id] not in processed_cases:

            # Process the joined cases
            if results[0] == '1a':
                # If it is part of a joined cluster, add to the recommendations
                if joined_query_id is not None:
                    add_to_recommendations('Joined', joined_query_to_write, key, recommendations, joined_query_id)
                if joined_subject_id is not None:
                    add_to_recommendations('Joined', joined_subject_to_write, key, recommendations, joined_subject_id)
            # Process the choice cases
            elif results[0] in ['1c', '2b', '3b', '4b']:
                # If it is not dropped and not the same joined cluster, add to the choice recommendations
                if not if_query_dropped and not if_subject_dropped and not if_same_joined:
                    # If not already reported (other Joined elements already reported with Joined ID)
                    if not find_both_values_in_dict_list(query_to_write, subject_to_write, recommendations[key]):
                        add_to_recommendations(f'Choice_{results[0]}', query_to_write, key, recommendations, choice_id)
                        add_to_recommendations(f'Choice_{results[0]}', subject_to_write, key, recommendations, choice_id)
            # Process cases where some ID is dropped
            elif results[0] in ['1b', '2a', '3a', '4a']:
                # If it is part of a joined cluster and it gets dropped, add to the recommendations
                if (joined_query_id and '*' in results[4][0]) or (joined_subject_id and '*' in results[4][1]) and not if_same_joined:
                    # If not already reported (other Joined elements already reported with Joined ID)
                    if not find_both_values_in_dict_list(query_to_write, subject_to_write, recommendations[key]):
                        add_to_recommendations(f'Choice_{results[0]}', query_to_write, key, recommendations, choice_id)
                        add_to_recommendations(f'Choice_{results[0]}', subject_to_write, key, recommendations, choice_id)
                # If it is not part of a joined cluster and it gets dropped, add to the recommendations
                if if_query_dropped:
                    # If it is not part of a joined cluster and it gets dropped, add to the recommendations as Dropped
                    if not if_joined_query and not if_query_in_choice:
                        add_to_recommendations('Drop', query_to_write, key, recommendations)
                        dropped_match.setdefault(key, []).append([query_to_write, subject_to_write, subject_to_write])
                # If it is not part of a joined cluster and it gets dropped, add to the recommendations
                elif if_subject_dropped:
                    # If it is not part of a joined cluster and it gets dropped, add to the recommendations as Dropped
                    if not if_joined_subject and not if_subject_in_choice:
                        add_to_recommendations('Drop', subject_to_write, key, recommendations)
                        dropped_match.setdefault(key, []).append([subject_to_write, query_to_write, query_to_write])
        
    # Add cases where some ID matched with dropped ID, we need to add the ID that matched with the ID that made the other match
    # to be Dropped. e.g x and y matched with x dropping and x also matched with z, then we need to make a choice between x and z.
    for key, matches in matched_with_dropped.items():
        if dropped_match.get(key):
            for dropped in dropped_match[key]:
                for match_ in matches:
                    if match_[2] in dropped:
                        add_to_recommendations('Choice', dropped[2], key, recommendations, match_[3])

    sort_order: List[str] = ['Joined', 'Choice', 'Keep', 'Drop']
    recommendations = {k: {l[0]: l[1] for l in sorted(v.items(), key=lambda x: sort_order.index(x[0].split('_')[0]))} for k, v in recommendations.items()}
    
    return related_clusters, recommendations


def write_blast_summary_results(related_clusters: Dict[str, List[Tuple[Any, ...]]],
                                count_results_by_class_with_inverse: Dict[str, Dict[str, Tuple[int, int]]], 
                                group_reps_ids: Dict[str, List[str]],
                                group_alleles_ids: Dict[str, List[str]], 
                                frequency_in_genomes: Dict[str, int],
                                recommendations: Dict[str, Dict[str, List[str]]], 
                                reverse_matches: bool,
                                classes_outcome: Tuple[str, ...],
                                output_directory: str) -> Tuple[str]:
    """
    Writes summary results of BLAST analysis to TSV files.

    This function generates two files: 'related_matches.tsv' and 'count_results_by_cluster.tsv'.
    The 'related_matches.tsv' file contains information about related clusters, while
    'count_results_by_cluster.tsv' details the count of results by cluster and class, including a total count.

    Parameters
    ----------
    related_clusters : Dict[str, List[Tuple[Any, ...]]]
        A dictionary where each key is a cluster identifier and each value is a list of tuples.
        Each tuple represents a related match with its details.
    count_results_by_class_with_inverse : Dict[str, Dict[str, Tuple[int, int]]]
        A dictionary where each key is a cluster identifier separated by '|', and each value is another dictionary.
        The inner dictionary's keys are class identifiers, and values are counts of results for that class.
    group_reps_ids : Dict[str, List[str]]
        A dictionary mapping sequence identifiers to their representative IDs.
    group_alleles_ids : Dict[str, List[str]]
        A dictionary mapping sequence identifiers to their allele IDs.
    frequency_in_genomes : Dict[str, int]
        A dictionary mapping sequence identifiers to their frequency in genomes.
    recommendations : Dict[str, Dict[str, List[str]]]
        A dictionary containing recommendations for each cluster based on the classification of the results.
    reverse_matches : bool
        A flag indicating whether there are reverse matches.
    classes_outcome : Tuple[str, ...]
        A tuple of possible class outcomes to sort the BLAST results into.
    results_output : str
        The path to the directory where the output files will be saved.
    
    Returns
    -------
    None
        This function does not return any value but writes the summary results to the specified files.

    Notes
    -----
    - The 'related_matches.tsv' file is formatted such that each related match is written on a new line,
      with details separated by tabs. A blank line is added after each cluster's matches.
    - The 'count_results_by_cluster.tsv' file includes the cluster identifier, class identifier, count of results,
      and total count of results for the cluster, with each piece of information separated by tabs.
      A blank line is added after each cluster's information.
    """
    
    # Write the recommendations to the output file
    recommendations_file_path: str = os.path.join(output_directory, "recommendations.tsv")
    with open(recommendations_file_path, 'w') as recommendations_report_file:
        recommendations_report_file.write("Recommendation\tIDs\n")
        for key, recommendation in recommendations.items():
            for category, ids in recommendation.items():
                category = category.split('_')[:2] if 'Choice' in category else category
                # If the category is Choice, add the class to the category
                if isinstance(category, list):
                    category = '_'.join(category)
                # Convert all to string
                ids = itf.convert_set_elements_to_strings(ids)
                recommendations_report_file.write(f"{category}\t{','.join(ids)}\n")
            recommendations_report_file.write("#\n")
            
    # Add the reverse matches to the related clusters
    reported_cases: Dict[str, List[Tuple[str, str]]] = {}
    for key, related in list(related_clusters.items()):
        for index, r in enumerate(list(related)):
            if reverse_matches:
                r.insert(4, '-')
                r.insert(5, '-')
            [query, subject] = [itf.remove_by_regex(i, r"\*") for i in r[:2]]
            
            # Add the total count of the representatives and alleles
            representatives_count_query: str = f"{len(group_reps_ids[query])}"
            representatives_count_subject: str = f"{len(group_reps_ids[subject])}" if reverse_matches else "|-"
            allele_count_query: str = f"{len(group_alleles_ids[query])}" if reverse_matches else "-"
            allele_count_subject: str = f"{len(group_alleles_ids[subject])}"
            representatives_count: str = f"{representatives_count_query}|{representatives_count_subject}"
            allele_count: str = f"{allele_count_query}|{allele_count_subject}"
            
            r.extend([representatives_count, allele_count])
            if (query, subject) not in itf.flatten_list(reported_cases.values()):
                reported_cases.setdefault(key, []).append((subject, query))
            elif reverse_matches:
                sublist_index: int = itf.find_sublist_index([[itf.remove_by_regex(i, r"\*")
                                                              for i in l[:2]]
                                                              for l in related_clusters[key]], [subject, query])
                insert: str = r[2] if r[2] is not None else '-'
                related[sublist_index][4] = insert
                insert = r[3] if r[3] is not None else '-'
                related[sublist_index][5] = insert
                related.remove(r)

    # Write the results to the output files
    related_matches_path: str = os.path.join(output_directory, "related_matches.tsv")
    with open(related_matches_path, 'w') as related_matches_file:
        related_matches_file.write("Query\tSubject\tClass\tClass_count" +
                                    ("\tInverse_class\tInverse_class_count" if reverse_matches else "") +
                                    "\tFrequency_in_genomes_query\tFrequency_in_genomes_subject"
                                    "\tAlleles_used_to_blast_count\tAlleles_blasted_against_count\n")
        for related in related_clusters.values():
            for r in related:
                related_matches_file.write('\t'.join(str(item) for item in r) + '\n')

            related_matches_file.write('#\n')
    
    # Write the count results to the output file
    tab: str = '\t'
    count_results_by_cluster_path: str = os.path.join(output_directory, "count_results_by_cluster.tsv")
    with open(count_results_by_cluster_path, 'w') as count_results_by_cluster_file:
        count_results_by_cluster_file.write("Query"
                                            "\tSubject"
                                            f"\t{tab.join(classes_outcome)}"
                                            "\tAlleles_used_to_blast_count"
                                            "\tAlleles_blasted_against_count"
                                            "\tFrequency_in_genomes_query"
                                            "\tFrequency_in_genomes_subject\n")
        for id_, classes in count_results_by_class_with_inverse.items():
            query: str
            subject: str
            query, subject = id_.split('|')
            count_results_by_cluster_file.write('\t'.join(id_.split('|')))
            total_count_origin: int = sum([i[0] for i in classes.values() if i[0] != '-'])
            total_count_inverse: int = sum([i[1] for i in classes.values() if i[1] != '-'])
            query = itf.try_convert_to_type(id_.split('|')[0], int)
            subject = itf.try_convert_to_type(id_.split('|')[1], int)
            
            representatives_count_query: int = len(group_reps_ids[query])
            representatives_count_subject: str = f"{len(group_reps_ids[subject])}" if reverse_matches else "|-"
            allele_count_query: str = f"{len(group_alleles_ids[query])}" if reverse_matches else "-"
            allele_count_subject: str = f"{len(group_alleles_ids[subject])}"
            representatives_count: str = f"{representatives_count_query}|{representatives_count_subject}"
            allele_count: str = f"{allele_count_query}|{allele_count_subject}"
            
            query_frequency: int = frequency_in_genomes[query]
            subject_frequency: int = frequency_in_genomes[subject]

            for class_outcome in classes_outcome:
                class_value: Union[Tuple[int, int], str] = classes.get(class_outcome, '-')
                if class_value == '-':
                    count_results_by_cluster_file.write(f"\t{class_value}")
                else:
                    query_class_count: Union[int, str] = class_value[0] if class_value[0] != '-' else '-'
                    subject_class_count: Union[int, str] = class_value[1] if class_value[1] != '-' else '-'
                    count_results_by_cluster_file.write(f"\t{query_class_count}|{total_count_origin}|{subject_class_count}|{total_count_inverse}")

            count_results_by_cluster_file.write(f"\t{representatives_count}\t{allele_count}\t{query_frequency}\t{subject_frequency}\n")
            count_results_by_cluster_file.write('#\n')

    return (related_matches_path, count_results_by_cluster_path, recommendations_file_path)


def get_matches(all_relationships: Dict[str, List[Tuple[str, str]]], clusters_to_keep: Dict[str, List[str]], 
                sorted_blast_dict: Dict[str, Any]) -> Tuple[Dict[str, Set[str]], Union[Dict[str, Set[str]], None]]:
    """
    Determines the matches between loci and their corresponding alleles or CDS based on the
    relationships and the current selection of CDS to keep.

    This function evaluates the relationships between loci and alleles or CDS to identify matches.
    It operates in two modes based on the presence of loci IDs: one where no specific loci IDs are
    provided and it uses all available relationships, and another where specific loci IDs are used
    to filter the matches. It also considers whether the loci or CDS are part of a joined cluster
    and adjusts the matching process accordingly.

    Parameters
    ----------
    all_relationships : Dict[str, List[Tuple[str, str]]]
        A dictionary containing all relationships between loci and alleles or CDS, with loci as keys
        and lists of related alleles or CDS as values.
    clusters_to_keep : Dict[str, List[str]]
        A dictionary with classes as keys and lists of CDS or loci IDs to be kept as values.
    sorted_blast_dict : Dict[str, Any]
        A dictionary containing sorted BLAST results, used to identify loci that have matches.

    Returns
    -------
    is_matched : Dict[str, Set[str]]
        A dictionary with loci or CDS IDs as keys and sets of matched loci IDs as values, indicating
        successful matches.
    is_matched_alleles : Dict[str, Set[str]] or None
        A dictionary similar to `is_matched` but specifically for alleles, or None if no specific loci
        IDs are provided.

    Notes
    -----
    - The function first checks if `allele_ids` is provided to determine the mode of operation.
    - It uses utility functions like `itf.flatten_list` to simplify the structure of `all_relationships`
      and `itf.remove_by_regex` to clean up the IDs for matching.
    - The matching process accounts for whether entries are part of a joined cluster and adjusts the
      matching logic accordingly.
    - The function returns two dictionaries: one for general matches and one specifically for alleles,
      the latter being applicable only when `allele_ids` are provided.
    """
    # Initialize dictionaries to store matches
    is_matched: Dict[str, Set[str]] = {}
    is_matched_alleles: Dict[str, Set[str]] = {}

    # Flatten the list of all relationships
    relationships: List[Tuple[str, str]] = itf.flatten_list(all_relationships.values())
    
    # Change IDs to remove suffixes
    changed_ids: List[Tuple[str, str]] = [[r[0], r[1].split('_')[0]] for r in relationships]
    
    # Identify loci that had matches in the sorted BLAST results
    had_matches: Set[str] = set([rep.split('_')[0] for rep in sorted_blast_dict])
    
    # Iterate over clusters to keep and determine matches
    for class_, entries in list(clusters_to_keep.items()):
        for entry in list(entries):
            if entry not in had_matches and class_ != '1a':
                id_: str = entry
                entry_list: List[str] = [entry]
                
                # Determine general matches
                is_matched.setdefault(id_, set([i[0] for i in changed_ids if i[1] in entry_list]))
                
                # Determine allele-specific matches
                is_matched_alleles.setdefault(id_, set([i[1] 
                                                        for i in relationships 
                                                        if i[0] in is_matched[id_] 
                                                        and i[1].split('_')[0] in entry_list]))
    
    return is_matched, is_matched_alleles


def run_blasts(blast_db: str, cds_to_blast: List[str], reps_translation_dict: Dict[str, str], rep_paths_nuc: Dict[str, str], 
               output_dir: str, constants: List[Any], cpu: int,
               multi_fasta: Dict[str, List[str]]) -> Tuple[Dict[str, Dict[str, Any]], 
                                                           Dict[str, Dict[str, Any]], 
                                                           Dict[str, Dict[str, Any]], 
                                                           Dict[str, Dict[str, float]], 
                                                           Dict[str, float]]:
    """
    This function runs both BLASTn and subsequently BLASTp based on results of BLASTn.

    Parameters
    ----------
    blast_db : str
        Path to the BLAST db folder.
    cds_to_blast : List[str]
        A list of CDS IDs to be used for BLASTn against the BLAST db.
    reps_translation_dict : Dict[str, str]
        A dictionary mapping sequence IDs to their translations (amino acid sequences).
    rep_paths_nuc : Dict[str, str]
        A dictionary mapping CDS IDs to the path of their corresponding FASTA files.
    output_dir : str
        The directory path where output files will be saved.
    constants : List[Any]
        A list of constants used within the function, such as thresholds for filtering BLAST results.
    cpu : int
        The number of CPU cores to use for parallel processing.
    multi_fasta : Dict[str, List[str]]
        A dictionary used when the input FASTA files contain multiple CDSs, to ensure correct BLASTn
        execution.

    Returns
    -------
    Tuple[Dict[str, Dict[str, Any]], Dict[str, Dict[str, Any]], Dict[str, Dict[str, Any]], Dict[str, Dict[str, float]], Dict[str, float]]
        A tuple containing:
        - representative_blast_results: Dict that contains representative BLAST results.
        - representative_blast_results_coords_all: Dict that contains the coordinates for all of the entries.
        - representative_blast_results_coords_pident: Dict that contains the coordinates for all of the entries above a certain pident value.
        - bsr_values: Dict that contains BSR values between CDS.
        - self_score_dict: Dict that contains the self-score values for all of the CDSs that are processed in this function.
    """
    
    print("\nRunning BLASTn...")
    # BLASTn folder
    blastn_output: str = os.path.join(output_dir, '1_BLASTn_processing')
    ff.create_directory(blastn_output)
    # Create directory
    blastn_results_folder: str = os.path.join(blastn_output, 'BLASTn_results')
    ff.create_directory(blastn_results_folder)
    # Run BLASTn
    # Calculate max id length for print.
    max_id_length: int = len(max(cds_to_blast, key=len))
    total_reps: int = len(rep_paths_nuc)
    representative_blast_results: Dict[str, Dict[str, Any]] = {}
    representative_blast_results_coords_all: Dict[str, Dict[str, Any]] = {}
    representative_blast_results_coords_pident: Dict[str, Dict[str, Any]] = {}
    # Get Path to the blastn executable
    get_blastn_exec: str = lf.get_tool_path('blastn')
    i: int = 1
    with concurrent.futures.ProcessPoolExecutor(max_workers=cpu) as executor:
        for res in executor.map(bf.run_blastdb_multiprocessing,
                                repeat(get_blastn_exec),
                                repeat(blast_db),
                                rep_paths_nuc.values(),
                                cds_to_blast,
                                repeat(blastn_results_folder)):
            filtered_alignments_dict: Dict[str, Dict[str, Any]]
            alignment_coords_all: Dict[str, Dict[str, Any]]
            alignment_coords_pident: Dict[str, Dict[str, Any]]
            filtered_alignments_dict, _, alignment_coords_all, alignment_coords_pident = af.get_alignments_dict_from_blast_results(
                res[1], constants[1], True, False, True, True, False)
            # Save the BLASTn results
            representative_blast_results.update(filtered_alignments_dict)
            representative_blast_results_coords_all.update(alignment_coords_all)
            representative_blast_results_coords_pident.update(alignment_coords_pident)

            print(
                f"\rRunning BLASTn for cluster representatives: {res[0]} - {i}/{total_reps: <{max_id_length}}", 
                end='', flush=True)
            i += 1

    print("\nRunning BLASTp based on BLASTn results matches...")
    # Obtain the list for what BLASTp runs to do, no need to do all vs all as previously.
    # Based on BLASTn results.
    blastp_runs_to_do: Dict[str, List[str]] = {query: itf.flatten_list([[subject[1]['subject']
                                            for subject in subjects.values()]]) 
                         for query, subjects in representative_blast_results.items()}
    
    # Create directories.
    blastp_results: str = os.path.join(output_dir, '2_BLASTp_processing')
    ff.create_directory(blastp_results)
    
    blastn_results_matches_translations: str = os.path.join(blastp_results,
                                                       'blastn_results_matches_translations')
    ff.create_directory(blastn_results_matches_translations)

    representatives_blastp_folder: str = os.path.join(blastn_results_matches_translations,
                                                'cluster_rep_translation')
    ff.create_directory(representatives_blastp_folder)
    
    blastp_results_folder: str = os.path.join(blastp_results,
                                         'BLASTp_results')
    ff.create_directory(blastp_results_folder)
    
    blastp_results_ss_folder: str = os.path.join(blastp_results,
                                            'BLASTp_results_self_score_results')
    ff.create_directory(blastp_results_ss_folder)
    # Write the protein FASTA files.
    rep_paths_prot: Dict[str, str] = {}
    rep_matches_prot: Dict[str, str] = {}
    if multi_fasta:
        blasts_to_run: Dict[str, Set[str]] = {}
        seen_entries: Dict[str, Set[str]] = {}
    for query_id, subjects_ids in blastp_runs_to_do.items():
        
        filename: Union[str, None] = itf.identify_string_in_dict_get_key(query_id, multi_fasta)
        if filename is not None:
            blasts_to_run.setdefault(filename, set()).update(subjects_ids)
            seen_entries[filename] = set()
        else:
            filename = query_id
            seen_entries[filename] = set()
            blasts_to_run.setdefault(filename, set()).update(subjects_ids)
        # First write the representative protein sequence.
        rep_translation_file: str = os.path.join(representatives_blastp_folder,
                                            f"cluster_rep_translation_{filename}.fasta")
        
        write_type: str = 'a' if os.path.exists(rep_translation_file) else 'w'
        
        rep_paths_prot[filename] = rep_translation_file
        with open(rep_translation_file, write_type) as trans_fasta_rep:
            trans_fasta_rep.writelines(">"+query_id+"\n")
            trans_fasta_rep.writelines(str(reps_translation_dict[query_id])+"\n")
        # Then write in another file all of the matches for that protein sequence
        # including the representative itself.
        rep_matches_translation_file: str = os.path.join(blastn_results_matches_translations,
                                                    f"cluster_matches_translation_{filename}.fasta")
        
        rep_matches_prot[filename] = rep_matches_translation_file
        with open(rep_matches_translation_file, write_type) as trans_fasta:            
            for subject_id in subjects_ids:
                if multi_fasta:
                    if subject_id in seen_entries[filename]:
                        continue

                trans_fasta.writelines(">"+subject_id+"\n")
                trans_fasta.writelines(str(reps_translation_dict[subject_id])+"\n")
                
            if multi_fasta:  
                seen_entries.setdefault(filename, set()).update(subjects_ids)

    # Calculate BSR based on BLASTp.
    bsr_values: Dict[str, Dict[str, float]] = {}
    
    # Create query entries
    for query in blastp_runs_to_do:
        bsr_values[query] = {}
        
    if multi_fasta:
        blastp_runs_to_do = blasts_to_run
    # Total number of runs
    total_blasts: int = len(blastp_runs_to_do)
    # If there is need to calculate self-score
    print("\nCalculate self-score for the CDSs...")
    self_score_dict: Dict[str, float] = {}
    # Get Path to the blastp executable
    get_blastp_exec: str = lf.get_tool_path('blastp')
    i = 1
    # Calculate self-score
    with concurrent.futures.ProcessPoolExecutor(max_workers=cpu) as executor:
        for res in executor.map(bf.run_self_score_multiprocessing,
                                rep_paths_prot.keys(),
                                repeat(get_blastp_exec),
                                rep_paths_prot.values(),
                                repeat(blastp_results_ss_folder)):
            
            self_score: Dict[str, float]
            _, self_score, _, _ = af.get_alignments_dict_from_blast_results(res[1], 0, True, True, True, True, False)
    
            # Save self-score
            self_score_dict[res[0]] = self_score
                            
            print(f"\rRunning BLASTp to calculate self-score for {res[0]: <{max_id_length}}", end='', flush=True)
            i += 1
    # Print newline
    print('\n')  
    
    print("Running BLASTp...")
    # Run BLASTp between all BLASTn matches (rep vs all its BLASTn matches).      
    i = 1
    with concurrent.futures.ProcessPoolExecutor(max_workers=cpu) as executor:
        for res in executor.map(bf.run_blast_fastas_multiprocessing,
                                blastp_runs_to_do, 
                                repeat(get_blastp_exec),
                                repeat(blastp_results_folder),
                                repeat(rep_paths_prot),
                                rep_matches_prot.values()):
            
            filtered_alignments_dict: Dict[str, Dict[str, Any]]
            filtered_alignments_dict, _, _, _ = af.get_alignments_dict_from_blast_results(res[1], 0, True, False, True, True, False)

            # Since BLAST may find several local alignments, choose the largest one to calculate BSR.
            for query, subjects_dict in filtered_alignments_dict.items():
                for subject_id, results in subjects_dict.items():
                    # Highest score (First one)
                    subject_score: float = next(iter(results.values()))['score']
                    bsr_values[query].update({subject_id: bf.compute_bsr(subject_score, self_score_dict[res[0]])})
        
            print(f"\rRunning BLASTp for cluster representatives matches: {res[0]} - {i}/{total_blasts: <{max_id_length}}", end='', flush=True)
            i += 1

    return (representative_blast_results, representative_blast_results_coords_all,
            representative_blast_results_coords_pident, bsr_values, self_score_dict)


def write_processed_results_to_file(clusters_to_keep: Dict[str, Union[List[str], Dict[str, List[str]]]], 
                                    representative_blast_results: Dict[str, Dict[str, Dict[str, Any]]],
                                    classes_outcome: List[str], all_alleles: Dict[str, List[str]], 
                                    is_matched: Dict[str, Set[str]], is_matched_alleles: Dict[str, Set[str]], 
                                    output_path: str) -> None:
    """
    Write processed results to files in specified output directories.

    Parameters
    ----------
    clusters_to_keep : Dict[str, Union[List[str], Dict[str, List[str]]]]
        Dictionary containing clusters to keep, categorized by class.
    representative_blast_results : Dict[str, Dict[str, Dict[str, Any]]]
        Dictionary containing representative BLAST results.
    classes_outcome : List[str]
        List of class outcomes to process.
    all_alleles : Dict[str, List[str]]
        Dictionary containing all alleles information.
    is_matched : Dict[str, Set[str]]
        Dictionary indicating if clusters are matched.
    is_matched_alleles : Dict[str, Set[str]]
        Dictionary containing matched alleles information.
    output_path : str
        Path to the output directory where results will be written.

    Returns
    -------
    None
        This function does not return any value. It writes results to files.
    """
    # Create output directories
    blast_by_cluster_output: str = os.path.join(output_path, 'blast_by_cluster')
    ff.create_directory(blast_by_cluster_output)
    blast_results_by_class_output: str = os.path.join(output_path, 'blast_results_by_class')
    ff.create_directory(blast_results_by_class_output)

    # Process clusters
    for class_, cds in clusters_to_keep.items():
        # Skip clusters that are not matched
        if class_ == 'Retained_not_matched_by_blastn':
            continue
        # Process clusters
        for cluster in cds if not isinstance(cds, dict) else cds.items():
            # Determine cluster type
            if isinstance(cds, dict):
                cluster_id: str = cluster[0]
                cluster: List[str] = cluster[1]
                cluster_type: str = 'joined_cluster'
                cluster = cds[cluster_id]
            else:
                cluster_id = cluster
                cluster = [cluster]
                cluster_type = 'retained'
            # Get all alleles in the cluster
            cluster_alleles: List[str] = []
            for entry in cluster:
                cluster_alleles += all_alleles[entry]
            # Write results
            write_dict: Dict[str, Dict[str, Dict[str, Any]]] = {
                query: {
                    subject: {id_: entry for id_, entry in entries.items()}
                    for subject, entries in subjects.items()
                }
                for query, subjects in representative_blast_results.items()
                if query.split('_')[0] in cluster
            }
            # If the cluster is matched and not joined, write the results
            if is_matched.get(cluster_id) and class_ != '1a':
                queries: Set[str] = is_matched[cluster_id]
                cluster: Set[str] = is_matched_alleles[cluster_id]
                write_dict = {
                    query: {
                        subject: {id_: entry for id_, entry in entries.items()}
                        for subject, entries in subjects.items() if subject in cluster
                    }
                    for query, subjects in representative_blast_results.items()
                    if query in queries
                }

            report_file_path: str = os.path.join(blast_by_cluster_output, f"blast_{cluster_type}_{cluster_id}.tsv")
            alignment_dict_to_file(write_dict, report_file_path, 'w')

    # Process classes
    for class_ in classes_outcome:
        write_dict: Dict[str, Dict[str, Dict[str, Any]]] = {
            query: {
                subject: {id_: entry for id_, entry in entries.items() if entry['class'] == class_}
                for subject, entries in subjects.items()
            }
            for query, subjects in representative_blast_results.items()
        }
        report_file_path: str = os.path.join(blast_results_by_class_output, f"blastn_group_{class_}.tsv")
        alignment_dict_to_file(write_dict, report_file_path, 'w')


def extract_clusters_to_keep(classes_outcome: List[str], count_results_by_class: Dict[str, Dict[str, int]], 
                            drop_mark: Set[int]) -> Tuple[Dict[str, Union[List[Union[str, List[str]]], Dict[str, List[str]]]], Set[str]]:
    """
    Extracts and organizes CDS (Coding Sequences) to keep based on classification outcomes.

    This function processes BLAST results to determine which coding sequences (CDS) should
    be retained for further analysis based on their classification outcomes. It organizes
    CDS into categories, prioritizes them according to a predefined order of classes, and
    identifies sequences to be dropped.

    Parameters
    ----------
    classes_outcome : List[str]
        An ordered list of class identifiers that determine the priority of classes for keeping CDS.
    count_results_by_class : Dict[str, Dict[str, int]]
        A dictionary where keys are concatenated query and subject IDs separated by '|', and values
        are dictionaries with class identifiers as keys and counts as values.
    drop_mark : Set[int]
        A set of identifiers that are marked for dropping based on previous criteria.

    Returns
    -------
    clusters_to_keep : Dict[str, Union[List[Union[int, List[int]]], Dict[int, List[str]]]]
        A dictionary with class identifiers as keys and lists of CDS identifiers or pairs of identifiers
        to be kept in each class.
    drop_possible_loci : Set[int]
        A set of CDS identifiers that are determined to be dropped based on their classification and
        presence in `drop_mark`.

    Notes
    -----
    - The function first initializes `clusters_to_keep` with empty lists for each class in `classes_outcome`.
    - It then iterates through `count_results_by_class` to assign CDS to the most appropriate class
      based on the provided outcomes.
    - Special handling is given to class '1a', where CDS pairs are clustered and indexed.
    - CDS marked in `drop_mark` and falling under certain classes are added to `drop_possible_loci` for exclusion.
    - The function uses utility functions like `itf.try_convert_to_type` for type conversion and
      `cf.cluster_by_ids` for clustering CDS pairs in class '1a'.
    """
    # Temporary dictionary to keep track of the best class for each CDS
    temp_keep: Dict[str, str] = {}
    
    # Initialize clusters_to_keep with empty lists for each class in classes_outcome
    clusters_to_keep: Dict[str, Union[Dict[int, List[str]]]] = {class_: [] for class_ in classes_outcome if class_ != '1a'}
    temp_clusters_1a: List[List[str]] = []
    # Initialize a set to keep track of CDS to be dropped
    drop_possible_loci: Set[str] = set()
    
    # Iterate through count_results_by_class to assign CDS to the most appropriate class
    for ids, result in count_results_by_class.items():
        class_: str = next(iter(result))
        query: str
        subject: str
        query, subject = ids.split('|')
        
        # Special handling for class '1a'
        if class_ == '1a':
            temp_clusters_1a.append([query, subject])
        
        # Update temp_keep with the best class for each CDS
        if not temp_keep.get(query):
            temp_keep[query] = class_
        elif classes_outcome.index(class_) < classes_outcome.index(temp_keep[query]):
            temp_keep[query] = class_
        
        if not temp_keep.get(subject):
            temp_keep[subject] = class_
        elif classes_outcome.index(class_) < classes_outcome.index(temp_keep[subject]):
            temp_keep[subject] = class_
    
    # Iterate through temp_keep to finalize clusters_to_keep and drop_possible_loci
    for keep, class_ in temp_keep.items():
        if class_ == '1a':
            continue
        if keep in drop_mark and class_ in ['1b', '2a', '3a']:
            drop_possible_loci.add(itf.try_convert_to_type(keep, int))
        else:
            clusters_to_keep.setdefault(class_, []).append(keep)
    
    # Cluster and index CDS pairs in class '1a'
    clusters_to_keep_1a: Dict[int, List[str]] = {i: list(values) for i, values in enumerate(cf.cluster_by_ids(temp_clusters_1a), 1)}
    
    return clusters_to_keep_1a, clusters_to_keep, drop_possible_loci


def count_number_of_reps_and_alleles(merged_all_classes: Dict[str, Dict[int, List[int]]], processing_mode: str, clusters: Dict[int, List[int]], 
                                    drop_possible_loci: Set[int], group_reps_ids: Dict[int, Set[int]], 
                                    group_alleles_ids: Dict[int, Set[int]]) -> Tuple[Dict[int, Set[int]], Dict[int, Set[int]]]:
    """
    Counts the number of representatives and alleles for each group in the given CDS clusters, excluding those in
    the drop set.

    This function iterates through the clusters to keep and counts the number of representatives and alleles
    for each group, updating the provided dictionaries with the results. It excludes groups that are marked
    for dropping.

    Parameters
    ----------
    clusters_to_keep : Dict[str, Dict[int, List[int]]]
        Dictionary of CDS clusters to keep, organized by class and group.
    clusters : Dict[int, List[int]]
        Dictionary mapping group IDs to their member CDS IDs.
    drop_possible_loci : Set[int]
        Set of group IDs to be excluded from the count.
    group_reps_ids : Dict[int, Set[int]]
        Dictionary to be updated with representative IDs for each group.
    group_alleles_ids : Dict[int, Set[int]]
        Dictionary to be updated with allele IDs for each group.

    Returns
    -------
    Tuple[Dict[int, Set[int]], Dict[int, Set[int]]]
        Updated dictionaries where the key is the CDS cluster ID and the value is a set of representative IDs
        and allele IDs, respectively.

    Notes
    -----
    - The function first iterates through the clusters to keep, updating the representative and allele IDs
      for each group.
    - It then iterates through the drop set to ensure that any groups marked for dropping are also included
      in the dictionaries.
    """
    # Iterate over each class in clusters_to_keep
    for class_, cds_group in merged_all_classes.items():
        # Iterate over each group in the class
        for group in cds_group:
            if class_ == '1a':
                # Iterate over each representative in the joined group
                for cds in cds_group[group]:
                    if group_reps_ids.get(cds):
                        continue
                    if processing_mode[0] == 'alleles':
                        group_reps_ids.setdefault(cds, set()).update(clusters[cds])
                    else:
                        group_reps_ids.setdefault(cds, set()).add(cds)
                    if processing_mode[1] == 'alleles':
                        group_alleles_ids.setdefault(cds, set()).update(clusters[cds])
                    else:
                        group_alleles_ids.setdefault(cds, set()).add(cds)
                    
            elif group_reps_ids.get(group):
                continue
            else:
                if processing_mode[0] == 'alleles':
                    group_reps_ids.setdefault(cds, set()).update(clusters[cds])
                else:
                    group_reps_ids.setdefault(cds, set()).add(cds)
                if processing_mode[1] == 'alleles':
                    group_alleles_ids.setdefault(cds, set()).update(clusters[cds])
                else:
                    group_alleles_ids.setdefault(cds, set()).add(cds)
    
    # Iterate over the drop set to ensure groups marked for dropping are included
    for id_ in drop_possible_loci:
        if id_ not in group_reps_ids:
            group_reps_ids.setdefault(id_, set()).add(id_)
            group_alleles_ids.setdefault(id_, set()).update(clusters[id_])

    return group_reps_ids, group_alleles_ids


def create_graphs(file_path: str, output_path: str, filename: str, other_plots: Optional[List[str]] = None) -> None:
    """
    Create graphs based on representative_blast_results written inside a TSV file.

    This function creates several plots related to palign and protein values, with
    the option to create additional plots based on input values.

    Parameters
    ----------
    file_path : str
        Path to the TSV file.
    output_path : str
        Path to the output directory.
    filename : str
        Name of the output HTML file.
    other_plots : Optional[List[Dict[str, Any]]], optional
        List that contains additional data to create plots. Each dictionary in the list
        should contain the data and metadata required for creating the plot.

    Returns
    -------
    None
        Creates an HTML file inside the output_path that contains all of the created graphs.

    Notes
    -----
    - The function first creates a directory for storing the graphs.
    - It then imports the BLAST results from the TSV file into a DataFrame.
    - It creates violin plots for various palign and protein values.
    - If additional plots are specified, it creates those as well.
    - Finally, it saves all the plots to an HTML file.
    """
    # Create the output directory for the graphs
    results_output: str = os.path.join(output_path, "Graph_folder")
    ff.create_directory(results_output)
    
    # Import the BLAST results from the TSV file into a DataFrame
    blast_results_df: pd.DataFrame = ff.import_df_from_file(file_path, '\t')
    
    # Create violin plots for palign values
    traces: List[Any] = []
    for column in ['Global_palign_all_min', 'Global_palign_all_max', 'Global_palign_pident_min', 'Global_palign_pident_max', 'Palign_local_min']:
        traces.append(gf.create_violin_plot(y=blast_results_df[column], name=blast_results_df[column].name))
    
    violinplot1: Any = gf.generate_plot(traces, "Palign Values between BLAST results", "Column", "Palign")
    
    # Create violin plots for protein values
    traces = []
    for column in ['Prot_BSR', 'Prot_seq_Kmer_sim', 'Prot_seq_Kmer_cov']:
        traces.append(gf.create_violin_plot(y=blast_results_df[column], name=blast_results_df[column].name))
    
    violinplot2: Any = gf.generate_plot(traces, "Protein values between BLAST results", "BLAST entries ID", "Columns")
    
    # Create additional plots if specified
    extra_plot: List[Any] = []
    if other_plots:
        for plot in other_plots:
            plot_df: pd.DataFrame = pf.dict_to_df(plot[0])
            for column in plot_df.columns.tolist():
                if plot[1] == 'histogram':
                    trace: Any = gf.create_histogram(x=plot_df[column], name=plot_df[column].name)
            
            extra_plot.append(gf.generate_plot(trace, plot[2], plot[3], plot[4]))

    # Save all the plots to an HTML file
    gf.save_plots_to_html([violinplot1, violinplot2] + extra_plot, results_output, filename)


def print_classifications_results(clusters_to_keep: Dict[str, Any], drop_possible_loci: List[int], 
                                  to_blast_paths: Dict[str, str], clusters: Dict[str, Any]) -> None:
    """
    Prints the classification results based on the provided parameters.

    Parameters
    ----------
    clusters_to_keep : Dict[str, Any]
        Dictionary containing CDS to keep, classified by their class type.
    drop_possible_loci : List[int]
        List of possible loci dropped.
    to_blast_paths : Dict[str, str]
        Path to BLAST.
    clusters : Dict[str, Any]
        The dictionary containing the clusters.

    Returns
    -------
    None
        Prints the classification results to stdout.

    Notes
    -----
    - The function first processes the `clusters_to_keep` dictionary to count the number of CDS
      representatives for each class.
    - It then prints the results, including the number of groups classified under each class and
      any recommendations for verification.
    - If there are any retained groups not matched by BLASTn, it handles them separately.
    """
    def print_results(class_: str, count: int, printout: Dict[str, Any]) -> None:
        """
        Prints the classification results based on the class type.

        Parameters
        ----------
        class_ : str
            The class type.
        count : int
            The count of groups.
        printout : Dict[str, Any]
            The dictionary containing printout information.

        Returns
        -------
        None
            Prints the classification results to stdout.

        Notes
        -----
        - The function prints different messages based on the class type.
        - It provides recommendations for verification for certain classes.
        """
        if count > 0:
            if class_ in ['2b', '4b']:
                print(f"\t\tOut of those groups, {count} are classified as {class_} and were retained"
                      " but it is recommended to verify them as they may be contained or contain partially inside"
                      " their BLAST match.")
            elif class_ == '1a':
                print(f"\t\tOut of those groups, {count} {'CDSs groups'} are classified as {class_}"
                      f" and are contained in {len(printout['1a'])} joined groups that were retained.")
            elif class_ == 'dropped':
                print(f"\t\tOut of those {count} have been dropped due to frequency")
            else:
                print(f"\t\tOut of those groups, {count} are classified as {class_} and were retained.")

    # If 'Retained_not_matched_by_blastn' exists in clusters_to_keep, remove it and store it separately
    retained_not_matched_by_blastn: Optional[Any] = clusters_to_keep.pop('Retained_not_matched_by_blastn', None)

    # Display info about the results obtained from processing the classes.
    # Get the total number of CDS reps considered for classification.
    count_cases: Dict[str, int] = {}

    for class_, loci in clusters_to_keep.items():
        if class_ == '1a':
            count_cases[class_] = len(itf.flatten_list(loci.values()))
        else:
            count_cases[class_] = len(loci)
        
    count_cases['dropped'] = len(drop_possible_loci)
    # Check if loci is not empty
    total_loci: int = sum(count_cases.values())

    print(f"Out of {len(to_blast_paths)}:")
    print(f"\t{total_loci} representatives had matches with BLASTn against the.")
    for class_, count in count_cases.items():
        print_results(class_, count, clusters_to_keep)

    print(f"\tOut of those {len(to_blast_paths.values()) - sum(count_cases.values())} didn't have any matches")

    if retained_not_matched_by_blastn:
        clusters_to_keep['Retained_not_matched_by_blastn'] = retained_not_matched_by_blastn


def add_cds_to_dropped_cds(drop_possible_loci: List[str], dropped_cds: Dict[str, str], clusters_to_keep: Dict[str, Any],
                           clusters_to_keep_1a: Dict[str, List[str]],
                            clusters: Dict[str, List[str]], reason: str, processed_drop: List[str]) -> None:
    """
    Adds CDS to the dropped CDS list based on the provided parameters.

    This function processes a list of possible loci to be dropped and updates the dropped CDS list
    with the provided reason. It ensures that each CDS is processed only once and handles both
    individual CDS and joined groups of CDS.

    Parameters
    ----------
    drop_possible_loci : List[int]
        List of possible loci dropped.
    dropped_cds : Dict[int, str]
        Dictionary to store dropped CDS with their reasons.
    clusters_to_keep : Dict[str, Any]
        Dictionary containing CDS to keep, classified by their class type.
    clusters : Dict[int, List[int]]
        Dictionary containing clusters of CDS.
    reason : str
        Reason for dropping the CDS.
    processed_drop : List[int]
        List of already processed drop IDs.

    Returns
    -------
    None
        The function updates the `dropped_cds` dictionary in place.

    Notes
    -----
    - The function first checks if each drop ID has already been processed to avoid duplication.
    - It identifies whether the drop ID belongs to a joined group (class '1a') or another class.
    - If the drop ID belongs to a joined group, it processes all elements of the group.
    - It updates the `dropped_cds` dictionary with the reason for dropping each CDS.
    """
    # Iterate over a copy of the drop_possible_loci list to avoid modifying the list during iteration
    for drop_id in drop_possible_loci.copy():
        # Skip if the drop ID has already been processed
        if drop_id in processed_drop:
            continue
        else:
            processed_drop.append(drop_id)

        # Check if the drop ID belongs to a joined group (class '1a')
        class_1a_id: Optional[str] = itf.identify_string_in_dict_get_key(drop_id, clusters_to_keep_1a)
        if class_1a_id:
            # Add all elements of the joined group to the dropped list
            process_ids: List[str] = clusters_to_keep_1a[class_1a_id]
            del clusters_to_keep_1a[drop_id]
        else:
            # Check if the drop ID belongs to another class
            class_: Optional[str] = itf.identify_string_in_dict_get_key(drop_id, {key: value for key, value in clusters_to_keep.items() if key != '1a'})
            if class_:
                clusters_to_keep[class_].remove(drop_id)

        # Update the dropped_cds dictionary with the reason for dropping each CDS
        if class_1a_id:
            for rep_id in process_ids:
                for cds_id in clusters[rep_id]:
                    dropped_cds[cds_id] = reason
        else:
            for cds_id in clusters[drop_id]:
                dropped_cds[cds_id] = reason


#Unused
def identify_problematic_new_loci(clusters_to_keep: Dict[str, Dict[int, List[int]]], all_alleles: Dict[int, List[int]], 
                                  cds_present: str, all_nucleotide_sequences: Dict[int, str], constants: List[Any], 
                                  results_output: str) -> Set[int]:
    """
    Identify problematic new loci based on the presence of NIPHs and NIPHEMs.

    Parameters
    ----------
    clusters_to_keep : Dict[str, Dict[int, List[int]]]
        A dictionary where keys are class labels and values are dictionaries with cluster IDs as keys 
        and lists of cluster members as values. For key '1a', the values are dicts with joined cluster
        ID as key and list as value.
    all_alleles : Dict[int, List[int]]
        A dictionary where keys are cluster IDs and values are lists of allele IDs.
    cds_present : str
        Path to the distinct.hashtable file.
    all_nucleotide_sequences : Dict[int, str]
        A dictionary where keys are allele IDs and values are sequences not included in the schema.
    constants : List[Any]
        A list of constants used in the function. The 9th element (index 8) is the threshold for 
        problematic proportion.
    results_output : str
        The path to the directory where the output file will be saved.

    Returns
    -------
    dropped_problematic : Set[int]
        The updated set of cluster IDs that should be dropped.

    Notes
    -----
    - The function first decodes the CDS sequences from the provided file.
    - It then iterates through the clusters to keep, identifying NIPHs and NIPHEMs for each cluster.
    - It calculates the proportion of problematic genomes for each cluster and determines if it should be dropped.
    - Finally, it writes the results to a TSV file in the specified output directory.
    """
    # Initialize the set to store problematic cluster IDs to be dropped
    dropped_problematic: Set[int] = set()
    
    # Decode the CDS sequences from the provided file
    decoded_sequences_ids: Dict[str, List[Any]] = itf.decode_CDS_sequences_ids(cds_present)
    
    # Initialize dictionaries to store NIPHEMs and NIPHs in possible new loci
    niphems_in_possible_new_loci: Dict[int, List[int]] = {}
    niphs_in_possible_new_loci: Dict[int, Set[int]] = {}
    temp_niphs_in_possible_new_loci: Dict[int, Dict[int, Set[int]]] = {}
    total_possible_new_loci_genome_presence: Dict[int, int] = {}
    problematic_loci: Dict[int, float] = {}
    
    # Iterate through the clusters to keep
    for class_, cluster_keep in clusters_to_keep.items():
        for cluster_id in cluster_keep:
            niphems_in_possible_new_loci.setdefault(cluster_id, [])
            temp_niphs_in_possible_new_loci.setdefault(cluster_id, {})
            
            # Flatten the list of alleles for class '1a'
            if class_ == '1a':
                cluster: List[int] = itf.flatten_list([all_alleles[i] for i in clusters_to_keep['1a'][cluster_id]])
            else:
                cluster = all_alleles[cluster_id]
            
            # Iterate through each allele in the cluster
            for allele_id in cluster:
                sequence: str = all_nucleotide_sequences[allele_id]
                hashed_seq: str = sf.seq_to_hash(str(sequence))
                allele_presence_in_genomes: List[int] = decoded_sequences_ids[hashed_seq][1:]
                
                # NIPHs
                temp_niphs_in_possible_new_loci[cluster_id].setdefault(allele_id, set(allele_presence_in_genomes))
                
                # NIPHEMs
                unique_elements: Set[int] = set(allele_presence_in_genomes)
                if len(unique_elements) != len(allele_presence_in_genomes):
                    niphems_genomes: List[int] = itf.get_duplicates(allele_presence_in_genomes)
                    niphems_in_possible_new_loci.setdefault(cluster_id, []).extend(niphems_genomes)
            
            # Get shared NIPHs in genomes
            niphs_in_genomes: Set[int] = set(itf.get_shared_elements(temp_niphs_in_possible_new_loci[cluster_id]))
            niphs_in_possible_new_loci.setdefault(cluster_id, niphs_in_genomes)
            
            # Get NIPHEMs in genomes
            niphems_in_genomes: Set[int] = set(niphems_in_possible_new_loci[cluster_id])
            
            # Calculate problematic genomes in possible new loci
            problematic_genomes_in_possible_new_loci: Set[int] = niphs_in_genomes | niphems_in_genomes
            
            # Calculate total possible new loci genome presence
            total_possible_new_loci_genome_presence[cluster_id] = len(set(itf.flatten_list(temp_niphs_in_possible_new_loci[cluster_id].values())))
            
            # Calculate problematic proportion
            problematic_proportion: float = len(problematic_genomes_in_possible_new_loci) / total_possible_new_loci_genome_presence[cluster_id]
            problematic_loci.setdefault(cluster_id, problematic_proportion)
            
            # Determine if the cluster should be dropped
            if problematic_proportion >= constants[8]:
                dropped_problematic.add(cluster_id)
    
    # Write the groups that were removed due to the presence of NIPHs or NIPHEMs
    niphems_and_niphs_file: str = os.path.join(results_output, 'niphems_and_niphs_groups.tsv')
    with open(niphems_and_niphs_file, 'w') as niphems_and_niphs:
        niphems_and_niphs.write('Group_ID\tProportion_of_NIPHs_and_NIPHEMs\tOutcome\n')
        for group, proportion in problematic_loci.items():
            outcome: str = 'Dropped' if group in dropped_problematic else 'Kept'
            niphems_and_niphs.write(f"{group}\t{proportion}\t{outcome}\n")
    
    return dropped_problematic


def write_dropped_possible_new_loci_to_file(drop_possible_loci: Set[str], dropped_cds: Dict[str, str], 
                                            output_directory: str) -> str:
    """
    Write the dropped possible new loci to a file with the reasons for dropping them.

    This function writes the IDs of possible new loci that should be dropped, along with the reasons
    for dropping them, to a TSV file in the specified output directory.

    Parameters
    ----------
    drop_possible_loci : Set[str]
        A set of possible new loci IDs that should be dropped.
    dropped_cds : Dict[str, str]
        A dictionary where keys are CDS (Coding Sequences) IDs and values are the reasons for dropping them.
    results_output : str
        The path to the directory where the output file will be saved.

    Returns
    -------
    None
        The function writes the results to a file and does not return any value.

    Notes
    -----
    - The function first constructs the output file path.
    - It then creates a dictionary mapping locus IDs to their drop reasons by extracting the locus ID
      from the CDS ID.
    - Finally, it writes the locus IDs and their drop reasons to the output file.
    """
    # Construct the output file path
    drop_possible_loci_output: str = os.path.join(output_directory, 'drop_loci_reason.tsv')
    
    # Create a dictionary mapping locus IDs to their drop reasons
    locus_drop_reason: Dict[str, str] = {cds.split('_')[0]: reason 
                                         for cds, reason in dropped_cds.items() if '_' in cds}
    
    # Write the locus IDs and their drop reasons to the output file
    with open(drop_possible_loci_output, 'w') as drop_possible_loci_file:
        drop_possible_loci_file.write('Possible_new_loci_ID\tDrop_Reason\n')
        for locus in drop_possible_loci:
            drop_possible_loci_file.write(f"{locus}\t{locus_drop_reason[locus]}\n")
    
    return drop_possible_loci_output