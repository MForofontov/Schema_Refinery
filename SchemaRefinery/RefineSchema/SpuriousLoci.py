#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
try:
    from utils import (core_functions as cof,
                       file_functions as ff,
                       sequence_functions as sf,
                       blast_functions as bf,
                       iterable_functions as itf,
                       linux_functions as lf)
except ModuleNotFoundError:
    from SchemaRefinery.utils import (core_functions as cof,
                       file_functions as ff,
                       sequence_functions as sf,
                       blast_functions as bf,
                       iterable_functions as itf,
                       linux_functions as lf)

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
     _] = cof.run_blasts(blast_db_nuc,
                     schema_loci_short,
                     reps_trans_dict_cds,
                     schema_loci_short,
                     blast_results,
                     constants,
                     cpu,
                     all_alleles,
                     run_type)

    cof.add_items_to_results(representative_blast_results,
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
    classes_outcome = cof.separate_blastn_results_into_classes(representative_blast_results,
                                                           constants)
    blast_results = os.path.join(results_output, 'blast_results')
    ff.create_directory(blast_results)
    report_file_path = os.path.join(blast_results, 'blast_all_matches.tsv')
    # Write all of the BLASTn results to a file.
    cof.alignment_dict_to_file(representative_blast_results, report_file_path, 'w', True)
    
    print("\nProcessing classes...")
    sorted_blast_dict = cof.sort_blast_results_by_classes(representative_blast_results,
                                                          classes_outcome)
    # Process the results_outcome dict and write individual classes to TSV file.
    [processed_results,
     count_results_by_class,
     count_results_by_class_with_inverse,
     reps_and_alleles_ids,
     drop_mark] = cof.process_classes(sorted_blast_dict,
                                classes_outcome,
                                all_alleles)
    # Sort the count_results_by_class dict by the classes_outcome tuple.
    count_results_by_class = itf.sort_subdict_by_tuple(count_results_by_class,
                                                       classes_outcome)
    # Extract CDS to keep and drop set.
    clusters_to_keep, drop_possible_loci = cof.extract_clusters_to_keep(classes_outcome,
                                                                        count_results_by_class,
                                                                        drop_mark)
        
    cof.count_number_of_reps_and_alleles(clusters_to_keep,
                                         all_alleles,
                                         drop_possible_loci,
                                         group_reps_ids,
                                         group_alleles_ids)

    # Extract the related clusters and recommendations what to do with them.
    print("\nExtracting results...")
    all_relationships, related_clusters, recommendations  = cof.extract_results(processed_results,
                                                                           count_results_by_class,
                                                                           frequency_in_genomes,
                                                                           clusters_to_keep,
                                                                           drop_possible_loci,
                                                                           classes_outcome)
    print("\nWritting count_results_by_cluster.tsv and related_matches.tsv files...")
    cof.write_blast_summary_results(related_clusters,
                                count_results_by_class_with_inverse,
                                group_reps_ids,
                                group_alleles_ids,
                                frequency_in_genomes,
                                recommendations,
                                run_type,
                                results_output)

    # Get all of the CDS that matched with loci
    [is_matched, is_matched_alleles] = cof.get_matches(all_relationships,
                                                       clusters_to_keep,
                                                       sorted_blast_dict)

    print("\nWritting classes and cluster results to files...")
    cof.write_processed_results_to_file(clusters_to_keep,
                                    sorted_blast_dict,
                                    classes_outcome,
                                    all_alleles,
                                    alleles,
                                    is_matched,
                                    is_matched_alleles,
                                    run_type,
                                    blast_results)
    

    cds_cases, loci_cases = cof.print_classifications_results(clusters_to_keep,
                                                              drop_possible_loci,
                                                              groups_paths,
                                                              all_alleles,
                                                              schema_loci,
                                                              run_type)

    print("\nWrapping up BLAST results...")
    cof.wrap_up_blast_results(clusters_to_keep,
                        None,
                        all_alleles,
                        results_output,
                        constants,
                        schema_loci,
                        groups_paths,
                        cds_cases,
                        loci_cases,
                        run_type)

def main(schema, output_directory, allelecall_directory, alignment_ratio_threshold, 
        pident_threshold, size_threshold, translation_table, bsr, size_ratio, cpu):
    frequency_in_genomes = {}
    loci_ids = [True, True]
    constants = [alignment_ratio_threshold, 
            pident_threshold,
            None,
            None,
            None,
            size_threshold,
            translation_table,
            bsr,
            None,
            size_ratio]

    run_type = 'loci_vs_loci'
    process_schema(schema,
                       [],
                       output_directory,
                       None,
                       None,
                       None,
                       frequency_in_genomes,
                       allelecall_directory,
                       None,
                       loci_ids,
                       run_type,
                       True,
                       constants,
                       cpu)