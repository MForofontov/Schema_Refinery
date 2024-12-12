import os
from typing import Dict, List, Set, Union, Tuple

try:
    from utils import (file_functions as ff,
                       sequence_functions as sf,
                       clustering_functions as cf,
                       iterable_functions as itf,
                       kmers_functions as kf,)
except ModuleNotFoundError:
    from SchemaRefinery.utils import (file_functions as ff,
                                        sequence_functions as sf,
                                        clustering_functions as cf,
                                        iterable_functions as itf,
                                        kmers_functions as kf,)

def write_dropped_cds_to_file(dropped_cds: Dict[str, str], results_output: str) -> None:
    """
    Write dropped CDS to file.

    Parameters
    ----------
    dropped_cds : Dict[str, str]
        The dictionary containing the dropped CDSs and their reasons.
    results_output : str
        The path where the output will be written.

    Returns
    -------
    None
        Writes to file.
    """
    dropped_cds_output: str = os.path.join(results_output, 'dropped_cds.tsv')
    with open(dropped_cds_output, 'w') as dropped_cds_file:
        dropped_cds_file.write('CDS_ID\tReason_for_dropping\n')
        for cds_id, reason in dropped_cds.items():
            dropped_cds_file.write(f"{cds_id}\t{reason}\n")

def update_ids_and_save_changes(clusters_to_keep: Dict[str, List[str]], 
                                clusters: Dict[str, List[str]], 
                                cds_original_ids: Dict[str, List[str]], 
                                dropped_cds: Dict[str, str],
                                all_nucleotide_sequences: Dict[str, str], 
                                results_output: str) -> None:
    """
    Update the IDs based on clustering and joining operations and save the changes.

    This function iterates through each class and its corresponding group of CDS (Coding DNA Sequences) to keep,
    updates the IDs based on the provided clusters and the original to new ID mappings, and saves the final ID changes
    to a TSV (Tab-Separated Values) file in the specified output directory.

    Parameters
    ----------
    clusters_to_keep : Dict[str, List[str]]
        A dictionary where each key is a class and each value is a list of CDS to keep.
    clusters : Dict[str, List[str]]
        A dictionary mapping representative IDs to their cluster members.
    cds_original_ids : Dict[str, List[str]]
        A dictionary mapping original IDs to their new IDs after processing.
    dropped_cds : Dict[str, str]
        A dictionary mapping all of the dropped CDSs to the cause of drop.
    all_nucleotide_sequences : Dict[str, str]
        A dictionary that contains DNA sequences for each CDS.
    results_output : str
        The directory path where the ID changes file will be saved.

    Returns
    -------
    None
        The function writes the output files to the specified directory.

    Notes
    -----
    The function iterates through the `clusters_to_keep` dictionary, updating IDs for each CDS based on their membership
    in the provided `clusters`. It generates a new ID for each CDS, updates `cds_original_ids` with these new IDs,
    and writes the original and new IDs to a TSV file named 'cds_id_changes.tsv' in the `results_output` directory.

    The ID updating process involves generating a new ID by appending an index to the main representative ID for each
    CDS in a cluster. This index is incremented for each CDS in the cluster.

    Examples
    --------
    Assuming the existence of appropriate dictionaries for `clusters_to_keep`, `clusters`, `cds_original_ids`, and a valid
    path for `results_output`, the function can be called as follows:

    >>> update_ids_and_save_changes(clusters_to_keep, clusters, cds_original_ids, dropped_cds, all_nucleotide_sequences, '/path/to/output')
    
    This would process the IDs as described and save the changes to '/path/to/output/cds_id_changes.tsv'.
    """

    # Iterate through each class and its CDS group
    for class_, cds_group in clusters_to_keep.items():
        for cds in cds_group:
            main_rep: str = cds  # The main representative ID for the CDS group
            
            # If the class is not '1a', treat the CDS as a single-element list
            if class_ != '1a':
                cds = [cds]
            else:
                # For class '1a', get the CDS group from clusters_to_keep
                cds = clusters_to_keep[class_][cds]
            
            index: int = 1  # Initialize an index for creating new IDs
            
            # Iterate through each representative ID in the CDS group
            for rep_id in list(cds):
                # Get all CDS IDs in the cluster for the representative ID
                cds_ids: List[str] = clusters[rep_id]
                # Delete clusters with old IDs
                del clusters[rep_id]
                # Create new rep ID
                # Iterate through each CDS ID in the cluster
                for cds_id in list(cds_ids):
                    # Skip cases
                    if cds_id in dropped_cds:
                        continue
                    if not clusters.get(rep_id):
                        clusters[rep_id] = []
                    # Create a new ID using the main representative ID and the index
                    new_id: str = f"{main_rep}_{index}"
                    # Update the original ID with the new ID in cds_original_ids
                    cds_id_first: str = itf.identify_string_in_dict_get_key(cds_id, cds_original_ids)
                    cds_id_second: str = itf.identify_string_in_dict_get_value(cds_id, cds_original_ids)[-1]
                    # Replace in FASTA dict
                    all_nucleotide_sequences[new_id] = all_nucleotide_sequences.pop(cds_id_second)
                    # Add new cluster ID
                    clusters[rep_id].append(new_id)
                    cds_original_ids[cds_id_first].append(new_id)
                    index += 1  # Increment the index for the next ID
            
    # Prepare to write the ID changes to a file
    tab: str = "\t"
    id_changes_file: str = os.path.join(results_output, 'cds_id_changes.tsv')
    
    # Open the file and write the header and ID changes
    with open(id_changes_file, 'w') as id_changes:
        id_changes.write('Original_ID\tID_after_clustering\tID_after_joining\n')
        for original_ids, changed_ids in cds_original_ids.items():
            # Write each original ID and its changed IDs to the file
            id_changes.write(f"{original_ids}\t{tab.join(changed_ids)}\n")


