import logging as log

import os
import sys

import csv

try:
    from lxml import etree
    log.debug("running with lxml.etree")
except ImportError:
    try:
        # Python 2.5
        import xml.etree.cElementTree as etree
        log.debug("running with cElementTree on Python 2.5+")
    except ImportError:
        try:
            # Python 2.5
            import xml.etree.ElementTree as etree
            log.debug("running with ElementTree on Python 2.5+")
        except ImportError:
            try:
                # normal cElementTree install
                import cElementTree as etree
                log.debug("running with cElementTree")
            except ImportError:
                try:
                    # normal ElementTree install
                    import elementtree.ElementTree as etree
                    log.debug("running with ElementTree")
                except ImportError:
                    log.warn("Failed to import ElementTree from any known place")


import concept_mapper_utils as cm
import snomed_utils as snomed_u
import spreadsheet_utils as csv_u
import umls_utils as uu


def concepts_to_concept_mapper( concepts , concept_mapper_filename , cui_list = None ):
    root = cm.create_concept_mapper_template()
    if( cui_list is None ):
        cui_list = sorted( concepts )
    for cui in cui_list:
        token = etree.Element( "token" )
        ##
        variant_terms = concepts[ cui ][ 'variant_terms' ]
        if( 'preferred_term' in concepts[ cui ] ):
            preferred_term = concepts[ cui ][ 'preferred_term' ]
        else:
            preferred_term = ''
            if( len( variant_terms ) > 0 ):
                preferred_term = variant_terms[ 0 ]
            else:
                continue
        if( 'tui' in concepts[ cui ] ):
            tui = concepts[ cui ][ 'tui' ]
            token.set( 'umlsTui' , tui )
        else:
            tui = ''
        token.set( 'canonical' , preferred_term )
        token.set( 'umlsCui' , cui )
        all_fsns = set()
        if( 'head_cui' in concepts[ cui ] ):
            token.set( 'headCui' ,  concepts[ cui ][ 'head_cui' ] )            
        ## TODO - this is a simple hack so we don't have to do
        ##        a check for SNOMEDCT entries in the next
        ##        for loop.
        if( 'SNOMEDCT' not in concepts[ cui ] ):
            concepts[ cui ][ 'SNOMEDCT' ] = []
        for cid in sorted( concepts[ cui ][ 'SNOMEDCT' ] ):
            ###
            variant = etree.Element( 'variant' )
            fully_specified_name = concepts[ cui ][ 'SNOMEDCT' ][ cid ][ 'FSN' ]
            all_fsns.add( fully_specified_name )
            variant.set( 'base' , fully_specified_name )
            variant.set( 'fsn' , fully_specified_name )
            variant.set( 'snomedCid' , cid )
            ## Set the base concepts preferred name to the first
            ## FSN we run across if it hasn't already been set.
            if( 'canonical' not in token.keys() ):
                token.set( 'canonical' , fully_specified_name )
            token.append( variant )
        for term in sorted( variant_terms ):
            if( term in all_fsns ):
                ## Skip over any terms that were already added as a SNOMED concepet
                continue
            variant = etree.Element( 'variant' )
            variant.set( 'base' , term )
            token.append( variant )
            ## Set the base concepts preferred name to the first
            ## FSN we run across if it hasn't already been set.
            if( 'canonical' not in token.keys() ):
                token.set( 'canonical' , term )
        ##
        root.append( token )
    new_tree = etree.ElementTree( root )
    new_tree.write( concept_mapper_filename ,
                    xml_declaration = True ,
                    encoding = 'UTF-8' ,
                    pretty_print = True )

def concepts_to_binary_csv( concepts , csv_filename ,
                            exclude_terms_flag = True ,
                            symmetric_flag = False ,
                            cui_list = None ,
                            append_to_csv = False ):
    if( not append_to_csv ):
        open( csv_filename , 'w' ).close()
    if( cui_list is None ):
        cui_list = sorted( concepts )
    for cui in cui_list:
        if( 'head_cui' in concepts[ cui ] ):
            headCui = concepts[ cui ][ 'head_cui' ]
            with open( csv_filename , 'a' ) as fp:
                fp.write( '{}\t{}\n'.format( headCui , cui ) )
                if( symmetric_flag ):
                    fp.write( '{}\t{}\n'.format( cui , headCui ) )
        elif( exclude_terms_flag ):
            ## No head_cui means that this *is* a head_cui
            ## and so we won't find any interesting cuis
            ## associated with it. Since we aren't
            ## writing out any terms for the cui, there
            ## is nothing to do.
            continue
        else:
            headCui = cui
        if( exclude_terms_flag ):
            continue
        if( 'preferred_term' in concepts[ cui ] ):
            preferred_term = concepts[ cui ][ 'preferred_term' ]
            with open( csv_filename , 'a' ) as fp:
                fp.write( '{}\t{}\n'.format( headCui , preferred_term ) )
                if( symmetric_flag ):
                    fp.write( '{}\t{}\n'.format( preferred_term , headCui ) )
        else:
            preferred_term = None
        for term in sorted( concepts[ cui ][ 'variant_terms' ] ):
            if( term == preferred_term ):
                continue
            with open( csv_filename , 'a' ) as fp:
                fp.write( '{}\t{}\n'.format( headCui , term ) )
                if( symmetric_flag ):
                    fp.write( '{}\t{}\n'.format( term , headCui ) )


