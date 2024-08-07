import os
import concurrent.futures
from itertools import repeat

try:
    from utils import (file_functions as ff,
                       sequence_functions as sf,
                       clustering_functions as cf,
                       blast_functions as bf,
                       alignments_functions as af,
                       iterable_functions as itf,
                       linux_functions as lf,
                       graphical_functions as gf,
                       kmers_functions as kf,
                       pandas_functions as pf)
except ModuleNotFoundError:
    from SchemaRefinery.utils import (file_functions as ff,
                                      sequence_functions as sf,
                                      clustering_functions as cf,
                                      blast_functions as bf,
                                      alignments_functions as af,
                                      iterable_functions as itf,
                                      linux_functions as lf,
                                      graphical_functions as gf,
                                      kmers_functions as kf,
                                      pandas_functions as pf)

def alignment_dict_to_file(blast_results_dict, file_path, write_type, add_group_column = False):
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
    add_group_column : bool, optional
        Indicates whether to add a 'CDS_group' column to the header of the output file. Defaults to False.

    Returns
    -------
    None
        Writes the alignment data to the specified file based on the provided dictionary structure and parameters.

    Notes
    -----
    - The function constructs a header for the output file based on the alignment data structure and the `add_group_column`
    parameter.
    - It iterates over the nested dictionary structure to write each piece of alignment data to the file, formatting
    each row as tab-separated values.
    - This function is useful for exporting BLAST alignment results to a file for further analysis or reporting.
    """
    
    header = ['Query\t',
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

    if add_group_column:
        header[-1] = 'CDS_group\t'
        header.append('Class\n')

    # Write or append to the file
    with open(file_path, write_type) as report_file:
        # Write the header only if the file is being created
        if write_type == 'w':
            report_file.write("".join(header))
        # Write all the alignment data
        for results in blast_results_dict.values():
            for result in results.values():
                for r in result.values():
                    report_file.write('\t'.join(map(str, r.values())) + '\n')

def add_items_to_results(representative_blast_results, reps_kmers_sim, bsr_values,
                         representative_blast_results_coords_all,
                         representative_blast_results_coords_pident,
                         frequency_in_genomes, allele_ids, add_groups_ids):
    """
    Enhances BLAST results with additional metrics and frequencies.

    This function enriches the given BLAST results dictionary with several key metrics and frequencies
    to provide a more comprehensive analysis of the BLAST hits. It adds metrics such as Blast
    Score Ratio (BSR), k-mer similarities and coverage, and frequencies of query and subject CDS in
    schema genomes. It also includes global and local pairwise alignment scores, both in terms of
    coverage and percentage identity, with the ability to focus on specific percentage identity thresholds.

                                  
    Parameters
    ----------                                  
    representative_blast_results : dict
        A dictionary containing BLAST results. Each entry is expected to represent a unique BLAST hit with
        various metrics.
    reps_kmers_sim : dict
        A dictionary mapping pairs of CDS to their k-mer similarity scores.
    bsr_values : dict
        A dictionary mapping pairs of CDS to their Blast Score Ratio (BSR) values. Can be None if BSR values
        are not available.
    representative_blast_results_coords_all : dict
        A dictionary containing the coordinates for all BLAST entries, used for calculating global alignment metrics.
    representative_blast_results_coords_pident : dict
        A dictionary containing the coordinates for BLAST entries above a certain percentage identity threshold,
        used for calculating specific global alignment metrics.
    frequency_in_genomes : dict
        A dictionary summarizing the frequency of each representative cluster within the genomes of the schema,
        enhancing the context of BLAST results.
    allele_ids : list
        Indicates whether the IDs of loci representatives are included in the `frequency_in_genomes`. If true,
        IDs follow the format `loci1_x`.
    add_groups_ids : Dict, optional
        A dictionary mapping group IDs to their member CDS. This is used to add group information to the BLAST
        results for enhanced analysis.

    Returns
    -------
    No returns, modifies the representative_blast_results dict inside the main
    function.

    Notes
    -----
    - The function is designed to work with detailed BLAST results and requires several pre-computed metrics
    and frequencies as input.
    - It is crucial for enhancing the analysis of BLAST results, especially in comparative genomics and
    schema development projects.
    """
    def get_kmer_values(reps_kmers_sim, query, subject):
        """
        Retrieves k-mer similarity and coverage values for a specified query and subject pair.

        This function looks up the k-mer similarity and coverage values between a query and a
        subject sequence from a precomputed dictionary. It is designed to facilitate the analysis
        of genomic sequences by providing key metrics that reflect the degree of similarity and the
        extent of coverage between pairs of sequences. These metrics are crucial for understanding
        the genetic relationships and variations among sequences.

        Parameters
        ----------
        reps_kmers_sim : dict
            A dictionary where keys are query sequence IDs and values are dictionaries with subject
            sequence IDs as keys. Each inner dictionary's values are tuples containing the k-mer
            similarity and coverage values.
        query : str
            The identifier for the query sequence. This is used to look up the corresponding dictionary
            of subjects within `reps_kmers_sim`.
        subject : str
            The identifier for the subject sequence. This is used to retrieve the similarity and coverage
            values from the dictionary associated with the `query`.

        Returns
        -------
        sim : float or str
            The k-mer similarity value between the query and subject sequences. Returns 0 if no value is
            found, or '-' if the `reps_kmers_sim` dictionary is empty or not provided.
        cov : float or str
            The coverage value indicating the extent to which the k-mers of the query sequence are present
            in the subject sequence. Returns 0 if no value is found, or '-' if the `reps_kmers_sim` dictionary
            is empty or not provided.

        Notes
        -----
        - The function is robust to missing data, providing default values when specific similarity or coverage values
        are unavailable.
        - It is a utility function primarily used in genomic analysis workflows, particularly in the context of
        comparing sequences for similarity and coverage using k-mer based metrics.
        """
        if reps_kmers_sim:
            if subject in reps_kmers_sim[query]:
                sim, cov = reps_kmers_sim[query][subject]
            else:
                sim = 0
                cov = 0
        else:
            sim = '-'
            cov = '-'
        return sim, cov

    def get_bsr_value(bsr_values, query, subject):
        """
        Fetches the BLAST Score Ratio (BSR) for a specified pair of sequences.

        This function extracts the BSR value for a given pair of sequences identified by their respective
        query and subject IDs from a pre-populated dictionary. The BSR is a normalized metric used to
        compare the BLAST scores of different alignments, providing insight into the relative similarity
        between sequences. If the BSR exceeds 1.0, it is rounded to the nearest whole number to maintain
        consistency in reporting.

        Parameters
        ----------
        bsr_values : dict
            A dictionary where keys are query sequence IDs and values are dictionaries with subject sequence
            IDs as keys. Each inner dictionary's values are the BSR values.
        query : str
            The identifier for the query sequence. This is used to select the appropriate dictionary of subject
            sequences within `bsr_values`.
        subject : str
            The identifier for the subject sequence. This is used to retrieve the BSR value from the dictionary
            associated with the `query`.

        Returns
        -------
        bsr : float
            The BSR value between the query and subject sequences. Returns 0 if no BSR value is found for the
            given pair. If the BSR value is greater than 1, it is rounded to the nearest whole number. The BSR
            value is rounded by 4 decimal places for consistency.

        Notes
        -----add_items_to_results
        - The BSR value is a crucial metric in bioinformatics for assessing the quality of sequence alignments, with values typically ranging from 0 to 1. Values greater than 1 are considered anomalies and are adjusted accordingly.
        - This function is essential for workflows involving comparative genomics or sequence alignment analysis, where BSR values provide a standardized measure of sequence similarity.
        """
        bsr = bsr_values[query].get(subject, 0)
        if bsr > 1.0:
            bsr = float(round(bsr))
        return round(bsr, 4)

    def calculate_total_length(representative_blast_results_coords, query, subject):
        """
        Calculates the total aligned length for each reference sequence in a given query-subject pair.

        This function computes the total length of aligned sequences for each reference sequence associated
        with a specific query-subject pair. It processes the alignment intervals for each reference sequence,
        merges overlapping intervals to avoid double counting, and sums up the lengths of these intervals to
        determine the total aligned length.

        Parameters
        ----------
        representative_blast_results_coords : dict
            A nested dictionary where the first level keys are query sequence IDs, the second level keys are
            subject sequence IDs, and the values are dictionaries mapping reference sequence IDs to lists of
            alignment intervals.
        query : str
            The identifier for the query sequence. This is used to select the appropriate dictionary of subject
            sequences within `representative_blast_results_coords`.
        subject : str
            The identifier for the subject sequence. This is used to retrieve the dictionary of reference sequences
            and their alignment intervals.

        Returns
        -------
        total_length : dict
            A dictionary where keys are reference sequence IDs and values are the total aligned length for that
            reference sequence. The total aligned length is calculated by merging overlapping intervals and
            summing the lengths of the resulting intervals.

        Notes
        -----
        - The function assumes that alignment intervals are provided as tuples or lists of two elements, where the
        first element is the start position and the second element is the end position of the interval.
        - Overlapping intervals for each reference sequence are merged to ensure that the total aligned length is
        accurately calculated without double counting overlapping regions.
        - This function is particularly useful in genomic analyses where understanding the extent of alignment
        coverage is important for interpreting BLAST results.
        """
        total_length = {}
        for ref, intervals in representative_blast_results_coords[query][subject].items():
            if intervals:
                sorted_intervals = sorted(intervals, key=lambda x: x[0])
                length = sum(interval[1] - interval[0] + 1 for interval in af.merge_intervals(sorted_intervals))
                total_length[ref] = length
            else:
                total_length[ref] = 0
        return total_length

    def calculate_global_palign(total_length, result):
        """
        Calculates the minimum and maximum global pairwise alignment percentages.

        This function computes the global pairwise alignment (palign) percentages for a query and its subject
        based on their total aligned lengths and original lengths. It calculates both the minimum and maximum
        palign values to provide a range of alignment coverage, which can be useful for assessing the quality
        and extent of the alignment between the query and subject sequences.

        Parameters
        ----------
        total_length : dict
            A dictionary where keys are 'query' and 'subject', and values are the total aligned lengths for the
            query and subject sequences, respectively.
        result : dict
            A dictionary containing the lengths of the query and subject sequences under the keys 'query_length'
            and 'subject_length'.

        Returns
        -------
        global_palign_min : float
            The minimum global pairwise alignment percentage, calculated as the smaller of the two ratios: total
            aligned length of the query to its original length, and total aligned length of the subject to its
            original length. The value is rounded to 4 decimal places.
        global_palign_max : float
            The maximum global pairwise alignment percentage, calculated as the larger of the two ratios: total
            aligned length of the query to its original length, and total aligned length of the subject to its
            original length. The value is rounded to 4 decimal places.

        Notes
        -----
        - The global pairwise alignment percentage is a measure of how much of the original sequences
        (query and subject) are covered by the alignment. It provides insight into the completeness of the alignment.
        - This function is particularly useful in bioinformatics for evaluating the quality of sequence alignments,
        where higher coverage percentages might indicate more reliable alignments.
        """
        global_palign_min = min(total_length['query'] / result['query_length'],
                                total_length['subject'] / result['subject_length'])
        global_palign_max = max(total_length['query'] / result['query_length'],
                                total_length['subject'] / result['subject_length'])
        return round(global_palign_min, 4), round(global_palign_max, 4)

    def calculate_local_palign(result):
        """
        Calculates the minimum local pairwise alignment percentage.

        This function computes the local pairwise alignment (palign) percentage for a given BLAST search result
        by comparing the aligned lengths of the query and subject sequences to their total lengths. It calculates
        the alignment percentage for both the query and subject, and returns the minimum of these two percentages.
        This metric is useful for assessing the extent of alignment within the local regions of interest in both 
        sequences.

        Parameters
        ----------
        result : dict
            A dictionary containing the result of a BLAST search, including the start and end positions of the alignment
            on both the query and subject sequences, as well as their total lengths.

        Returns
        -------
        local_palign_min : float
            The minimum local pairwise alignment percentage, calculated as the smaller of the two ratios: aligned
            length of the query to its total length, and aligned length of the subject to its total length. The value
            is rounded to 4 decimal places.

        Notes
        -----
        - The local pairwise alignment percentage provides insight into the local similarity between the query and
        subject sequences, focusing on the aligned regions.
        - This function is particularly useful in sequence alignment analyses, where understanding the coverage and
        similarity of local alignments is important.
        """
        local_palign_min = min((result['query_end'] - result['query_start'] + 1) / result['query_length'],
                            (result['subject_end'] - result['subject_start'] + 1) / result['subject_length'])
        return round(local_palign_min, 4)

    def update_results(representative_blast_results, query, subject, entry_id, bsr, sim, cov, frequency_in_genomes,
                       global_palign_all_min, global_palign_all_max, global_palign_pident_min, global_palign_pident_max,
                       local_palign_min, allele_ids, add_groups_ids):
        """
        Updates the BLAST results for a specific query and subject pair with new data.

        This function modifies the existing BLAST results dictionary by updating the entries for a given query and
        subject pair with new information. It handles the addition of various metrics such as BSR, similarity,
        coverage, frequency in genomes, global and local pairwise alignment percentages, and group IDs. The function
        also supports the modification of query and subject IDs based on loci information.

        Parameters
        ----------
        representative_blast_results : dict
            A dictionary containing BLAST results where keys are query IDs, values are dictionaries with subject
            IDs as keys, and each subject dictionary contains dictionaries of entry IDs with their respective data.
        query : str
            The query sequence ID.
        subject : str
            The subject sequence ID.
        entry_id : str
            The ID of the entry to update within the BLAST results.
        bsr, sim, cov : float
            The BSR, similarity, and coverage values to update.
        frequency_in_genomes : dict
            A dictionary containing the frequency of the query and subject in genomes.
        global_palign_all_min, global_palign_all_max, global_palign_pident_min, global_palign_pident_max : float
            The minimum and maximum global pairwise alignment percentages, including those based on Pident threshold.
        local_palign_min : float
            The minimum local pairwise alignment percentage.
        allele_ids : list
            A list indicating whether to modify the query and/or subject IDs based on loci information.
        add_groups_ids : dict
            A dictionary containing group IDs to be added to the results, where keys are subject IDs and values
            are the group members.

        Returns
        -------
        None
            This function does not return any value but modifies the `representative_blast_results` dictionary in place.

        Notes
        -----
        - The function assumes the presence of a utility module `itf` with functions for ID manipulation and
        identification within dictionaries.
        - It is designed to be flexible, allowing for the update of specific metrics as needed without requiring
        a complete overhaul of the entry data.
        """
        if allele_ids[0]:
            query_before = query
            query = itf.remove_by_regex(query, '_(\d+)')
        if allele_ids[1]:
            subject_before = subject
            subject = itf.remove_by_regex(subject, '_(\d+)')
        update_dict = {
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

        if add_groups_ids:
            id_ = itf.identify_string_in_dict_get_key(subject, add_groups_ids) or subject
            update_dict = {'cds_group': id_}
            representative_blast_results[query][subject][entry_id].update(update_dict)

    def remove_results(representative_blast_results, query, subject, entry_id):
        """
        Removes a specific entry from the BLAST results for a given query and subject pair.

        This function is designed to modify an existing dictionary of BLAST results by removing a specified
        entry identified by its entry ID for a particular query and subject pair. It directly alters the
        `representative_blast_results` dictionary, removing the entry corresponding to the provided `entry_id`
        within the nested structure of query and subject IDs.

        Parameters
        ----------
        representative_blast_results : dict
            A dictionary containing BLAST results, structured with query IDs as keys, each mapping to a dictionary
            of subject IDs, which in turn map to dictionaries of entry IDs and their associated data.
        query : str
            The identifier for the query sequence, used to locate the correct subset of results within
            `representative_blast_results`.
        subject : str
            The identifier for the subject sequence, used in conjunction with `query` to further narrow down the
            specific subset of results.
        entry_id : str
            The identifier of the specific entry to be removed from the results.

        Returns
        -------
        None
            This function does not return any value. It modifies the `representative_blast_results` dictionary in
            place, removing the specified entry.

        Notes
        -----
        - This function is useful for cleaning up BLAST results, allowing for the removal of specific entries that are
        no longer needed or relevant.
        - It operates directly on the provided dictionary, requiring careful handling to avoid unintended modifications.
        """
        del representative_blast_results[query][subject][entry_id]

    def clean_up_results(representative_blast_results, query, subject):
        """
        Cleans up BLAST results for a specific query and subject by removing empty entries.

        This function is designed to modify an existing dictionary of BLAST results by checking for and
        removing any entries that are empty for a given query and subject pair. It aims to streamline the BLAST
        results by ensuring that only entries with data are retained. The function operates directly on the
        `representative_blast_results` dictionary, removing entries without returning any value.

        Parameters
        ----------
        representative_blast_results : dict
            A dictionary containing BLAST results, where keys are query IDs, and values are dictionaries with
            subject IDs as keys, each mapping to their respective result entries.
        query : str
            The identifier for the query sequence, used to locate the correct subset of results within
            `representative_blast_results`.
        subject : str
            The identifier for the subject sequence, used in conjunction with `query` to further narrow down the
            specific subset of results to be cleaned.
        
        Returns
        -------
        None
            This function does not return any value. It modifies the `representative_blast_results` dictionary in
            place, removing the specified entry.

        Notes
        -----
        - The function checks for and removes entries that are empty for the specified query and subject. If the
        subject entry under a query is empty, it is removed. If this results in the query entry becoming empty,
        it is also removed.
        - This cleanup process is essential for maintaining the integrity and usability of BLAST results, especially
        in large-scale genomic analyses where empty entries can clutter the dataset.
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
                    update_results(representative_blast_results, query, subject, entry_id, bsr, sim, cov, frequency_in_genomes, global_palign_all_min, global_palign_all_max, global_palign_pident_min, global_palign_pident_max, local_palign_min, allele_ids, add_groups_ids)
                else:
                    remove_results(representative_blast_results, query, subject, entry_id)

            clean_up_results(representative_blast_results, query, subject)