def remove_dropped_cds_from_analysis(dropped_cds: Dict[str, str], 
                                     all_nucleotide_sequences: Dict[str, str],
                                     cds_translation_dict: Dict[str, str], 
                                     protein_hashes: Dict[str, List[str]]) -> None:
    """
    Removes dropped CDS from the analysis based on the provided parameters.

    Parameters
    ----------
    dropped_cds : Dict[str, str]
        Dictionary containing dropped CDS with their reasons.
    all_nucleotide_sequences : Dict[str, str]
        Dictionary of allele IDs and their corresponding DNA sequences.
    cds_translation_dict : Dict[str, str]
        Dictionary mapping CDS to their translations.
    protein_hashes : Dict[str, List[str]]
        Dictionary mapping protein hashes to their associated CDS.

    Returns
    -------
    None
        The function updates the dictionaries in place and does not return any value.

    Notes
    -----
    The function iterates through the `dropped_cds` dictionary and removes the dropped CDS from the analysis.
    It updates the `dropped_cds` dictionary with similar protein IDs, removes the CDS from the `all_nucleotide_sequences`,
    `cds_translation_dict`, and `protein_hashes` dictionaries, and ensures that protein hashes with no associated CDS
    are removed from the `protein_hashes` dictionary.
    """
    for dropped_id, reason in list(dropped_cds.items()):
        if cds_translation_dict.get(dropped_id):
            for similar_protein_id in itf.identify_string_in_dict_get_value(dropped_id, protein_hashes):
                dropped_cds[similar_protein_id] = reason

    for dropped_id, reason in list(dropped_cds.items()):
        # Remove from associated translation hashes dict.
        translation_hash: str = itf.identify_string_in_dict_get_key(dropped_id, protein_hashes)
        if translation_hash is not None:
            dropped_cds[dropped_id] = reason
            if all_nucleotide_sequences.get(dropped_id):
                del all_nucleotide_sequences[dropped_id]
            # If this CDS is the representative in translation dict
            if cds_translation_dict.get(dropped_id):
                del cds_translation_dict[dropped_id]
            protein_hashes[itf.identify_string_in_dict_get_key(dropped_id, protein_hashes)].remove(dropped_id)
            # Remove all hash of the protein if it has no more CDS associated with it.
            if len(protein_hashes[translation_hash]) == 0:
                del protein_hashes[translation_hash]


