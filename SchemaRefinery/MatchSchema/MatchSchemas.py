import os
import re
from Bio import SeqIO
from typing import Dict, List, Tuple

try:
	from utils import (
						sequence_functions as sf,
						blast_functions as bf,
						linux_functions as lf,
						file_functions as ff,
						alignments_functions as af,
						Types as tp,
						print_functions as pf,
						logger_functions as logf,
						globals as gb
	)
except ModuleNotFoundError:
	from SchemaRefinery.utils import (
									sequence_functions as sf,
									blast_functions as bf,
									linux_functions as lf,
									file_functions as ff,
									alignments_functions as af,
									Types as tp,
									print_functions as pf,
									logger_functions as logf,
									globals as gb
									
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
							 blast_folder: str, self_score_dict: Dict[str, float], max_id_length: int,
							 get_blastp_exec: str, bsr: float, cpu: int) -> Dict[str, Dict[str, float]]:
	"""
	Run BLASTp to match schemas and calculate BSR values.

	Parameters
	----------
	query_translations_paths : dict
		Dictionary with keys as query identifiers and values as paths to the query translation files.
	blast_db_files : str
		Path to the BLAST database files.
	blast_folder : str
		Path to the folder where BLAST results will be stored.
	self_score_dict : dict
		Dictionary with query identifiers as keys and their self-scores as values.
	max_id_length : int
		Maximum length of the query identifiers.
	get_blastp_exec : str
		Path to the BLASTp executable.
	bsr : float
		BSR threshold value.
	cpu : int
		Number of CPU cores to use for multiprocessing.

	Returns
	-------
	dict
		Dictionary with loci identifiers as keys and tuples of the best subject identifier and BSR value as values.
	"""
	
	# Run BLASTp
	pf.print_message("Running BLASTp...", "info")
	blastp_results_folder: str = os.path.join(blast_folder, 'blastp_results')
	ff.create_directory(blastp_results_folder)
	
	# Initialize dictionaries to store BSR values
	bsr_values: Dict[str, Dict[str, float]] = {}
	best_bsr_values: Dict[str, Dict[str, float]] = {}
	total_blasts: int = len(query_translations_paths)
	blastp_results_files = bf.run_blastp_operations(cpu,
													get_blastp_exec,
													blast_db_files,
													query_translations_paths,
													blastp_results_folder,
													total_blasts,
													max_id_length)

	for blast_result_file in blastp_results_files:
		# Get the alignments
		filtered_alignments_dict: tp.BlastDict 
		filtered_alignments_dict, _, _ = af.get_alignments_dict_from_blast_results_simplified(blast_result_file,
																									0,
																									False,
																									True)
	   

		# Since BLAST may find several local alignments, choose the largest one to calculate BSR.
		for query, subjects_dict in filtered_alignments_dict.items():
			# Get the loci name
			query_loci_id: str = query.split('_')[0]

			best_bsr_values.setdefault(query_loci_id, {})
			# Create the dict of the query
			bsr_values.setdefault(query, {})
			for subject_id, results in subjects_dict.items():
				subject_loci_id = subject_id.split('_')[0]
				# Highest score (First one)
				subject_score: float = next(iter(results.values()))['score']
				# Calculate BSR value
				computed_score: float = bf.compute_bsr(subject_score, self_score_dict[query])
				# Check if the BSR value is higher than the threshold
				if computed_score >= bsr:
					# Round BSR values if they are superior to 1.0 to 1 decimal place
					if computed_score > 1.0:
						computed_score = round(computed_score, 1)
					# Save all of the different matches that this query had and their BSR values
					bsr_values[query].update({subject_id: computed_score})
				else:
					continue
				# Save the best match for each query and subject matches
				subject_loci_id = subject_id.split('_')[0]
				if not best_bsr_values[query_loci_id].get(subject_loci_id):
					best_bsr_values[query_loci_id][subject_loci_id] = computed_score
				elif computed_score > best_bsr_values[query_loci_id][subject_loci_id]:
					best_bsr_values[query_loci_id][subject_loci_id] = computed_score

	best_bsr_values = {query: match for query, match in best_bsr_values.items() if match}

	return best_bsr_values


