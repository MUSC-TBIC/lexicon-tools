
import logging as log
import os
import sys

import csv

from tqdm import tqdm

import requests
import json

import pickle

import concept_mapper_utils as cm
import umls_utils as uu

try:
    from umls.umls import UMLSLookup
    umls_lu = UMLSLookup()
    log.debug( 'Local py-umls look-up system loaded' )
except ImportError:
    umls_lu = None
    log.debug( 'Local py-umls look-up system not available' )


########################################################################
##
########################################################################

def add_variant_term( auth_client , concepts , cui , variant , head = None ):
    log.debug( 'Adding variant term {} ~ {}'.format( cui , variant ) )
    ## Make sure we have a CUI entry to hang this variant on
    concepts = flesh_out_concept( auth_client , concepts , cui ,
                                  head = head )
    if( cui not in concepts ):
        concepts[ cui ] = {}
        concepts[ cui ][ 'preferred_term' ] = ''
        concepts[ cui ][ 'tui' ] = ''
        concepts[ cui ][ 'variant_terms' ] = set()
    if( variant not in concepts[ cui ][ 'variant_terms' ] ):
        concepts[ cui ][ 'variant_terms' ].add( variant )
    return( concepts )


def seed_concept( concepts , cui , head = None ):
    log.debug( 'Seeding concept {} ( total concepts = {}, head = {} )'.format( cui , len( concepts ) , head ) )
    if( cui not in concepts ):
        ## TODO - add a real empty dictionary here
        concepts[ cui ] = {}
        ##
        if( head is not None ):
            concepts[ cui ][ 'head_cui' ] = head
            if( head not in concepts ):
                log.warning( 'Missing head CUI:  {}'.format( head ) )
            else:
                if( 'related_cuis' not in concepts[ head ] ):
                    concepts[ head ][ 'related_cuis' ] = set()
                concepts[ head ][ 'related_cuis' ].add( cui )
    ##
    log.debug( 'New concept count = {}'.format( len( concepts ) ) )
    return( concepts )


def flesh_out_seed_concept( auth_client , concepts , cui ):
    log.debug( 'Fleshing out {} ( total concepts = {} )'.format( cui , len( concepts ) ) )
    if( cui not in concepts ):
        log.warn( 'CUI \'{}\' was never seeded. Skipping'.format( cui ) )
        return( concepts )
    elif( 'preferred_term' not in concepts[ cui ] ):
        ## Initializing this to empty tells us later that we've
        ## already looked for this concept
        concepts[ cui ][ 'preferred_term' ] = ''
        concepts[ cui ][ 'tui' ] = ''
        concepts[ cui ][ 'variant_terms' ] = set()
        ##
        preferred_term = uu.get_cuis_preferred_atom( auth_client ,
                                                     'current' ,
                                                     cui )
        if( preferred_term is None ):
            return( concepts )
        concepts[ cui ][ 'preferred_term' ] = preferred_term
        ## TODO - make this function call less surprising
        ## TODO - check if multiple TUIs are possible
        tui = uu.get_cuis_atom( auth_client , 'current' ,
                                cui , atom_type = '' )
        concepts[ cui ][ 'tui' ] = tui
        ##
        variant_terms = uu.get_cuis_eng_atom( auth_client ,
                                              'current' ,
                                              cui )
        log.debug( '\tVariant Terms:  {}'.format( variant_terms ) )
        concepts[ cui ][ 'variant_terms' ] = variant_terms
        ##
    return( concepts )


def flesh_out_concept( auth_client , concepts , cui , head = None ):
    log.debug( 'Fleshing out {} ( total concepts = {}, head = {} )'.format( cui , len( concepts ) , head ) )
    if( cui not in concepts ):
        log.warn( 'CUI \'{}\' was never seeded. Skipping'.format( cui ) )
        return( concepts )
    elif( 'preferred_term' not in concepts[ cui ] ):
        preferred_term = uu.get_cuis_preferred_atom( auth_client ,
                                                     'current' ,
                                                     cui )
        if( preferred_term is None ):
            return( concepts )
        concepts[ cui ][ 'preferred_term' ] = preferred_term
        ## TODO - make this function call less surprising
        ## TODO - check if multiple TUIs are possible
        tui = uu.get_cuis_atom( auth_client , 'current' ,
                                cui , atom_type = '' )
        concepts[ cui ][ 'tui' ] = tui
        ## TODO NEXT
        #variant_terms = uu.get_cuis_eng_atom( auth_client ,
        #                                      'current' ,
        #                                      cui )
        #log.debug( '\tVariant Terms:  {}'.format( variant_terms ) )
        #concepts[ cui ][ 'variant_terms' ] = variant_terms
    ##
    return( concepts )


def get_concept_properties( cui ):
    description_triple = umls_lu.lookup_code( cui )
    if( len( description_triple ) == 1 ):
        preferred_term , src , semantic_type = description_triple[ 0 ]
        ## TODO - add a check to see if we're overwriting the preferred term
        ##        or TUI
        return( preferred_term , semantic_type )
    elif( len( description_triple ) > 1 ):
        log.warning( 'Error:\t{} terms returned for CUI {} (expected exactly 1)'.format( len( description_triple ) ,
                                                                                         cui ) )
        return( None , None )
    else:
        log.warning( 'Error:\t{} terms returned for CUI {} (expected exactly 1)'.format( 0 ,
                                                                                         cui ) )
        return( None , None )


def flesh_out_concept_via_py_umls( concepts , cui , head = None ):
    log.debug( 'Fleshing out {} ( total concepts = {}, head = {} )'.format( cui , len( concepts ) , head ) )
    if( cui not in concepts ):
        preferred_term , semantic_type = get_concept_properties( cui )
        if( preferred_term is None or
            semantic_type is None ):
            return( concepts )
        concepts[ cui ] = {}
        concepts[ cui ][ 'preferred_term' ] = preferred_term
        log.debug( '\tPT:  {}'.format( preferred_term ) )
        concepts[ cui ][ 'tui' ] = semantic_type
        log.debug( '\tTUI:  {}'.format( semantic_type ) )
        ##
        variant_terms = set()
        for term_pair in umls_lu.lookup_variants( cui , sources = 'MTH' ):
            variant_term , term_source = term_pair
            variant_terms.add( variant_term )
        log.debug( '\tVariant Terms:  {}'.format( variant_terms ) )
        concepts[ cui ][ 'variant_terms' ] = variant_terms
        ##
        if( head is not None ):
            concepts[ cui ][ 'head_cui' ] = head
            if( head not in concepts ):
                log.warning( 'Missing head CUI:  {}'.format( head ) )
            else:
                if( 'related_cuis' not in concepts[ head ] ):
                    concepts[ head ][ 'related_cuis' ] = set()
                concepts[ head ][ 'related_cuis' ].add( cui )
    ##
    log.debug( 'New concept count = {}'.format( len( concepts ) ) )
    return( concepts )