def replace_ids_in_clusters(clusters: Dict[str, List[str]], 
                            frequency_cds: Dict[str, int], 
                            dropped_cds: Dict[str, str], 
                            all_nucleotide_sequences: Dict[str, str], 
                            prot_len_dict: Dict[str, int],
                            cds_translation_dict: Dict[str, str], 
                            protein_hashes: Dict[str, List[str]], 
                            cds_presence_in_genomes: Dict[str, List[str]],
                            reps_kmers_sim: Dict[str, Dict[str, List[int]]]) -> Dict[str, List[str]]:
    """
    Replace the IDs of cluster alleles with new IDs in the format 'cluster_x' and update all relevant dictionaries.

    Parameters
    ----------
    clusters : Dict[str, List[str]]
        Dictionary of clusters with their members.
    frequency_cds : Dict[str, int]
        Dictionary mapping CDS IDs to their frequencies.
    dropped_cds : Dict[str, str]
        Dictionary of dropped CDS IDs.
    all_nucleotide_sequences : Dict[str, str]
        Dictionary of allele IDs and their DNA sequences.
    prot_len_dict : Dict[str, int]
        Dictionary mapping CDS IDs to their protein lengths.
    cds_translation_dict : Dict[str, str]
        Dictionary mapping CDS IDs to their translation sequences.
    protein_hashes : Dict[str, List[str]]
        Dictionary mapping protein hashes to lists of CDS IDs.
    cds_presence_in_genomes : Dict[str, List[str]]
        Dictionary mapping CDS IDs to their presence in genomes.
    reps_kmers_sim : Dict[str, Dict[str, List[int]]]
        Dictionary mapping representative cluster IDs to their k-mer similarities.

    Returns
    -------
    cds_original_ids : Dict[str, List[str]]
        Dictionary mapping original CDS IDs to their new IDs.

    Notes
    -----
    The function iterates through the `clusters` dictionary, replacing the IDs of cluster alleles with new IDs in the format
    'cluster_x'. It updates all relevant dictionaries (`frequency_cds`, `dropped_cds`, `all_nucleotide_sequences`, `prot_len_dict`,
    `cds_translation_dict`, `protein_hashes`, `cds_presence_in_genomes`, and `reps_kmers_sim`) with the new IDs.

    Examples
    --------
    Assuming the existence of appropriate dictionaries for `clusters`, `frequency_cds`, `dropped_cds`, `all_nucleotide_sequences`,
    `prot_len_dict`, `cds_translation_dict`, `protein_hashes`, `cds_presence_in_genomes`, and `reps_kmers_sim`, the function can be called as follows:

    >>> replace_ids_in_clusters(clusters, frequency_cds, dropped_cds, all_nucleotide_sequences, prot_len_dict, cds_translation_dict, protein_hashes, cds_presence_in_genomes, reps_kmers_sim)
    
    This would process the IDs as described and update all relevant dictionaries.
    """
    cds_original_ids: Dict[str, List[str]] = {}
    # Replace the IDs of cluster alleles to x_1 and replace all of the alleles in the variables.
    for cluster, members in list(clusters.items()):
        i: int = 1
        new_members_ids: List[str] = []
        for member in list(members):
            # Get the new ID.
            new_id: str = f"{cluster}_{i}"
            # Add the new ID to the dict.
            cds_original_ids[member] = [new_id]
            # Replace the old ID with the new ID for frequency_cds.
            frequency_cds[new_id] = frequency_cds.pop(member)
            # Dropped cds
            dropped_id: str = itf.identify_string_in_dict_get_key(member, dropped_cds)
            if dropped_id is not None:
                dropped_cds[new_id] = dropped_cds.pop(dropped_id)
            # Save the new members IDs.
            new_members_ids.append(new_id)
            # Replace the old ID with the new ID for the DNA sequences.
            all_nucleotide_sequences[new_id] = all_nucleotide_sequences.pop(member)
            # Replace in hashes dict
            translation_hash: str = itf.identify_string_in_dict_get_key(member, protein_hashes)
            # Replace in prot_len_dict
            if prot_len_dict.get(member):
                prot_len_dict[new_id] = prot_len_dict.pop(member)

            index: int = protein_hashes[translation_hash].index(member)
            # Replace the old ID with the new ID for the translation sequences.
            # Since only representatives are in the dict we first check if it is present
            if cds_translation_dict.get(member):
                cds_translation_dict[new_id] = cds_translation_dict.pop(member)
            else: # Add the sequences previously deduplicated
                rep_id: str = protein_hashes[translation_hash][0]
                cds_translation_dict[new_id] = cds_translation_dict[rep_id]

            # Replace the value at the found index
            protein_hashes[translation_hash][index] = new_id  # Replace `new_id` with the actual value you want to set
            # Replace the old ID with the new ID for the protein hashes.
            cds_presence_in_genomes[new_id] = cds_presence_in_genomes.pop(member)
            i += 1
        clusters[cluster] = new_members_ids
    # Change IDs in reps_kmers_sim
    for cds_id, elements_id in list(reps_kmers_sim.items()):
        new_id_key = cds_original_ids.get(cds_id)[0]
        reps_kmers_sim.setdefault(new_id_key, {})
        for element_id, kmers in elements_id.items():
            if cds_original_ids.get(element_id):
                new_id: str = cds_original_ids[element_id][0]
            reps_kmers_sim[new_id_key].setdefault(new_id, kmers)
        del reps_kmers_sim[cds_id]

    return cds_original_ids

            