def write_best_blast_matches_to_file(match_data, output_directory, match_type):
	"""
	"""
	# Define path to output file
	output_file = os.path.join(output_directory, match_type+'_matches.tsv')
	match_lists = []
	for k, v in match_data.items():
		current_matches = [[k, *e, match_type] for e in v]
		match_lists.extend(current_matches)
	match_lines = ['\t'. join(l) for l in match_lists]
	ff.write_lines(match_lines, output_file)

	return output_file


# def write_best_blast_matches_to_file(best_bsr_values,
# 									 query_translations_paths: Dict[str, str], 
# 									 subject_translations_paths: Dict[str, str], 
# 									 output_folder: str, 
# 									 rep_vs_alleles: bool, 
# 									 process_name: str) -> str:
# 	"""
# 	Write the best BLAST matches to a file.

# 	Parameters
# 	----------
# 	best_bsr_values : dict
# 		Dictionary with loci identifiers as keys and tuples of the best subject identifier and BSR value as values.
# 	query_translations_paths : dict
# 		Dictionary with keys as query identifiers and values as paths to the query translation files.
# 	subject_translations_paths : dict
# 		Dictionary with keys as subject identifiers and values as paths to the subject translation files.
# 	output_folder : str
# 		Path to the folder where the output file will be stored.

# 	Returns
# 	-------
# 	None
# 	"""
# 	# Path to output files
# 	best_blast_matches_file = os.path.join(output_folder, "Match_Schemas_Results.tsv")
# 	existing_matches_file = os.path.join(output_folder, "existing_matches.txt")

# 	# Load existing matches from existing matches file to avoid repetition across runs
# 	existing_matches = set()
# 	written_queries = set()

# 	if os.path.exists(existing_matches_file):
# 		with open(existing_matches_file, "r") as f:
# 			for line in f:
# 				parts = line.strip().split("\t")
# 				if parts:  
# 					existing_matches.add(line.strip())
# 					written_queries.add(parts[0])

# 	# Initialize lists
# 	matched_entries = []
# 	non_matched_query = []
# 	non_matched_subject = []

# 	# Identify loci that were not matched
# 	not_matched_loci = [query for query in query_translations_paths.keys() if query not in best_bsr_values.keys()]
# 	not_matched_subject = [subject for subject in subject_translations_paths.keys() if subject not in {s for d in best_bsr_values.values() for s in d.keys()}]

# 	# Check if the best matches file exists
# 	file_exists = os.path.exists(best_blast_matches_file)

# 	# Read existing file to avoid duplicates in this run
# 	if file_exists:
# 		with open(best_blast_matches_file, "r") as f:
# 			next(f)
# 			for line in f:
# 				parts = line.strip().split("\t")
# 				if parts:
# 					existing_matches.add(line.strip())
# 					written_queries.add(parts[0])

# 	# Write best matches
# 	with open(best_blast_matches_file, "a" if file_exists else "w") as out:
# 		if not file_exists:
# 			out.write("Query\tSubject\tBSR\tProcess\n")

# 		for query, match in best_bsr_values.items():
# 			if query in written_queries:
# 				continue  # Skip if query was already written
# 			for subject, computed_score in match.items():
# 				entry = f"{query}\t{subject}\t{computed_score}"
# 				if entry not in existing_matches:
# 					existing_matches.add(f"{entry}")
# 					matched_entries.append((query, f"{entry}\t{process_name}"))
# 			written_queries.add(query)

# 		# Process unmatched queries
# 		for query in not_matched_loci:
# 			if query in written_queries:
# 				continue  # Skip if query was already written
# 			entry = f"{query}\tNot matched\tNA"
# 			non_matched_query.append((query, f"{entry}\t{process_name}"))
# 			written_queries.add(query) 

# 		# Process unmatched subjects
# 		for subject in not_matched_subject:
# 			entry = f"Not matched\t{subject}\tNA"
# 			non_matched_subject.append((subject, f"{entry}\t{process_name}"))

# 		# Sort and write all entries
# 		for _, entry in sorted(matched_entries, key=lambda x: x[0]):
# 			out.write(entry + "\n")
# 		if rep_vs_alleles:
# 			for _, entry in sorted(non_matched_query, key=lambda x: x[0]):
# 				if process_name == "rep_vs_alleles":
# 					out.write(entry + "\n")
# 			for _, entry in sorted(non_matched_subject, key=lambda x: x[0]):
# 				if process_name == "rep_vs_alleles":
# 					out.write(entry + "\n")
# 		else:
# 			for _, entry in sorted(non_matched_query, key=lambda x: x[0]):
# 				if process_name == "rep_vs_rep":
# 					out.write(entry + "\n")
# 			for _, entry in sorted(non_matched_subject, key=lambda x: x[0]):
# 				if process_name == "rep_vs_rep":
# 					out.write(entry + "\n")
# 	