def separate_blastn_results_into_classes(representative_blast_results, constants):
    """
    Separates BLAST results into predefined classes based on specific criteria.

    This function iterates through BLAST results and classifies each result into a specific class
    based on criteria such as global alignment percentage, bit score ratio (bsr), and frequency ratios
    between query and subject CDS in genomes. The classification is done by updating the results
    dictionary with a new key-value pair indicating the class of each BLAST result.

    Parameters
    ----------
    representative_blast_results : dict
        A nested dictionary where the first level keys are query sequence IDs, the second level keys
        are subject sequence IDs, and the third level keys are unique identifiers for each BLAST
        result. Each BLAST result is a dictionary containing keys such as 'frequency_in_genomes_query_cds',
        'frequency_in_genomes_subject_cds', 'global_palign_all_min', 'bsr', and 'pident'.
    constants : tuple or list
        A collection of constants used in the classification criteria. Specifically, `constants[1]`
        is used as a threshold for the percentage identity (pident) in one of the classification conditions.

    Returns
    -------
    classes_outcome : tuple
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
    def add_class_to_dict(class_name):
        """
        Adds a class identifier to a BLAST result within the representative_blast_results dictionary.

        This helper function is used to update the BLASTNresult dictionaries with a 'class' key,
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
        - It is designed to be used only within the `separate_blastn_results_into_classes` function.
        """
        representative_blast_results[query][id_subject][id_].update({'class': class_name})

    # Define classes based on priority
    classes_outcome = ('1a', '1b', '2a', '3a', '2b', '1c', '3b', '4a', '4b', '4c','5')

    # Loop through the representative BLAST results
    for query, rep_blast_result in representative_blast_results.items():
        for id_subject, matches in rep_blast_result.items():
            for id_, blastn_entry in matches.items():
                # Calculate the frequency ratio
                query_freq = blastn_entry['frequency_in_genomes_query_cds']
                subject_freq = blastn_entry['frequency_in_genomes_subject_cds']
                # If one of the frequencies is 0, set the ratio to 0.1 if the other frequency is 10 times greater
                if query_freq == 0 or subject_freq == 0:
                    freq_ratio = 0.1 if query_freq > 10 or subject_freq > 10 else 1
                else:
                    freq_ratio = min(query_freq/subject_freq,
                                    subject_freq/query_freq)
                
                # Classify based on global_palign_all_min and bsr
                if blastn_entry['global_palign_all_min'] >= 0.8:
                    if blastn_entry['bsr'] >= constants[7]:
                        # Add to class '1a' if bsr is greater than or equal to bsr value
                        add_class_to_dict('1a')
                    elif freq_ratio <= 0.1:
                        # Add to class '1b' if frequency ratio is less than or equal to 0.1
                        add_class_to_dict('1b')
                    else:
                        # Add to class '1c' if none of the above conditions are met
                        add_class_to_dict('1c')
                elif 0.4 <= blastn_entry['global_palign_all_min'] < 0.8:
                    if blastn_entry['pident'] >= constants[1]:
                        if blastn_entry['global_palign_pident_max'] >= 0.8:
                            # Add to class '2a' or '2b' based on frequency ratio
                            add_class_to_dict('2a' if freq_ratio <= 0.1 else '2b')
                        else:
                            # Add to class '3a' or '3b' based on frequency ratio
                            add_class_to_dict('3a' if freq_ratio <= 0.1 else '3b')
                    else:
                        if blastn_entry['global_palign_pident_max'] >= 0.8:
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

def process_classes(representative_blast_results, classes_outcome, all_alleles = None):
    """
    Processes BLAST results to determine class-based relationships and counts.

    This function iterates through representative BLAST results to establish relationships
    between different coding sequences (CDS) and to count occurrences by class. It handles
    allele replacements, prioritizes classes based on a predefined order, and identifies
    important relationships between sequences.

    Parameters
    ----------
    representative_blast_results : dict
        A nested dictionary where the first key is the query sequence ID, the second key is
        the subject sequence ID, and the value is another dictionary containing match details
        including the class of the match.
    classes_outcome : tuple
        A list of class identifiers ordered by priority. This order determines which classes are
        considered more significant when multiple matches for the same pair of sequences are found.
    all_alleles : dict, optional
        A dictionary mapping sequence IDs to their corresponding allele names. If provided, it is
        used to replace allele IDs with loci/CDS names in the processing.

    Returns
    -------
    processed_results : dict
        A dictionary containing processed results with keys formatted as "query|subject" and values being tuples
        containing information about the processed sequences, their class, relationships, and additional details.
    count_results_by_class : dict
        A dictionary containing counts of results by class, with keys formatted as "query|subject" and values being
        dictionaries with class identifiers as keys and counts as values.
    count_results_by_class_with_inverse : dict
        A dictionary containing counts of results by class, including inverse matches, with keys formatted as
        "query|subject" and values being dictionaries with class identifiers as keys and counts as values.
    reps_and_alleles_ids : dict
        A dictionary mapping pairs of query and subject sequences to their unique loci/CDS IDs and alleles IDs.

    Notes
    -----
    - The function dynamically adjusts based on the presence of `all_alleles`, affecting how sequence IDs
    are replaced and processed.
    - It employs a complex logic to handle different scenarios based on class types and the presence or absence of
    alleles in the processed results, including handling allele replacements and determining the importance of
    relationships.
    """
    # Initialize variables
    count_results_by_class = {}
    count_results_by_class_with_inverse = {}
    reps_and_alleles_ids = {}
    processed_results = {}
    drop_mark = []
    inverse_match = []
    # Process the CDS to find what CDS to retain while also adding the relationships between different CDS
    for query, rep_blast_result in representative_blast_results.items():
        for id_subject, matches in rep_blast_result.items():
            class_ = matches[1]['class'] 
            ids_for_relationship = [query, id_subject]
            new_query = query
            new_id_subject = id_subject

            strings = [str(query), str(id_subject), class_]
            if all_alleles:
                replaced_query = itf.identify_string_in_dict_get_key(query, all_alleles)
                if replaced_query:
                    new_query = replaced_query
                    strings[0] = new_query
                replaced_id_subject = itf.identify_string_in_dict_get_key(id_subject, all_alleles)
                if replaced_id_subject:
                    new_id_subject = replaced_id_subject
                    strings[1] = new_id_subject

                current_allele_class_index = classes_outcome.index(class_)
                # Check if the current loci were already processed
                if not processed_results.get(f"{new_query}|{new_id_subject}"):
                    run_next_step = True
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
            reps_and_alleles_ids.setdefault(f"{new_query}|{new_id_subject}", [set(), set()])
            if ids_for_relationship[0] not in reps_and_alleles_ids[f"{new_query}|{new_id_subject}"][0]:
                reps_and_alleles_ids[f"{new_query}|{new_id_subject}"][0].add(ids_for_relationship[0])
            if ids_for_relationship[1] not in reps_and_alleles_ids[f"{new_query}|{new_id_subject}"][1]:
                reps_and_alleles_ids[f"{new_query}|{new_id_subject}"][1].add(ids_for_relationship[1])
    
            if run_next_step:
                # Set all None to run newly for this query/subject combination
                processed_results[f"{new_query}|{new_id_subject}"] = (None,
                                                        None,
                                                        None,
                                                        None,
                                                        None,
                                                        None)

                if class_ in ['1b', '2a', '3a']:
                    blastn_entry = matches[list(matches.keys())[0]]
                    # Determine if the frequency of the query is greater than the subject.
                    is_frequency_greater = blastn_entry['frequency_in_genomes_query_cds'] >= blastn_entry['frequency_in_genomes_subject_cds']
                    # Determine if the query or subject should be dropped.
                    query_or_subject = new_id_subject if is_frequency_greater else new_query
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
                        dropped = new_id_subject if is_frequency_greater else new_query
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

    return processed_results, count_results_by_class, count_results_by_class_with_inverse, reps_and_alleles_ids, drop_mark

def extract_results(processed_results, count_results_by_class, frequency_in_genomes,
                    cds_to_keep, drop_set, classes_outcome):
    """
    Extracts and organizes results from process_classes.

    Parameters
    ----------
    processed_results : dict
        The processed results data.
    count_results_by_class : dict
        A dictionary with counts of results by class.
    frequency_in_genomes : dict
        A dictionary containing the frequency of the query and subject in genomes.
    classes_outcome : list
        A list of class outcomes.process_id

    Returns
    -------
    all_relationships : dict
        All relationships between loci and CDS.
    related_clusters : dict
        Dict that groups CDS/loci by ID and that contains strings to write in output file.
    
    Notes
    -----
    - The function iterates over `processed_results` to organize and cluster related CDS/loci based
    on their classification outcomes and the presence in specific clusters.
    - It uses helper functions like `cf.cluster_by_ids` for clustering and `itf.identify_string_in_dict_get_key`
    for identifying if a query or subject ID is present in the clusters.
    """
    def cluster_data(processed_results):
        """
        Cluster data based on a specific key extracted from the processed results.

        Parameters
        ----------
        processed_results : dict
            A dictionary containing the processed results to be clustered.

        Returns
        -------
        return : dict
            A dictionary where each key is an integer starting from 1, and each value is a cluster of data
            based on the extracted key, excluding entries with specific identifiers.
        """
        key_extractor = lambda v: v[3]
        condition = lambda v: v[0] not in ['4c', '5']

        return {i: cluster for i, cluster in enumerate(cf.cluster_by_ids([key_extractor(v) for v in processed_results.values() if condition(v)]), 1)}

    def choice_data(processed_results, to_cluster_list):
        """
        Select and cluster data based on specific conditions and a list of identifiers to cluster.

        Parameters
        ----------
        processed_results : dict
            A dictionary containing the processed results to be selected and clustered.
        to_cluster_list : list
            A list of identifiers indicating which entries should be considered for clustering.

        Returns
        -------
        return : dict
            A dictionary where each key is an integer starting from 1, and each value is a cluster of data
            selected based on the given conditions and the to_cluster_list.
        """
        key_extractor = lambda v: v[3]
        additional_condition = lambda v: '*' in v[4][0] or '*' in v[4][1]
        return {i: cluster for i, cluster in enumerate(cf.cluster_by_ids([key_extractor(v) for v in processed_results.values() if v[0] not in ['1a','4c','5'] or ((itf.identify_string_in_dict_get_key(v[3][0], to_cluster_list) and additional_condition(v)) or (itf.identify_string_in_dict_get_key(v[3][1], to_cluster_list) and additional_condition(v)))]), 1)}
    
    def process_id(id_, to_cluster_list, cds_to_keep):
        """
        Process an identifier to check its presence in specific lists.

        Parameters
        ----------
        id_ : str
            The identifier to be processed.
        to_cluster_list : list
            A list of identifiers to check for the presence of id_.
        cds_to_keep : dict
            A dictionary containing identifiers to check for a joined condition.

        Returns
        -------
        return : tuple
            A tuple containing the original id, a boolean indicating if the id is present in the to_cluster_list,
            and a boolean indicating if the id is present in the cds_to_keep under a specific key.
        """
        present = itf.identify_string_in_dict_get_key(id_, to_cluster_list)
        joined_id = itf.identify_string_in_dict_get_key(id_, cds_to_keep['1a'])
        return id_, present, joined_id

    def check_in_recommendations(id_, joined_id, recommendations, key, categories):
        """
        Check if an identifier or its joined form is present in a set of recommendations.

        Parameters
        ----------
        id_ : str
            The original identifier to check.
        joined_id : str
            The joined form of the identifier to check.
        recommendations : dict
            A dictionary of recommendations to search within.
        key : str
            The key within the recommendations to search under.
        categories : list
            A list of categories to consider when searching in the recommendations.

        Returns
        -------
        return : bool
            True if the identifier or its joined form is present in the recommendations under the specified categories,
            False otherwise.
        """
        return any((joined_id or id_) in itf.flatten_list([v for k, v in recommendations[key].items() if cat in k]) for cat in categories)


    def add_to_recommendations(category, id_to_write, joined_id=None):
        """
        Add an identifier to the recommendations under a specific category.

        Parameters
        ----------
        category : str
            The category under which to add the identifier.
        id_to_write : str
            The identifier to add to the recommendations.
        joined_id : str, optional
            The joined form of the identifier, if applicable. Default is None.

        Returns
        -------
        None
            This function does not return any value but modifies the `recommendations` dictionary in place.
        """
        if joined_id is not None:  # For joined or choice categories
            recommendations[key].setdefault(f'{category}_{joined_id}', set()).add(id_to_write)
        else:  # For keep or drop categories
            recommendations[key].setdefault(category, set()).add(id_to_write)

    all_relationships = {class_: [] for class_ in classes_outcome} # All relationships between loci and CDS
    related_clusters = {} # To keep track of the related clusters
    recommendations = {} # To keep track of the recommendations
    dropped_match = {} # To keep track of the dropped matches
    matched_with_dropped = {} # To keep track of the matches that matched with dropped
    processed_cases = [] # To keep track of the processed cases
    # Normal run, where IDs are only loci or CDS original IDs.
    to_cluster_list = cluster_data(processed_results) # All of the cluster of related CDS/loci by ID.
    choice = choice_data(processed_results, to_cluster_list) # All of the possible cases of choice.

    related_clusters = {}
    for results in processed_results.values():
        if results[0] in ['4c','5', 'Retained_not_matched_by_blastn']:
            continue

        query_id, query_present, joined_query_id = process_id(results[3][0], to_cluster_list, cds_to_keep)
        subject_id, subject_present, joined_subject_id = process_id(results[3][1], to_cluster_list, cds_to_keep)

        key = query_present if query_present else subject_present

        related_clusters.setdefault(key, []).append(results[4] 
                                                    + [f"{count_results_by_class[f'{results[3][0]}|{results[3][1]}'][results[0]]}/{sum(count_results_by_class[f'{results[3][0]}|{results[3][1]}'].values())}"]
                                                    + [str(frequency_in_genomes[results[3][0]])]
                                                    + [str(frequency_in_genomes[results[3][1]])])

        recommendations.setdefault(key, {})
        if_same_joined = (joined_query_id == joined_subject_id) if joined_query_id and joined_subject_id else False
        if_joined_query = check_in_recommendations(query_id, joined_query_id, recommendations, key, ['Joined'])
        if_joined_subject = check_in_recommendations(subject_id, joined_subject_id, recommendations, key, ['Joined'])
        if_query_in_choice = check_in_recommendations(query_id, joined_query_id, recommendations, key, ['Choice'])
        if_subject_in_choice = check_in_recommendations(subject_id, joined_subject_id, recommendations, key, ['Choice'])
    
        if_query_dropped = (joined_query_id or query_id) in drop_set
        if_subject_dropped = (joined_subject_id or subject_id) in drop_set

        choice_query_id = itf.identify_string_in_dict_get_key(query_id, choice)
        choice_subject_id = itf.identify_string_in_dict_get_key(subject_id, choice)

        # What IDs to addto the Keep, Drop and Choice.
        query_to_write = joined_query_id or query_id
        subject_to_write = joined_subject_id or subject_id
        
        query_to_write = query_to_write
        subject_to_write = subject_to_write

        joined_query_to_write = query_id
        joined_subject_to_write = subject_id

        # Check if the pair was not processed yet
        if [query_id, subject_id] not in processed_cases:
            processed_cases.append([subject_id, query_id])  # Add the inverse pair to the processed cases
            reverse_id = f"{subject_id}|{query_id}"
            reverse_results = processed_results[reverse_id] if processed_results.get(reverse_id) else None
            if reverse_results and classes_outcome.index(results[0]) > classes_outcome.index(reverse_results[0]):
                results = reverse_results

            if results[0] == '1a':
                if joined_query_id is not None:
                    add_to_recommendations('Joined', joined_query_to_write, joined_query_id)
                if joined_subject_id is not None:
                    add_to_recommendations('Joined', joined_subject_to_write, joined_subject_id)

            elif results[0] in ['1c', '2b', '3b', '4b']:
                if not if_query_dropped and not if_subject_dropped and not if_same_joined:
                    add_to_recommendations('Choice', query_to_write, choice_query_id)
                    add_to_recommendations('Choice', subject_to_write, choice_subject_id)
                elif if_query_dropped:
                    add_to_recommendations('Choice', subject_to_write, choice_subject_id)
                    matched_with_dropped.setdefault(key, []).append([query_to_write, subject_to_write, query_to_write, choice_query_id])
                elif if_subject_dropped:
                    add_to_recommendations('Choice', query_to_write, choice_query_id)
                    matched_with_dropped.setdefault(key, []).append([query_to_write, subject_to_write, subject_to_write, choice_query_id])
            elif results[0] in ['1b', '2a', '3a', '4a']:
                if (joined_query_id and '*' in results[4][0]) or (joined_subject_id and '*' in results[4][1]):
                    add_to_recommendations('Choice', query_to_write, choice_query_id)
                    add_to_recommendations('Choice', subject_to_write, choice_subject_id)
                if query_id in drop_set:
                    if not if_joined_query and not if_query_in_choice:
                        add_to_recommendations('Drop', query_to_write)
                        dropped_match.setdefault(key, []).append([query_to_write, subject_to_write, subject_to_write])

                elif subject_id in drop_set:
                    if not if_joined_subject and not if_subject_in_choice:
                        add_to_recommendations('Drop', subject_to_write)
                        dropped_match.setdefault(key, []).append([subject_to_write, query_to_write, query_to_write])
    # Add cases where some ID matched with dropped ID, we need to add the ID that matched with the ID that made the other match
    # to be Dropped. e.g x and y matched with x dropping and x also matched with z, then we need to make a choice between x and z.
    for key, matches in matched_with_dropped.items():
        if dropped_match.get(key):
            for dropped in dropped_match[key]:
                for match_ in  matches:
                    if match_[2] in dropped:
                        add_to_recommendations('Choice', dropped[2], match_[3])
            

    for k, v in processed_results.items():
        all_relationships.setdefault(v[0], []).append(v[1])

    sort_order = ['Joined', 'Choice', 'Keep', 'Drop']
    recommendations = {k: {l[0]: l[1] for l in sorted(v.items(), key=lambda x: sort_order.index(x[0].split('_')[0]))} for k, v in recommendations.items()}
    
    return all_relationships, related_clusters, recommendations

def write_blast_summary_results(related_clusters, count_results_by_class, group_reps_ids, group_alleles_ids,
                                frequency_in_genomes, recommendations, reverse_matches, results_output):
    """
    Writes summary results of BLAST analysis to TSV files.

    This function generates two files: 'related_matches.tsv' and 'count_results_by_cluster.tsv'.
    The 'related_matches.tsv' file contains information about related clusters, while
    'count_results_by_cluster.tsv' details the count of results by cluster and class, including a total count.

    Parameters
    ----------
    related_clusters : dict
        A dictionary where each key is a cluster identifier and each value is a list of tuples.
        Each tuple represents a related match with its details.
    count_results_by_class : dict
        A dictionary where each key is a clusters identifiers separate by '|' and each value is another dictionary.
        The inner dictionary's keys are class identifiers, and values are counts of results for that class.
    reps_and_alleles_ids : dict
        A dictionary mapping pairs of query and subject sequences to their unique loci/CDS IDs and alleles IDs.
    frequency_in_genomes : dict
        A dictionary mapping sequence identifiers to their frequency in genomes.
    recommendations : dict
        A dictionary containing recommendations for each cluster based on the classification of the results.
    reverse_matches : bool
        A flag indicating whether there are reverse matches
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
    related_matches = os.path.join(results_output, "related_matches.tsv")
    reported_cases = {}
    for key, related in list(related_clusters.items()):
        for index, r in enumerate(list(related)):
            if reverse_matches:
                r.insert(4, '-')
                r.insert(5, '-')
            [query, subject] = [itf.remove_by_regex(i, r"\*") for i in r[:2]]
            if (query, subject) not in itf.flatten_list(reported_cases.values()):
                reported_cases.setdefault(key, []).append((subject, query))
            elif reverse_matches:
                sublist_index = itf.find_sublist_index([[itf.remove_by_regex(i, r"\*") for i in l[:2]] for l in related_clusters[key]], [subject, query])
                insert = r[2] if not None else '-'
                related[sublist_index][4] = insert
                insert = r[3] if not None else '-'
                related[sublist_index][5] = insert
                related.remove(r)
        
        for index, i in enumerate(recommendations[key]):
            related_clusters[key][index] += ([itf.flatten_list([[k] + [i for i in v]]) for k , v in recommendations[key].items()][index])


    with open(related_matches, 'w') as related_matches_file:
        related_matches_file.write("Query\tSubject\tClass\tClass_count" +
                                    ("\tInverse_class\tInverse_class_count" if reverse_matches else "") +
                                    "\tFrequency_in_genomes_query\tFrequency_in_genomes_subject\n")
        for related in related_clusters.values():
            for r in related:
                related_matches_file.write('\t'.join(str(item) for item in r) + '\n')

            related_matches_file.write('#\n')

    count_results_by_cluster = os.path.join(results_output, "count_results_by_cluster.tsv")
    with open(count_results_by_cluster, 'w') as count_results_by_cluster_file:
        count_results_by_cluster_file.write("Query\tSubject\tClass\tClass_count\tInverse_class_count"
                                            "\tRepresentatives_count"
                                            "\tAlelles_count\tFrequency_in_genomes_query"
                                            "\tFrequency_in_genomes_subject\n")
        for id_, classes in count_results_by_class.items():
            query, subject = id_.split('|')
            count_results_by_cluster_file.write('\t'.join(id_.split('|')))
            total_count_origin = sum([i[0] for i in classes.values() if i[0] != '-'])
            total_count_inverse = sum([i[1] for i in classes.values() if i[1] != '-'])
            query = itf.try_convert_to_type(id_.split('|')[0], int)
            subject = itf.try_convert_to_type(id_.split('|')[1], int)

            for i, items in enumerate(classes.items()):
                if i == 0:
                    count_results_by_cluster_file.write('\t'.join([f"\t{items[0]}",
                                                        f"{items[1][0]}/{total_count_origin}",
                                                        f"{items[1][1]}/{total_count_inverse}" if reverse_matches else "-",
                                                        (f"{len(group_reps_ids[query])}") + 
                                                        (f"|{len(group_reps_ids[subject])}" if reverse_matches else "|-"),
                                                        (f"{len(group_alleles_ids[query])}" if reverse_matches else "-") +
                                                        (f"|{len(group_alleles_ids[subject])}"),
                                                        f"{frequency_in_genomes[query]}",
                                                        f"{frequency_in_genomes[subject]}\n"]))
                else:
                    count_results_by_cluster_file.write('\t'.join([f"\t\t{items[0]}",
                                                        f"{items[1][0]}/{total_count_origin}",
                                                        f"{items[1][1]}/{total_count_inverse}" if reverse_matches else "-",
                                                        "\n"]))
            count_results_by_cluster_file.write('\n')

