#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Dec 15 18:18:38 2022

AUTHOR

    Mykyta Forofontov
    github: @MForofontov
"""
import os
import sys
import csv
import subprocess
import ast
import pandas as pd

def tryeval(val):
    """
    Evaluates the type of the input.
    """
    
    try:
      val = ast.literal_eval(val)
    except ValueError:
      pass
    return val

def main(args):
        
    if args.filter_criteria_path is not None:
        #import filtering criterias file
        with open(args.filter_criteria_path,'r') as filters:
            criterias = dict(csv.reader(filters, delimiter='\t'))
        
        #Transform dictionary keys and values into variables
        try:
            abundance = tryeval(criterias['abundance'])
            genome_size = tryeval(criterias['genome_size'])
            size_threshold = tryeval(criterias['size_threshold'])
            max_contig_number = tryeval(criterias['max_contig_number'])
            known_st = tryeval(criterias['known_st'])
            any_quality = tryeval(criterias['any_quality'])
            ST_list_path = tryeval(criterias['ST_list_path'])
            assembly_level = tryeval(criterias['assembly_level'])
            reference = tryeval(criterias['reference_genome'])
            assembly_source = tryeval(criterias['assembly_source'])
            file_extension = tryeval(criterias['file_extension'])
            
        except KeyError:
            sys.exit("\nError: Missing parameters in the filtering criteria file.")
        
        finally:
            print("\nLoaded filtering criteria file successfully.")

        #Verify variables integrity and validity
        print("\nVerifying filtering criteria input table.")
        
        wrong_inputs = []
        
        if abundance is not None:
            if (not 0 < abundance <= 1):
                wrong_inputs.append('abundance: float values between 0 < x <= 1')
                
        if genome_size is not None:
            if (genome_size < 0 or type(genome_size) is not int):
                wrong_inputs.append('genome_size: int value > 0')
                
        if size_threshold is not None:
            if (not 0 < size_threshold <= 1):
                wrong_inputs.append('size_threshold: float values between 0 < x <= 1')
                
        if max_contig_number is not None:
            if (max_contig_number < 0 or type(max_contig_number) is not int):
                wrong_inputs.append('max_contig_number: int value > 0')
                
        if known_st is not None:        
            if (type(known_st) is not bool):
                wrong_inputs.append('known_st: bool value')
                
        if any_quality is not None:             
            if (type(any_quality) is not bool):
                wrong_inputs.append('any_quality: bool value')
                
        if ST_list_path is not None:   
            if (not os.path.exists(ST_list_path) or type(ST_list_path) is not str):
                wrong_inputs.append('ST_list_path: path to the file with ST list')
                
        if assembly_level is not None:
            if type(assembly_level) is str:
                if (not all(level in ['chromosome','complete','contig','scaffold']
                        for level in assembly_level.split(','))):
                    
                    wrong_inputs.append('assembly_level: ' 
                                        'one or more of the following separated '
                                        'by a comma: '
                                        'chromosome,complete,contig,scaffold')
            else:
                wrong_inputs.append('assembly_level: ' 
                                    'one ore more of the following separated '
                                    'by a comma: '
                                    'chromosome,complete,contig,scaffold')
                
        if reference is not None:                
            if (type(reference) is not bool):
                wrong_inputs.append('reference: bool value')
                
        if assembly_source is not None:        
            if (assembly_source not in ['RefSeq','GenBank','all']):
                wrong_inputs.append('assembly_source: one of the following:' 
                                    'RefSeq,GenBank,all')
                
        if file_extension is not None:        
            if (file_extension not in ['genome','rna','protein','cds','gff3','gtf',
                                       'gbff','seq-report','none']):
                wrong_inputs.append('file_extension: one or more of the following separated '
                                    'by comma: genome,rna,protein,cds,gff3,gtf, '
                                    'gbff,seq-report,none')
            
        if len(wrong_inputs) > 0:
            print('\nFiltering table inputs have wrong values or types:')
            for inputs in wrong_inputs:
                print('\n' + inputs)
            os.sys.exit()
        
    print("\nFetching assemblies from {}.".format(args.database))
      
    if args.database == 'NCBI':
        """
        If Database option is set to NCBI, run one of the two tools depending
        if there is a input table containing the ids of desired assemblies, if
        table exists then script downloads them otherwise it downloads all 
        assemblies for the desired species.
        """
        #Import modules
        try:
            from Download_module import ncbi_datasets_summary
            from Download_module import ncbi_linked_ids
            from Download_module import fetch_metadata
                
        except ModuleNotFoundError:
            from Schema_refinery.Download_module import ncbi_datasets_summary
            from Schema_refinery.Download_module import ncbi_linked_ids
            from Schema_refinery.Download_module import fetch_metadata
        
        if args.input_table is not None:
            #If assemblies ids list is present
            failed_list,list_to_download = ncbi_datasets_summary.metadata_from_id_list(args.input_table,
                                                          size_threshold,
                                                          max_contig_number,
                                                          genome_size,
                                                          assembly_level,
                                                          reference,
                                                          args.threads,
                                                          args.api_key)
            
            #save ids to download
            with open(os.path.join(args.output_directory,
                                   "assemblies_ids_to_download.tsv"),'w+') as ids_to_txt:
                
                ids_to_txt.write("\n".join(map(str, list_to_download)))
            
            #save ids that failed criteria
            with open(os.path.join(args.output_directory,
                                   "id_failed_criteria.tsv"),'w+') as ids_to_txt:
                
                ids_to_txt.write("\n".join(map(str, failed_list)))       
                

            #If any assembly passed filtering criteria
            if not list_to_download:
                print("\nNo assemblies meet the desired filtering criterias.")
                
                sys.exit("\nAssemblies that failed are in the following" 
                         "TSV file: {}".format(os.path.join(args.output_directory,
                                                            "id_failed_criteria.tsv.tsv")))
                
            #Build initial arguments for the subprocess run of datasets
            arguments = ['datasets','download','genome','accession','--inputfile',
                         os.path.join(args.output_directory,
                                      'assemblies_ids_to_download.tsv')]
            
            if args.api_key is not None:
                arguments += ['--api-key',args.api_key]
                
            if file_extension is not None:
                arguments += ['--include',file_extension]
            
            #download assemblies
            if args.download:
                print("\nDownloading assemblies...")
                os.chdir(args.output_directory)
                subprocess.run(arguments)
                
            else:
                print("\nAssemblies to be downloaded are in the following TSV file: {}".format(
                    os.path.join(args.output_directory,"assemblies_ids_to_download.tsv")))

                
        else:
            #Fetch from species identifier
            failed_list,list_to_download = ncbi_datasets_summary.metadata_from_species(args.species,
                                                          size_threshold,
                                                          max_contig_number,
                                                          genome_size,
                                                          assembly_level,
                                                          reference,
                                                          assembly_source,
                                                          args.api_key)
                
            #save ids to download
            with open(os.path.join(args.output_directory,
                                   "assemblies_ids_to_download.tsv"),'w+') as ids_to_txt:
                
                ids_to_txt.write("\n".join(map(str, list_to_download)))
            
            #save ids that failed criteria
            with open(os.path.join(args.output_directory,
                                   "id_failed_criteria.tsv"),'w+') as ids_to_txt: 
                
                ids_to_txt.write("\n".join(map(str, failed_list)))
            
            #If any assembly passed filtering criteria
            if not list_to_download:
                print("\nNo assemblies meet the desired filtering criterias.")
                
                sys.exit("\nAssemblies that failed are in the following " 
                         "TSV file: {}".format(os.path.join(args.output_directory,
                                                            "id_failed_criteria.tsv.tsv")))
                
            #Build initial arguments for the subprocess run of datasets
            arguments = ['datasets','download','genome','accession','--inputfile',
                         os.path.join(args.output_directory,
                                      'assemblies_ids_to_download.tsv')]
            
            if args.api_key is not None:
                arguments = arguments + ['--api-key',args.api_key]
            
            if args.download:
                print("\nDownloading assemblies...")
                os.chdir(args.output_directory)
                subprocess.run(arguments)
            
            else:
                print("\nAssemblies to be downloaded are in the following TSV file: {}".format(
                    os.path.join(args.output_directory,"assemblies_ids_to_download.tsv")))
        
        if args.f_metadata:
                
            if not os.path.exists(os.path.join(args.output_directory,'metadata')):
                os.mkdir(os.path.join(args.output_directory,'metadata'))  
                    
                
            print("\nFetching related ids...")
            
            ncbi_linked_ids.main(os.path.join(args.output_directory,'assemblies_ids_to_download.tsv'),
                                 os.path.join(args.output_directory,'metadata/id_matches.tsv'),
                                 args.email, 
                                 args.threads, 
                                 args.retry, 
                                 args.api_key)
            
            print("\nFetching additional metadata...") 
            
            biosamples = pd.read_csv(os.path.join(args.output_directory,'metadata/id_matches.tsv'),
                        delimiter = '\t')['BioSample'].values.tolist()
            
            #create file with biosamples ids
            with open(os.path.join(args.output_directory,
                                   'metadata/biosamples.tsv'),'w+') as ids:
                
                ids.write("\n".join(map(str, biosamples)))
                           
            fetch_metadata.main(os.path.join(args.output_directory,'metadata/biosamples.tsv'),
                                os.path.join(args.output_directory,'metadata'),
                                args.email,
                                args.threads,
                                args.api_key,
                                args.retry)
            
            #remove biosamples file
            os.remove(os.path.join(args.output_directory,'metadata/biosamples.tsv'))
    else:
        try:
            from Download_module import ena661k_assembly_fetcher
            from Download_module import ncbi_linked_ids
            from Download_module import fetch_metadata
            
        except ModuleNotFoundError:
            from Schema_refinery.Download_module import ena661k_assembly_fetcher
            from Schema_refinery.Download_module import ncbi_linked_ids
            from Schema_refinery.Download_module import fetch_metadata
            
        ena661k_assembly_fetcher.main(args.metadata_table,
                                      args.paths_table,
                                      args.species, 
                                      args.output_directory,
                                      args.download, 
                                      abundance, 
                                      genome_size, 
                                      size_threshold,
                                      max_contig_number, 
                                      args.species, 
                                      known_st, 
                                      any_quality, 
                                      args.stride,
                                      args.retry, 
                                      ST_list_path, 
                                      args.threads)

        if args.f_metadata:
            
            if not os.path.exists(os.path.join(args.output_directory,'metadata')):
                os.mkdir(os.path.join(args.output_directory,'metadata'))  
            
            ncbi_linked_ids.main(os.path.join(args.output_directory,'assemblies_ids_to_download.tsv'),
                                 os.path.join(args.output_directory,'metadata/id_matches.tsv'),
                                 args.email, 
                                 args.threads, 
                                 args.retry, 
                                 args.api_key)
            
            fetch_metadata.main(os.path.join(args.output_directory,'assemblies_ids.tsv'),
                                os.path.join(args.output_directory,'metadata'),
                                args.email,
                                args.threads,
                                args.api_key,
                                args.retry)
        