# 	# Save `existing_matches` to a file for persistence
# 	with open(existing_matches_file, "w") as f:
# 		for entry in existing_matches:
# 			f.write(entry + "\n")

# 	return best_blast_matches_file


def translate_files(input_files, output_directory):
	"""
	"""
	# Store paths to FASTA files containing translations
	translated_paths: Dict[str, str] = {}
	# Store protein hashes from all translations
	protein_hashes: Dict[str, str] = {}

	i = 0
	pf.print_message("", "info")
	pf.print_message("Translating query alleles...", "info")
	for locus, file_path in input_files.items():
		# Read FASTA file
		records: Dict[str, str] = sf.import_sequences(file_path)
		# Create translation file path
		translated_file_path = os.path.join(output_directory, f"{locus}_translation.fasta")
		# Translate sequences, save untranslated sequences, get the protein hashes and update translation dictionary
		_, prot_hashes, _ = sf.translate_seq_deduplicate(records,
														translated_file_path,
														0,
														translation_table,
														True)
		# Update the query translation and protein dictionaries
		if len(prot_hashes) > 0:
			translated_paths[locus] = translated_file_path
			# Add hashes used for exact matching
			protein_hashes.update(prot_hashes)

		# Increment number of translated files
		i += 1
		pf.print_message(f"Translated {i}/{len(input_files)}", "info", end='\r', flush=True)
	
	return translated_paths, protein_hashes