########################################################################
##
########################################################################

def get_related_rxnorm_concepts( auth_client , concepts , rxcui_str , relation , head = None ):
    base_uri = 'https://rxnav.nlm.nih.gov/REST/'
    content_endpoint = "rxcui/" + rxcui_str + "/related.json?tty=" + relation
    ##log( base_uri , content_endpoint )
    r = requests.get( base_uri + content_endpoint )
    r.encoding = 'utf-8'
    ##log( r )
    items  = json.loads(r.text)
    all_cuis = set()
    groupData = items[ "relatedGroup" ][ "conceptGroup" ]
    ##log( items , groupData )
    for group in groupData:
        if( 'conceptProperties' in group ):
            cProps = group[ "conceptProperties" ]
            for prop in cProps:
                umls_cui = prop[ 'umlscui' ]
                name = prop[ 'name' ]
                add_variant_term( auth_client , concepts , umls_cui , name , head = head )
                all_cuis.add( umls_cui )
    return( concepts , all_cuis )

def get_rxcui_brands( auth_client , concepts , rxcui_str , head = None ):
    concepts , all_cuis = get_related_rxnorm_concepts( auth_client , concepts ,
                                                       rxcui_str , relation = "BN" ,
                                                       head = head )
    ##log( all_cuis )
    return( concepts , all_cuis )

def get_rxcui_ingredients( auth_client , concepts , rxcui_str , head = None ):
    concepts , all_cuis = get_related_rxnorm_concepts( auth_client , concepts ,
                                                       rxcui_str , relation = "IN+MIN" ,
                                                       head = head )
    ##log( all_cuis )
    return( concepts , all_cuis )

########################################################################
##
########################################################################