def write_temp_loci(clusters_to_keep: Dict[str, List[str]], 
                    all_nucleotide_sequences: Dict[str, str], 
                    clusters: Dict[str, List[str]], 
                    output_path: str) -> Dict[str, str]:
    """
    This function wraps up the results for processing of the unclassified CDSs
    by writing FASTA files for the possible new loci to include.
    
    Parameters
    ----------
    clusters_to_keep : Dict[str, List[str]]
        Dictionary of the CDS to keep by each classification.
    all_nucleotide_sequences : Dict[str, str]
        Dictionary that contains all of the DNA sequences for all of the alleles.
    clusters : Dict[str, List[str]]
        Dictionary that contains the cluster representatives as keys and similar CDS
        as values.
    output_path : str
        Path to where the FASTA files will be written.

    Returns
    -------
    temp_fastas_paths : Dict[str, str]
        Dictionary that contains as keys the ID of each group while the value is the
        path to the FASTA file that contains its nucleotide sequences.
    """
    def write_possible_new_loci(class_: str, 
                                cds_list: List[str], 
                                temp_fastas: str,
                                groups_paths: Dict[str, str], 
                                all_nucleotide_sequences: Dict[str, str],
                                clusters: Dict[str, List[str]]) -> None:
        """
        Process each class and CDS list in clusters_to_keep.

        Parameters
        ----------
        class_ : str
            The class type.
        cds_list : List[str]
            The list of CDSs.
        temp_fastas : str
            The path to the temp FASTAs folder.
        groups_paths : Dict[str, str]
            The dictionary containing the paths to the groups.
        all_nucleotide_sequences : Dict[str, str]
            The dictionary containing DNA sequences for each allele.
        clusters : Dict[str, List[str]]
            The dictionary containing the clusters.

        Returns
        -------
        None
            Writes FASTA files.
        """
        for cds in cds_list:
            main_rep: str = cds
            cds_group_fasta_file: str = os.path.join(temp_fastas, main_rep + '.fasta')
            groups_paths[main_rep] = cds_group_fasta_file
            save_ids_index: Dict[str, str] = {}
            if class_ != '1a':
                cds = [cds]
            else:
                cds = clusters_to_keep[class_][cds]
            index: int = 1
            # Write all of the alleles to the files.
            with open(cds_group_fasta_file, 'w') as fasta_file:
                for rep_id in cds:
                    cds_ids: List[str] = clusters[rep_id]
                    for cds_id in cds_ids:
                        # Save the new ID to the dictionary where the old ID is the key.
                        save_ids_index[cds_id] = cds_id
                        # Write the allele to the file.
                        fasta_file.write(f">{index}\n{str(all_nucleotide_sequences[cds_id])}\n")
                        index += 1

    temp_fastas_paths: Dict[str, str] = {}
    print("Writing FASTA and additional files for possible new loci...")
    temp_fastas_folder: str = os.path.join(output_path, 'temp_fastas')
    ff.create_directory(temp_fastas_folder)
    # Process each class and CDS list in clusters_to_keep
    for class_, cds_list in clusters_to_keep.items():
        write_possible_new_loci(class_, cds_list, temp_fastas_folder,
                                temp_fastas_paths, all_nucleotide_sequences,
                                clusters)
        
    fastas_paths_txt: str = os.path.join(output_path, "temp_fastas_path.txt")
    with open(fastas_paths_txt, 'w') as fastas_path:
        for path in temp_fastas_paths.values():
            fastas_path.write(path + '\n')

    return temp_fastas_paths, fastas_paths_txt, temp_fastas_folder


def set_minimum_genomes_threshold(temp_folder: str, constants: List[Union[int, float]]) -> None:
    """
    Sets the minimum genomes threshold based on the dataset size.

    Parameters
    ----------
    temp_folder : str
        Path to the temporary folder containing genome data.
    constants : List[Union[int, float]]
        List of constants where the threshold will be set.

    Returns
    -------
    None
        The function updates the constants list in place.
    """
    count_genomes_path: str = os.path.join(temp_folder, '1_cds_prediction')
    
    try:
        genome_files: List[str] = ff.get_paths_in_directory_with_suffix(count_genomes_path, '.fasta')
        number_of_genomes: int = len(genome_files)
        
        if number_of_genomes <= 20:
            constants[2] = 5
        else:
            constants[2] = round(number_of_genomes * 0.01)
    except Exception as e:
        print(f"Error setting minimum genomes threshold: {e}")
        constants[2] = 5  # Default value in case of error