def concepts_to_csv( concepts , csv_filename , cui_list = None , append_to_csv = False ):
    if( not append_to_csv ):
        open( csv_filename , 'w' ).close()
    if( cui_list is None ):
        cui_list = sorted( concepts )
    for cui in cui_list:
        if( 'preferred_term' in concepts[ cui ] ):
            preferred_term = concepts[ cui ][ 'preferred_term' ]
        else:
            preferred_term = ''
        if( 'tui' in concepts[ cui ] ):
            tui = concepts[ cui ][ 'tui' ]
        else:
            tui = ''
        for term in sorted( concepts[ cui ][ 'variant_terms' ] ):
            with open( csv_filename , 'a' ) as fp:
                fp.write( '{}\t{}\t{}\t{}\n'.format( cui ,
                                                     term ,
                                                     preferred_term ,
                                                     tui ) )

def concepts_from_csv( csv_filename ):
    concepts = {}
    with open( csv_filename , 'r' ) as in_fp:
        in_tsv = csv.reader( in_fp , dialect=csv.excel_tab )
        for cols in in_tsv:
            cui = cols[ 0 ]
            term = cols[ 1 ]
            preferred_term = cols[ 2 ]
            tui = cols[ 3 ]
            if( cui not in concepts ):
                concepts[ cui ] = {}
                concepts[ cui ][ 'preferred_term' ] = preferred_term
                concepts[ cui ][ 'tui' ] = tui
                concepts[ cui ][ 'variant_terms' ] = set()
            ##
            concepts[ cui ][ 'variant_terms' ].add( term )
    return( concepts )


if __name__ == "__main__":
    ## TODO - make these configurable via command line
    input_dir = 'in'
    partials_dir = 'partials'
    output_dir = 'out'
    # TODO - add real argparser
    focus_type = sys.argv[ 1 ] ## focusedAllergen || focusedProblem
    set_num = sys.argv[ 2 ] ## batch1 , batch2, etc.
    focused_input_filename = sys.argv[ 3 ] ## Allergen_mappings.csv'
    log.basicConfig()
    formatter = log.Formatter( '%(asctime)s %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s' )
    ## TODO - make the date format easier to read
    #datefmt = '%Y-%m-%d %H:%M:%S'
    log.getLogger().setLevel( log.DEBUG )
    log.getLogger().handlers[0].setFormatter( formatter )
    log.debug( "Verbose output." )
    ## Turn logging for url lib to a higher level than default
    log.getLogger( 'urllib3.connectionpool' ).setLevel( log.INFO )
    ## Make sure inputs are all available
    if( not os.path.exists( input_dir ) ):
        log.error( 'The input directory does not exist:  {}'.format( input_dir ) )
        exit( 1 )
    if( not os.path.exists( focused_input_filename ) ):
        log.error( 'The input file does not exist:  {}'.format( focused_input_filename ) )
        exit( 1 )
    ## Make sure we can access the output directory
    if( not os.path.exists( output_dir ) ):
        log.warning( 'Creating output folder:  {}'.format( output_dir ) )
        try:
            os.makedirs( output_dir )
        except OSError as e:
            log.error( 'OSError caught while trying to create output folder:  {}'.format( e ) )
        except IOError as e:
            log.error( 'IOError caught while trying to create output folder:  {}'.format( e ) )
    ## Compose full output filenames
    dict_output_filename = os.path.join( output_dir ,
                                         'conceptMapper_{}_{}.dict'.format( focus_type ,
                                                                            set_num ) )
    binary_csv_output_filename = os.path.join( output_dir ,
                                               'binarydict_{}_{}.csv'.format( focus_type ,
                                                                              set_num ) )
    csv_output_filename = os.path.join( output_dir ,
                                        '4waydict_{}_{}.csv'.format( focus_type ,
                                                                     set_num ) )
    wide_csv_output_filename = os.path.join( output_dir ,
                                             'widedict_{}_{}.csv'.format( focus_type ,
                                                                          set_num ) )
    ##
    log.info( 'CSV In:\t{}'.format( focused_input_filename ) )
    log.info( 'ConceptMapper Out:\t{}'.format( dict_output_filename ) )
    log.info( 'CSV Outs:\n\t{}\n\t{}\n\t{}'.format( binary_csv_output_filename ,
                                                    csv_output_filename ,
                                                    wide_csv_output_filename ) )
    if( partials_dir is not None and
        not os.path.exists( partials_dir ) ):
        log.debug( 'Partials output directory does not exist.  Creating now:  {}'.format( partials_dir ) )
        os.makedirs( partials_dir )
    ##
    if( focus_type == 'focusedAllergen' ):
        concepts = csv_u.parse_focused_allergens( focused_input_filename ,
                                                  partials_dir = partials_dir )
    elif( focus_type == 'focusedProblem' ):
        ## TODO - write explanation for file contents.
        ## TODO - create function to generate a new version of this file
        csv_input_filename = os.path.join( input_dir , '4colTsv_focused_problems_v2.csv' )
        if( os.path.exists( csv_input_filename ) ):
            csv_concepts = concepts_from_csv( csv_input_filename )
        else:
            csv_concepts = {}
        cui_dict , concepts = csv_u.parse_focused_problems( focused_input_filename ,
                                                            concepts = csv_concepts ,
                                                            partials_dir = partials_dir )
    concepts_to_concept_mapper( concepts , dict_output_filename )
    concepts_to_binary_csv( concepts , binary_csv_output_filename )
    concepts_to_4col_csv( concepts , csv_output_filename )
    #concepts_to_wide_csv( concepts , wide_csv_output_filename )