def parse_focused_allergens( input_filename , concepts = {} , partials_dir = None ):
    ##
    cui_dict = {}
    synonym_dict = {}
    ##
    with open( input_filename , 'r' ) as in_fp:
        in_tsv = csv.reader( in_fp , dialect=csv.excel_tab )
        ## Skip the header
        headers = next( in_tsv , None )
        for cols in tqdm( in_tsv , desc = 'Fixed rows' , total = 137 ,
                          file = sys.stdout ):
            ## ALLERGEN_DESCRIPTION
            alt_name = cols[ 0 ]
            if( len( alt_name ) == 0 ):
                continue
            ## CUI
            head_cui = cols[ 1 ]
            ## Include parents (all RN)?
            include_umls_parents_str = cols[ 2 ]
            ## set later if not None
            parents_str = None ## cols[ 3 / 'Parents (or RO) to include (if some)' ] 
            ## Include RO?
            include_ro_str = cols[ 4 ]
            ## Include children or children
            include_children_of_children_str = cols[ 5 ]
            ## SNOMED
            snomed_concepts_str = cols[ 6 ] ## SNOMED-CT conceptsIDs
            ## RxNORM (RxCUI)
            rxcui_str = cols[ 7 ]
            ## Include parents (RxNORM ancestors)?
            include_parents_str = cols[ 8 ]
            ## Children to be excluded
            exclude_children_str = cols[ 9 ] ## Children to be excluded
            ## Do we need to process this line or can we just update our
            ## model with a partial already saved in a pickle?
            pickle_file = os.path.join( partials_dir , 'processed_{}.pkl'.format( head_cui ) )
            if( partials_dir is not None and
                os.path.exists( pickle_file ) ):
                log.debug( 'Pickle file already exists for CUI {}. Loading and continuing to next.'.format( head_cui ) )
                with open( pickle_file , 'rb' ) as fp:
                    cui_dict , synonym_dict , concepts = pickle.load( fp )
                continue
            ## Re-up the authentication token for every row
            auth_client = uu.init_authentication( uu.UMLS_API_TOKEN )
            ##
            cui_dict[ head_cui ] = {}
            synonym_dict = set()
            log.debug( 'Old CUI:\t{}'.format( head_cui ) )
            ##
            cui_dict[ head_cui ][ 'include_umls_parents_flag' ] = None
            cui_dict[ head_cui ][ 'parents_include_list' ] = []
            cui_dict[ head_cui ][ 'descendants_include_list' ] = []
            cui_dict[ head_cui ][ 'descendants_exclude_list' ] = []
            cui_dict[ head_cui ][ 'include_umls_ro_flag' ] = None
            cui_dict[ head_cui ][ 'include_umls_children_of_children_flag' ] = None
            cui_dict[ head_cui ][ 'include_rxnorm_parents_flag' ] = None
            cui_dict[ head_cui ][ 'ro_include_list' ] = []
            cui_dict[ head_cui ][ 'ro_exclude_list' ] = []
            ## Child CUIs to Exclude
            if( include_children_of_children_str.lower() == 'yes' ):
                cui_dict[ head_cui ][ 'include_umls_children_of_children_flag' ] = True
            else:
                cui_dict[ head_cui ][ 'include_umls_children_of_children_flag' ] = False
            if( exclude_children_str != '' ):
                for this_cui in exclude_children_str.split( ',' ):
                    this_cui = this_cui.lstrip( ' ' )
                    this_cui = this_cui.strip( '"' )
                    cui_dict[ head_cui ][ 'descendants_exclude_list' ].append( this_cui )
                    log.debug( '\tEx: {}'.format( this_cui ) )
            ## Include UMLS Parents (RN)
            if( include_umls_parents_str.lower() == 'yes' ):
                cui_dict[ head_cui ][ 'include_umls_parents_flag' ] = True
                parent_cuis = uu.get_rns( auth_client , 'current' , head_cui )
                for parent_cui in parent_cuis:
                    cui_dict[ head_cui ][ 'parents_include_list' ].append( parent_cui )
                    log.debug( '\tP:  {}'.format( parent_cui ) )
                    synonym_dict.add( parent_cui )
            elif( include_umls_parents_str.lower() == 'no' ):
                cui_dict[ head_cui ][ 'include_umls_parents_flag' ] = False
            elif( include_umls_parents_str.lower() != 'no' ):
                log.warning( 'Error:\t{}\n\t{}'.format( 'Unrecognized Include Parents Flag' ,
                                                        include_umls_parents_str ) )
            # ##
            ## Include UMLS RO (related other)
            ## Include SNOMED Concepts -> CUIs
            ## Include SNOMED Parents (ISA)
            if( include_ro_str.lower() == 'yes' ):
                cui_dict[ head_cui ][ 'include_ro_flag' ] = True
                ro_cuis = uu.get_ros( auth_client , 'current' , head_cui )
                for new_cui in ro_cuis:
                    cui_dict[ head_cui ][ 'ro_include_list' ].append( new_cui )
                    log.debug( '\tR:  {}'.format( new_cui ) )
                    synonym_dict.add( new_cui )
            elif( include_ro_str.lower() == 'no' ):
                cui_dict[ head_cui ][ 'include_ro_flag' ] = False
            elif( include_ro_str.lower() != 'some' ):
                log.warning( 'Error:\t{}\n\t{}'.format( 'Unrecognized Include RO Flag' ,
                                                        include_ro_str ) )
            ##
            if( include_umls_parents_str.lower() == 'some' or
                include_ro_str.lower() == 'some' ):
                parents_str = cols[ 3 ]
                for this_cui in parents_str.split( ',' ):
                    this_cui = this_cui.strip( )
                    this_cui = this_cui.strip( '"' )
                    cui_dict[ head_cui ][ 'parents_include_list' ].append( this_cui )
                    log.debug( '\tP:  {}'.format( this_cui ) )
                    synonym_dict.add( this_cui )
            # ##
            descendant_cuis = uu.get_first_umls_children( auth_client , head_cui ,
                                                          cui_dict[ head_cui ][ 'descendants_exclude_list' ] ,
                                                          get_grandchildren = cui_dict[ head_cui ][ 'include_umls_children_of_children_flag' ] )
            for descendant_cui in descendant_cuis:
                log.debug( '\tD:  {}'.format( descendant_cui ) )
                synonym_dict.add( descendant_cui )
            # #####
            if( rxcui_str.isdigit() ):
                log.debug( '\tRx: {}'.format( rxcui_str ) )
                concepts , brand_cuis = get_rxcui_brands( auth_client , concepts , rxcui_str , head = head_cui )
                for brand_cui in tqdm( brand_cuis , desc = 'Finding Brands' ,
                                       leave = False ,
                                       file = sys.stdout ):
                    if( brand_cui in cui_dict[ head_cui ][ 'descendants_exclude_list' ] ):
                        continue
                    log.debug( '\t\tD:  {}'.format( brand_cui ) )
                    synonym_dict.add( brand_cui )
                concepts , ingredient_cuis = get_rxcui_ingredients( auth_client , concepts , rxcui_str , head = head_cui )
                for ingredient_cui in tqdm( ingredient_cuis , desc = 'Finding Ingredients' ,
                                            leave = False ,
                                            file = sys.stdout ):
                    if( ingredient_cui in cui_dict[ head_cui ][ 'descendants_exclude_list' ] ):
                        continue
                    log.debug( '\t\tD:  {}'.format( ingredient_cui ) )
                    synonym_dict.add( ingredient_cui )
            else:
                for this_rxcui in rxcui_str.split( ',' ):
                    this_rxcui = this_rxcui.lstrip( ' ' )
                    this_rxcui = this_rxcui.strip( '"' )
                    log.debug( '\tRC: {}'.format( this_rxcui ) )
                    all_rxcuis = uu.get_rxclass_members( this_rxcui )
                    for this_rxcui in tqdm( all_rxcuis , desc = 'Finding RxClass Members' ,
                                            leave = False ,
                                            file = sys.stdout ):
                        log.debug( '\t\tRx: {}'.format( this_rxcui ) )
                        rxcuis_umls_cui = uu.get_rxcui_umls_cui( this_rxcui )
                        for umls_cui in rxcuis_umls_cui:
                            synonym_dict.add( umls_cui )
                        concepts , brand_cuis = get_rxcui_brands( auth_client , concepts , this_rxcui , head = head_cui )
                        for brand_cui in brand_cuis:
                            if( brand_cui in cui_dict[ head_cui ][ 'descendants_exclude_list' ] ):
                                continue
                            log.debug( '\t\t\tD:  {}'.format( brand_cui ) )
                            synonym_dict.add( brand_cui )
                        concepts , ingredient_cuis = get_rxcui_ingredients( auth_client , concepts , this_rxcui , head = head_cui )
                        for ingredient_cui in ingredient_cuis:
                            if( ingredient_cui in cui_dict[ head_cui ][ 'descendants_exclude_list' ] ):
                                continue
                            log.debug( '\t\t\tD:  {}'.format( ingredient_cui ) )
                            synonym_dict.add( ingredient_cui )
            ### Write out a uniq'd list of synonymous CUIs
            concepts = flesh_out_concept( auth_client , concepts , head_cui )
            #all_eng_atoms = set()
            #all_eng_atoms.add( head_atom )
            for cui in synonym_dict:
                concepts = flesh_out_concept( auth_client , concepts , cui , head = head_cui )
            ## At the end of every loop, we want to update our partial file
            ## with the latest datastructures (in pickle form)
            if( partials_dir is not None ):
                with open( os.path.join( partials_dir , 'processed_{}.pkl'.format( head_cui ) ) , 'wb' ) as fp:
                    pickle.dump( [ cui_dict , synonym_dict , concepts ] , fp )
    ####
    return( concepts )


########################################################################
##
########################################################################