def filter_cds_by_size(all_nucleotide_sequences: Dict[str, str], size_threshold: int) -> Tuple[Dict[str, int], Dict[str, str], Dict[str, str]]:
    """
    Filters CDS by their size and updates the dropped CDS dictionary.

    Parameters
    ----------
    all_nucleotide_sequences : Dict[str, str]
        Dictionary with CDS IDs as keys and sequences as values.
    size_threshold : int
        Minimum size threshold for CDS.

    Returns
    -------
    Tuple[Dict[str, int], Dict[str, str], Dict[str, str]]
        A tuple containing the CDS size dictionary, filtered CDS dictionary, and the dropped CDS dictionary.
    """
    # Count CDS size
    cds_size: Dict[str, int] = {key: len(str(sequence)) for key, sequence in all_nucleotide_sequences.items()}

    dropped_cds: Dict[str, str] = {}
    total_cds: int = len(all_nucleotide_sequences)
    print(f"\nIdentified {total_cds} valid CDS not present in the schema.")

    # Filter by size
    if size_threshold:
        all_nucleotide_sequences = {key: sequence for key, sequence in all_nucleotide_sequences.items() if cds_size[key] >= size_threshold}
        dropped_cds = {key: 'Dropped_due_to_cds_size' for key, length in cds_size.items() if length < size_threshold}
        print(f"{len(all_nucleotide_sequences)}/{total_cds} have size greater or equal to {size_threshold} bp.")
    else:
        size_threshold = 0
        print("No size threshold was applied to the CDS filtering.")

    return cds_size, all_nucleotide_sequences, dropped_cds


def write_cds_to_fasta(all_nucleotide_sequences: Dict[str, str], output_path: str) -> None:
    """
    Writes CDS sequences to a FASTA file.

    Parameters
    ----------
    all_nucleotide_sequences : Dict[str, str]
        Dictionary with CDS IDs as keys and sequences as values.
    output_path : str
        Path to the output FASTA file.

    Returns
    -------
    None
        The function writes the sequences to the specified output file.
    """
    with open(output_path, 'w+') as cds_not_found:
        for id_, sequence in all_nucleotide_sequences.items():
            cds_not_found.write(f">{id_}\n{str(sequence)}\n")


def count_cds_frequency(all_nucleotide_sequences: Dict[str, str], decoded_sequences_ids: Dict[str, List[str]]) -> Tuple[Dict[str, int], Dict[str, List[str]]]:
    """
    Counts the frequency of CDS in the genomes and identifies their presence.

    Parameters
    ----------
    all_nucleotide_sequences : Dict[str, str]
        Dictionary with CDS IDs as keys and sequences as values.
    decoded_sequences_ids : Dict[str, List[str]]
        Dictionary with hashed sequences as keys and genome IDs as values.

    Returns
    -------
    Tuple[Dict[str, int], Dict[str, List[str]]]
        A tuple containing the frequency of CDS and their presence in genomes.
    """
    frequency_cds: Dict[str, int] = {}
    cds_presence_in_genomes: Dict[str, List[str]] = {}

    for id_, sequence in all_nucleotide_sequences.items():
        hashed_seq: str = sf.seq_to_hash(str(sequence))
        if hashed_seq in decoded_sequences_ids:
            frequency_cds[id_] = len(set(decoded_sequences_ids[hashed_seq][1:]))
            cds_presence_in_genomes[id_] = decoded_sequences_ids[hashed_seq][1:]
        else:
            frequency_cds[id_] = 0

    return frequency_cds, cds_presence_in_genomes


def process_cds_not_present(initial_processing_output: str, temp_folder: str, all_nucleotide_sequences: Dict[str, str]) -> Tuple[str, Dict[str, int], Dict[str, List[str]]]:
    """
    Processes CDS not present in the schema and writes them to a FASTA file.

    Parameters
    ----------
    initial_processing_output : str
        Path to the initial processing output directory.
    temp_folder : str
        Path to the temporary folder.
    all_nucleotide_sequences : Dict[str, str]
        Dictionary with CDS IDs as keys and sequences as values.

    Returns
    -------
    Tuple[str, Dict[str, int], Dict[str, List[str]]]
        A tuple containing the path to the CDS present file, frequency of CDS, and their presence in genomes.
    """
    print("Identifying CDS present in the schema and counting frequency of missing CDSs in the genomes...")
    
    cds_not_present_file_path: str = os.path.join(initial_processing_output, 'CDS_not_found.fasta')
    write_cds_to_fasta(all_nucleotide_sequences, cds_not_present_file_path)

    cds_present: str = os.path.join(temp_folder, "2_cds_preprocess/cds_deduplication/distinct.hashtable")
    decoded_sequences_ids: Dict[str, List[str]] = itf.decode_CDS_sequences_ids(cds_present)

    frequency_cds, cds_presence_in_genomes = count_cds_frequency(all_nucleotide_sequences, decoded_sequences_ids)

    return cds_present, frequency_cds, cds_presence_in_genomes


