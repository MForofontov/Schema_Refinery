"""
Purpose
-------

This module contains default values for Schema_refinery's
parameters.

Code documentation
------------------
"""

# GitHub repository and contacts
repository = 'https://github.com/B-UMMI/Schema_Refinery'
contacts = 'imm-bioinfo@medicina.ulisboa.pt'

# minimum Python version
MIN_PYTHON = [(3, 6, 0), '3.6.0']

# socket timeout for urllib calls
SOCKET_TIMEOUT = 30

# URL template for proteome download
PROTEOME_TEMPLATE_URL = 'https://rest.uniprot.org/uniprotkb/stream?query=proteome:{0}&format=fasta&compressed=true'

LOCUS_CLASSIFICATIONS_TO_CHECK = ["ASM", 
                                  #"ALM", 
                                  #"NIPH", 
                                  #"NIPHEM"
                                  ]

DNA_BASES = 'AGCT'

MAX_GAP_UNITS = 4

OPACITY = 0.2