def parse_focused_problems_via_api( cui_dict , concepts = {} , partials_dir = None ):
    #######################################################################
    dict_keys = sorted( cui_dict.keys() )
    for head_cui in tqdm( dict_keys , desc = 'Extracting Terms' ,
                          file = sys.stdout ):
        pickle_file = os.path.join( partials_dir , 'processed_{}.pkl'.format( head_cui ) )
        if( partials_dir is not None and
            os.path.exists( pickle_file ) ):
            log.debug( 'Pickle file already exists for CUI {}. Loading and continuing to next.'.format( head_cui ) )
            with open( pickle_file , 'rb' ) as fp:
                cui_dict , concepts = pickle.load( fp )
            continue
        auth_client = uu.init_authentication( uu.UMLS_API_TOKEN )
        if( 'preferred_term' not in concepts[ head_cui ] or
            concepts[ head_cui ][ 'preferred_term' ] == '' ):
            preferred_term = uu.get_cuis_preferred_atom( auth_client ,
                                                         'current' ,
                                                         head_cui )
            concepts[ head_cui ][ 'preferred_term' ] = preferred_term
        ##
        if( 'tui' not in concepts[ head_cui ] or
            concepts[ head_cui ][ 'tui' ] == '' ):
            ## TODO - make this function call less surprising
            ## TODO - check if multiple TUIs are possible
            tui = uu.get_cuis_atom( auth_client , 'current' ,
                                    head_cui , atom_type = '' )
            concepts[ head_cui ][ 'tui' ] = tui
        ##
        if( 'variant_terms' not in concepts[ head_cui ] or
            not bool( concepts[ head_cui ][ 'variant_terms' ] ) ):
            variant_terms = uu.get_cuis_eng_atom( auth_client ,
                                                  'current' ,
                                                  head_cui )
            log.debug( '\tVariant Terms:  {}'.format( variant_terms ) )
            concepts[ head_cui ][ 'variant_terms' ] = variant_terms
        ##
        if( cui_dict[ head_cui ][ 'include_parents_flag' ] == True ):
            if( cui_dict[ head_cui ][ 'parents_include_list' ] == [] ):
                parent_cuis = uu.get_rns( auth_client , 'current' , head_cui )
                for parent_cui in parent_cuis:
                    cui_dict[ head_cui ][ 'parents_include_list' ].append( parent_cui )
            ##
            for parent_cui in tqdm( cui_dict[ head_cui ][ 'parents_include_list' ] , desc = 'Finding Parents' ,
                                    leave = False ,
                                    file = sys.stdout ):
                log.debug( '\tP:  {}'.format( parent_cui ) )
                concepts = flesh_out_concept( auth_client , concepts , parent_cui , head = head_cui )
        log.debug( 'Done with parents' )
        ##
        if( cui_dict[ head_cui ][ 'include_ro_flag' ] == True ):
            ro_cuis = uu.get_ros( auth_client , 'current' , head_cui )
            for new_cui in ro_cuis:
                if( new_cui in cui_dict[ head_cui ][ 'ro_exclude_list' ] ):
                    continue
                cui_dict[ head_cui ][ 'ro_include_list' ].append( new_cui )
            for ro_cui in tqdm( cui_dict[ head_cui ][ 'ro_include_list' ] , desc = 'Finding ROs' ,
                                leave = False ,
                                file = sys.stdout ):
                log.debug( '\tR:  {}'.format( ro_cui ) )
                concepts = flesh_out_concept( auth_client , concepts , ro_cui , head = head_cui )
        log.debug( 'Done with ROs' )
        ##
        descendant_cuis = uu.get_all_umls_descendants( auth_client , head_cui ,
                                                       concepts ,
                                                       cui_dict[ head_cui ][ 'descendants_exclude_list' ] )
        for descendant_cui in tqdm( descendant_cuis , desc = 'Finding Descendants' ,
                                    leave = False ,
                                    file = sys.stdout ):
            log.debug( '\tD:  {}'.format( descendant_cui ) )
            concepts = flesh_out_concept( auth_client , concepts , descendant_cui , head = head_cui )
        log.debug( 'Done with descendants' )
        ##
        for snomed_cui in tqdm( cui_dict[ head_cui ][ 'snomed_parent_list' ] , desc = 'Finding SNOMED Parents' ,
                                leave = False ,
                                file = sys.stdout ):
            log.debug( '\tR:  {}'.format( ro_cui ) )
            concepts = flesh_out_concept( auth_client , concepts , snomed_cui , head = head_cui )
        ##
        for snomed_cui in tqdm( cui_dict[ head_cui ][ 'snomed_include_list' ] , desc = 'Finding SNOMED Concepts' ,
                                leave = False ,
                                file = sys.stdout ):
            descendant_cuis = uu.get_all_snomed_descendants( auth_client , snomed_cui ,
                                                             cui_dict[ head_cui ][ 'descendants_exclude_list' ] )
            for descendant_cui in descendant_cuis:
                log.debug( '\t\tD:  {}'.format( descendant_cui ) )
                concepts = flesh_out_concept( auth_client , concepts , descendant_cui , head = head_cui )
        log.debug( 'Done with SNOMED' )
        ## At the end of every loop, we want to update our partial file
        ## with the latest datastructures (in pickle form)
        if( partials_dir is not None ):
            with open( os.path.join( partials_dir , 'processed_{}.pkl'.format( head_cui ) ) , 'wb' ) as fp:
                pickle.dump( [ cui_dict , concepts ] , fp )
        ##print( '{}\t{}'.format( cui , preferred_term ) )
    return( cui_dict , concepts )