def get_matches(all_relationships, cds_to_keep, sorted_blast_dict):
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
    all_relationships : dict
        A dictionary containing all relationships between loci and alleles or CDS, with loci as keys
        and lists of related alleles or CDS as values.
    cds_to_keep : dict
        A dictionary with classes as keys and lists of CDS or loci IDs to be kept as values.
    sorted_blast_dict : dict
        A dictionary containing sorted BLAST results, used to identify loci that have matches.

    Returns
    -------
    is_matched : dict
        A dictionary with loci or CDS IDs as keys and sets of matched loci IDs as values, indicating
        successful matches.
    is_matched_alleles : dict or None
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
    is_matched = {}
    is_matched_alleles = {}

    relationships = itf.flatten_list(all_relationships.values())
    changed_ids = [[r[0], itf.remove_by_regex(r[1], '_(\d+)')] for r in relationships]
    had_matches = set([itf.remove_by_regex(rep, '_(\d+)') for rep in sorted_blast_dict])
    is_matched_alleles = {}
    for class_, entries in list(cds_to_keep.items()):
        for entry in list(entries):
            if entry not in had_matches and not class_ == '1a':
                id_ = entry
                entry = [entry]
                is_matched.setdefault(id_, set([i[0] for i in changed_ids if i[1] in entry]))
                is_matched_alleles.setdefault(id_, set([i[1] 
                                                        for i in relationships 
                                                        if i[0] in is_matched[id_] 
                                                        and itf.remove_by_regex(i[1], '_(\d+)') in entry]))
    return is_matched, is_matched_alleles

def wrap_up_blast_results(cds_to_keep, not_included_cds, clusters, output_path, 
                          constants, drop_set, loci, groups_paths_old, frequency_in_genomes,
                          run_type):
    """
    This function wraps up the results for processing of the unclassified CDSs
    by writing FASTAs files for the possible new loci to include.
    
    Parameters
    ----------
    cds_to_keep : dict
        Dict of the CDS to keep by each classification.
    not_included_cds : dict
        Dict that contains all of the DNA sequences for all of the CDS.
    clusters : dict
        Dict that contains the cluster representatives as keys and similar CDS
        as values.
    output_path : str
        Path to were write the FASTA files.
    constants : list
        Contains the constants to be used in this function.
    drop_set : set
        Contains the CDS IDs to be removed from further processing for appearing
        fewer time in genomes than their match.
    loci : dict
        Dict that contains the loci IDs and paths.
    groups_paths_old : dict
        The dictionary containing the old paths for the CDSs groups used 
        to cp instead of creating new FASTAs files.
    frequency_in_genomes : dict
        Dict that contains sum of frequency of that representatives cluster in the
        genomes of the schema.
    run_type : list
        What type of run to make.

    Returns
    -------
    groups_paths : dict
        Dict that contains as Key the ID of each group while the value is the
        path to the FASTA file that contains its nucleotide sequences.
    trans_dict_cds : dict
        Dict that contais the translations of all the CDSs inside the various
        groups.
    master_file_rep : str or None
        Path to the master file that contains all of the representative sequences.
    """
    def print_classification_results(class_, count, printout, i):
        """
        Prints the classification results based on the class type.

        Parameters
        ----------
        class_ : str
            The class type.
        count : int
            The count of groups.
        printout : dict
            The dictionary containing printout information.
        i : int
            An index used to determine the printout message.

        Returns
        -------
        None, prints in stdout
        """
        if count > 0:
            if class_ in ['2b', '4b']:
                print(f"\t\tOut of those groups, {count} {'CDSs' if i == 0 else 'loci'} are classified as {class_} and were retained"
                    " but it is recommended to verify them as they may be contained or contain partially inside"
                    " their BLAST match.")
            elif class_ == '1a':
                print(f"\t\tOut of those groups, {count} {'CDSs groups' if i == 0 else 'loci'} are classified as {class_}"
                    f" and are contained in {len(printout['1a'])} joined groups that were retained.")
            elif class_ == 'dropped':
                if run_type == 'loci_vs_loci':
                    print(f"\t\tOut of those {count} loci are recommended to be removed.")
                else:
                    print(f"\t\tOut of those {count} {'CDSs groups' if i== 0 else 'loci'}"
                        f" {'were removed from the analysis' if i == 0 else 'are recommended to be replaced with their matched CDS in the schema.'}")
            else:
                print(f"\t\tOut of those groups, {count} {'CDSs' if i == 0 else 'loci'} are classified as {class_} and were retained.")

    def write_ids_by_class(output_path, case_id, cases):
        """
        Create directories and write cases IDs to  to TSV.

        Parameters
        ----------
        output_path : str
            The path where the output will be written.
        case_id : int
            The ID of the case.
        cases : dict
            The dictionary containing the cases.

        Returns
        -------
        None, writes to TSV file.
        """
        id_folder = os.path.join(output_path, 'results_IDs')
        ff.create_directory(id_folder)
        id_report_path = os.path.join(id_folder, f"{'CDS_Results' if case_id == 0 else 'Loci_Results'}.tsv")
        ff.write_dict_to_tsv(id_report_path, cases)

    def copy_fasta(class_, cds_list, case_id, cds_outcome_results, groups_paths_old, loci):
        """
        Process each class and CDS list in cases.

        Parameters
        ----------
        class_ : str
            The class type.
        cds_list : list
            The list of CDSs.
        case_id : int
            The ID of the case.
        cds_outcome_results : str
            The path to the results folder.
        groups_paths_old : dict
            The dictionary containing the old paths for the CDSs groups used 
            to cp instead of creating new FASTAs files.
        loci : dict
            The dictionary containing the loci IDs and paths.

        Returns
        -------
        None, copies file from origin to destination.
        """
        for cds in cds_list:
            if class_ == '1a':
                class_name_cds = f"joined_{cds}"
                for i in cds_list[cds]:
                    file_path = os.path.join(cds_outcome_results, class_name_cds)
                    origin_path = groups_paths_old.pop(i) if case_id == 0 else loci[i]
                    if not os.path.exists(file_path):
                        ff.copy_file(origin_path, file_path)
                    else:
                        ff.concat_files(origin_path, file_path)
                continue
            elif class_ == 'dropped':
                class_name_cds = f"dropped_{cds}"
            else:
                class_name_cds = f"retained_{class_}_{cds}"
            
            file_path = os.path.join(cds_outcome_results, class_name_cds)
            origin_path = groups_paths_old.pop(cds) if case_id == 0 else loci[cds]
            ff.copy_file(origin_path, file_path)

    def write_possible_new_loci(class_, cds_list, cds_outcome_results_fastas_folder, cds_outcome_results_reps_fastas_folder,
                                fasta_folder, groups_paths, groups_paths_reps, not_included_cds, clusters):
        """
        Process each class and CDS list in cds_to_keep.

        Parameters
        ----------
        class_ : str
            The class type.
        cds_list : list
            The list of CDSs.
        cds_outcome_results_fastas_folder : str
            The path to the results folder.
        cds_outcome_results_reps_fastas_folder : str
            The path to the folder where the representative results will be stored.
        fasta_folder : str
            The path to the folder where the fasta files are stored.
        groups_paths : dict
            The dictionary containing the paths to the groups.
        groups_paths_reps : dict
            The dictionary containing the paths to the representative groups.
        not_included_cds : dict
            The dictionary containing the CDSs that were not included.
        clusters : dict
            The dictionary containing the clusters.

        Returns
        -------
        None, writtes FASTA files.
        """
        for cds in cds_list:
            main_rep = cds
            if class_ == '1a':
                class_name_cds = f"{main_rep}_joined"
            elif class_ == 'Retained_not_matched_by_blastn':
                class_name_cds = f"retained_not_matched_by_blastn_{main_rep}"
            else:
                class_name_cds = f"retained_{class_}_{main_rep}"
            
            cds_group_fasta_file = os.path.join(cds_outcome_results_fastas_folder, class_name_cds + '.fasta')    
            cds_group_reps_file = os.path.join(cds_outcome_results_reps_fastas_folder, class_name_cds + '.fasta')
            master_file = os.path.join(fasta_folder, 'master_file.fasta')
            master_file_rep = os.path.join(fasta_folder, 'master_rep_file.fasta')
            groups_paths[main_rep] = cds_group_fasta_file
            groups_paths_reps[main_rep] = cds_group_reps_file
            save_ids_index = {}
            if class_ != '1a':
                cds = [cds]
            else:
                cds = cds_to_keep[class_][cds]
            index = 1
            # Write all of the alleles to the files.
            with open(cds_group_fasta_file, 'w') as fasta_file:
                for rep_id in cds:
                    cds_ids = [cds_id for cds_id in clusters[rep_id]]
                    for cds_id in cds_ids:
                        # New ID for the allele.
                        new_id = f"{main_rep}_{index}"
                        # Save the new ID to the dictionary where the old ID is the key.
                        save_ids_index[cds_id] = new_id
                        # Write the allele to the file.
                        fasta_file.write(f">{new_id}\n{str(not_included_cds[cds_id])}\n")
                        # Save the ID for that possible new loci.
                        alleles.setdefault(main_rep, []).append(f"{main_rep}_{index}")
                        index += 1
            index = 1
            # Write all of the alleles to the master file.
            write_type = 'a' if os.path.exists(master_file) else 'w'
            with open(master_file, write_type) as fasta_file:
                for rep_id in cds:
                    cds_ids = [cds_id for cds_id in clusters[rep_id]]
                    for cds_id in cds_ids:
                        fasta_file.write(f">{main_rep}_{index}\n{str(not_included_cds[cds_id])}\n")
                        index += 1

            # Write only the representative to the files.
            with open(cds_group_reps_file, 'w') as fasta_file:
                for rep_id in cds:
                    # Get the right new ID and write the representative to the file.
                    fasta_file.write(f">{save_ids_index[rep_id]}\n{str(not_included_cds[rep_id])}\n")

            # Write the representative to the master file.
            with open(master_file_rep, write_type) as fasta_file:
                for rep_id in cds:
                    # Get the right new ID and write the representative to the file.
                    fasta_file.write(f">{save_ids_index[rep_id]}\n{str(not_included_cds[rep_id])}\n")


    def translate_possible_new_loci(fasta_folder, groups_paths, groups_paths_reps, constants):
        """
        Translate possible new loci and writes to master file.

        Parameters
        ----------
        fasta_folder : str
            The path to the folder where the fasta files are stored.
        groups_paths : dict
            The dictionary containing the paths to the groups.
        groups_paths_reps : dict
            The dictionary containing the paths to the representative groups.
        constants : list
            The list of constants.

        Returns
        -------
        reps_trans_dict_cds : dict
            The dictionary containing the translated representatives sequences.
        trans_dict_cds : dict
            The dictionary containing the translated sequences.
        """
        # Translate the possible new loci.
        groups_trans_folder = os.path.join(fasta_folder, 'cds_groups_translation')
        ff.create_directory(groups_trans_folder)
        groups_trans = {}
        trans_dict_cds = {}
        for key, group_path in groups_paths.items():
            trans_path = os.path.join(groups_trans_folder, os.path.basename(group_path))
            groups_trans[key] = trans_path
            fasta_dict = sf.fetch_fasta_dict(group_path, False)
            trans_dict, _, _ = sf.translate_seq_deduplicate(fasta_dict,
                                                            trans_path,
                                                            None,
                                                            constants[5],
                                                            False,
                                                            constants[6],
                                                            False)
            for id_, sequence in trans_dict.items():
                trans_dict_cds[id_] = sequence
        # Translate the representative sequences.
        group_trans_rep_folder = os.path.join(fasta_folder, 'cds_groups_translation_reps')
        ff.create_directory(group_trans_rep_folder)
        groups_trans_reps_paths = {}
        reps_trans_dict_cds = {}
        for key, group_path in groups_paths_reps.items():
            trans_path = os.path.join(group_trans_rep_folder, os.path.basename(group_path))
            groups_trans_reps_paths[key] = trans_path
            fasta_dict = sf.fetch_fasta_dict(group_path, False)
            trans_dict, _, _ = sf.translate_seq_deduplicate(fasta_dict,
                                                            trans_path,
                                                            None,
                                                            constants[5],
                                                            False,
                                                            constants[6],
                                                            False)
            for id_, sequence in trans_dict.items():
                reps_trans_dict_cds[id_] = sequence

        return reps_trans_dict_cds, trans_dict_cds

    # Create directories.
    fasta_folder = os.path.join(output_path, 'results_fastas')
    ff.create_directory(fasta_folder)
    # Create directories for the FASTA (possible new Loci).
    if not loci:
        cds_outcome_results_fastas_folder = os.path.join(fasta_folder, 'results_group_dna_fastas')
        ff.create_directory(cds_outcome_results_fastas_folder)
        cds_outcome_results_reps_fastas_folder = os.path.join(fasta_folder, 'results_group_dna_reps_fastas')
        ff.create_directory(cds_outcome_results_reps_fastas_folder)


    # If 'Retained_not_matched_by_blastn' exists in cds_to_keep, remove it and store it separately
    Retained_not_matched_by_blastn = cds_to_keep.pop('Retained_not_matched_by_blastn', None)

    # Display info about the results obtained from processing the classes.
    # Get the total number of CDS reps considered for classification.
    count_cases = {}
    loci_cases = {}
    cds_cases = {}
    if loci:
        # Iterate over classes and their associated CDS sets
        for class_, cds_set in cds_to_keep.items():
            # Initialize dictionaries for class '1a'
            if class_ == '1a':
                loci_cases['1a'] = {}
                cds_cases['1a'] = {}
                # Iterate over groups and their associated CDS in class '1a'
                for group, cds in cds_set.items():
                    # Separate CDS into those in loci and those not in loci
                    loci_cases['1a'][group] = [c for c in cds if c in loci]
                    cds_cases['1a'][group] = [c for c in cds if c not in loci]
            else:
                # For other classes, separate CDS into those in loci and those not in loci
                loci_cases[class_] = [cds for cds in cds_set if cds in loci]
                cds_cases[class_] = [cds for cds in cds_set if cds not in loci]

        # Process drop_set in the same way as above
        loci_cases['dropped'] = [d for d in drop_set if d in loci]
        cds_cases['dropped'] = [d for d in drop_set if d not in loci]

    else:
        for class_, cds_set in cds_to_keep.items():
            cds_cases[class_] = cds_set
            if class_ == '1a':
                count_cases[class_] = len(itf.flatten_list(cds_set.values()))
            else:
                count_cases[class_] = len(cds_set)
        cds_cases['dropped'] = drop_set
    # Check if loci is not empty
    if loci:
        for i, printout in enumerate([cds_cases, loci_cases]):
            if run_type == 'loci_vs_loci' and i == 0:
                continue
            total_loci = len(itf.flatten_list([i 
                                               for class_, i
                                               in printout.items()
                                               if class_ != '1a'])) + len(itf.flatten_list(cds_to_keep['1a'].values()))

            print(f"Out of {len(groups_paths_old) if i==0 else len(loci)} {'CDSs groups' if i == 0 else 'loci'}:")
            print(f"\t{total_loci} {'CDSs' if i == 0 else 'loci'}"
                f" representatives had matches with BLASTn against the {'CDSs' if i == 1 else 'schema'}.")

            # Print the classification results
            for class_, group in printout.items():
                print_classification_results(class_ ,len(group) if class_ != '1a' else len(itf.flatten_list(group.values())) ,printout, i)

            if i == 0:
                print(f"\t{len(groups_paths_old) - len(itf.flatten_list(printout.values()))}"
                    " didn't have any BLASTn matches so they were retained.\n")
    else:
        # Write info about the classification results.
        print(f"Out of {len(clusters)} clusters:")
        print(f"\t{sum(count_cases.values()) + len(drop_set)} CDS representatives had matches with BLASTn"
            f" which resulted in {len(itf.flatten_list(cds_to_keep.values()))} groups")

        # Print the classification results
        for class_, count in count_cases.items():
            print_classification_results(class_, count, cds_to_keep, 0)

        print(f"\t\tOut of those {len(drop_set)} CDSs groups were removed from the analysis.")

        if Retained_not_matched_by_blastn:
            print(f"\t\t{len(Retained_not_matched_by_blastn)} didn't have any BLASTn matches so they were retained.")
            
            cds_to_keep['Retained_not_matched_by_blastn'] = Retained_not_matched_by_blastn
    # Skip the next step to copy or write FASTAS because we are working with the
    # schema only.

    # Initialize dictionaries to store paths
    groups_paths = {}
    groups_paths_reps = {}
    alleles = {}
    # Check if loci is not None.
    if loci:
        print("\nWriting FASTA file for possible new loci...")
        for case_id, cases in enumerate([cds_cases, loci_cases]):
            if run_type == 'loci_vs_loci' and case_id == 0:
                continue
            # Create directories and write IDS to TSV
            cds_outcome_results = os.path.join(fasta_folder, f"results_{'CDSs' if case_id == 0 else 'loci'}_fastas")
            ff.create_directory(cds_outcome_results)
            # Write the IDs to TSV by class
            write_ids_by_class(output_path, case_id, cases)

            # Process each class and CDS list in cases
            for class_, cds_list in cases.items():
                copy_fasta(class_, cds_list, case_id, cds_outcome_results, groups_paths_old, loci)
            # Copy CDS that didnt match
            if case_id == 0 and run_type == 'loci_vs_cds':
                for cds, path in groups_paths_old.items():
                    cds_name = f"retained_not_matched_by_blastn_{cds}"
                    file_path = os.path.join(cds_outcome_results, cds_name)
                    ff.copy_file(path, file_path)
        # Create variables that are not needed
        master_file = None
        reps_trans_dict_cds = None
        trans_dict_cds = None
        alleles = None
    else:
        print("Writing FASTA and additional files for possible new loci...")

        # Create directories and write dict to TSV
        write_ids_by_class(output_path, 0, cds_cases)
        # Process each class and CDS list in cds_to_keep
        for class_, cds_list in cds_to_keep.items():
            write_possible_new_loci(class_, cds_list, cds_outcome_results_fastas_folder,
                                    cds_outcome_results_reps_fastas_folder, fasta_folder,
                                    groups_paths, groups_paths_reps, not_included_cds,
                                    clusters)
        # Translate possible new loci and write to master file
        reps_trans_dict_cds, trans_dict_cds = translate_possible_new_loci(fasta_folder, groups_paths, groups_paths_reps, constants)

        master_file = os.path.join(fasta_folder, 'master_file.fasta')

    return groups_paths_reps, groups_paths, reps_trans_dict_cds, trans_dict_cds, master_file, alleles