def translate_and_deduplicate_cds(all_nucleotide_sequences: Dict[str, str], 
                                  initial_processing_output: str, 
                                  constants: List[Union[int, float]]) -> Tuple[Dict[str, str], Dict[str, List[str]], Dict[str, int]]:
    """
    Translates and deduplicates CDS sequences, and counts translation sizes.

    Parameters
    ----------
    all_nucleotide_sequences : Dict[str, str]
        Dictionary with CDS IDs as keys and sequences as values.
    initial_processing_output : str
        Path to the initial processing output directory.
    constants : List[Union[int, float]]
        List of constants used for translation and deduplication.

    Returns
    -------
    Tuple[Dict[str, str], Dict[str, List[str]], Dict[str, int]]
        A tuple containing the translation dictionary, protein hashes, and CDS translation sizes.
    """
    # Define file paths for translated and untranslated CDS
    cds_not_present_trans_file_path: str = os.path.join(initial_processing_output, "CDS_not_found_translation.fasta")
    cds_not_present_untrans_file_path: str = os.path.join(initial_processing_output, "CDS_not_found_untranslated.fasta")

    # Translate and deduplicate protein sequences
    all_translation_dict: Dict[str, str]
    protein_hashes: Dict[str, List[str]]
    all_translation_dict, protein_hashes, _ = sf.translate_seq_deduplicate(
        all_nucleotide_sequences,
        cds_not_present_trans_file_path,
        cds_not_present_untrans_file_path,
        constants[5],
        True,
        constants[6],
        True
    )

    # Count translation sizes
    cds_translation_size: Dict[str, int] = {key: len(sequence) for key, sequence in all_translation_dict.items()}

    # Print additional information about translations and deduplications
    print(f"\n{len(all_translation_dict)}/{len(all_nucleotide_sequences)} unique protein translations.")

    return all_translation_dict, protein_hashes, cds_translation_size


def remove_dropped_cds(all_translation_dict: Dict[str, str], 
                       dropped_cds: Set[str], 
                       protein_hashes: Dict[str, List[str]]) -> Dict[str, str]:
    """
    Removes dropped CDS from the translation dictionary and updates protein hashes.

    Parameters
    ----------
    all_translation_dict : Dict[str, str]
        Dictionary with CDS IDs as keys and sequences as values.
    dropped_cds : Set[str]
        Set of CDS IDs that are dropped.
    protein_hashes : Dict[str, List[str]]
        Dictionary with protein hashes as keys and CDS IDs as values.

    Returns
    -------
    Dict[str, str]
        Updated translation dictionary.
    """
    for key in list(all_translation_dict.keys()):
        if key in dropped_cds:
            protein_hash: str = itf.identify_string_in_dict_get_key(key, protein_hashes)
            same_protein_id: List[str] = protein_hashes[protein_hash]
            if key == same_protein_id[0]:
                protein_hashes[protein_hash].remove(key)
                if not protein_hashes[protein_hash]:
                    del protein_hashes[protein_hash]
                    continue
                new_id: str = protein_hashes[protein_hash][0]
                all_translation_dict[new_id] = all_translation_dict.pop(key)
            else:
                protein_hashes[protein_hash].remove(key)

    return {k: v for k, v in all_translation_dict.items() if k not in dropped_cds}


def sort_by_protein_size(all_translation_dict: Dict[str, str]) -> Dict[str, str]:
    """
    Sorts the translation dictionary by the size of the proteins in descending order.

    Parameters
    ----------
    all_translation_dict : Dict[str, str]
        Dictionary with CDS IDs as keys and sequences as values.

    Returns
    -------
    Dict[str, str]
        Sorted translation dictionary.
    """
    return {k: v for k, v in sorted(all_translation_dict.items(), key=lambda x: len(x[1]), reverse=True)}