def parse_focused_problems_via_py_umls( input_filename , concepts , partials_dir = None ):
    ##
    concepts = {}
    cui_dict = {}
    synonym_dict = {}
    ##
    with open( input_filename , 'r' ) as in_fp:
        in_tsv = csv.reader( in_fp , dialect=csv.excel_tab )
        ## Skip the header
        headers = next( in_tsv , None )
        for cols in in_tsv:
            alt_name = cols[ 0 ]
            if( len( alt_name ) == 0 ):
                continue
            ## UMLS concepts
            head_cui = cols[ 1 ]
            include_umls_parents_str = cols[ 2 ]
            parents_str = None ## cols[ 3 ] set later if not None
            include_ro_str = cols[ 4 ]
            ro_str = None ## cols[ 5 ] set later if not none
            ## SNOMED concepts 
            snomed_concepts_str = cols[ 6 ] ## SNOMED-CT conceptsIDs
            include_snomed_parents_str = cols[ 7 ] ## Include parents (SNOMED ancestors)?
            ancestors_str = cols[ 8 ] ## Ancestors to include (if some)
            descendants_exclude_str = cols[ 9 ] ## Children to be excluded
            #vocabulary = 'SNOMEDCT_US'
            #cui , alt_name = get_cui( auth_client , 'current' , c_code , vocabulary ).split( '\t' )
            ##
            log.debug( 'Old CUI:\t{}'.format( head_cui ) )
            cui_dict[ head_cui ] = {}
            synonym_dict[ head_cui ] = set()
            if( head_cui not in concepts ):
                concepts[ head_cui ] = {}
            cui_dict[ head_cui ][ 'include_parents_flag' ] = None
            cui_dict[ head_cui ][ 'parents_include_list' ] = []
            cui_dict[ head_cui ][ 'descendants_include_list' ] = []
            cui_dict[ head_cui ][ 'descendants_exclude_list' ] = []
            cui_dict[ head_cui ][ 'include_ro_flag' ] = None
            cui_dict[ head_cui ][ 'ro_include_list' ] = []
            cui_dict[ head_cui ][ 'ro_exclude_list' ] = []
            cui_dict[ head_cui ][ 'snomed_include_list' ] = []
            ## Child CUIs to Exclude
            if( descendants_exclude_str != '' ):
                for this_cui in descendants_exclude_str.split( ',' ):
                    this_cui = this_cui.lstrip( ' ' )
                    this_cui = this_cui.strip( '"' )
                    cui_dict[ head_cui ][ 'descendants_exclude_list' ].append( this_cui )
                    log.debug( '\tEx: {}'.format( this_cui ) )
            ## Include UMLS Parents (RN)
            ## Include UMLS RO (related other)
            ## Include SNOMED Concepts -> CUIs
            ## Include SNOMED Parents (ISA)
            if( include_umls_parents_str.lower() == 'no' ):
                cui_dict[ head_cui ][ 'include_parents_flag' ] = False
            elif( include_umls_parents_str.lower() == 'yes' ):
                cui_dict[ head_cui ][ 'include_parents_flag' ] = True
            elif( include_umls_parents_str.lower() == 'some' ):
                cui_dict[ head_cui ][ 'include_parents_flag' ] = True
                parents_str = cols[ 3 ]
                for this_cui in parents_str.split( ',' ):
                    this_cui = this_cui.strip( )
                    this_cui = this_cui.strip( '"' )
                    cui_dict[ head_cui ][ 'parents_include_list' ].append( this_cui )
                    log.debug( '\tP:  {}'.format( this_cui ) )
            else:
                log.warning( 'Error:\t{}\n\t{}'.format( 'Unrecognized Include Parents Flag' ,
                                                        include_umls_parents_str ) )
            # ##
            if( include_ro_str.lower() == 'yes' ):
                cui_dict[ head_cui ][ 'include_ro_flag' ] = True
                ro_str = cols[ 5 ]
                if( ro_str != '' ):
                    for this_cui in ro_str.split( ',' ):
                        this_cui = this_cui.lstrip( ' ' )
                        this_cui = this_cui.strip( '"' )
                        cui_dict[ head_cui ][ 'ro_exclude_list' ].append( this_cui )
            elif( include_ro_str.lower() == 'no' ):
                cui_dict[ head_cui ][ 'include_ro_flag' ] = False
            else:
                log.warning( 'Error:\t{}\n\t{}'.format( 'Unrecognized Include RO Flag' ,
                                                        include_ro_str ) )
    #######################################################################
    for head_cui in tqdm( cui_dict , desc = 'Extracting Terms' ,
                          file = sys.stdout ):
        log.debug( 'Head CUI:\t{}'.format( head_cui ) )
        if( 'preferred_term' not in concepts[ head_cui ] or
            concepts[ head_cui ][ 'preferred_term' ] == '' or
            'tui' not in concepts[ head_cui ] or
            concepts[ head_cui ][ 'tui' ] == '' ):
            preferred_term , semantic_type = get_concept_properties( head_cui )
            if( preferred_term is None or
                semantic_type is None ):
                next
            concepts[ head_cui ][ 'preferred_term' ] = preferred_term
            log.debug( '\tPT:\t{}'.format( preferred_term ) )
            concepts[ head_cui ][ 'tui' ] = semantic_type
            log.debug( '\tTUI:\t{}'.format( semantic_type ) )
        ##
        if( 'variant_terms' not in concepts[ head_cui ] or
            not bool( concepts[ head_cui ][ 'variant_terms' ] ) ):
            variant_terms = set()
            for term_pair in umls_lu.lookup_variants( head_cui , sources = 'MTH' ):
                variant_term , term_source = term_pair
                variant_terms.add( variant_term )
            log.debug( '\tVariant Terms:  {}'.format( variant_terms ) )
            concepts[ head_cui ][ 'variant_terms' ] = variant_terms
        ################################################################
        ## TODO - configuration file left to parse
        # if( cui_dict[ head_cui ][ 'include_parents_flag' ] == True ):
        #     if( cui_dict[ head_cui ][ 'parents_include_list' ] == [] ):
        #         parent_cuis = uu.get_rns( auth_client , 'current' , head_cui )
        #         for parent_cui in parent_cuis:
        #             cui_dict[ head_cui ][ 'parents_include_list' ].append( parent_cui )
        #     ##
        #     for parent_cui in tqdm( cui_dict[ head_cui ][ 'parents_include_list' ] , desc = 'Finding Parents' ,
        #                             leave = False ,
        #                             file = sys.stdout ):
        #         log.debug( '\tP:  {}'.format( parent_cui ) )
        #         concepts = flesh_out_concept( auth_client , concepts , parent_cui , head = head_cui )
        # log.debug( 'Done with parents' )
        # ##
        # if( cui_dict[ head_cui ][ 'include_ro_flag' ] == True ):
        #     ro_cuis = uu.get_ros( auth_client , 'current' , head_cui )
        #     for new_cui in ro_cuis:
        #         if( new_cui in cui_dict[ head_cui ][ 'ro_exclude_list' ] ):
        #             continue
        #         cui_dict[ head_cui ][ 'ro_include_list' ].append( new_cui )
        #     for ro_cui in tqdm( cui_dict[ head_cui ][ 'ro_include_list' ] , desc = 'Finding ROs' ,
        #                         leave = False ,
        #                         file = sys.stdout ):
        #         log.debug( '\tR:  {}'.format( ro_cui ) )
        #         concepts = flesh_out_concept( auth_client , concepts , ro_cui , head = head_cui )
        # log.debug( 'Done with ROs' )
        # ##
        # descendant_cuis = uu.get_all_umls_descendants( auth_client , head_cui ,
        #                                                concepts ,
        #                                                cui_dict[ head_cui ][ 'descendants_exclude_list' ] )
        # for descendant_cui in tqdm( descendant_cuis , desc = 'Finding Descendants' ,
        #                             leave = False ,
        #                             file = sys.stdout ):
        #     log.debug( '\tD:  {}'.format( descendant_cui ) )
        #     concepts = flesh_out_concept( auth_client , concepts , descendant_cui , head = head_cui )
        # log.debug( 'Done with descendants' )
        ################################################################
        from snomed import SNOMEDConcept
        for snomed_cui in tqdm( cui_dict[ head_cui ][ 'snomed_parent_list' ] ,
                                desc = 'Finding SNOMED Parents' ,
                                leave = False ,
                                file = sys.stdout ):
            log.debug( '\tR:  {}'.format( ro_cui ) )
            concepts = flesh_out_concept_via_py_umls( concepts , snomed_cui , head = head_cui )
        ################################################################
        ## TODO - configuration file left to parse
        # ##
        # for snomed_cui in tqdm( cui_dict[ head_cui ][ 'snomed_include_list' ] , desc = 'Finding SNOMED Concepts' ,
        #                         leave = False ,
        #                         file = sys.stdout ):
        #     descendant_cuis = uu.get_all_snomed_descendants( auth_client , snomed_cui ,
        #                                                      cui_dict[ head_cui ][ 'descendants_exclude_list' ] )
        #     for descendant_cui in descendant_cuis:
        #         log.debug( '\t\tD:  {}'.format( descendant_cui ) )
        #         concepts = flesh_out_concept( auth_client , concepts , descendant_cui , head = head_cui )
        # log.debug( 'Done with SNOMED' )
        ################################################################
        ##print( '{}\t{}'.format( cui , preferred_term ) )
    #concepts_to_concept_mapper( concepts , dict_output_filename )
    #concepts_to_csv( concepts , csv_output_filename )
    return( cui_dict , concepts )