def run_blasts(blast_db, cds_to_blast, reps_translation_dict,
               rep_paths_nuc, output_dir, constants, cpu, multi_fasta, run_type):
    """
    This functions runs both BLASTn and Subsequently BLASTp based on results of
    BLASTn.
    
    Parameters
    ----------
    blast_db : str
        Path to the BLAST db folder.
    cds_to_blast : list
        A list of CDS IDs to be used for BLASTn against the BLAST db.
    reps_translation_dict : dict
        A dictionary mapping sequence IDs to their translations (amino acid sequences).
    rep_paths_nuc : dict
        A dictionary mapping CDS IDs to the path of their corresponding FASTA files.
    output_dir : str
        The directory path where output files will be saved.
    constants : list
        A list of constants used within the function, such as thresholds for filtering BLAST results.
    cpu : int
        The number of CPU cores to use for parallel processing.
    multi_fasta : dict
       A dictionary used when the input FASTA files contain multiple CDSs, to ensure correct BLASTn
       execution.
    run_type : str
        A flag indicating what type of run to perform, can be cds_vs_cds, loci_vs_cds or loci_vs_loci.
        
    Returns
    -------
    representative_blast_results : 
        Dict that contains representatibes BLAST results.
    representative_blast_results_coords_all : dict
        Dict that contain the coords for all of the entries.
    representative_blast_results_coords_pident : dict
        Dict that contain the coords for all of the entries above certain pident value.
    bsr_values : dict
        Dict that contains BSR values between CDS.
    self_score_dict : dict
        This dict contains the self-score values for all of the CDSs that are
        processed in this function.
    """
    
    print("\nRunning BLASTn between cluster representatives vs cluster alleles..." if run_type == 'cds_vs_cds' else
          "\nRunning BLASTn between Schema representatives CDS clusters..." if run_type == 'loci_vs_cds' else
          "\nRunning BLASTn between loci representatives against schema loci...")
    # BLASTn folder
    blastn_output = os.path.join(output_dir, '1_BLASTn_processing')
    ff.create_directory(blastn_output)
    # Create directory
    blastn_results_folder = os.path.join(blastn_output, 'BLASTn_results')
    ff.create_directory(blastn_results_folder)
    # Run BLASTn
    # Calculate max id length for print.
    max_id_length = len(max(cds_to_blast))
    total_reps = len(rep_paths_nuc)
    representative_blast_results = {}
    representative_blast_results_coords_all = {}
    representative_blast_results_coords_pident = {}
    # Get Path to the blastn executable
    get_blastn_exec = lf.get_tool_path('blastn')
    i = 1
    with concurrent.futures.ProcessPoolExecutor(max_workers=cpu) as executor:
        for res in executor.map(bf.run_blastdb_multiprocessing,
                                repeat(get_blastn_exec),
                                repeat(blast_db),
                                rep_paths_nuc.values(),
                                cds_to_blast,
                                repeat(blastn_results_folder)
                                ):

            filtered_alignments_dict, _, alignment_coords_all, alignment_coords_pident = af.get_alignments_dict_from_blast_results(
                res[1], constants[1], True, False, True, True)
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
    blastp_runs_to_do = {query: itf.flatten_list([[subject[1]['subject']
                                            for subject in subjects.values()]]) 
                         for query, subjects in representative_blast_results.items()}
    
    # Create directories.
    blastp_results = os.path.join(output_dir, '2_BLASTp_processing')
    ff.create_directory(blastp_results)
    
    blastn_results_matches_translations = os.path.join(blastp_results,
                                                       'blastn_results_matches_translations')
    ff.create_directory(blastn_results_matches_translations)

    representatives_blastp_folder = os.path.join(blastn_results_matches_translations,
                                                'cluster_rep_translation')
    ff.create_directory(representatives_blastp_folder)
    
    blastp_results_folder = os.path.join(blastp_results,
                                         'BLASTp_results')
    ff.create_directory(blastp_results_folder)
    
    blastp_results_ss_folder = os.path.join(blastp_results,
                                            'BLASTp_results_self_score_results')
    ff.create_directory(blastp_results_ss_folder)
    # Write the protein FASTA files.
    rep_paths_prot = {}
    rep_matches_prot = {}
    if multi_fasta:
        blasts_to_run = {}
        seen_entries = {} 
    for query_id, subjects_ids in blastp_runs_to_do.items():
        
        filename = itf.identify_string_in_dict_get_key(query_id, multi_fasta)
        if filename:
            blasts_to_run.setdefault(filename, set()).update(subjects_ids)
            seen_entries[filename] = set()
        else:
            filename = query_id
            seen_entries[filename] = set()
            blasts_to_run.setdefault(filename, set()).update(subjects_ids)
        # First write the representative protein sequence.
        rep_translation_file = os.path.join(representatives_blastp_folder,
                                            f"cluster_rep_translation_{filename}.fasta")
        
        write_type = 'a' if os.path.exists(rep_translation_file) else 'w'
        
        rep_paths_prot[filename] = rep_translation_file
        with open(rep_translation_file, write_type) as trans_fasta_rep:
            trans_fasta_rep.writelines(">"+query_id+"\n")
            trans_fasta_rep.writelines(str(reps_translation_dict[query_id])+"\n")
        # Then write in another file all of the matches for that protein sequence
        # including the representative itself.
        rep_matches_translation_file = os.path.join(blastn_results_matches_translations,
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
    bsr_values = {}
    
    # Create query entries
    for query in blastp_runs_to_do:
        bsr_values[query] = {}
        
    if multi_fasta:
        blastp_runs_to_do = blasts_to_run
    # Total number of runs
    total_blasts = len(blastp_runs_to_do)
    # If there is need to calculate self-score
    print("\nCalculate self-score for the CDSs...")
    self_score_dict = {}
    for query in rep_paths_prot:
        # For self-score
        self_score_dict[query] = {}
    # Get Path to the blastp executable
    get_blastp_exec = lf.get_tool_path('blastp')
    i = 1
    # Calculate self-score
    with concurrent.futures.ProcessPoolExecutor(max_workers=cpu) as executor:
        for res in executor.map(bf.run_self_score_multiprocessing,
                                rep_paths_prot.keys(),
                                repeat(get_blastp_exec),
                                rep_paths_prot.values(),
                                repeat(blastp_results_ss_folder)):
            
            _, self_score, _, _ = af.get_alignments_dict_from_blast_results(res[1], 0, True, True, True, True)
    
            # Save self-score
            self_score_dict[res[0]] = self_score
                            
            print(f"\rRunning BLASTp to calculate self-score for {res[0]: <{max_id_length}}", end='', flush=True)
            i += 1
    # Print newline
    print('\n')  
    
    print("Running BLASTp for representatives against cluster alleles..." if run_type == 'cds_vs_cds'
          else "Running BLASTp of schema representatives against cluster alleles..." if run_type == 'loci_vs_cds'
          else "Running BLASTp for schema representatives against schema alleles")
    # Run BLASTp between all BLASTn matches (rep vs all its BLASTn matches)  .      
    i = 1
    with concurrent.futures.ProcessPoolExecutor(max_workers=cpu) as executor:
        for res in executor.map(bf.run_blast_fastas_multiprocessing,
                                blastp_runs_to_do, 
                                repeat(get_blastp_exec),
                                repeat(blastp_results_folder),
                                repeat(rep_paths_prot),
                                rep_matches_prot.values()):
            
            filtered_alignments_dict, _, _, _ = af.get_alignments_dict_from_blast_results(res[1], 0, True, False, True)

            # Since BLAST may find several local aligments choose the largest one to calculate BSR.
            for query, subjects_dict in filtered_alignments_dict.items():
                for subject_id, results in subjects_dict.items():
                    #Highest score (First one)
                    subject_score = next(iter(results.values()))['score']
                    bsr_values[query].update({subject_id: bf.compute_bsr(subject_score, self_score_dict[res[0]])})
        
            print(f"\rRunning BLASTp for cluster representatives matches: {res[0]} - {i}/{total_blasts: <{max_id_length}}", end='', flush=True)
            i += 1

    return [representative_blast_results, representative_blast_results_coords_all,
            representative_blast_results_coords_pident, bsr_values, self_score_dict]

def write_processed_results_to_file(cds_to_keep, representative_blast_results,
                                    classes_outcome, all_alleles, alleles, is_matched,
                                    is_matched_alleles, all_loci, output_path):
    """
    Writes the results of the classification and matching process to files for further analysis or review. 
    This function takes the processed data, including the CDS to keep, representative BLAST results, 
    classification outcomes, allele information, and matching results, and writes them to specified files 
    within a given output directory. It is designed to organize and present the data in a way that facilitates 
    easy access and interpretation.
    
    Parameters
    ----------
    cds_to_keep : dict
        A dictionary categorizing CDS by their classification for retention.
    representative_blast_results : dict
        A nested dictionary with query identifiers as keys, each mapping to another dictionary of subject 
        identifiers and their match details, organized by classification.
    classes_outcome : list
        A list of class IDs, structured as a list of lists, indicating the classification outcomes used 
        in subsequent analyses.
    all_alleles : dict
        A dictionary mapping loci or joined group identifiers to their corresponding alleles and element IDs. 
        This can be `None` if the process does not involve loci.
    is_matched : dict
        A dictionary indicating which CDS/loci have been matched, organized by their identifiers.
    is_matched_alleles : dict
        A dictionary detailing the alleles associated with matched CDS/loci.
    all_loci : bool
        A flag that indicates if only loci are present.
    output_path : str
        The file path to the directory where the output files will be written.

    Creates
    -------
    Files in output directory : 
        Multiple files are created in the specified `output_path`, each containing parts of the processed 
        data. The files are organized to reflect the structure of the input data and the results of the 
        classification and matching process.

    Notes
    -----
    - The function is designed to handle complex data structures resulting from bioinformatics analyses, 
    such as BLAST searches, and to organize this information into a more accessible format.
    - It ensures that the results are not only stored for record-keeping but also formatted in a way that 
    supports easy review and further analysis.
    - The specific format and naming of the output files are determined within the function, based on the 
    structure of the input data and the requirements of the subsequent analysis steps.
    """
    def process_clusters(cds_to_keep, representative_blast_results, all_alleles, alleles, is_matched,
                         is_matched_alleles, add_group_column, output_path):
        """
        Processes the results of cluster analysis, specifically focusing on the classification and
        matching of Coding Sequences (CDS) or loci. It iterates through each class of CDS, excluding
        those not matched by BLASTn, to process and document the details of each cluster.
        The function generates a report for each cluster, detailing the CDS or loci involved,
        their match status, and other relevant information. The reports are saved as TSV files
        in a specified output directory. Additionally, the function determines whether an extra
        column for group names is necessary in the report, based on the processed clusters.

        Parameters
        ----------
        cds_to_keep : dict
            A dictionary categorizing CDS by their classification for retention.
        representative_blast_results : dict
            A nested dictionary with query identifiers as keys, each mapping to another dictionary of
            subject identifiers and their match details.
        all_alleles : dict
            A dictionary mapping loci or joined group identifiers to their corresponding alleles and
            element IDs.
        is_matched : dict
            A dictionary indicating which CDS/loci have been matched, organized by their identifiers.
        is_matched_alleles : dict
            A dictionary detailing the alleles associated with matched CDS/loci.
        add_group_column : bool
            A flag indicating whether an additional column for group names should be included in the report.
        output_path : str
            The file path to the directory where the output files will be written.

        Returns
        -------
        None
            Creates and writes TSV files to the specified output directory.

        Notes
        -----
        - The function skips processing for the class 'Retained_not_matched_by_blastn'.
        - It utilizes helper functions such as `process_cluster` to obtain cluster details and
        `generate_write_dict` to prepare data for writing.
        - The output TSV files are named according to the cluster type and its identifier, facilitating
        easy identification and review.
        """
        # Loop over each class and its corresponding CDS
        for class_, cds in cds_to_keep.items():
            if class_ == 'Retained_not_matched_by_blastn':
                continue
            # Loop over each cluster in the CDS
            for cluster in cds if not isinstance(cds, dict) else cds.items():
                if isinstance(cds, dict):
                    id_ = cluster[0]
                    cluster = cluster[1]
                else:
                    id_ = None
                # Process the cluster and get the necessary details
                id_, cluster, cluster_type = process_cluster(class_, id_,
                                                                    cluster,
                                                                    all_alleles,
                                                                    alleles,
                                                                    cds)
                # Generate a dictionary to be written to the file
                write_dict = generate_write_dict(id_, cluster, is_matched, is_matched_alleles,
                                                 representative_blast_results)
                # Define the path of the report file
                report_file_path = os.path.join(output_path, f"blast_{cluster_type}_{id_}.tsv")
                # Write the dictionary to the file
                alignment_dict_to_file(write_dict, report_file_path, 'w', add_group_column)

    def process_cluster(class_, id_, cluster, all_alleles, alleles, cds):
        """
        Processes a single cluster, determining its type, elements, and whether it represents a CDS or a loci. 
        It also identifies if additional group IDs are present, affecting the structure of the output report.

        Parameters
        ----------
        class_ : str
            The classification of the cluster.
        id_ : str or int
            The identifier of the cluster.
        cluster : str or int
            The identifier of the cluster, used when `class_` does not indicate a joined cluster.
        all_alleles : dict
            A dictionary mapping loci or joined group identifiers to their corresponding alleles and
            element IDs.
        alleles : dict or None
            A dictionary containing the alleles of the CDSs.
        cds : dict or str
            Information about the CDS; if it's a single CDS, it contains a string, if it's a joined cluster,
            it contains a dictionary.

        Returns
        -------
        id_ : str or int
            The identifier of the cluster.
        cluster : list
            A list containing the elements' IDs of the cluster.
        cluster_type : str
            The type of the cluster, indicating if it's a joined cluster, retained, CDS cluster, or loci.

        Notes
        -----
        - The function first checks the class of the cluster to determine its type and elements.
        - It then assesses whether the cluster represents a CDS or loci based on the presence of alleles
        in `all_alleles`.
        - The presence of additional group IDs is determined by the structure of `all_alleles` and the
        type of entries in the cluster.
        - This function is designed to process clusters in a context where distinguishing between CDS
        and loci, as well as identifying joined clusters, is crucial.
        """
        # Check the class and process accordingly
        if class_ == '1a':
            cluster_type = 'joined_cluster'
            cluster = cds[id_]
        else:
            id_ = cluster
            cluster = [cluster]
            cluster_type = 'retained'

        # Check if all_alleles exist
        if all_alleles:
            is_cds = False
            cluster_alleles = []
            for entry in cluster:
                if alleles and entry in alleles:
                    cluster = alleles[entry]
                    cluster_type = 'CDS_cluster'
                    is_cds = True
                else:
                    cluster_type = 'loci'
                    cluster_alleles += all_alleles[entry]
            if not is_cds:
                cluster = cluster_alleles

        return id_, cluster, cluster_type

    def generate_write_dict(id_, cluster, is_matched, is_matched_alleles,
                            representative_blast_results):
        """
        Generates a dictionary structured for writing to a file, based on the provided cluster
        information, match status, and BLAST results. This function is tailored to handle
        different scenarios, including whether the cluster represents a CDS, if it has been
        matched, and the specifics of those matches.

        Parameters
        ----------
        id_ : str or int
            The identifier of the cluster, which can be a string or an integer.
        cluster : list
            A list containing the identifiers of elements within the cluster.
        is_matched : dict
            A dictionary indicating which clusters have been matched, keyed by cluster ID.
        is_matched_alleles : dict
            A dictionary containing the alleles of the matched clusters, keyed by cluster ID.
        representative_blast_results : dict
            A dictionary containing the BLAST results, structured with query identifiers as keys
            and subject identifiers with their match details as values.

        Returns
        -------
        write_dict : dict
            A dictionary formatted for writing to a file. The structure of this dictionary varies
            depending on the match status and type of the cluster (CDS or not).

        Notes
        -----
        - The function handles three main scenarios:
            1. When the cluster itself didn't match but was matched against, it generates a dictionary
            based on the matches and the alleles of the matched clusters.
            2. For all other cases, it creates a dictionary including all subjects for each query within
            the cluster.
        - The function dynamically adjusts the structure of the `write_dict` based on the input parameters,
        ensuring the output is tailored for the specific scenario.
        """
        # for cases that didn't match anything but got matched against.
        if is_matched and id_ in is_matched:
            queries = is_matched[id_]
            cluster = is_matched_alleles[id_]
            # Generate the dictionary to be written
            write_dict = {query : {subject: {id_: entry for id_, entry in entries.items()}
                                for subject, entries in subjects.items() if subject in cluster}
                        for query, subjects in representative_blast_results.items()
                        if query in queries}
        # For all other normal cases.
        else:
            # Generate the dictionary to be written
            write_dict = {query : {subject: {id_: entry for id_, entry in entries.items()}
                                for subject, entries in subjects.items()}
                        for query, subjects in representative_blast_results.items()
                        if query in cluster}
        return write_dict

    def process_classes(classes_outcome, representative_blast_results, output_path, add_group_column):
        """
        Processes the outcomes of different classes from BLAST results and writes the results to files.
        For each class outcome, it generates a dictionary of representative BLAST results filtered by
        class. This dictionary is then written to a TSV file in the specified output directory. The
        function can optionally add a column header for group information based on the `add_group_column`
        parameter.

        Parameters
        ----------
        classes_outcome : list
            A list of class outcomes to process.
        representative_blast_results : dict
            A dictionary containing BLAST results, structured with query identifiers as keys and subject
            identifiers with their match details as values.
        output_path : str
            The path to the directory where the output files will be written.
        add_group_column : bool
            A boolean indicating whether to add a column header for group information in the output files.

        Returns
        -------
        None
            The function does not return any value. It writes the results to TSV files in the specified
            output directory.

        Notes
        -----
        - The function iterates over each class outcome, creating a filtered dictionary of BLAST results
        for that class.
        - It constructs the file path for each class's report using the `output_path` and the class name,
        then writes the filtered results to this file.
        - The `alignment_dict_to_file` function is used to write the dictionary to a TSV file, with the
        option to add a group column if `add_group_column` is True.
        - This function is useful for organizing BLAST results by class and facilitating further analysis
        of these results.
        """
        # Loop over each class in the outcome
        for class_ in classes_outcome:
            # Generate the dictionary to be written
            write_dict = {query : {subject: {id_: entry for id_, entry in entries.items() if entry['class'] == class_}
                                for subject, entries in subjects.items()}
                        for query, subjects in representative_blast_results.items()}
            # Define the path of the report file
            report_file_path = os.path.join(output_path, f"blastn_group_{class_}.tsv")
            # Write the dictionary to the file
            alignment_dict_to_file(write_dict, report_file_path, 'w', add_group_column)

    # Create directories for output
    blast_by_cluster_output = os.path.join(output_path, 'blast_by_cluster')
    ff.create_directory(blast_by_cluster_output)
    blast_results_by_class_output = os.path.join(output_path, 'blast_results_by_class')
    ff.create_directory(blast_results_by_class_output)

    add_group_column = True if not all_loci and all_alleles else False
    # Process and write cluster results
    process_clusters(cds_to_keep, representative_blast_results, all_alleles, alleles,
                    is_matched, is_matched_alleles, add_group_column, blast_by_cluster_output)

    # Process and write class results
    process_classes(classes_outcome, representative_blast_results, blast_results_by_class_output,
                    add_group_column)

def extract_cds_to_keep(classes_outcome, count_results_by_class, drop_mark):
    """
    Extracts and organizes CDS (Coding Sequences) to keep based on classification outcomes.

    This function processes BLAST results to determine which coding sequences (CDS) should
    be retained for further analysis based on their classification outcomes. It organizes
    CDS into categories, prioritizes them according to a predefined order of classes, and
    identifies sequences to be dropped.

    Parameters
    ----------
    classes_outcome : list
        An ordered list of class identifiers that determine the priority of classes for keeping CDS.
    count_results_by_class : dict
        A dictionary where keys are concatenated query and subject IDs separated by '|', and values
        are dictionaries with class identifiers as keys and counts as values.
    drop_mark : set
        A set of identifiers that are marked for dropping based on previous criteria.

    Returns
    -------
    cds_to_keep : dict
        A dictionary with class identifiers as keys and lists of CDS identifiers or pairs of identifiers
        to be kept in each class.
    drop_set : set
        A set of CDS identifiers that are determined to be dropped based on their classification and
        presence in `drop_mark`.

    Notes
    -----
    - The function first initializes `cds_to_keep` with empty lists for each class in `classes_outcome`.
    - It then iterates through `count_results_by_class` to assign CDS to the most appropriate class
    based on the provided outcomes.
    - Special handling is given to class '1a', where CDS pairs are clustered and indexed.
    - CDS marked in `drop_mark` and falling under certain classes are added to `drop_set` for exclusion.
    - The function uses utility functions like `itf.try_convert_to_type` for type conversion and
    `cf.cluster_by_ids` for clustering CDS pairs in class '1a'.
    """
    temp_keep = {}
    cds_to_keep = {class_: [] for class_ in classes_outcome}
    drop_set = set()
    for ids, result in count_results_by_class.items():
        class_ = next(iter(result))
        [query, subject] = list(map(lambda x: itf.try_convert_to_type(x, int), ids.split('|')))
        if class_ == '1a':
            cds_to_keep.setdefault('1a', []).append([query, subject])
        if not temp_keep.get(query):
            temp_keep[query] = class_
        elif classes_outcome.index(class_) < classes_outcome.index(temp_keep[query]):
            temp_keep[query] = class_
        if not temp_keep.get(subject):
            temp_keep[subject] = class_
        elif classes_outcome.index(class_) < classes_outcome.index(temp_keep[subject]):
            temp_keep[subject] = class_

    for keep, class_ in temp_keep.items():
        if class_ == '1a':
            continue
        if keep in drop_mark and class_ in ['1b', '2a', '3a']:
            drop_set.add(itf.try_convert_to_type(keep, int))
        else:
            cds_to_keep.setdefault(class_, []).append(keep)

    cds_to_keep['1a'] = {i: list(values) for i, values in enumerate(cf.cluster_by_ids(cds_to_keep['1a']), 1)}

    return cds_to_keep, drop_set

def count_number_of_reps_and_alleles(cds_to_keep, clusters, drop_set, group_reps_ids, group_alleles_ids):
    """
    Counts the number of representatives and alleles for each group in the given CDS clusters, excluding those in the drop set.

    Parameters
    ----------
    cds_to_keep : dict
        Dictionary of CDS clusters to keep, organized by class and group.
    clusters : dict
        Dictionary mapping group IDs to their member CDS IDs.
    drop_set : set
        Set of group IDs to be excluded from the count.
    group_reps_ids : dict
        Dictionary to be updated with representative IDs for each group.
    group_alleles_ids : dict
        Dictionary to be updated with allele IDs for each group.

    Returns
    -------
    group_reps_ids : dict
        Dictionary where key is the CDS cluster ID and value is a set of representative IDs.
    group_alleles_ids : dict
        Dictionary where key is the CDS cluster ID and value is a set of allele IDs.
    """
    # Iterate over each class.
    for class_, cds_group in list(cds_to_keep.items()):
        # Iterate over each group in class.
        for group in cds_group:
            if class_ == '1a':
                # Iterate over each representative in joined group.
                for cds in cds_group[group]:
                    if group_reps_ids.get(cds):
                        continue
                    group_reps_ids.setdefault(cds, set()).add(cds)
                    group_alleles_ids.setdefault(cds, set()).update(clusters[cds])
            elif group_reps_ids.get(group):
                continue
            else:
                group_reps_ids.setdefault(group, set()).add(group)
                group_alleles_ids.setdefault(group, set()).update(clusters[group])
    
    for id_ in drop_set:
        if id_ not in group_reps_ids:
            group_reps_ids.setdefault(id_, set()).add(id_)
            group_alleles_ids.setdefault(id_, set()).update(clusters[id_])

    return group_reps_ids, group_alleles_ids

def process_schema(schema, groups_paths, results_output, reps_trans_dict_cds, 
                   alleles, frequency_in_genomes, allelecall_directory, 
                   master_file, allele_ids, run_type, master_alleles, constants, cpu):
    """
    This function processes data related to the schema seed, importing, translating
    and BLASTing against the unclassified CDS clusters representatives groups to
    validate them.
    
    Parameters
    ----------
    schema : str
        Path to the schema seed folder.
    groups_paths : dict
        Dict that contains the path to the FASTA file for each group.
    results_output : str
        Path were to write the results of this function.
    reps_trans_dict_cds : dict
        Dict that contains the translations for each CDS.
    alleles : dict or None
        Alleles of each group.
    frequency_in_genomes : dict
        Dict that contains sum of frequency of that representatives cluster in the
        genomes of the schema.
    allelecall_directory : str
        Path to the allele call directory.
    master_file : str
        Path to the master file containing retained CDS.
    allele_ids : list
        List containg two bools, each representing query and subject, True
        if they are contain alleles False otherwise.
    run_type : str
        A flag indicating what type of run to perform, can be cds_vs_cds, loci_vs_cds or loci_vs_loci.
    master_alleles : bool
        If True, the function will process all of the alleles of the loci, if False only the
        representatives.
    constants : list
        Contains the constants to be used in this function.
    cpu : int
        Number of CPUs to use during multi processing.

    Returns
    -------
    representative_blast_results : dict
        Dict that contains BLAST results of the representatives with all of the additional
        info.

    """
    blast_results = os.path.join(results_output, '1_BLAST_processing')
    ff.create_directory(blast_results)
    # Create BLASTn_processing directoryrun_type
    blastn_output = os.path.join(blast_results, '1_BLASTn_processing')
    ff.create_directory(blastn_output)
    
    # Get all of the schema loci short FASTA files path.
    schema_short_path = os.path.join(schema, 'short')
    schema_loci_short = {os.path.basename(loci_path.replace("_short.fasta", "")): os.path.join(schema_short_path, loci_path) 
                         for loci_path in ff.get_paths_in_directory_with_suffix(schema_short_path, '_short.fasta')}
    
    # Get all of the schema loci FASTA files path.
    schema_loci = {os.path.basename(loci_path.replace(".fasta", "")): os.path.join(schema, loci_path) 
                         for loci_path in ff.get_paths_in_directory_with_suffix(schema, '.fasta')}

    #Count the number of reps and alleles in the schema.
    group_reps_ids = {}
    group_alleles_ids = {}
    for loci, fasta_path in schema_loci_short.items():
            fasta_dict = sf.fetch_fasta_dict(fasta_path, False)
            for id_, fasta in fasta_dict.items():
                group_reps_ids.setdefault(loci, set()).add(id_)
            fasta_dict = sf.fetch_fasta_dict(schema_loci[loci], False)
            for id_, fasta in fasta_dict.items():
                group_alleles_ids.setdefault(loci, set()).add(id_)

    # Create a folder for short translations.
    blastp_output =  os.path.join(blast_results, '2_BLASTp_processing')
    ff.create_directory(blastp_output)
    short_translation_folder = os.path.join(blastp_output, 'short_translation_folder')
    ff.create_directory(short_translation_folder)

    # Find the file in the allele call results that contains the total of each.
    # classification obtained for each loci.
    results_statistics = os.path.join(allelecall_directory, 'loci_summary_stats.tsv')
    # Convert TSV table to dict.
    results_statistics_dict = itf.tsv_to_dict(results_statistics)
    # Add the results for all of the Exact matches to the frequency_in_genomes dict.
    for key, value in results_statistics_dict.items():
        frequency_in_genomes.setdefault(key, int(value[0]))
    # Translate each short loci and write to master fasta.
    print("Translate and write to master fasta file...")
    i = 1
    len_short_folder = len(schema_loci_short)
    all_alleles = {}
    if not master_file:
        filename = 'master_file' if master_alleles else 'master_rep_file'
        master_file_folder = os.path.join(blastn_output, filename)
        ff.create_directory(master_file_folder)
        master_file = os.path.join(master_file_folder, f"{filename}.fasta")
        write_to_master = True
    else:
        write_to_master = False
    # Create varible to store proteins sequences if it doesn't exist.
    reps_trans_dict_cds = {} if not reps_trans_dict_cds else reps_trans_dict_cds
    # If to BLAST against reps or all of the alleles.
    schema_loci if master_alleles else schema_loci_short
    for loci, loci_path in schema_loci.items():
        print(f"\rTranslated{'' if master_alleles else ' short'} loci FASTA: {i}/{len_short_folder}", end='', flush=True)
        i += 1
        fasta_dict = sf.fetch_fasta_dict(loci_path, False)
        
        for allele_id, sequence in fasta_dict.items():
            all_alleles.setdefault(loci, []).append(allele_id)

            if write_to_master:
                write_type = 'w' if not os.path.exists(master_file) else 'a'
                with open(master_file, write_type) as m_file:
                    m_file.write(f">{allele_id}\n{sequence}\n")

        loci_short_translation_path = os.path.join(short_translation_folder, f"{loci}.fasta")
        translation_dict, _, _ = sf.translate_seq_deduplicate(fasta_dict, 
                                                              loci_short_translation_path,
                                                              None,
                                                              constants[5],
                                                              False,
                                                              constants[6],
                                                              False)
        for allele_id, sequence in translation_dict.items():
            reps_trans_dict_cds[allele_id] = sequence

    # Create BLAST db for the schema DNA sequences.
    print(f"\nCreate BLAST db for the {'schema' if master_alleles else 'unclassified'} DNA sequences...")
    makeblastdb_exec = lf.get_tool_path('makeblastdb')
    blast_db = os.path.join(blastn_output, 'blast_db_nucl')
    ff.create_directory(blast_db)
    blast_db_nuc = os.path.join(blast_db, 'Blast_db_nucleotide')
    bf.make_blast_db(makeblastdb_exec, master_file, blast_db_nuc, 'nucl')

    [representative_blast_results,
     representative_blast_results_coords_all,
     representative_blast_results_coords_pident,
     bsr_values,
     _] = run_blasts(blast_db_nuc,
                     schema_loci_short,
                     reps_trans_dict_cds,
                     schema_loci_short,
                     blast_results,
                     constants,
                     cpu,
                     all_alleles,
                     run_type)

    add_items_to_results(representative_blast_results,
                         None,
                         bsr_values,
                         representative_blast_results_coords_all,
                         representative_blast_results_coords_pident,
                         frequency_in_genomes,
                         allele_ids,
                         alleles)

    # Add CDS joined clusters to all_alleles IDS
    if alleles:
        all_alleles.update(alleles)
    # Separate results into different classes.
    classes_outcome = separate_blastn_results_into_classes(representative_blast_results,
                                                           constants)
    blast_results = os.path.join(results_output, 'blast_results')
    ff.create_directory(blast_results)
    report_file_path = os.path.join(blast_results, 'blast_all_matches.tsv')
    # Write all of the BLASTn results to a file.
    alignment_dict_to_file(representative_blast_results, report_file_path, 'w', True)
    
    print("\nProcessing classes...")
    sorted_blast_dict = sort_blast_results_by_classes(representative_blast_results, classes_outcome)
    # Process the results_outcome dict and write individual classes to TSV file.
    [processed_results,
     count_results_by_class,
     count_results_by_class_with_inverse,
     reps_and_alleles_ids,
     drop_mark] = process_classes(sorted_blast_dict,
                                classes_outcome,
                                all_alleles)
    # Sort the count_results_by_class dict by the classes_outcome tuple.
    count_results_by_class = itf.sort_subdict_by_tuple(count_results_by_class, classes_outcome)
    # Extract CDS to keep and drop set.
    cds_to_keep, drop_set = extract_cds_to_keep(classes_outcome, count_results_by_class, drop_mark)
        
    count_number_of_reps_and_alleles(cds_to_keep, all_alleles, drop_set, group_reps_ids, group_alleles_ids)

    # Extract the related clusters and recommendations what to do with them.
    print("\nExtracting results...")
    all_relationships, related_clusters, recommendations  = extract_results(processed_results,
                                                                           count_results_by_class,
                                                                           frequency_in_genomes,
                                                                           cds_to_keep,
                                                                           drop_set,
                                                                           classes_outcome)
    print("\nWritting count_results_by_cluster.tsv and related_matches.tsv files...")
    write_blast_summary_results(related_clusters,
                                count_results_by_class_with_inverse,
                                group_reps_ids,
                                group_alleles_ids,
                                frequency_in_genomes,
                                recommendations,
                                run_type,
                                results_output)

    # Get all of the CDS that matched with loci
    [is_matched, is_matched_alleles] = get_matches(all_relationships, cds_to_keep, sorted_blast_dict)

    print("\nWritting classes and cluster results to files...")
    write_processed_results_to_file(cds_to_keep,
                                    sorted_blast_dict,
                                    classes_outcome,
                                    all_alleles,
                                    alleles,
                                    is_matched,
                                    is_matched_alleles,
                                    run_type,
                                    blast_results)
    
    print("\nWrapping up BLAST results...")

    wrap_up_blast_results(cds_to_keep,
                        None,
                        all_alleles,
                        results_output,
                        constants,
                        drop_set,
                        schema_loci,
                        groups_paths,
                        frequency_in_genomes,
                        run_type)

    return sorted_blast_dict

def create_graphs(file_path, output_path, filename, other_plots = None):
    """
    Create graphs based on representative_blast_results written inside a TSV file,
    this function creates severall plots related to palign and protein values, with
    the option to create additional plots based on inputs values.
    
    Parameters
    ----------
    file_path : str
        Path to the TSV file.
    output_path : str
        Path to the output directory.
    other_plots : list, optional
        List that contains additional data to create plots.

    Returns
    -------
    Create an HTML file inside the output_path that contains all of the created
    graphs.
    """
    results_output = os.path.join(output_path, "Graph_folder")
    ff.create_directory(results_output)
    
    blast_results_df = ff.import_df_from_file(file_path, '\t')
    
    # Create boxplots
    traces = []
    for column in ['Global_palign_all_min', 'Global_palign_all_max', 'Global_palign_pident_min', 'Global_palign_pident_max', 'Palign_local_min']:
        traces.append(gf.create_violin_plot(y = blast_results_df[column], name = blast_results_df[column].name))
    
    violinplot1 = gf.generate_plot(traces, "Palign Values between BLAST results", "Column", "Palign")
    
    # Create line plot.
    traces = []
    for column in ['Prot_BSR', 'Prot_seq_Kmer_sim', 'Prot_seq_Kmer_cov']:
        traces.append(gf.create_violin_plot(y = blast_results_df[column], name = blast_results_df[column].name))
    
    violinplot2 = gf.generate_plot(traces, "Protein values between BLAST results", "BLAST entries ID", "Columns")
    
    # Create other plots
    extra_plot = []
    if other_plots:
        for plot in other_plots:
            plot_df = pf.dict_to_df(plot[0])
            for column in plot_df.columns.tolist():
                if plot[1] == 'histogram':
                   trace = gf.create_histogram(x = plot_df[column], name = plot_df[column].name)
            
            extra_plot.append(gf.generate_plot(trace, plot[2], plot[3], plot[4]))

    gf.save_plots_to_html([violinplot1, violinplot2] + extra_plot, results_output, filename)

def identify_problematic_cds(cds_presence_in_genomes, cds_translation_dict, protein_hashes, not_included_cds, cds_output,
                             bsr_value, dropped_cluster, cpu):
    """
    Identifies problematic CDS (Coding DNA Sequences) based on specified criteria and outputs the results
    and Remove the instace of CDS from all the dicts.

    Parameters
    ----------
    cds_presence_in_genomes : dict
        A dictionary mapping each genome to the presence data of CDS.
    cds_translation_dict : dict
        A dictionary mapping CDS identifiers to their translated protein sequences.
    protein_hashes : set
        A set of unique hashes representing protein sequences, used to identify duplicates or problematic sequences.
    not_included_cds : set
        A set of CDS identifiers that are not included in the analysis, potentially due to previous filtering.
    cds_output : str
        The file path where the results of the analysis will be saved.
    bsr_value : float
        The BLAST Score Ratio (BSR) threshold used to determine problematic sequences. Sequences with a BSR below this value may be considered problematic.
    dropped_cluster : set
        A set of cluster identifiers that have been dropped from the analysis, potentially due to being identified as problematic.
    cpu : int
        The number of CPU cores to be used for parallel processing tasks within the function.

    Returns
    -------
    None
        This function does not return a value but writes the results of the analysis to the specified output file.

    Notes
    -----
    This function is part of a larger pipeline for analyzing genomic data, specifically focusing on the identification
    of problematic CDS based on duplication, absence in certain genomes, or low BLAST Score Ratios. The results are used
    to refine the dataset for further analysis.
    """

    print("\nIdentifying possible NIPHEMs...")
    # Identify NIPHEMs.
    same_origin_genome = {}
    niphems_presence_in_genome = {}
    only_niphems_in_genomes = {}
    # Iterate over each CDS and check for NIPHEMs.
    for id_, cds_in_genomes in cds_presence_in_genomes.items():
        # Remove the protein number from the ID.
        genome_id = itf.remove_by_regex(id_, r'-protein\d+')
        same_origin_genome.setdefault(genome_id, set()).add(id_)
        # If there are duplicates in genomes.
        if len(cds_in_genomes) != len(set(cds_in_genomes)):
            # If all of the genomes contain only NIPHEMs in genomes.
            if itf.check_if_all_elements_are_duplicates(cds_in_genomes):
                # Remove from same_origin_genomes since these IDs were dropped.
                same_origin_genome[genome_id].remove(id_)
                # Save the CDS that are only NIPHEMs in genomes.
                only_niphems_in_genomes.setdefault(id_, set(cds_in_genomes))
                dropped_cluster.setdefault(id_, 'Dropped_due_to_being_only_NIPHEM_in_genomes')
                # Remove the CDS from the dictionaries.
                del not_included_cds[id_]
                # If this CDSs is the representative in translation dict
                if cds_translation_dict.get(id_):
                    del cds_translation_dict[id_]
                #Remove from associated translation hashes dict.
                translation_hash = itf.identify_string_in_dict_get_key(id_, protein_hashes)
                protein_hashes[translation_hash].remove(id_)
                # Remove all reference of the protein if it has no more CDSs associated with it.
                if len(protein_hashes[translation_hash]) == 0:
                    del protein_hashes[translation_hash]
            else:
                # Add to the dict for further processing when to calculate if to exclude
                # possible new loci
                niphems_presence_in_genome.setdefault(id_, cds_in_genomes)
    # Write the identified NIPHEMs to a file.
    niphems_file = os.path.join(cds_output, 'identified_NIPHEMs_CDSs.tsv')
    tab = "\t"
    with open(niphems_file, 'w') as niphems:
        niphems.write('CDS_ID\tGenome_presence:\n')
        for cds, genomes_id in only_niphems_in_genomes.items():
            niphems.write(f"{cds}{tab}{tab.join([str(i) for i in genomes_id])}\n")
    # Print the results.
    print(f"There were identified {len(niphems_presence_in_genome)} CDSs containing NIPHEMs in genomes "
          f"and {len(only_niphems_in_genomes)} were removed for being present in genomes that only contain NIPHEMs.")

    # Identify CDSs present in the same genome.
    same_origin_genome = {genome_id: [cds for cds in cds_ids if cds_translation_dict.get(cds)] for genome_id, cds_ids in same_origin_genome.items()}
    # Filter out genomes with only one CDS.
    same_origin_genome = {genome_id: cds_ids for genome_id, cds_ids in same_origin_genome.items() if len(cds_ids) > 1}
    # Identify which cases to run.
    sequences_to_run = {}
    sequences_to_run_against = {}
    for genome_id, cds_ids in same_origin_genome.items():
        for cds in cds_ids:
            if cds_translation_dict.get(cds):
                sequences_to_run.setdefault(cds, cds_translation_dict[cds])
                sequences_to_run_against.setdefault(cds, [cds_id for cds_id in cds_ids if (cds_id != cds and cds_translation_dict.get(cds_id))])

    #Create folders.
    niphs_folder = os.path.join(cds_output, 'NIPHs_and_NIPHEMs_processing')
    ff.create_directory(niphs_folder)
    translation_sequences_folder = os.path.join(niphs_folder, 'translation_sequences')
    ff.create_directory(translation_sequences_folder)
    translation_sequences_to_run_against_folder = os.path.join(niphs_folder, 'translation_sequences_to_run_against')
    ff.create_directory(translation_sequences_to_run_against_folder)

    #Write all of the FASTAs.
    sequences_fasta_path = {}
    to_run_against_paths = {}
    # Write the FASTAs for the CDSs and the CDSs to run against.
    for cds, cds_ids_to_run_against in sequences_to_run_against.items():
        member_file = os.path.join(translation_sequences_folder, f"{cds}.fasta")
        sequences_fasta_path[cds] = member_file
        #FASTAs to run.
        with open(member_file, 'w') as m_file:
            m_file.write(f">{cds}\n{sequences_to_run[cds]}\n")
        member_file = os.path.join(translation_sequences_to_run_against_folder, f"{cds}.fasta")
        to_run_against_paths[cds] = member_file
        #FASTAs proteins to run against
        for member_id in cds_ids_to_run_against:
            write_type = 'w' if not os.path.exists(member_file) else 'a'
            with open(member_file, write_type) as m_file:
                m_file.write(f">{member_id}\n{sequences_to_run[member_id]}\n")

    # Run BLASTp to identify possible NIPHs.
    print("\nIdentifying possible NIPHs...")
    self_score_folder = os.path.join(niphs_folder, 'self_score')
    ff.create_directory(self_score_folder)
    # Get the path to the BLASTp executable.
    get_blastp_exec = lf.get_tool_path('blastp')
    i = 1
    # Create a dictionary to store the self-score of each CDS.
    self_score_dict_niphs = {}
    # Get the max length of the IDs.
    max_id_length = len(max(sequences_fasta_path))
    # Calculate self-score.
    print("Calculating self-score for possible NIPHs...")
    with concurrent.futures.ProcessPoolExecutor(max_workers=cpu) as executor:
        for res in executor.map(bf.run_self_score_multiprocessing,
                                sequences_fasta_path.keys(),
                                repeat(get_blastp_exec),
                                sequences_fasta_path.values(),
                                repeat(self_score_folder)):
            
            _, self_score, _, _ = af.get_alignments_dict_from_blast_results(res[1], 0, False, True, True, False)
    
            # Save self-score.
            self_score_dict_niphs[res[0]] = self_score
                            
            print(f"\rRunning BLASTp to calculate self-score for possible NIPHs {res[0]: <{max_id_length}}", end='', flush=True)
            i += 1
    # Run BLASTp to confirm possible NIPHs.
    niphs_blastp_results_folder = os.path.join(niphs_folder, 'niphs_blastp_results')
    ff.create_directory(niphs_blastp_results_folder)
    save_bsr_score = {}
    total_blasts = len(sequences_fasta_path)
    i = 1
    # Run Blastp and calculate BSR.
    print("\nRunning BLASTp to confirm possible NIPHs...")
    with concurrent.futures.ProcessPoolExecutor(max_workers=cpu) as executor:
        for res in executor.map(bf.run_blast_fastas_multiprocessing,
                                sequences_fasta_path, 
                                repeat(get_blastp_exec),
                                repeat(niphs_blastp_results_folder),
                                repeat(sequences_fasta_path),
                                to_run_against_paths.values()):
            
            filtered_alignments_dict, _, _, _ = af.get_alignments_dict_from_blast_results(res[1], 0, False, False, False)


            # Since BLAST may find several local aligments choose the first one (highest one) to calculate BSR.
            for query, subjects_dict in filtered_alignments_dict.items():
                for subject_id, results in subjects_dict.items():
                    #Highest score (First one)
                    subject_score = next(iter(results.values()))['score']
                    save_bsr_score.setdefault(query, {}).update({subject_id: bf.compute_bsr(subject_score, self_score_dict_niphs[query])})

            print(f"\rRunning BLASTp to confirm identified NIPHs: {res[0]} - {i}/{total_blasts: <{max_id_length}}", end='', flush=True)
            i += 1

    #Identify NIPHS
    niphs_in_genomes = {}
    #Filter the BSR score.
    filtered_save_bsr_score = {query: {subject_id: bsr for subject_id, bsr in subjects_ids.items() if bsr >= bsr_value} for query, subjects_ids in save_bsr_score.items()}
    #Remove empty dicts.
    itf.remove_empty_dicts_recursive(filtered_save_bsr_score)

    # When some IDs didnt get in the same group
    to_merge_lists = [[query] + [subject for subject in subjects_ids.keys()] for query, subjects_ids in filtered_save_bsr_score.items()]
    niphs_in_genomes = {index: set(value) for index, value in enumerate(cf.cluster_by_ids_bigger_sublists(to_merge_lists))}

    for index, niphs in list(niphs_in_genomes.items()):
        for cds in list(niphs):
            same_protein_ids = itf.identify_string_in_dict_get_value(cds, protein_hashes)
            niphs_in_genomes[index].update(same_protein_ids)

    #Write the identified NIPHs to a file.
    niphs_presence_in_genomes = {}
    count_niphs_groups = 0
    count_niphs_cds = 0
    total_niphs = len(niphs_in_genomes)
    niphs_file = os.path.join(cds_output, 'identified_NIPHs_CDSs.tsv')
    # Iterate over possible NIPHs and write to file.
    for niph_id, cds_ids in list(niphs_in_genomes.items()):
        temp_niph_holder = []
        # Get the presence of the CDS in the genomes.
        for cds_id in cds_ids:
            niphs_presence_in_genomes[cds_id] = cds_presence_in_genomes[cds_id]
            temp_niph_holder.append(set(cds_presence_in_genomes[cds_id]))
        # Check if all of the sets are the same.
        if itf.check_if_all_sets_are_same(temp_niph_holder):
            # Write to file.
            write_type = 'w' if not os.path.exists(niphs_file) else 'a'
            with open(niphs_file, write_type) as niphs:
                count_niphs_groups += 1
                del niphs_in_genomes[niph_id]
                if write_type == 'w':
                    niphs.write('CDS_ID\tGenome_presence:\n')
                for cds_id in cds_ids:
                    count_niphs_cds += 1
                    niphs.write(f"{cds_id}{tab}{tab.join([str(i) for i in niphs_presence_in_genomes[cds_id]])}\n")
                    # Remove from cds not included in the schema dict.
                    dropped_cluster.setdefault(cds_id, 'Dropped_to_being_only_NIPH_in_genomes')
                    # Remove from dictionaries.
                    del not_included_cds[cds_id]
                    # Remove from NIPHEMs dict
                    if niphems_presence_in_genome.get(cds_id):
                        del niphems_presence_in_genome[cds_id]
                    # If this CDSs is the representative in translation dict
                    if cds_translation_dict.get(cds_id):
                        del cds_translation_dict[cds_id]
                    # Remove from NIPHs
                    del niphs_presence_in_genomes[cds_id]
                    #Remove from associated translation hashes dict.
                    translation_hash = itf.identify_string_in_dict_get_key(cds_id, protein_hashes)
                    if translation_hash:
                        protein_hashes[itf.identify_string_in_dict_get_key(cds_id, protein_hashes)].remove(cds_id)
                        # Remove all hash of the protein if it has no more CDSs associated with it.
                        if len(protein_hashes[translation_hash]) == 0:
                            del protein_hashes[translation_hash]
                niphs.write("\n")
    # Convert the niphs_in_genomes dict to a list of sets.
    niphs_in_genomes = {key: list(value) for key, value in niphs_in_genomes.items()}
    print(f"There were Identified {total_niphs} groups of CDSs containing NIPHs and {count_niphs_groups}"
          f" groups ({count_niphs_cds} CDSs) were removed for being present in genomes that only contain NIPHs.")

    return niphems_presence_in_genome, niphs_in_genomes, niphs_presence_in_genomes

def remove_problematic_loci(niphems_presence_in_genome, niphs_in_genomes, niphs_presence_in_genomes,
                            cds_presence_in_genomes, cds_to_keep, clusters, drop_set, problematic_proportion,
                            dropped_cluster, results_output):
    """
    Removes loci deemed problematic based on a specified proportion of NIPHS and NIPHEMS present in the genomes.

    Parameters
    ----------
    niphems_presence_in_genome : dict
        A dictionary mapping each genome to its Niphems presence data.
    niphs_in_genomes : dict
        A dictionary mapping each genome to its Niphs data.
    niphs_presence_in_genomes : dict
        A dictionary mapping each genome to the presence data of Niphs.
    cds_presence_in_genomes : dict
        A dictionary mapping each genome to the presence data of CDS (Coding Sequences).
    cds_to_keep : list
        A list of CDS identifiers that should be retained.
    clusters : dict
        A dictionary mapping cluster identifiers to their respective genomic data.
    drop_set : set
        A set of loci identifiers that are considered problematic and should be removed.
    problematic_proportion : float
        The proportion threshold above which a locus is considered problematic.
    dropped_cluster : dict
        A dictionary mapping cluster identifiers to the reason they were dropped.
    cds_output : str
        The file path to save the filtered CDS presence data.

    Returns
    -------
    proportion_of_niph_genomes : dict
        A dictionary mapping each genome to the proportion of NIPHS and NIPHEMS present in it.
    dropped_due_to_niphs_or_niphems : set
        A set of loci identifiers that were dropped due to the presence of NIPHS or NIPHEMS.
    cds_to_keep_all_members : dict
        A dictionary mapping each group to its member CDS identifiers.
    cds_to_keep_all_genomes : dict
        A dictionary mapping each group to the genomes in which it is present.

    Notes
    -----
    This function is designed to work with genomic data, specifically focusing on the presence and absence of certain
    NIPHEMs, NIPHs. It filters out loci based on a defined problematic proportion and updates the genomic data structures
    accordingly.
    """
    # Create file Path.
    potential_paralagous = os.path.join(results_output, 'potential_paralagous.tsv')
    # Pre process NIPHs
    for key, niphs in list(niphs_in_genomes.items()):
        # Get ids without the allele identifier.
        niphs_ids = [niph.split('_')[0] for niph in niphs]
        id_class_1a = [itf.identify_string_in_dict_get_key(niph_id, cds_to_keep['1a']) for niph_id in niphs_ids]
        # If all IDs are the same (mantain them).
        if all(id_class_1a) and len(set(id_class_1a)) == 1:
            continue
        elif len(set(niphs_ids)) == 1:
            continue
        # If IDs are different (meaning that they were not clustered together or joined).
        # we remove them and write to file the potential paralogous.
        else:
            if any(id_class_1a):
                # Get indices of all values that are not None
                indices_not_none = [index for index, value in enumerate(id_class_1a) if value is not None]
                # Replace the IDs with the joined IDs.
                for index in indices_not_none:
                    niphs_ids[index] = id_class_1a[index]
            niphs_ids = set(niphs_ids)
            write_type = 'w' if not os.path.exists(potential_paralagous) else 'a'
            with open(potential_paralagous, write_type) as niph_and_niphem_report:
                niph_and_niphem_report.write('\t'.join(niphs_ids) + '\n')
                del niphs_in_genomes[key]
                for niph in niphs:
                    del niphs_presence_in_genomes[niph]

    # Get all of the genomes that one groups is present in.
    cds_to_keep_all_members = {}
    cds_to_keep_all_genomes = {}
    for class_, cds_group in list(cds_to_keep.items()):
    # Iterate over each group in class.
        for group in list(cds_group):
            cds_to_keep_all_members.setdefault(group, set())
            cds_to_keep_all_genomes.setdefault(group, set())
            # If the group is a joined group.
            if class_ == '1a':
                for cds in cds_group[group]:
                    for cds_allele in clusters[cds]:
                        cds_to_keep_all_members[group].add(cds_allele)
                        cds_to_keep_all_genomes[group].update(cds_presence_in_genomes[cds_allele])
            # If the group is not a joined group.
            else:
                for cds_allele in clusters[group]:
                    cds_to_keep_all_members[group].add(cds_allele)
                    cds_to_keep_all_genomes[group].update(cds_presence_in_genomes[cds_allele])

    # Get all of the NIPHs and NIPHEMs in the genomes to consider.
    get_niphems_in_genomes = {}
    proportion_of_niph_genomes = {}
    genomes_that_are_niphs_and_niphems = {}
    # Process NIPHS.
    for niphs in niphs_in_genomes.values():
        intersection_set = None
        for niph in niphs:
            # Get the ID without the allele identifier.
            niph_genome_id = niph.split('_')[0]
            # Get the ID for the joined IDs.
            id_class_1a = itf.identify_string_in_dict_get_key(niph_genome_id, cds_to_keep['1a'])
            # Get all of the IDs of the genomes that intersect only in the NIPHs (two similiar alleles present in the same genomes).
            if not intersection_set:
                # Get the first set.
                intersection_set = set(niphs_presence_in_genomes[niph])
            else:
                # Get the intersection of the sets.
                intersection_set.intersection_update(niphs_presence_in_genomes[niph])
        # Here id_class_1a or niph_genome_id is the key and mather which one in the order it is since they both are in the same
        # joined group or are in the same cluster.
        genomes_that_are_niphs_and_niphems.setdefault(id_class_1a or niph_genome_id, set()).update(intersection_set)

    # Process NIPHEMs.
    for niphem in list(niphems_presence_in_genome):
        niphem_genome_id = niphem.split('_')[0]
        id_class_1a = itf.identify_string_in_dict_get_key(niphem_genome_id, cds_to_keep['1a'])
        # Add which genomes are present in duplicate for that allele (two or more of the same genome ID).
        ids_of_genomes = itf.get_duplicates(niphems_presence_in_genome[niphem])
        get_niphems_in_genomes.setdefault(id_class_1a or niphem_genome_id, []).append(ids_of_genomes)
        
        # Add identified NIPHEMs to the dict that contains the NIPHs and NIPHEMs.
        # Add the genomes that are NIPHEMs.
        genomes_that_are_niphs_and_niphems.setdefault(id_class_1a or niphem_genome_id, set()).update(set(ids_of_genomes))

    # Get the proportion of NIPHs and NIPHEMs in the genomes for each group were they are present.
    dropped_due_to_niphs_or_niphems = set()
    for key, genomes in list(genomes_that_are_niphs_and_niphems.items()):
        # Remove cases that were dropped in classification phase.
        if key in drop_set:
            continue
        # Get the proportion of NIPHs and NIPHEMs in the genomes.
        proportion = len(genomes) / len(cds_to_keep_all_genomes[key])
        proportion_of_niph_genomes.setdefault(key, proportion)
        # If the proportion is greater than the threshold, remove the group.
        if proportion >= problematic_proportion:
            if cds_to_keep['1a'].get(key):
                del cds_to_keep['1a'][key]
            else:
                class_ = itf.identify_string_in_dict_get_key(key, {key: value for key, value in cds_to_keep.items() if key != '1a'})
                cds_to_keep[class_].remove(key)

            dropped_due_to_niphs_or_niphems.add(key)
            dropped_cluster.setdefault(key, 'Dropped_due_to_NIPHs_and_NIPHEMs')
            drop_set.add(key)
    
    # Write the groups that were removed due to the presence of NIPHs or NIPHEMs.
    niphems_and_niphs_file = os.path.join(results_output, 'niphems_and_niphs_groups.tsv')
    with open(niphems_and_niphs_file, 'w') as niphems_and_niphs:
        niphems_and_niphs.write('Group_ID\tProportion_of_NIPHs_and_NIPHEMs\tOutcome\n')
        for group, proportion in proportion_of_niph_genomes.items():
            niphems_and_niphs.write(f"{group}\t{proportion}\t{'Dropped' if group in dropped_due_to_niphs_or_niphems else 'Kept'}\n")

    return proportion_of_niph_genomes, dropped_due_to_niphs_or_niphems, cds_to_keep_all_members, cds_to_keep_all_genomes

def write_cluster_members_to_file(output_path, cds_to_keep, clusters, frequency_in_genomes, drop_set):
    """
    Write cluster members to file.

    Parameters
    ----------
    output_path : str
        The path where the output will be written.
    cds_to_keep : dict
        The dictionary containing the CDSs to keep.
    clusters : dict
        The dictionary containing the clusters.
    frequency_in_genomes : dict
        Dict that contains sum of frequency of that representatives cluster in the
        genomes of the schema.

    Returns
    -------
    None, writes to file.
    """
    write_cds = cds_to_keep
    write_cds.setdefault('Dropped', drop_set)
    cluster_members_output = os.path.join(output_path, 'cluster_members.tsv')
    with open(cluster_members_output, 'w') as cluster_members_file:
        cluster_members_file.write('Cluster_ID\tRepresentatives_IDs\tRep_cluster_members\tFrequency_of_rep'
                                   '\tClassification\n')
        for class_, cds_list in cds_to_keep.items():
            for cds in cds_list:
                classification = class_
                if class_ == '1a':
                    cluster_members_file.write(str(cds))
                    cds = cds_to_keep[class_][cds]
                else:
                    cluster_members_file.write(cds)
                    cds = [cds]
                for rep_id in cds:
                    cluster_members_file.write('\t' + str(rep_id))
                    cds_ids = [cds_id for cds_id in clusters[rep_id]]
                    for count, cds_id in enumerate(cds_ids):
                        if count == 0:
                            cluster_members_file.write('\t' + cds_id + '\t' + str(frequency_in_genomes[rep_id])
                                                       + '\t' + classification + '\n')
                        else:
                            cluster_members_file.write('\t\t' + cds_id + '\n')

def update_ids_and_save_changes(cds_to_keep, clusters, cds_original_ids, dropped_cluster, results_output):
    """
    Update the IDs based on clustering and joining operations and save the changes.

    This function iterates through each class and its corresponding group of CDS (Coding DNA Sequences) to keep,
    updates the IDs based on the provided clusters and the original to new ID mappings, and saves the final ID changes
    to a TSV (Tab-Separated Values) file in the specified output directory.

    Parameters
    ----------
    cds_to_keep : dict
        A dictionary where each key is a class and each value is a group of CDS to keep.
    clusters : dict
        A dictionary mapping representative IDs to their cluster members.
    cds_original_ids : dict
        A dictionary mapping original IDs to their new IDs after processing.
    dropped_cluster : dict
    A dictionary mapping all of the dropped CDSs to the cause of drop.
    results_output : str
        The directory path where the ID changes file will be saved.

    Notes
    -----
    The function iterates through the `cds_to_keep` dictionary, updating IDs for each CDS based on their membership
    in the provided `clusters`. It generates a new ID for each CDS, updates `cds_original_ids` with these new IDs,
    and writes the original and new IDs to a TSV file named 'cds_id_changes.tsv' in the `results_output` directory.

    The ID updating process involves generating a new ID by appending an index to the main representative ID for each
    CDS in a cluster. This index is incremented for each CDS in the cluster.

    Examples
    --------
    Assuming the existence of appropriate dictionaries for `cds_to_keep`, `clusters`, `cds_original_ids`, and a valid
    path for `results_output`, the function can be called as follows:

    >>> update_ids_and_save_changes(cds_to_keep, clusters, cds_original_ids, '/path/to/output')
    
    This would process the IDs as described and save the changes to '/path/to/output/cds_id_changes.tsv'.
    """

    # Iterate through each class and its CDS group
    for class_, cds_group in cds_to_keep.items():
        for cds in cds_group:
            main_rep = cds  # The main representative ID for the CDS group
            
            # If the class is not '1a', treat the CDS as a single-element list
            if class_ != '1a':
                cds = [cds]
            else:
                # For class '1a', get the CDS group from cds_to_keep
                cds = cds_to_keep[class_][cds]
            
            index = 1  # Initialize an index for creating new IDs
            
            # Iterate through each representative ID in the CDS group
            for rep_id in cds:
                # Get all CDS IDs in the cluster for the representative ID
                cds_ids = [cds_id for cds_id in clusters[rep_id]]
                
                # Iterate through each CDS ID in the cluster
                for cds_id in cds_ids:
                    # Create a new ID using the main representative ID and the index
                    new_id = f"{main_rep}_{index}"
                    # Update the original ID with the new ID in cds_original_ids
                    cds_id = itf.identify_string_in_dict_get_key(cds_id, cds_original_ids)
                    cds_original_ids[cds_id].append(new_id)
                    index += 1  # Increment the index for the next ID

    # Add why CDS was dropped
    for cds_member, cause in dropped_cluster.items():
        cds_id = itf.identify_string_in_dict_get_key(cds_member, cds_original_ids) or cds_member
        if cds_original_ids.get(cds_id):
            cds_original_ids[cds_id].append(cause)
        else:
            cds_original_ids.setdefault(cds_id, [cause])

    # Prepare to write the ID changes to a file
    tab = "\t"
    id_changes_file = os.path.join(results_output, 'cds_id_changes.tsv')
    
    # Open the file and write the header and ID changes
    with open(id_changes_file, 'w') as id_changes:
        id_changes.write('Original_ID\tID_after_clustering\tID_after_joining\n')
        for original_ids, changed_ids in cds_original_ids.items():
            # Write each original ID and its changed IDs to the file
            id_changes.write(f"{original_ids}\t{tab.join(changed_ids)}\n")

def find_new_representatives(reps_trans_dict_cds, trans_dict_cds, groups_paths_reps, groups_paths):
    pass

def classify_cds(schema, output_directory, allelecall_directory, constants, temp_paths, cpu):

    temp_folder = temp_paths[0]
    file_path_cds = temp_paths[1]
    #missing_classes_fastas = temp_paths[2]

    # Verify if the dataset is small, if it is, keep minimum genomes in which
    # specific CDS cluster is present to 5 if not to 1% of the dataset size.
    count_genomes_path = os.path.join(temp_folder, '1_cds_prediction')
    if not constants[2]:
        number_of_genomes = len(ff.get_paths_in_directory_with_suffix(count_genomes_path, '.fasta'))
        if number_of_genomes <= 20:
            constants[2] = 5
        else:
            constants[2] = round(number_of_genomes * 0.01)
    # Get all of the genomes IDs.
    genomes_ids = ff.get_paths_in_directory_with_suffix(count_genomes_path, '.fasta')

    print("Identifying CDS present in the schema...")
    cds_present = os.path.join(temp_folder,"2_cds_preprocess/cds_deduplication/distinct.hashtable")
    # Get dict of CDS and their sequence hashes.
    decoded_sequences_ids = itf.decode_CDS_sequences_ids(cds_present)

    print("Identifying CDS not present in the schema...")
    # Get dict with CDS ids as key and sequence as values.
    not_included_cds = sf.fetch_fasta_dict(file_path_cds, True)
    #Make IDS universally usable
    for key, value in list(not_included_cds.items()):
        not_included_cds[itf.replace_by_regex(key, '_', '-')] = not_included_cds.pop(key)

    print("\nFiltering missing CDS in the schema...")
    # Count CDS size
    cds_size = {}
    for key, sequence in not_included_cds.items():
        cds_size.setdefault(key, len(str(sequence)))

    dropped_cluster = {}
    total_cds = len(not_included_cds)
    print(f"\nIdentified {total_cds} valid CDS not present in the schema.")
    # Filter by size.
    if constants[5]:
        for key, values in list(not_included_cds.items()):
            if len(values) < constants[5]:
                dropped_cluster.setdefault(key, 'Dropped_due_to_genome_size')
                del not_included_cds[key]
        print(f"{len(not_included_cds)}/{total_cds} have size greater or equal to {constants[5]} bp.")
    else:
        constants[5] = 0
        print("No size threshold was applied to the CDS filtering.")

    # Create directories.
    ff.create_directory(output_directory)

    cds_output = os.path.join(output_directory, '1_CDS_processing')
    ff.create_directory(cds_output)
    # This file contains unique CDS.
    cds_not_present_file_path = os.path.join(cds_output, 'CDS_not_found.fasta')

    # Count the number of CDS not present in the schema and write CDS sequence
    # into a FASTA file.
    frequency_cds = {}
    cds_presence_in_genomes = {}

    with open(cds_not_present_file_path, 'w+') as cds_not_found:
        for id_, sequence in list(not_included_cds.items()):
            cds_not_found.write(f">{id_}\n{str(sequence)}\n")
            
            hashed_seq = sf.seq_to_hash(str(sequence))
            # if CDS sequence is present in the schema count the number of
            # genomes that it is found minus the first (subtract the first CDS genome).
            if hashed_seq in decoded_sequences_ids:
                #Count frequency.
                frequency_cds[id_] = len(decoded_sequences_ids[hashed_seq][1:])
                cds_presence_in_genomes.setdefault(id_, decoded_sequences_ids[hashed_seq][1:])
            else:
                frequency_cds[id_] = 0

    print("\nTranslate and deduplicate CDS...")
    # Translate the CDS and find unique proteins using hashes, the CDS with
    # the same hash will be added under that hash in protein_hashes.
    cds_not_present_trans_file_path = os.path.join(cds_output, "CDS_not_found_translation.fasta")
    cds_not_present_untrans_file_path = os.path.join(cds_output, "CDS_not_found_untranslated.fasta")
    # Translate and deduplicate protein sequences.
    cds_translation_dict, protein_hashes, _ = sf.translate_seq_deduplicate(not_included_cds,
                                                                           cds_not_present_trans_file_path,
                                                                           cds_not_present_untrans_file_path,
                                                                           constants[5],
                                                                           True,
                                                                           constants[6],
                                                                           True)
    # Count translation sizes.
    cds_translation_size = {}
    for key, sequence in cds_translation_dict.items():
        cds_translation_size.setdefault(key, len(sequence))

    # Print additional information about translations and deduplications.
    print(f"\n{len(cds_translation_dict)}/{len(not_included_cds)} unique protein translations.")
    
    print("\nIdentify problematics CDSs...")
    [niphems_presence_in_genome,
     niphs_in_genomes,
     niphs_presence_in_genomes] = identify_problematic_cds(cds_presence_in_genomes,
                                                           cds_translation_dict,
                                                           protein_hashes,
                                                           not_included_cds,
                                                           cds_output,
                                                           constants[7],
                                                           dropped_cluster,
                                                           cpu)

    print("\nExtracting minimizers for the translated sequences and clustering...")
    # Create variables to store clustering info.
    reps_groups = {}
    clusters = {}
    reps_sequences = {}

    # Sort by size of proteins.
    cds_translation_dict = {k: v for k, v in sorted(cds_translation_dict.items(),
                                                    key=lambda x: len(x[1]),
                                                    reverse=True)}
    # Cluster by minimizers.
    [clusters, reps_sequences, 
     reps_groups, prot_len_dict] = cf.minimizer_clustering(cds_translation_dict,
                                                           5,
                                                           5,
                                                           True,
                                                           1, 
                                                           clusters,
                                                           reps_sequences, 
                                                           reps_groups,
                                                           1,
                                                           constants[3], 
                                                           constants[4],
                                                           True)

    # Reformat the clusters output, we are interested only in  the ID of cluster members.
    clusters = {cluster_rep: [value[0] for value in values]
                for cluster_rep, values in clusters.items()}
    # For protein hashes get only those that have more than one CDS.
    filtered_protein_hashes = {hash_prot: cds_ids for hash_prot, cds_ids in protein_hashes.items()
                      if len(cds_ids) > 1}
    # Add also the unique CDS ID to clusters that have the same protein as representative.
    for cluster_rep, values in list(clusters.items()):
        for cds_id in list(values):
            protein_hash = itf.identify_string_in_dict_get_key(cds_id, filtered_protein_hashes)
            if protein_hash:
                clusters[cluster_rep] += filtered_protein_hashes[protein_hash][1:]

    total_number_clusters = len(clusters)
    print(f"{len(cds_translation_dict)} unique proteins have been clustered into {total_number_clusters} clusters.")
    singleton_cluster = len([cluster for cluster in clusters if len(cluster) == 1])
    print(f"\tOut of those clusters, {singleton_cluster} are singletons")
    print(f"\tOut of those clusters, {total_number_clusters - singleton_cluster} have more than one CDS.")
    print("\nFiltering clusters...")
    # Get frequency of cluster.
    frequency_in_genomes = {rep: sum([frequency_cds[entry] for entry in value]) 
                             for rep, value in clusters.items()}
    # Add reason for filtering out CDS.
    dropped_cluster.update({cds_id: 'Dropped_due_to_cluster_frequency_filtering' for cds_id in itf.flatten_list([clusters[rep] for rep in clusters if frequency_in_genomes[rep] < constants[2]])})
    # Filter cluster by the total sum of CDS that are present in the genomes, based on input value.
    clusters = {rep: cluster_member for rep, cluster_member in clusters.items() 
                if frequency_in_genomes[rep] >= constants[2]}
    cds_original_ids = {}
    # Replace the IDS of cluster alleles to x_1 and replace all of the alleles in
    # the variables.
    for cluster, members in list(clusters.items()):
        i = 0
        new_members_ids = []
        for member in list(members):
            # Get the new ID.
            new_id = f"{cluster}_{i}" if i != 0 else member
            # Add the new ID to the dict.
            cds_original_ids[member] = [new_id]
            # Replace the old ID with the new ID for frequency_cds.
            frequency_cds[new_id] = frequency_cds.pop(member)
            # Save the new members IDs.
            new_members_ids.append(new_id)
            # Replace the old ID with the new ID for the DNA sequences.
            not_included_cds[new_id] = not_included_cds.pop(member)
            # Replace in hashes dict
            translation_hash = itf.identify_string_in_dict_get_key(member, protein_hashes)
            index = protein_hashes[translation_hash].index(member)
            # Replace the old ID with the new ID for the translation sequences.
            # Since only representatives are in the dict we first check if it is present
            if cds_translation_dict.get(member):
                cds_translation_dict[new_id] = cds_translation_dict.pop(member)
            else: # Add the sequences previousy deduplicated
                rep_id = protein_hashes[translation_hash][0]
                cds_translation_dict[new_id] = cds_translation_dict[rep_id]

            # Replace the value at the found index
            protein_hashes[translation_hash][index] = new_id  # Replace `new_id` with the actual value you want to set
            # Replace the old ID with the new ID for the protein hashes.
            cds_presence_in_genomes[new_id] = cds_presence_in_genomes.pop(member)
            # Replace the old ID with the new ID for the NIPHEMs dict.
            if niphems_presence_in_genome.get(member):
                niphems_presence_in_genome[new_id] = niphems_presence_in_genome.pop(member)
            # Replace the old ID with the new ID for the NIPHs genome dict.
            if niphs_presence_in_genomes.get(member):
                niphs_presence_in_genomes[new_id] = niphs_presence_in_genomes.pop(member)
            # Replace the old ID with the new ID for the CDSs that matched as NIPHs.
            niphs_group_id = itf.identify_string_in_dict_get_key(member, niphs_in_genomes)
            if niphs_group_id:
                niphs_group_member_index = niphs_in_genomes[niphs_group_id].index(member)
                niphs_in_genomes[niphs_group_id][niphs_group_member_index] = new_id
            i += 1
        clusters[cluster] = new_members_ids
    # Join NIPHS and NIPHEMS into the same cluster

    print(f"After filtering by CDS frequency in the genomes (>= {constants[2]}),"
          f" out of {total_number_clusters} clusters, {len(clusters)} remained.")
    
    intial_length = len(clusters)

    if intial_length != len(clusters):
        print(f"After filtering by CDS frequency in the genomes (>= {len(genomes_ids)}),"
              f" out of {intial_length} clusters, {len(clusters)} remained.") 
    
    print("\nRetrieving kmers similiarity and coverage between representatives...")
    reps_kmers_sim = {}
    # Get the representatives protein sequence.
    reps_translation_dict = {rep_id: rep_seq for rep_id, rep_seq in cds_translation_dict.items()
                             if rep_id in clusters}
    # Sort the representative translation dict from largest to smallest.
    reps_translation_dict = {k: v for k, v in sorted(reps_translation_dict.items(),
                                                     key=lambda x: len(x[1]),
                                                     reverse=True)}
    # recalculate the sim and cov between reps, get all of the values, so threshold
    # is set to 0.
    for cluster_id in reps_translation_dict:
        kmers_rep = set(kf.determine_minimizers(reps_translation_dict[cluster_id],
                                                5,
                                                5,
                                                1,
                                                True,
                                                True))
        
        reps_kmers_sim[cluster_id] = cf.select_representatives(kmers_rep,
                                                               reps_groups,
                                                               0,
                                                               0,
                                                               prot_len_dict,
                                                               cluster_id,
                                                               5)

        reps_kmers_sim[cluster_id] = {match_values[0]: match_values[1:]
                                      for match_values in reps_kmers_sim[cluster_id]}

    # Create directories.
    blast_output = os.path.join(output_directory, '2_BLAST_processing')
    ff.create_directory(blast_output)
    
    blastn_output = os.path.join(blast_output, '1_BLASTn_processing')
    ff.create_directory(blastn_output)
    # Create directory and files path where to write FASTAs.
    representatives_blastn_folder = os.path.join(blastn_output,
                                                'cluster_representatives_fastas')
    ff.create_directory(representatives_blastn_folder)

    representatives_all_fasta_file = os.path.join(representatives_blastn_folder,
                                                  'all_clusters.fasta')
    # Write files for BLASTn.
    rep_paths_nuc = {}
    # Write master file for the representatives.
    with open(representatives_all_fasta_file, 'w') as all_fasta:
        for cluster_rep_id, members in clusters.items():
            for member in members:
                all_fasta.write(f">{member}\n{str(not_included_cds[member])}\n")

            rep_fasta_file = os.path.join(representatives_blastn_folder,
                                          f"cluster_rep_{cluster_rep_id}.fasta")
            rep_paths_nuc[cluster_rep_id] = rep_fasta_file
            # Write the representative FASTA file.
            with open(rep_fasta_file, 'w') as rep_fasta:
                rep_fasta.write(f">{cluster_rep_id}\n{str(not_included_cds[cluster_rep_id])}\n")
    
    # Create BLAST db for the schema DNA sequences.
    print("\nCreating BLASTn database for the unclassified and missed CDSs...")
    # Get the path to the makeblastdb executable.
    makeblastdb_exec = lf.get_tool_path('makeblastdb')
    blast_db = os.path.join(blastn_output, 'blast_db_nucl', 'blast_nucleotide_db')
    bf.make_blast_db(makeblastdb_exec, representatives_all_fasta_file, blast_db, 'nucl')

    # Run the BLASTn and BLASTp
    run_type = 'cds_vs_cds' # Set run type as cds_vs_cds
    [representative_blast_results,
     representative_blast_results_coords_all,
     representative_blast_results_coords_pident,
     bsr_values,
     _] = run_blasts(blast_db,
                        clusters,
                        cds_translation_dict,
                        rep_paths_nuc,
                        blast_output,
                        constants,
                        cpu,
                        clusters,
                        run_type)
    
    # Add various results to the dict
    add_items_to_results(representative_blast_results,
                         reps_kmers_sim,
                         bsr_values,
                         representative_blast_results_coords_all,
                         representative_blast_results_coords_pident,
                         frequency_in_genomes,
                         [False, True],
                         clusters)

    print("\nFiltering BLAST results into classes...")
    results_output = os.path.join(output_directory, '3_CDS_processing_results')
    ff.create_directory(results_output)
    blast_results = os.path.join(results_output, 'blast_results')
    ff.create_directory(blast_results)
    report_file_path = os.path.join(blast_results, 'blast_all_matches.tsv')
    
    # Separate results into different classes.
    classes_outcome = separate_blastn_results_into_classes(representative_blast_results,
                                                           constants)
    # Write all of the BLASTn results to a file.
    alignment_dict_to_file(representative_blast_results, report_file_path, 'w')
    
    print("\nProcessing classes...")
    sorted_blast_dict = sort_blast_results_by_classes(representative_blast_results, classes_outcome)
    # Process the results_outcome dict and write individual classes to TSV file.
    [processed_results,
     count_results_by_class,
     count_results_by_class_with_inverse,
     reps_and_alleles_ids,
     drop_mark] = process_classes(sorted_blast_dict,
                                classes_outcome,
                                clusters)

    count_results_by_class = itf.sort_subdict_by_tuple(count_results_by_class, classes_outcome)

    cds_to_keep, drop_set = extract_cds_to_keep(classes_outcome, count_results_by_class, drop_mark)

    cds_to_keep['1a'] = {values[0]: values for key, values in cds_to_keep['1a'].items()}
    
    # Add new frequencies in genomes for joined groups
    # Update the changed clusters frequency from Joined CDSs
    updated_frequency_in_genomes = {}
    new_cluster_freq = {}
    for cluster_id, cluster_members in cds_to_keep['1a'].items():
        new_cluster_freq[cluster_id] = 0
        for member in cluster_members:
            new_cluster_freq[(cluster_id)] += frequency_in_genomes[member]
        for member in cluster_members:
            updated_frequency_in_genomes[member] = new_cluster_freq[cluster_id]
    #Add all the others frequencies.
    updated_frequency_in_genomes.update(frequency_in_genomes)
    updated_frequency_in_genomes.update(new_cluster_freq)

    group_reps_ids = {}
    group_alleles_ids = {}
    count_number_of_reps_and_alleles(cds_to_keep, clusters, drop_set, group_reps_ids, group_alleles_ids)
    
    print("\nAdd remaining cluster that didn't match by BLASTn...")
    # Add cluster not matched by BLASTn
    cds_to_keep['Retained_not_matched_by_blastn'] = set([cluster for cluster in clusters.keys() if cluster not in representative_blast_results.keys()])
    print("\nFiltering problematic probable new loci...")

    [proportion_of_niph_genomes,
     dropped_due_to_niphs_or_niphems,
     cds_to_keep_all_members,
     cds_to_keep_all_genomes] = remove_problematic_loci(niphems_presence_in_genome, niphs_in_genomes, niphs_presence_in_genomes,
                                                        cds_presence_in_genomes, cds_to_keep, clusters, drop_set, constants[8], 
                                                        dropped_cluster, results_output)

    print("\nExtracting results...")
    all_relationships, related_clusters, recommendations = extract_results(processed_results,
                                                                          count_results_by_class,
                                                                          frequency_in_genomes,
                                                                          cds_to_keep,
                                                                          drop_set,
                                                                          classes_outcome)
    print("\nWritting count_results_by_cluster.tsv and related_matches.tsv files...")
    write_blast_summary_results(related_clusters,
                                count_results_by_class_with_inverse,
                                group_reps_ids,
                                group_alleles_ids,
                                frequency_in_genomes,
                                recommendations,
                                True,
                                results_output)

    print("\nWritting classes and cluster results to files...")
    write_processed_results_to_file(cds_to_keep,
                                    representative_blast_results,
                                    classes_outcome,
                                    None,
                                    None,
                                    None,
                                    None,
                                    [False, False],
                                    blast_results)
    
    print("\nUpdating IDs and saving changes...")
    dropped_cluster.update({id_ : 'Dropped_due_to_frequency' for id_ in itf.flatten_list([clusters[i] for i in drop_set])})
    update_ids_and_save_changes(cds_to_keep, clusters, cds_original_ids, dropped_cluster, results_output)

    print("\nWritting possible new loci Fastas...")
    [groups_paths_reps,
     groups_paths,
     reps_trans_dict_cds,
     trans_dict_cds,
     master_file,
     alleles] = wrap_up_blast_results(cds_to_keep,
                                              not_included_cds,
                                              clusters,
                                              results_output,
                                              constants,
                                              drop_set,
                                              None,
                                              None,
                                              frequency_in_genomes,
                                              run_type)
    
    print("Identifying new representatives for possible new loci...")
    find_new_representatives(reps_trans_dict_cds, trans_dict_cds, groups_paths_reps, groups_paths)
    write_cluster_members_to_file(results_output, cds_to_keep, clusters, frequency_in_genomes,
                                  drop_set)

    print("Create graphs for the BLAST results...")
    cds_size_dicts = {'IDs': cds_size.keys(),
                      'Size': cds_size.values()}
    cds_translation_size_dicts = {'IDs': cds_size.keys(),
                                  'Size': [int(cds/3) for cds in cds_size.values()]}
    create_graphs(report_file_path,
                  results_output,
                  'All_of_CDS_graphs',
                  [[cds_size_dicts, 'histogram', "Nucleotide Size", 'Size', 'CDS'],
                   [cds_translation_size_dicts, 'histogram','Protein Size' , 'Size', 'CDS']])
    
    for file in ff.get_paths_in_directory(os.path.join(blast_results, 'blast_results_by_class'), 'files'):
        create_graphs(file,
                      results_output,
                      f"graphs_class_{os.path.basename(file).split('_')[-1].replace('.tsv', '')}")

    print("\nReading schema loci short FASTA files...")
    # Create directory
    results_output = os.path.join(output_directory, '4_Schema_processing')
    ff.create_directory(results_output)

    allele_ids = [True, True]
    run_type = 'loci_vs_cds' # Set run type as loci_vs_cds
    # Run Blasts for the found loci against schema short
    representative_blast_results = process_schema(schema,
                                                  groups_paths,
                                                  results_output,
                                                  trans_dict_cds,
                                                  alleles,
                                                  updated_frequency_in_genomes,
                                                  allelecall_directory, 
                                                  master_file,
                                                  allele_ids,
                                                  run_type,
                                                  False,
                                                  constants,
                                                  cpu)