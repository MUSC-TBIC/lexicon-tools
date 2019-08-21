
import csv

from tqdm import tqdm

import concept_mapper_utils as cm
import umls_utils as uu

def parse_snomedct_core( filename ):
    concepts = {}
    with open( filename , 'r' ) as fp:
        snomedct_csv = csv.reader( fp , delimiter = '|' )
        for row in snomedct_csv:
            ## SNOMED_CONCEPT_STATUS
            concept_status = row[ 2 ]
            ## Skip any non-current entries
            if( concept_status != 'Current' ):
                continue
            ## SNOMED_CID
            snomed_cid = row[ 0 ]
            ## UMLS_CUI
            umls_cui = row[ 3 ]
            ## SNOMED_FSN
            fully_specified_name = row[ 1 ]
            if( umls_cui not in concepts ):
                concepts[ umls_cui ] = {}
                concepts[ umls_cui ][ 'SNOMEDCT' ] = {}
            concepts[ umls_cui ][ 'SNOMEDCT' ][ snomed_cid ] = {}
            concepts[ umls_cui ][ 'SNOMEDCT' ][ snomed_cid ][ 'FSN' ] = fully_specified_name
    auth_client = uu.init_authentication( UMLS_API_TOKEN )
    i = 0
    for cui in tqdm( concepts , desc = 'Extracting Terms' ):
        i += 1
        ## TODO - Reset the authentication key regularly
        if( i > 5 ):
            concepts[ cui ][ 'preferred_term' ] = ''
            concepts[ cui ][ 'variant_terms' ] = set()
            continue
            auth_client = uu.init_authentication( UMLS_API_TOKEN )
        preferred_term = uu.get_cuis_preferred_atom( auth_client ,
                                                     'current' ,
                                                     cui )
        concepts[ cui ][ 'preferred_term' ] = preferred_term
        ## TODO - make this function call less surprising
        ## TODO - check if multiple TUIs are possible
        tui = uu.get_cuis_atom( auth_client , 'current' ,
                                 cui , atom_type = '' )
        concepts[ cui ][ 'tui' ] = tui
        variant_terms = uu.get_cuis_eng_atom( auth_client ,
                                              'current' ,
                                              cui )
        concepts[ cui ][ 'variant_terms' ] = variant_terms
        ##print( '{}\t{}'.format( cui , preferred_term ) )
    return( concepts )

if __name__ == "__main__":
    concepts = parse_snomedct_core( 'SNOMEDCT_CORE_SUBSET_201811.txt' )
    root = cm.create_concept_mapper_template()
    for cui in sorted( concepts ):
        for cid in sorted( concepts[ cui ] ):
            print( '{}\t{}\t{}\t{}'.format( cui ,
                                            '' ,
                                            concepts[ cui ][ cid ][ 'FSN' ] ,
                                            cid ) )