def parse_focused_problems_tsv( input_filename ,
                                concepts = {} ):
    ##
    auth_client = uu.init_authentication( uu.UMLS_API_TOKEN )
    cui_dict = {}
    ##
    with open( input_filename , 'r' ) as in_fp:
        in_tsv = csv.DictReader( in_fp , dialect = 'excel-tab' )
        for cols in in_tsv:
            ## The first column can be named freely so we need to grab
            ## the contents based on position rather than using the
            ## dictionary key
            alt_name = next( iter( cols ) )
            if( len( alt_name ) == 0 ):
                continue
            ## UMLS concepts
            head_cui = cols[ 'CUI' ]
            include_umls_parents_str = cols[ 'Include parents (all RN)?' ]
            ## set later if not None
            parents_str = None ## cols[ 3 / 'Parents (or RO) to include (if some)' ]
            include_ro_str = cols[ 'Include RO?' ]
            ## set later if not none
            ro_str = None ## cols[ 5 / 'RO to exclude' ]
            ## SNOMED concepts 
            snomed_concepts_str = cols[ 'SNOMED-CT conceptsIDs' ]
            include_snomed_parents_str = cols[ 'Include parents (SNOMED ancestors)?' ]
            ancestors_str = cols[ 'Ancestors to include (if some)' ]
            descendants_exclude_str = cols[ 'Children to be excluded' ]
            ##
            log.debug( 'Old CUI:\t{}'.format( head_cui ) )
            cui_dict[ head_cui ] = {}
            concepts = seed_concept( concepts , cui = head_cui , head = None )
            cui_dict[ head_cui ][ 'include_parents_flag' ] = None
            cui_dict[ head_cui ][ 'parents_include_list' ] = []
            cui_dict[ head_cui ][ 'descendants_include_list' ] = []
            cui_dict[ head_cui ][ 'descendants_exclude_list' ] = []
            cui_dict[ head_cui ][ 'include_ro_flag' ] = None
            cui_dict[ head_cui ][ 'ro_include_list' ] = []
            cui_dict[ head_cui ][ 'ro_exclude_list' ] = []
            cui_dict[ head_cui ][ 'snomed_include_list' ] = []
            ## Child CUIs to Exclude
            if( descendants_exclude_str != '' ):
                for this_cui in descendants_exclude_str.split( ',' ):
                    this_cui = this_cui.lstrip( ' ' )
                    this_cui = this_cui.strip( '"' )
                    cui_dict[ head_cui ][ 'descendants_exclude_list' ].append( this_cui )
                    log.debug( '\tEx: {}'.format( this_cui ) )
            ## Include UMLS Parents (RN)
            ## Include UMLS RO (related other)
            ## Include SNOMED Concepts -> CUIs
            ## Include SNOMED Parents (ISA)
            if( include_umls_parents_str.lower() == 'no' or
                include_umls_parents_str.lower() == '' ):
                cui_dict[ head_cui ][ 'include_parents_flag' ] = False
            elif( include_umls_parents_str.lower() == 'yes' ):
                cui_dict[ head_cui ][ 'include_parents_flag' ] = True
            elif( include_umls_parents_str.lower() == 'some' ):
                cui_dict[ head_cui ][ 'include_parents_flag' ] = True
                parents_str = cols[ 'Parents (or RO) to include (if some)' ]
                for this_cui in parents_str.split( ',' ):
                    this_cui = this_cui.strip( )
                    this_cui = this_cui.strip( '"' )
                    cui_dict[ head_cui ][ 'parents_include_list' ].append( this_cui )
                    log.debug( '\tP:  {}'.format( this_cui ) )
            else:
                log.warning( 'Error:\t{}\n\t{}'.format( 'Unrecognized Include Parents Flag' ,
                                                        include_umls_parents_str ) )
            # ##
            if( include_ro_str.lower() == 'yes' ):
                cui_dict[ head_cui ][ 'include_ro_flag' ] = True
                ro_str = cols[ 'RO to exclude' ]
                if( ro_str != '' ):
                    for this_cui in ro_str.split( ',' ):
                        this_cui = this_cui.lstrip( ' ' )
                        this_cui = this_cui.strip( '"' )
                        cui_dict[ head_cui ][ 'ro_exclude_list' ].append( this_cui )
            elif( include_ro_str.lower() == 'no' or
                  include_ro_str.lower() == '' ):
                cui_dict[ head_cui ][ 'include_ro_flag' ] = False
            else:
                log.warning( 'Error:\t{}\n\t{}'.format( 'Unrecognized Include RO Flag' ,
                                                     include_ro_str ) )
            #####
            snomed_parent_cuis = set()
            cui_dict[ head_cui ][ 'snomed_parent_list' ] = []
            if( include_snomed_parents_str.lower() == 'no' ):
                cui_dict[ head_cui ][ 'include_snomed_parents_flag' ] = False
            elif( include_snomed_parents_str.lower() == 'some' ):
                cui_dict[ head_cui ][ 'include_snomed_parents_flag' ] = True
                for this_concept in ancestors_str.split( ',' ):
                    this_concept = this_concept.strip( )
                    this_concept = this_concept.strip( '"' )
                    this_parent_cui = uu.get_cui( auth_client , 'current' , this_concept , 'SNOMEDCT_US' )
                    if( this_parent_cui not in cui_dict[ head_cui ][ 'parents_include_list' ] ):
                        ## TODO - track snomed cid with this CUI for later dictionary entry
                        cui_dict[ head_cui ][ 'parents_include_list' ].append( this_parent_cui )
            elif( include_snomed_parents_str.lower() == 'yes' ):
                cui_dict[ head_cui ][ 'include_snomed_parents_flag' ] = True
                for this_concept in snomed_concepts_str.split( ',' ):
                    this_concept = this_concept.strip( )
                    this_concept = this_concept.strip( '"' )
                    log.debug( '\tSn: {}'.format( this_concept ) )
                    this_parent_cuis = uu.get_parents( auth_client , 'current' , head_cui , 'SNOMEDCT_US' ,
                                                       atoms = [ this_concept ] )
                    for this_parent_cui in this_parent_cuis:
                        if( this_parent_cui not in cui_dict[ head_cui ][ 'parents_include_list' ] ):
                            ## TODO - track snomed cid with this CUI for later dictionary entry
                            cui_dict[ head_cui ][ 'parents_include_list' ].append( this_parent_cui )
            else:
                log.warning( 'Error:\t{}:\t\'{}\''.format( 'Unrecognized Include SNOMED Parents Flag' ,
                                                      include_snomed_parents_str ) )
            ########################            
            ##
            if( snomed_concepts_str == 'None' or
                snomed_concepts_str is None ):
                continue
            for this_concept in snomed_concepts_str.split( ',' ):
                this_concept = this_concept.strip( )
                this_concept = this_concept.strip( '"' )
                log.debug( '\tSn: {}'.format( this_concept ) )
                cui_dict[ head_cui ][ 'snomed_include_list' ].append( this_concept )
    ##
    return( cui_dict , concepts )


