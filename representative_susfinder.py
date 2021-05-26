#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""

"""


import os
import argparse

from Bio import SeqIO


def main(schema_directory):

    # get Fasta files
    loci_list = [os.path.join(schema_directory, file)
                 for file in os.listdir(schema_directory)
                 if '.fasta' in file]

    loci_dict = {(os.path.basename(file)).split('.fasta')[0]: file
                 for file in loci_list}

    # get Fasta files with representatives
    short_directory = os.path.join(schema_directory, 'short')
    representative_files = [os.path.join(short_directory, file)
                            for file in os.listdir(short_directory)
                            if 'short.fasta' in file]

    representative_dict = {(os.path.basename(file)).split('_short.fasta')[0]: file
                           for file in representative_files}

    # check if representatives are in main file
    for locus, file in representative_dict.items():
        representative_records = {(rec.id).split('_')[-1]: str(rec.seq)
                                  for rec in SeqIO.parse(file, 'fasta')}

        locus_records = {(rec.id).split('_')[-1]: str(rec.seq)
                         for rec in SeqIO.parse(loci_dict[locus], 'fasta')}

        absent_recids = [k
                         for k in representative_records
                         if k not in locus_records]

        if len(absent_recids) > 0:
            print(locus, absent_recids)

        absent_seqs = [k
                       for k, v in representative_records.items()
                       if v != locus_records[k]]

        if len(absent_seqs) > 0:
            print(absent_seqs)


def parse_arguments():

    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)

    parser.add_argument('-s', type=str, required=True,
                        dest='schema_directory',
                        help='')

    args = parser.parse_args()

    return args


if __name__ == '__main__':

    args = parse_arguments()
    main(**vars(args))