def cluster_by_minimizers(all_translation_dict: Dict[str, str], 
                          constants: List[Union[int, float]]) -> Tuple[Dict[str, List[str]], Dict[str, str], Dict[str, List[str]], Dict[str, int]]:
    """
    Clusters the translation dictionary by minimizers.

    Parameters
    ----------
    all_translation_dict : Dict[str, str]
        Dictionary with CDS IDs as keys and sequences as values.
    constants : List[Union[int, float]]
        List of constants used for clustering.

    Returns
    -------
    Tuple[Dict[str, List[str]], Dict[str, str], Dict[str, List[str]], Dict[str, int]]
        A tuple containing all alleles, representative sequences, representative groups, and protein length dictionary.
    """
    reps_groups: Dict[str, List[str]] = {}
    all_alleles: Dict[str, List[str]] = {}
    reps_sequences: Dict[str, str] = {}

    all_alleles, reps_sequences, reps_groups, prot_len_dict = cf.minimizer_clustering(
        all_translation_dict,
        5,
        5,
        True,
        1,
        all_alleles,
        reps_sequences,
        reps_groups,
        1,
        constants[3],
        constants[4],
        True,
        constants[8]
    )

    return all_alleles, reps_sequences, reps_groups, prot_len_dict


def reformat_clusters(all_alleles: Dict[str, List[str]], 
                      protein_hashes: Dict[str, List[str]]) -> Dict[str, List[str]]:
    """
    Reformats the clusters to include only the IDs of cluster members and adds unique CDS IDs to clusters.

    Parameters
    ----------
    all_alleles : Dict[str, List[str]]
        Dictionary with cluster representatives as keys and cluster members as values.
    protein_hashes : Dict[str, List[str]]
        Dictionary with protein hashes as keys and CDS IDs as values.

    Returns
    -------
    Dict[str, List[str]]
        Reformatted clusters.
    """
    all_alleles = {cluster_rep: [value[0] for value in values] for cluster_rep, values in all_alleles.items()}
    filtered_protein_hashes: Dict[str, List[str]] = {hash_prot: cds_ids for hash_prot, cds_ids in protein_hashes.items() if len(cds_ids) > 1}

    for cluster_rep, values in list(all_alleles.items()):
        for cds_id in list(values):
            protein_hash: str = itf.identify_string_in_dict_get_key(cds_id, filtered_protein_hashes)
            if protein_hash is not None:
                all_alleles[cluster_rep] += filtered_protein_hashes[protein_hash][1:]

    return all_alleles


def get_representative_translation_dict(all_translation_dict: Dict[str, str], 
                                        all_alleles: Dict[str, List[str]]) -> Dict[str, str]:
    """
    Filters and sorts the representative translation dictionary.

    Parameters
    ----------
    all_translation_dict : Dict[str, str]
        Dictionary with CDS IDs as keys and sequences as values.
    all_alleles : Dict[str, List[str]]
        Dictionary with cluster representatives as keys and cluster members as values.

    Returns
    -------
    Dict[str, str]
        Sorted representative translation dictionary.
    """
    # Filter the representatives protein sequence
    reps_translation_dict: Dict[str, str] = {
        rep_id: rep_seq for rep_id, rep_seq in all_translation_dict.items()
        if rep_id.split('_')[0] in all_alleles
    }
    
    # Sort the representative translation dict from largest to smallest
    return {k: v for k, v in sorted(reps_translation_dict.items(), key=lambda x: len(x[1]), reverse=True)}


def calculate_kmers_similarity(reps_translation_dict: Dict[str, str], 
                               reps_groups: Dict[str, List[str]], 
                               prot_len_dict: Dict[str, int]) -> Dict[str, Dict[str, List[int]]]:
    """
    Calculates the k-mers similarity and coverage between representatives.

    Parameters
    ----------
    reps_translation_dict : Dict[str, str]
        Dictionary with representative CDS IDs as keys and sequences as values.
    reps_groups : Dict[str, List[str]]
        Dictionary with representative groups.
    prot_len_dict : Dict[str, int]
        Dictionary with protein lengths.

    Returns
    -------
    Dict[str, Dict[str, List[int]]]
        Dictionary with k-mers similarity and coverage between representatives.
    """
    reps_kmers_sim: Dict[str, Dict[str, List[int]]] = {}

    for cluster_id, rep_seq in reps_translation_dict.items():
        kmers_rep: Set[str] = set(kf.determine_minimizers(rep_seq, 5, 5, 1, True, True))
        
        reps_kmers_sim[cluster_id] = cf.select_representatives(
            kmers_rep, reps_groups, 0, 0, prot_len_dict, cluster_id, 5, False
        )
        
        reps_kmers_sim[cluster_id] = {
            match_values[0]: match_values[1:] for match_values in reps_kmers_sim[cluster_id]
        }

    return reps_kmers_sim