def parse_problems( input_filename ,
                            concepts = {} ,
                            engine = 'api' ,
                    partials_dir = None ,
                    max_distance = -1 ):
    ## If no patials directory was provided, then initialized these
    ## datastructures as empty
    if( partials_dir is not None and
        os.path.exists( os.path.join( partials_dir , 'parsed_tsv.pkl' ) ) ):
        log.debug( 'Loading parsed_tsv.pkl' )
        with open( os.path.join( partials_dir , 'parsed_tsv.pkl' ) , 'rb' ) as fp:
            cui_dict , concepts = pickle.load( fp )
    else:
        cui_dict , concepts = parse_focused_problems_tsv( input_filename = input_filename ,
                                                          concepts = concepts )
        ## After we're done processing the tsv, we want to update our partial file
        ## with the latest datastructures (in pickle form)
        if( partials_dir is not None ):
            log.debug( '\tSaving partials file for parsed tsv' )
            with open( os.path.join( partials_dir , 'parsed_tsv.pkl' ) , 'wb' ) as fp:
                pickle.dump( [ cui_dict , concepts ] , fp )
    ##
    if( engine == 'api' and
        uu.UMLS_API_TOKEN is not None ):
        cui_dict , concepts = parse_problems_via_api( cui_dict ,
                                                              concepts ,
                                                      partials_dir = partials_dir ,
                                                      max_distance = max_distance )
    elif( engine == 'py-umls' and
          umls_lu is not None ):
        cui_dict , concepts = parse_focused_problems_via_py_umls( input_filename ,
                                                                  concepts ,
                                                                  partials_dir = partials_dir )
    return( cui_dict , concepts )


def parse_problems_via_api( cui_dict , concepts = {} , partials_dir = None , max_distance = -1 ):
    #######################################################################
    dict_keys = sorted( cui_dict.keys() )
    standalone_queue = []
    mth_queue = []
    snomed_queue = []
    for head_cui in tqdm( dict_keys , desc = 'Extracting Terms' ,
                          file = sys.stdout ):
        pickle_file = os.path.join( partials_dir , 'processed_{}.pkl'.format( head_cui ) )
        if( partials_dir is not None and
            os.path.exists( pickle_file ) ):
            log.debug( 'Pickle file already exists for CUI {}. Loading and continuing to next.'.format( head_cui ) )
            with open( pickle_file , 'rb' ) as fp:
                cui_dict , concepts = pickle.load( fp )
            continue
        auth_client = uu.init_authentication( uu.UMLS_API_TOKEN )
        if( 'preferred_term' not in concepts[ head_cui ] or
            concepts[ head_cui ][ 'preferred_term' ] == '' ):
            preferred_term = uu.get_cuis_preferred_atom( auth_client ,
                                                         'current' ,
                                                         head_cui )
            concepts[ head_cui ][ 'preferred_term' ] = preferred_term
        ##
        if( 'tui' not in concepts[ head_cui ] or
            concepts[ head_cui ][ 'tui' ] == '' ):
            ## TODO - make this function call less surprising
            ## TODO - check if multiple TUIs are possible
            tui = uu.get_cuis_atom( auth_client , 'current' ,
                                    head_cui , atom_type = '' )
            concepts[ head_cui ][ 'tui' ] = tui
        ##
        if( 'variant_terms' not in concepts[ head_cui ] or
            not bool( concepts[ head_cui ][ 'variant_terms' ] ) ):
            variant_terms = uu.get_cuis_eng_atom( auth_client ,
                                                  'current' ,
                                                  head_cui )
            log.debug( '\tVariant Terms:  {}'.format( variant_terms ) )
            concepts[ head_cui ][ 'variant_terms' ] = variant_terms
            ##
        if( cui_dict[ head_cui ][ 'include_parents_flag' ] == True ):
            if( cui_dict[ head_cui ][ 'parents_include_list' ] == [] ):
                parent_cuis = uu.get_rns( auth_client , 'current' , head_cui )
                for parent_cui in parent_cuis:
                    cui_dict[ head_cui ][ 'parents_include_list' ].append( parent_cui )
                    standalone_queue.append( parent_cui )
                    concepts = seed_concept( concepts , parent_cui , head_cui )
        log.debug( 'Done with parents' )
        ##
        if( cui_dict[ head_cui ][ 'include_ro_flag' ] == True ):
            ro_cuis = uu.get_ros( auth_client , 'current' , head_cui )
            for new_cui in ro_cuis:
                if( new_cui in cui_dict[ head_cui ][ 'ro_exclude_list' ] ):
                    continue
                cui_dict[ head_cui ][ 'ro_include_list' ].append( new_cui )
                standalone_queue.append( new_cui )
                concepts = seed_concept( concepts , new_cui , head_cui )
        log.debug( 'Done with ROs' )
        ##
        descendant_cuis = uu.get_rbs( auth_client , 'current' , head_cui )
        log.debug( 'Grabbed RBs. descendant cui n = {}'.format( len( descendant_cuis ) ) )
        exclude_list = cui_dict[ head_cui ][ 'descendants_exclude_list' ]
        for descendant_cui in descendant_cuis:
            if( descendant_cui in exclude_list or
                descendant_cui in concepts ):
                continue
            concepts = seed_concept( concepts , descendant_cui , head_cui )
            mth_queue.append( descendant_cui )
        log.debug( 'Done with descendants' )
        ##
        for snomed_cui in tqdm( cui_dict[ head_cui ][ 'snomed_parent_list' ] , desc = 'Finding SNOMED Parents' ,
                                leave = False ,
                                file = sys.stdout ):
            log.debug( '\tR:  {}'.format( ro_cui ) )
            standalone_queue.append( snomed_cui )
            concepts = seed_concept( concepts , snomed_cui , head_cui )
        ##
        for snomed_cui in tqdm( cui_dict[ head_cui ][ 'snomed_include_list' ] , desc = 'Finding SNOMED Concepts' ,
                                leave = False ,
                                file = sys.stdout ):
            ## TODO NEXT - walk SNOMED in parallel to MTH
            descendant_concept_ids = uu.get_family_tree( auth_client , 'current' ,
                                                         snomed_cui ,
                                                         relation_type = 'children' )
            for descendant_concept_id in descendant_concept_ids:
                descendant_cui = uu.get_cui( auth_client , 'current' ,
                                             descendant_concept_id , 'SNOMEDCT_US' )
                if( descendant_cui in exclude_list or
                    descendant_cui in concepts ):
                    continue
                concepts = seed_concept( concepts , descendant_cui , head_cui )
                mth_queue.append( descendant_cui )
        log.debug( 'Done with SNOMED' )
        ## At the end of every loop, we want to update our partial file
        ## with the latest datastructures (in pickle form)
        if( partials_dir is not None ):
            with open( os.path.join( partials_dir , 'processed_{}.pkl'.format( head_cui ) ) , 'wb' ) as fp:
                pickle.dump( [ cui_dict , concepts ] , fp )
    ##
    with open( '/tmp/cui_dict_gen000.json' , 'w' ) as fp:
        fp.write( '{}'.format( cui_dict ) )
    with open( '/tmp/concepts_gen000.json' , 'w' ) as fp:
        fp.write( '{}'.format( concepts ) )
    concepts = parse_problems_queue( auth_client ,
                                     cui_dict ,
                                     concepts,
                                     partials_dir ,
                                     standalone_queue ,
                                     snomed_queue ,
                                     distance = 1 ,
                                     max_distance = max_distance )
    concepts = parse_problems_queue( auth_client ,
                                     cui_dict ,
                                     concepts,
                                     partials_dir ,
                                     mth_queue ,
                                     snomed_queue ,
                                     distance = 1 ,
                                     max_distance = max_distance )
    with open( '/tmp/cui_dict_genXYZ.json' , 'w' ) as fp:
        fp.write( '{}'.format( cui_dict ) )
    with open( '/tmp/concepts_genXYZ.json' , 'w' ) as fp:
        fp.write( '{}'.format( concepts ) )
    return( cui_dict , concepts )


