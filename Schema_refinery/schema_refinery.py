"""
Purpose
-------
This file call all other modules of the packages, containing several arguments
as input depending on the desired module.

Code documentation
------------------
"""
import sys
import argparse

try:
    from DownloadAssemblies import download_assemblies
except ModuleNotFoundError:
    from Schema_refinery.DownloadAssemblies import download_assemblies

def download_module():
    """
    Function that contains the required arguments for the download_module of the
    schema refinery package, this function exports the arguments to
    download_asseblies.py
    """
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)

    parser.add_argument('Download_module', nargs='+',
                        help='')

    #Common arguments between databases
    parser.add_argument('-db', '--database', type=str,
                        required=True, dest='database',
                        nargs='+',
                        choices = ['NCBI','ENA661K'],
                        help='Databases from which assemblies will be downloaded. ')

    parser.add_argument('-t', '--taxon', type=str,
                        required=True, dest='taxon',
                        help='Scientific name of the taxon.')

    parser.add_argument('-o', '--output-directory', type=str,
                        required=True, dest='output_directory',
                        help='Path to the output directory.')

    parser.add_argument('-th', '--threads', type=int,
                        required=False, default=2,
                        dest='threads',
                        help='Number of threads for download.')

    parser.add_argument('-r', '--retry', type=int,
                        required=False, dest='retry',
                        default=7,
                        help='Maximum number of retries when a '
                             'download fails.')

    parser.add_argument('-e', '--email', type=str,
                        required=True, dest='email',
                        help='email for entrez NCBI')

    parser.add_argument('-k', '--api_key', type=str,
                        required=False, dest='api_key',
                        help='API key to increase the mumber of requests')

    parser.add_argument('-fm', '--fetch-metadata',
                        required=False, dest='f_metadata',
                        action='store_true',
                        default = False,
                        help='Do not fetch metadata if toggled')

    parser.add_argument('-f', '--filter_criteria_path',type=str,
                        required=False, dest='filter_criteria_path',
                        help='TSV file containing filter parameters for choosen'
                             'assemblies before downloading')

    parser.add_argument('--download', action='store_true',
                        required=False, dest='download',
                        help='If the assemblies from the selected samples'
                             'should be downloaded.')

    #Arguments specific for NCBI

    parser.add_argument('-i', '--input-table', type=str,
                        required=False, dest='input_table',
                        help='TSV file downloaded from the '
                             'NCBI Genome Assembly and Annotation '
                             'report.')

    #Specific for ENA661k database

    parser.add_argument('-stride', '--stride', type=str,
                        required=False,
                        dest='stride',
                        help='Interval specifying which sample ids to '
                             'download. Example: "1:2000" - This will '
                             'download the first 2000 samples. Note: If '
                             'you want to download from the first id, '
                             'you have to put "1", not "0" in the lower '
                             'value.')

    args = parser.parse_args()

    del args.Download_module

    download_assemblies.main(args)

def main():
    """
    Main call function that sorts depending on the arguments what module of the
    schema_rifinery package to use.
    """
    module_info = {"Download_module":['Downloads assemblies from either NCBI '
                                      'or ENA661K database',download_module]}

    if len(sys.argv) == 1 or sys.argv[1] not in module_info:
        print('possible arguments here')
        sys.exit()

    module = sys.argv[1]
    module_info[module][1]()



if __name__ == "__main__":

    main()