first_schema_directory = '/home/rmamede/TestSR/MatchSchemas/spneumo_schema_latest/schema_seed'
second_schema_directory = '/home/rmamede/TestSR/MatchSchemas/spneumo_schema_legacy'
output_directory = '/home/rmamede/TestSR/MatchSchemas/test_pneumo'
bsr = 0.6
translation_table = 11
cpu = 6
no_cleanup = True
rep_vs_alleles = True
def match_schemas(first_schema_directory: str, second_schema_directory: str, output_directory: str, bsr: float,
				  translation_table: int, cpu: int, no_cleanup: bool, rep_vs_alleles: bool) -> str:
	"""
	Match schemas between query and subject directories.

	Parameters
	----------
	first_schema_directory : str
		Path to the first schema directory.
	second_schema_directory : str
		Path to the second schema directory.
	output_directory : str
		Path to the output directory.
	bsr : float
		BLAST Score Ratio value.
	translation_table : int
		Genetic code used for translation.
	cpu : int
		Number of CPU cores to use.
	no_cleanup : bool
		If True, temporary files will not be removed.
	rep_vs_alleles: bool
		If True then after the rep vs rep Blast the program will run a second Blast with rep vs alleles.

	Returns
	-------
	None
	"""
	# A schema files
	a_files: Dict[str, str]
	a_files_short: Dict[str, str]
	a_files, a_files_short = get_schema_files(first_schema_directory)
	# B schema files
	b_files: Dict[str, str]
	b_files_short: Dict[str, str]
	b_files, b_files_short = get_schema_files(second_schema_directory)

	# Choose which schema will be the query (the one with the higher average of alleles per loci)
	total_alleles_a = 0
	for query_loci, fasta_path in a_files.items():
		allele_dict: Dict[str, str] = sf.fetch_fasta_dict(fasta_path, False)
		num_alleles = len(allele_dict)
		total_alleles_a += num_alleles
	# Compute average number of alleles per locus for schema A
	avg_a = total_alleles_a/(len(a_files))

	total_alleles_b = 0
	for query_loci, fasta_path in b_files.items():
		allele_dict: Dict[str, str] = sf.fetch_fasta_dict(fasta_path, False)
		num_alleles = len(allele_dict)
		total_alleles_b += num_alleles
	# Compute average number of alleles per locus for schema B
	avg_b = total_alleles_b/(len(b_files))

	# 
	schema_a_data = [first_schema_directory, a_files, a_files_short, total_alleles_a, avg_a]
	schema_b_data = [second_schema_directory, b_files, b_files_short, total_alleles_b, avg_b]

	# 
	query_schema_data = schema_a_data if avg_a >= avg_b else schema_b_data
	subject_schema_data = schema_a_data if schema_a_data != query_schema_data else schema_b_data

	pf.print_message(f"{query_schema_data[0]} set as Query.", "info")
	pf.print_message(f"{subject_schema_data[0]} set as Subject.", "info")
	pf.print_message(f"Total alleles in Query Schema: {query_schema_data[3]}. Total Loci: {len(query_schema_data[1])}. And an average of {round(query_schema_data[4])} alleles per loci.", "info")
	pf.print_message(f"Total alleles in Subject Schema: {subject_schema_data[3]}. Total Loci: {len(subject_schema_data[1])}. And an average of {round(subject_schema_data[4])} alleles per loci.", "info")

	# Create the output directories
	blast_folder: str = os.path.join(output_directory, 'blast_processing')
	ff.create_directory(blast_folder)
	# Directories for complete schemas
	query_translation_folder: str = os.path.join(blast_folder, 'Query_Translation')
	ff.create_directory(query_translation_folder)
	subject_translation_folder: str = os.path.join(blast_folder, 'Subject_Translation')
	ff.create_directory(subject_translation_folder)
	# Directories for the representatives
	query_translation_rep_folder: str = os.path.join(blast_folder, 'Query_Translation_Rep')
	ff.create_directory(query_translation_rep_folder)
	subject_translation_rep_folder: str = os.path.join(blast_folder, 'Subject_Translation_Rep')
	ff.create_directory(subject_translation_rep_folder)

	# Process query FASTA files for the complete query schema
	pf.print_message('', 'info')
	pf.print_message('Processing the complete Query FASTA files...', 'info')
	query_allele_ids: Dict[str, List[List[str]]] = {}
	query_hashes: Dict[str, str] = {}
	for qlocus, path in query_schema_data[1].items():
		fasta_dict: Dict[str, str] = sf.import_sequences(path)
		hash_dict: Dict[str, str] = {sf.seq_to_hash(v): k for k, v in fasta_dict.items()}
		# Save the IDs of the alleles
		query_allele_ids.setdefault(qlocus, []).append([allele_id for allele_id in fasta_dict.keys()])
		# WIP: Need to consider that same sequence/hash can be represented more than once
		query_hashes.update(hash_dict)

	# Process subject FASTA files for the complete subject schema
	pf.print_message('Processing the complete Subject FASTA files...', 'info')
	subject_allele_ids: Dict[str, List[List[str]]] = {}
	subject_hashes: Dict[str, str] = {}
	for subject_loci, path in subject_schema_data[1].items():
		fasta_dict = sf.import_sequences(path)
		hash_dict: Dict[str, str] = {sf.seq_to_hash(v): k for k, v in fasta_dict.items()}
		# Save the IDs of the alleles
		subject_allele_ids.setdefault(subject_loci, []).append([allele_id for allele_id in fasta_dict.keys()])
		# WIP: Need to consider that same sequence/hash can be represented more than once
		subject_hashes.update(hash_dict)

	# -------------------------------------------------------------------
	# Comparision of the Query and Subject DNA hashes (BSR = 1.0)
	# -------------------------------------------------------------------
	# Prepare best BSR values and query translations

	pf.print_message("", "info")
	pf.print_message("Matching DNA hashes between query and subject schema", "info")
	pf.print_message(f"The query schema has {len(query_hashes)} dna hashes.", "info")
	pf.print_message(f"The subject schema has {len(subject_hashes)} dna hashes.", "info")

	# Find common keys (matching DNA hashes)
	common_keys = set(query_hashes) & set(subject_hashes)
	# Store subject loci that matched and were excluded
	excluded = set()
	match_data = {}
	for dna_hash in common_keys:
		# WIP: Need to consider that same sequence/hash can be represented more than once
		# Get query locus ID
		query_locus = '_'.join(query_hashes[dna_hash].split('_')[:-1])
		# Get subject locus ID
		subject_locus = '_'.join(subject_hashes[dna_hash].split('_')[:-1])
		# Do not proceed if subject locus was already excluded
		if subject_locus in excluded:
			continue
		# Exclude subject loci that matched
		# Exclude main FASTA file
		subject_schema_data[1].pop(subject_locus, None)
		# Exclude FASTA file with representative alleles
		subject_schema_data[2].pop(subject_locus, None)
		excluded.add(subject_locus)
		match_data.setdefault(query_locus, []).append((subject_locus, '1.0'))

	# Write results to the best matches file
	pf.print_message("Writting results to the output file...", "info")
	best_blast_matches_file = write_best_blast_matches_to_file(match_data, output_directory, 'hashes_dna')

	# Print out stats
	pf.print_message(f"The DNA hash comparison found {len(common_keys)} matches.", "info")
	pf.print_message(f"{len(excluded)} subject loci had matches and were excluded.", "info")
	pf.print_message(f"{len(subject_schema_data[1])} subject loci will continue to the next step.", "info")

	# Translate query schema
	query_translated_paths, query_protein_hashes = translate_files(query_schema_data[1], query_translation_folder)
	query_reps_translated_paths, query_reps_protein_hashes = translate_files(query_schema_data[2], query_translation_rep_folder)
	subject_translated_paths, subject_protein_hashes = translate_files(subject_schema_data[1], subject_translation_folder)
	subject_reps_translated_paths, subject_reps_protein_hashes = translate_files(subject_schema_data[2], subject_translation_rep_folder)

	# -------------------------------------------------------------------
	# Comparision of the Query and Subject protein hashes (the BSR = 1.0)
	# -------------------------------------------------------------------
	# Prepare best BSR values and query translations

	pf.print_message("", "info")
	pf.print_message("Matching protein hashes between query and subject schema", "info")
	pf.print_message(f"The query schema has {len(query_protein_hashes)} protein hashes.", "info")
	pf.print_message(f"The subject schema has {len(subject_protein_hashes)} protein hashes.", "info")
	best_bsr_values = {}

	# Find common keys (matching protein hashes)
	common_keys = set(query_protein_hashes) & set(subject_protein_hashes)
	# Store subject loci that matched and were excluded
	excluded = set()
	match_data = {}
	for prot_hash in common_keys:
		# WIP: Need to consider that same protein/hash can be represented more than once
		# Get query locus ID
		## HERE
		query_locus = '_'.join(query_protein_hashes[prot_hash][0].split('_')[:-1])
		# Get subject locus ID
		## HERE
		subject_locus = '_'.join(subject_protein_hashes[prot_hash][0].split('_')[:-1])
		# Do not proceed if subject locus was already excluded
		if subject_locus in excluded:
			continue
		# Exclude subject loci that matched
		# Exclude main FASTA file
		subject_schema_data[1].pop(subject_locus, None)
		# Exclude FASTA file with representative alleles
		subject_schema_data[2].pop(subject_locus, None)
		excluded.add(subject_locus)
		match_data.setdefault(query_locus, []).append((subject_locus, '1.0'))

	# Write results to the best matches file
	pf.print_message("Writting results to the output file...", "info")
	best_blast_matches_file = write_best_blast_matches_to_file(match_data, output_directory, 'hashes_prot')

	# Print out stats
	pf.print_message(f"The protein hash comparison found {len(common_keys)} matches.", "info")
	pf.print_message(f"{len(excluded)} subject loci had matches and were excluded.", "info")
	pf.print_message(f"{len(subject_schema_data)} subject loci will continue to the next step.", "info")

	# -------------------------------------------------------------------
	# Blast with rep vs rep
	# -------------------------------------------------------------------
	# Get Path to the blastp executable
	pf.print_message("", 'info')
	get_blastp_exec: str = lf.get_tool_path('blastp')

	# Get the maximum length of the IDs for better prints
	max_id_length: int = len(max(query_reps_translated_paths.keys(), key=len))

	# Calculate self-scores for each query
	## Optimize?
	self_score_dict: Dict[str, float] = bf.calculate_self_score(query_reps_translated_paths,
															  get_blastp_exec,
															  blast_folder,
															  max_id_length,
															  cpu)

	# Create BLAST database
	pf.print_message("Creating BLASTp database for subject representatives...", "info")
	# Concatenate FASTA files with subject representatives
	concat_file = os.path.join(subject_translation_rep_folder, 'subject_reps_concat.fasta')
	concat_file = ff.concatenate_files(subject_reps_translated_paths.values(), concat_file, header=None)

	blastdb_path: str = os.path.join(blast_folder, 'blastdb')
	ff.create_directory(blastdb_path)
	blast_db_files: str = os.path.join(blastdb_path, 'genbank_protein_db')
	makeblastdb_exec: str = lf.get_tool_path('makeblastdb')
	bf.make_blast_db(makeblastdb_exec, concat_file, blast_db_files, 'prot')

	# Run BLAST rep_vs_rep
	pf.print_message("Running BLASTs (rep vs rep) between schemas...", "info")
	best_bsr_values: Dict[str, Dict[str, float]] = run_blasts_match_schemas(query_reps_translated_paths,
																			blast_db_files,
																			blast_folder,
																			self_score_dict,
																			max_id_length,
																			get_blastp_exec,
																			bsr,
																			cpu)
	pf.print_message("", None)

	# Write the best BLAST matches to a file
	pf.print_message("Writting results to the output file...", "info")
	# Need to select best BLAST results first
	best_blast_matches_file = write_best_blast_matches_to_file(best_bsr_values, query_reps_translated_paths, subject_reps_translated_paths, output_directory, rep_vs_alleles, 'rep_vs_rep')
	###
	best_blast_matches_file = write_best_blast_matches_to_file(match_data, output_directory, 'rep_vs_rep')

	# Remove matched id from the full subject schema file
	locus_removal = 0
	subject_base_list = set()
	for query, match in best_bsr_values.items():
		for subject, score in match.items():
			subject_base = re.sub(r'_\*?\d+$', '', subject)
			subject_base_list.add(subject_base)

	for subject in subject_base_list:
		subject_translations_paths.pop(subject, None)
		locus_removal += 1

	# Write the sequences to the full master file
	pf.print_message("Writting master file...", "info")
	with open(master_file_path, 'w') as master:
		for locus_id, fasta_path in subject_translations_paths.items():
			with open(fasta_path, 'r') as fasta_file:
				for record in SeqIO.parse(fasta_file, 'fasta'):
					master.write(f">{record.id}\n{record.seq}\n")

	pf.print_message(f"From the rep vs rep Blast {len(best_bsr_values)} matches were found.", "info")
	pf.print_message(f"{locus_removal} loci were removed.", "info")
	pf.print_message(f"{len(subject_translations_paths)} subject loci have not found a match.", "info")

	# -------------------------------------------------------------------
	# Blast with rep vs alleles
	# -------------------------------------------------------------------
	# Create BLAST database
	if rep_vs_alleles:
		pf.print_message("", "info")
		pf.print_message("Creating Blast database with complete subject schema...", "info")
		blastdb_path: str = os.path.join(blast_folder, 'blastdb')
		ff.create_directory(blastdb_path)
		blast_db_files: str = os.path.join(blastdb_path, 'genbank_protein_db')
		makeblastdb_exec: str = lf.get_tool_path('makeblastdb')
		bf.make_blast_db(makeblastdb_exec, master_file_path, blast_db_files, 'prot')

		# Run BLAST rep query vs alleles subject
		pf.print_message("Running BLASTs (rep vs allele) between schemas...", "info")
		best_bsr_values: Dict[str, Dict[str, float]] = run_blasts_match_schemas(query_translations_rep_paths,
																				blast_db_files,
																				blast_folder,
																				self_score_dict,
																				max_id_length,
																				get_blastp_exec,
																				bsr,
																				cpu)
		pf.print_message("", None)

		# Remove matched id from the full subject schema file
		locus_removal = 0
		subject_base_list = set()
		for query, match in best_bsr_values.items():
			for subject, score in match.items():
				subject_base = re.sub(r'_\*?\d+$', '', subject)
				subject_base_list.add(subject_base)

		for subject in subject_base_list:
			subject_translations_paths.pop(subject, None)
			locus_removal += 1

		# Write the best BLAST matches to a file
		pf.print_message("Writting results to the output file...", "info")
		best_blast_matches_file = write_best_blast_matches_to_file(best_bsr_values, query_translations_rep_paths, subject_translations_paths, output_directory, rep_vs_alleles, 'rep_vs_alleles')

		pf.print_message(f"From the rep vs alleles Blast {len(best_bsr_values)} matches were found.", "info")
		pf.print_message(f"{locus_removal} loci were removed.", "info")
		pf.print_message(f"{len(subject_translations_paths)} subject loci had no matches.", "info")

	# Clean up temporary files
	if not no_cleanup:
		pf.print_message("Cleaning up temporary files...", "info")
		# Remove temporary files
		ff.cleanup(output_directory, [best_blast_matches_file, logf.get_log_file_path(gb.LOGGER)])

	return best_blast_matches_file