def parse_problems_queue( auth_client ,
                          cui_dict ,
                          concepts,
                          partials_dir ,
                          mth_queue ,
                          snomed_queue ,
                          distance = 1 ,
                          max_distance = -1 ):
    next_mth_queue = []
    next_snomed_queue = []
    for parent_cui in tqdm( sorted( mth_queue ) ,
                            desc = 'Filling out concepts at distance of {} from seeds'.format( distance ) ,
                            leave = True ,
                            file = sys.stdout ):
        concepts = flesh_out_seed_concept( auth_client , concepts , parent_cui )
        if( max_distance == -1 or
            distance < max_distance ):
            ## get descendants and add to queue
            descendant_cuis = uu.get_rbs( auth_client , 'current' , parent_cui )
            log.debug( 'Grabbed RBs. descendant cui n = {}'.format( len( descendant_cuis ) ) )
            head_cui = concepts[ parent_cui ][ 'head_cui' ]
            exclude_list = cui_dict[ head_cui ][ 'descendants_exclude_list' ]
            for descendant_cui in descendant_cuis:
                if( descendant_cui in exclude_list or
                    descendant_cui in concepts ):
                    continue
                concepts = seed_concept( concepts , descendant_cui , head_cui )
                next_mth_queue.append( descendant_cui )
        if( partials_dir is not None ):
            with open( os.path.join( partials_dir ,
                                     'processed_{}.pkl'.format( parent_cui ) ) ,
                       'wb' ) as fp:
                pickle.dump( [ cui_dict , concepts ] , fp )
    with open( '/tmp/concepts_gen{:03d}.json'.format( distance ) , 'w' ) as fp:
        fp.write( '{}'.format( concepts ) )
    ## If either queue has some work left to do, then go another level
    ## deeper.
    if( len( next_mth_queue ) > 0 or
        len( next_snomed_queue ) > 0 ):
        concepts = parse_problems_queue( auth_client ,
                                         cui_dict ,
                                         concepts,
                                         partials_dir ,
                                         next_mth_queue ,
                                         next_snomed_queue ,
                                         distance = distance + 1 ,
                                         max_distance = max_distance )
    return( concepts )

if __name__ == "__main__":
    input_filename = '/tmp/Book3.txt'
    cui_dict , concepts = parse_focused_problems( input_filename , concepts = {} )
    root = cm.create_concept_mapper_template()
    for cui in sorted( cui_dict ):
        preferred_term = concepts[ cui ][ 'preferred_term' ]
        tui = concepts[ cui ][ 'tui' ]
        for term in concepts[ cui ][ 'variant_terms' ]:
            print( '{}\t{}\t{}\t{}'.format( cui ,
                                            term ,
                                            preferred_term ,
                                            tui ) )
        ##print( '{}\t{}\t{}\t{}'.format( cui ,
        ##                                'HEAD' ,
        ##                                preferred_term ,
        ##                                tui ) )
        for related_cui in sorted( concepts[ cui ][ 'related_cuis' ] ):
            preferred_term = concepts[ related_cui ][ 'preferred_term' ]
            tui = concepts[ related_cui ][ 'tui' ]
            for term in concepts[ related_cui ][ 'variant_terms' ]:
                print( '{}\t{}\t{}\t{}'.format( cui ,
                                                term ,
                                                preferred_term ,
                                                tui ) )
            ##print( '{}\t{}\t{}\t{}'.format( related_cui ,
            ##                                '' ,
            ##                                preferred_term ,
            ##                                tui ) )
