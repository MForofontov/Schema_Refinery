#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Purpose
-------
This sub-module aligns representative alleles in a query schema
against all alleles in a subject schema to determine similar
loci in both schemas.

Code documentation
------------------
"""


import os
import argparse
import csv
import itertools

from Bio import SeqIO

try:
    from utils.file_functions import check_and_make_directory
    from utils.blast_functions import make_blast_db, run_blast
    from utils.sequence_functions import translate_sequence

except ModuleNotFoundError:
    from Schema_refinery.utils.file_functions import check_and_make_directory
    from Schema_refinery.utils.blast_functions import make_blast_db, run_blast
    from Schema_refinery.utils.sequence_functions import translate_sequence


def read_tabular(input_file, delimiter='\t'):
    """ Read a TSV file.

    Parameters
    ----------
    input_file : str
        Path to a tabular file.
    delimiter : str
        Delimiter used to separate file fields.

    Returns
    -------
    lines : list
        A list with a sublist per line in the input file.
        Each sublist has the fields that were separated by
        the specified delimiter.
    """

    with open(input_file, 'r') as infile:
        reader = csv.reader(infile, delimiter=delimiter)
        lines = [line for line in reader]

    return lines


def flatten_list(list_to_flatten):
    """ Flattens one level of a nested list.

    Parameters
    ----------
    list_to_flatten : list
        List with nested lists.

    Returns
    -------
    flattened_list : str
        Input list flattened by one level.
    """

    flattened_list = list(itertools.chain(*list_to_flatten))

    return flattened_list


def match_schemas(query_schema, subject_schema, output_path, blast_score_ratio, cpu_cores):

    output_path = os.path.join(output_path, "matchSchemas")
    check_and_make_directory(output_path)

    # import representative sequences in query schema
    rep_dir = os.path.join(query_schema, 'short')
    rep_files = [os.path.join(rep_dir, f)
                 for f in os.listdir(rep_dir)
                 if f.endswith('.fasta') is True]

    # get representative sequences from query schema
    query_ids = [os.path.basename(f).split('_')[0] for f in rep_files]
    query_reps = []
    for f in rep_files:
        locus_id = os.path.basename(f).split('_short')[0]
        records = SeqIO.parse(f, 'fasta')
        # only get the forst representative allele
        rec = next(records, None)
        seqid = rec.id
        allele_id = seqid.split('_')[-1]
        short_seqid = '{0}_{1}'.format(locus_id, allele_id)
        prot = translate_sequence(str(rec.seq), 11)
        sequence = '>{0}\n{1}'.format(short_seqid, prot)
        query_reps.append(sequence)

    # save query reps into same file
    query_prot_file = os.path.join(output_path, 'query_prots.fasta')
    with open(query_prot_file, 'w') as op:
        op.write('\n'.join(query_reps))

    # create BLAST db with query sequences and get self scores
    query_blastdb_path = os.path.join(output_path, 'query_blastdb')
    make_blast_db(query_prot_file, query_blastdb_path, 'prot')

    # determine self raw score for representative sequences
    self_blast_out = os.path.join(output_path, 'self_results.tsv')
    # max_targets has to be greater than 1
    # for some cases, the first alignment that is reported is
    # not the self-alignment
    run_blast('blastp', query_blastdb_path, query_prot_file, self_blast_out,
              max_hsps=1, threads=cpu_cores, ids_file=None, max_targets=5)

    self_blast_results = read_tabular(self_blast_out)
    self_blast_results = {r[0].split('_')[0]: r[2]
                          for r in self_blast_results
                          if r[0] == r[1]}

    # translate subject sequences
    subject_files = [os.path.join(subject_schema, f)
                     for f in os.listdir(subject_schema)
                     if f.endswith('.fasta') is True]

    subject_prots_file = os.path.join(output_path, 'subject_prots.fasta')
    ids = {}
    start = 1
    for file in subject_files:
        records = [(rec.id, str(rec.seq))
                   for rec in SeqIO.parse(file, 'fasta')]
        for rec in records:
            ids[rec[0]] = start
            start += 1
        sequences = ['>{0}\n{1}'.format(ids[rec[0]],
                                        translate_sequence(rec[1], 11))
                     for rec in records]
        with open(subject_prots_file, 'a') as sf:
            sf.write('\n'.join(sequences)+'\n')

    # create BLASTdb with subject sequences
    blastdb_path = os.path.join(output_path, 'subject_blastdb')
    make_blast_db(subject_prots_file, blastdb_path, 'prot')

    # BLASTp old seqs against new seqs
    blast_out = os.path.join(output_path, 'results.tsv')
    run_blast('blastp', blastdb_path, query_prot_file, blast_out,
              max_hsps=1, threads=cpu_cores, ids_file=None, max_targets=10)

    # import BLAST results
    blast_results = read_tabular(blast_out)

    ids_rev = {v: k for k, v in ids.items()}

    # determine BSR values
    bsr_values = {}
    multiple_matches = {}
    for m in blast_results:
        query = m[0].split('_')[0]
        subject = ids_rev[int(m[1])]
        score = m[-1]
        bsr = float(score) / float(self_blast_results[query])
        if query in bsr_values:
            if bsr > bsr_values[query][1]:
                bsr_values[query] = [subject, bsr]
            if bsr > blast_score_ratio:
                multiple_matches[query].append([subject, bsr])
        elif query not in bsr_values and bsr > blast_score_ratio:
            bsr_values[query] = [subject, bsr]
            multiple_matches[query] = [[subject, bsr]]

    # keep only queries with multiple matches
    multiple = []
    for k, v in multiple_matches.items():
        loci = [e[0].split('_')[0] for e in v]
        if len(set(loci)) > 1:
            matches = ['{0}\t{1}\t{2}'.format(k, e[0], e[1]) for e in v]
            multiple.extend(matches)

    multiple_lines = '\n'.join(multiple)

    multiple_file = os.path.join(output_path, 'multiple_matches.tsv')
    with open(multiple_file, 'w') as mh:
        mh.write(multiple_lines+'\n')

    # save matches between schemas loci
    matches = ['{0}\t{1}\t{2}'.format(k, v[0].split('_')[0], v[1])
               for k, v in bsr_values.items()]
    matches_lines = '\n'.join(matches)
    matches_file = os.path.join(output_path, 'matches.tsv')
    with open(matches_file, 'w') as mf:
        mf.write(matches_lines+'\n')

    # determine identifiers that had no match
    no_match = [i for i in self_blast_results if i not in bsr_values]
    no_match_lines = '\n'.join(no_match)
    no_match_file = os.path.join(output_path, 'no_match.txt')
    with open(no_match_file, 'w') as nm:
        nm.write(no_match_lines+'\n')

    return matches_file

def check_match_schemas_arguments(args_list:list):
    parser = argparse.ArgumentParser(prog='Match Schemas Annotations',
                                     description='This sub-module aligns representative ' 
                                     'alleles in a query schema against all alleles in '
                                     'a subject schema to determine similar '
                                     'loci in both schemas.' )
    
    parser.add_argument('-qs', '--query-schema', type=str, required=True,
                        dest='query_schema',
                        help='Path to the query schema directory.'
                             'This schema will be matched against '
                             'the subject schema.'
                             'This argument is needed by the Match Schemas'
                             'sub-module.')

    parser.add_argument('-ss', '--subject-schema', type=str, required=True,
                        dest='subject_schema',
                        help='Path to que subject schema directory. '
                             'This argument is needed by the Match Schemas '
                             'sub-module.')
    
    parser.add_argument('-oc', '--old-schema-columns', type=str, required=True,
                        nargs='+',
                        dest='old_schema_columns',
                        help='Columns from the old schema annotations to merge into '
                             'the new schema annotations table being created. '
                             'This argument is needed by the Match Schemas '
                             'sub-module.')
    
    parser.add_argument('-ma', '--match_to_add', type=str, required=True,
                        dest='match_to_add',
                        default = '',
                        help='Annotation of another schema, needed with '
                             '--old-schema-columns. '
                             'This argument is needed by the Match Schemas '
                             'sub-module.')


    parser.add_argument('--bsr', type=float, required=False,
                        default=0.6, dest='blast_score_ratio',
                        help='Minimum BSR value to consider aligned '
                             'alleles as alleles for the same locus. '
                             'This argument is optional for the Match Schemas '
                             'sub-module.')
    
    parser.add_argument('-cpu', '--cpu-cores', type=int, required=False,
                            dest='cpu_cores',
                            default=1,
                            help='Number of CPU cores to pass to BLAST.')

    parser.add_argument('-o', '--output-directory', type=str,
                        required=True, dest='output_directory',
                        help='Path to the output directory where to save the files.')
    
    parser.parse_args(args_list)