def write_fasta_file(file_path: str, sequences: Dict[str, str]) -> None:
    """
    Writes sequences to a FASTA file.

    Parameters
    ----------
    file_path : str
        Path to the output FASTA file.
    sequences : Dict[str, str]
        Dictionary with sequence IDs as keys and sequences as values.

    Returns
    -------
    None
        The function writes the sequences to the specified output file.
    """
    write_type: str = 'a' if os.path.exists(file_path) else 'w'
    with open(file_path, write_type) as fasta_file:
        for seq_id, sequence in sequences.items():
            fasta_file.write(f">{seq_id}\n{sequence}\n")


def prepare_files_to_blast(representatives_blastn_folder: str, 
                       all_alleles: Dict[str, List[str]], 
                       all_nucleotide_sequences: Dict[str, str], 
                       processing_mode: str) -> Tuple[Dict[str, str], str]:
    """
    Writes representative and master FASTA files for BLAST.

    Parameters
    ----------
    representatives_blastn_folder : str
        Path to the folder where BLAST files will be written.
    all_alleles : Dict[str, List[str]]
        Dictionary with cluster representatives as keys and cluster members as values.
    all_nucleotide_sequences : Dict[str, str]
        Dictionary with CDS IDs as keys and sequences as values.
    processing_mode : str
        Mode of processing, which determines how sequences are handled. Four types: reps_vs_reps,
        reps_vs_alleles, alleles_vs_alleles, alleles_vs_reps.

    Returns
    -------
    Tuple[Dict[str, str], str]
        A tuple containing a dictionary with paths to the BLAST files and the path to the master FASTA file.
    """
    # Create directory and files path where to write FASTAs.
    master_file_path: str = os.path.join(representatives_blastn_folder, 'master.fasta')
    
    to_blast_paths: Dict[str, str] = {}

    queries: str = processing_mode.split('_')[0]
    subjects: str = processing_mode.split('_')[-1]
    master_sequences: Dict[str, str] = {}
    for members in all_alleles.values():
        cluster_rep_id: str = members[0]
        loci: str = cluster_rep_id.split('_')[0]
        fasta_file: str = os.path.join(representatives_blastn_folder, f"cluster_rep_{cluster_rep_id}.fasta")
        to_blast_paths[loci] = fasta_file

        if queries == 'reps':
            sequence: Dict[str, str] = {cluster_rep_id: all_nucleotide_sequences[cluster_rep_id]}
        else:
            sequence = {}
            for member in members:
                sequence[member] = str(all_nucleotide_sequences[member])
        
        write_fasta_file(fasta_file, sequence)

        if subjects == 'reps':
            master_sequences[cluster_rep_id] = str(all_nucleotide_sequences[members[0]])
        else:
            for member in members:
                master_sequences[member] = str(all_nucleotide_sequences[member])

    write_fasta_file(master_file_path, master_sequences)

    return to_blast_paths, master_file_path


def update_frequencies_in_genomes(clusters_to_keep: Dict[str, Dict[str, List[str]]], 
                                  frequency_in_genomes: Dict[str, int]) -> Dict[str, int]:
    """
    Updates the frequencies in genomes for joined groups and updates the changed clusters frequency from joined CDSs.

    Parameters
    ----------
    clusters_to_keep : Dict[str, Dict[str, List[str]]]
        Dictionary containing clusters to keep with their members.
    frequency_in_genomes : Dict[str, int]
        Dictionary with the frequency of CDS in the genomes.

    Returns
    -------
    Dict[str, int]
        Updated frequency of CDS in the genomes.
    """
    updated_frequency_in_genomes: Dict[str, int] = {}
    new_cluster_freq: Dict[str, int] = {}

    # Calculate new frequencies for joined groups
    for cluster_id, cluster_members in clusters_to_keep['1a'].items():
        new_cluster_freq[cluster_id] = sum(frequency_in_genomes[member] for member in cluster_members)
        for member in cluster_members:
            updated_frequency_in_genomes[member] = new_cluster_freq[cluster_id]

    # Add all the other frequencies
    updated_frequency_in_genomes.update(frequency_in_genomes)
    updated_frequency_in_genomes.update(new_cluster_freq)

    return updated_frequency_in_genomes
