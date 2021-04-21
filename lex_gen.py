import logging as log

import os
import sys

import argparse

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

#############################################
## 
#############################################

def initialize_arg_parser():
    parser = argparse.ArgumentParser( description = """
    """ )
    parser.add_argument( '-v' , '--verbose' ,
                         help = "print more information" ,
                         action = "store_true" )
    
    parser.add_argument( '--input-dir' , default = 'in' ,
                         dest = 'inputDir' ,
                         help = 'Input directory containing supplementary files' )
     
    parser.add_argument( '--input-file' , required = True ,
                         dest = 'inputFile' ,
                         help = 'A pkl file if sourceType is \'pickle\' or an csv file specifying concepts to extract for all other sourceTypes' )
     
    parser.add_argument( '--source-type' , required = True ,
                         dest = 'sourceType' ,
                         choices = [ 'problems' , 'medications' , 'pickle' ] ,
                         help = 'The concept type to focus extraction on. \'pickle\' loads concepts from the partial pickle files' )

    parser.add_argument( '--batch-name' , required = True ,
                         dest = 'batchName' ,
                         help = 'Batch name or ID used to identify different runs of the same configuration files (e.g., batch001, batch123, testBatch)' )

    parser.add_argument( '--partials-dir' , default = 'partials' ,
                         dest = 'partialsDir' ,
                         help = 'Directory used for writing partial and intermediary files' )

    parser.add_argument( '--output-dir' , default = 'out' ,
                         dest = 'outputDir' ,
                         help = 'Output directory for writing file lexicons, dictionary, ontologies, and term lists' )
    
    ##
    return parser

def init_args( command_line_args ):
    ##
    parser = initialize_arg_parser()
    args = parser.parse_args( command_line_args )
    ##
    bad_args_flag = False
    ## Make sure inputs are all available
    if( not os.path.exists( args.inputDir ) ):
        log.error( 'The input directory does not exist:  {}'.format( args.inputDir ) )
        bad_args_flag = True
    if( not os.path.exists( args.inputFile ) ):
        log.error( 'The input file does not exist:  {}'.format( args.inputFile ) )
        bad_args_flag = True
    ## Make sure we can access the output directory
    if( not os.path.exists( args.outputDir ) ):
        log.warning( 'Creating output folder:  {}'.format( args.outputDir ) )
        try:
            os.makedirs( args.outputDir )
        except OSError as e:
            bad_args_flag = True
            log.error( 'OSError caught while trying to create output folder:  {}'.format( e ) )
        except IOError as e:
            bad_args_flag = True
            log.error( 'IOError caught while trying to create output folder:  {}'.format( e ) )
    if( args.partialsDir is not None and
        not os.path.exists( args.partialsDir ) ):
        log.debug( 'Partials output directory does not exist.  Creating now:  {}'.format( args.partialsDir ) )
        try:
            os.makedirs( args.partialsDir )
        except OSError as e:
            bad_args_flag = True
            log.error( 'OSError caught while trying to create partials folder:  {}'.format( e ) )
        except IOError as e:
            bad_args_flag = True
            log.error( 'IOError caught while trying to create partials folder:  {}'.format( e ) )
    ##
    if( bad_args_flag ):
        log.error( "I'm bailing out of this run because of errors mentioned above." )
        exit( 1 )
    ##
    return args

#############################################
## 
#############################################

def concepts_to_concept_mapper( concepts , concept_mapper_filename , cui_list = None ):
    """
    Convert the `concepts` data structure to ConceptMapper output
    """
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



def concepts_to_ttl_kb_mapper( concepts ,
                               ttl_output_filename ,
                               prefix_file ,
                               cui_list = None ):
    """
    Convert the `concepts` data structure to a TTL knowledgebase
    """
    node_map = { 'kbRoot' : 'http://www.ukp.informatik.tu-darmstadt.de/inception/1.0' ,
                 'semtypeRoot' : 'https://uts.nlm.nih.gov/uts/umls/semantic-network/' , ##T059
                 'utsRoot' : 'https://uts.nlm.nih.gov/uts/umls/concept/' ,
                 'rxNormRoot' : 'https://mor.nlm.nih.gov/RxNav/search?searchBy=RXCUI&searchTerm=' ,
                 'CUI' : 'nodex1' ,
                 'SemType' : 'nodex2' ,
                 'RXCUI' : 'nodex3' }
    ##########################
    if( prefix_file is not None ):
        with open( prefix_file , 'r' ) as in_fp:
            with open( ttl_output_filename , 'w' ) as out_fp:
                for line in in_fp:
                    line = line.rstrip()
                    out_fp.write( '{}\n'.format( line ) )
    if( cui_list is None ):
        cui_list = sorted( concepts )
    for cui in cui_list:
        this_node = '{}{}'.format( node_map[ 'utsRoot' ] , cui )
        node_map[ cui ] = this_node
        ## Grab the TUI and set it as the parent unless we get a
        ## better option later
        if( 'tui' in concepts[ cui ] ):
            tui = concepts[ cui ][ 'tui' ]
            parent_node = '{}{}'.format( node_map[ 'semtypeRoot' ] , tui )
            if( tui not in node_map ):
                node_map[ tui ] = parent_node
                with open( ttl_output_filename , 'a' ) as out_fp:
                    out_fp.write( '<{}> a :Class;\n'.format( parent_node ) )
                    ## TODO - switch this to a pretty SemType name
                    out_fp.write( '  :label "{}"@en;\n\n'.format( tui ) )
        else:
            tui = ''
            parent_node = ''
        ## The head CUI is a better parent than the TUI
        if( 'head_cui' in concepts[ cui ] ):
            head_cui = concepts[ cui ][ 'head_cui' ]
            parent_node = '{}/{}'.format( node_map[ 'utsRoot' ] , head_cui )
        ##
        variant_terms = sorted( list( concepts[ cui ][ 'variant_terms' ] ) )
        ## If the preferred term isn't in the variants list, then make
        ## sure to prepend it to the variants list
        if( 'preferred_term' in concepts[ cui ] ):
            preferred_term = concepts[ cui ][ 'preferred_term' ]
            if( preferred_term not in variant_terms ):
                variant_terms.insert( 0 , preferred_term )
        else:
            ## If we don't have a preferred term _or_ any variants,
            ## then this is a bum entry
            ## TODO - more error reporting
            if( len( variant_terms ) <= 0 ):
                continue
        ## TODO - this is a simple hack so we don't have to do
        ##        a check for SNOMEDCT entries in the next
        ##        for loop.
        if( 'SNOMEDCT' not in concepts[ cui ] ):
            concepts[ cui ][ 'SNOMEDCT' ] = []
        for cid in sorted( concepts[ cui ][ 'SNOMEDCT' ] ):
            ###
            fully_specified_name = concepts[ cui ][ 'SNOMEDCT' ][ cid ][ 'FSN' ]
            if( fully_specified_name not in variant_terms ):
                variant_terms.append( fully_specified_name )
            #variant.set( 'snomedCid' , cid )
        with open( ttl_output_filename , 'a' ) as out_fp:
            out_fp.write( '<{}> a :Class;\n'.format( this_node ) )
            out_fp.write( '  <{}#{}> "{}";\n'.format( node_map[ 'kbRoot' ] ,
                                                      node_map[ 'CUI' ] ,
                                                      cui ) )
            for variant in variant_terms:
                out_fp.write( '  :label "{}"@en;\n'.format( variant ) )
            out_fp.write( '  :subClassOf <{}> .\n\n'.format( parent_node ) )
        ##
    

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


def concepts_to_4col_csv( concepts , csv_filename , cui_list = None , append_to_csv = False ):
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


def concepts_to_wide_csv( concepts , csv_filename ,
                          exclude_terms_flag = True ,
                          cui_list = None ,
                          append_to_csv = False ):
    if( not append_to_csv ):
        open( csv_filename , 'w' ).close()
    if( cui_list is None ):
        cui_list = sorted( concepts )
    wide_list = {}
    for cui in cui_list:
        if( 'head_cui' in concepts[ cui ] ):
            headCui = concepts[ cui ][ 'head_cui' ]
            if( headCui not in wide_list ):
                wide_list[ headCui ] = set()
            wide_list[ headCui ].add( cui )
        else:
            if( cui not in wide_list ):
                wide_list[ cui ] = set()
            if( exclude_terms_flag ):
                ## No head_cui means that this *is* a head_cui
                ## and so we won't find any interesting cuis
                ## associated with it. Since we aren't
                ## writing out any terms for the cui, there
                ## is nothing to do after we make sure it
                ## is in the wide_list for printing.
                if( cui not in wide_list ):
                    wide_list[ cui ] = set()
                continue
            headCui = cui
        if( exclude_terms_flag ):
            continue
        if( 'preferred_term' in concepts[ cui ] ):
            preferred_term = concepts[ cui ][ 'preferred_term' ]
            wide_list[ headCui ].add( preferred_term )
        for term in sorted( concepts[ cui ][ 'variant_terms' ] ):
            wide_list[ headCui ].add( term )
    for head_cui in wide_list:
        if( head_cui is None ):
            continue
        with open( csv_filename , 'a' ) as fp:
            fp.write( '{}'.format( head_cui ) )
            for related_cui_or_term in wide_list[ head_cui ]:
                fp.write( '\t{}'.format( related_cui_or_term ) )
            fp.write( '\n' )


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

#############################################
## 
#############################################

if __name__ == "__main__":
    ##
    log.basicConfig()
    formatter = log.Formatter( '%(asctime)s %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s' )
    ## TODO - make the date format easier to read
    #datefmt = '%Y-%m-%d %H:%M:%S'
    log.getLogger().setLevel( log.DEBUG )
    log.getLogger().handlers[0].setFormatter( formatter )
    log.debug( "Verbose output." )
    ## Turn logging for url lib to a higher level than default
    log.getLogger( 'urllib3.connectionpool' ).setLevel( log.INFO )
    ##
    args = init_args( sys.argv[ 1: ] )
    ## Compose full output filenames
    dict_output_filename = os.path.join( args.outputDir ,
                                         'conceptMapper_{}_{}.dict'.format( args.sourceType ,
                                                                            args.batchName ) )
    ttl_output_filename = os.path.join( args.outputDir ,
                                        'kb_{}_{}.ttl'.format( args.sourceType ,
                                                               args.batchName ) )
    binary_csv_output_filename = os.path.join( args.outputDir ,
                                               'binarydict_{}_{}.csv'.format( args.sourceType ,
                                                                              args.batchName ) )
    csv_output_filename = os.path.join( args.outputDir ,
                                        '4waydict_{}_{}.csv'.format( args.sourceType ,
                                                                     args.batchName ) )
    wide_csv_output_filename = os.path.join( args.outputDir ,
                                             'widedict_{}_{}.csv'.format( args.sourceType ,
                                                                          args.batchName ) )
    ##
    log.info( 'CSV In:\t{}'.format( args.inputFile ) )
    log.info( 'ConceptMapper Out:\t{}'.format( dict_output_filename ) )
    log.info( 'TTL Knowledgebase Out:\t{}'.format( ttl_output_filename ) )
    log.info( 'CSV Outs:\n\t{}\n\t{}\n\t{}'.format( binary_csv_output_filename ,
                                                    csv_output_filename ,
                                                    wide_csv_output_filename ) )
    ##
    if( args.sourceType == 'medications' ):
        concepts = csv_u.parse_focused_allergens( args.inputFile ,
                                                  partials_dir = args.partialsDir )
    elif( args.sourceType == 'problems' ):
        ## TODO - write explanation for file contents.
        ## TODO - create function to generate a new version of this file
        csv_input_filename = os.path.join( args.inputDir , '4colTsv_focused_problems_v2.csv' )
        if( os.path.exists( csv_input_filename ) ):
            csv_concepts = concepts_from_csv( csv_input_filename )
        else:
            csv_concepts = {}
        #cui_dict , concepts = csv_u.parse_focused_problems( args.inputFile ,
        #                                                    concepts = csv_concepts ,
        #                                                    partials_dir = args.partialsDir )
        cui_dict , concepts = csv_u.parse_problems( args.inputFile ,
                                                            concepts = csv_concepts ,
                                                    partials_dir = args.partialsDir )
    elif( args.sourceType == 'pickle' ):
        with open( args.inputFile , 'rb' ) as fp:
            cui_dict , concepts = pickle.load( fp )
    ##
    concepts_to_concept_mapper( concepts , dict_output_filename )
    concepts_to_ttl_kb_mapper( concepts , ttl_output_filename ,
                               prefix_file = 'kb_meta/problem_prefix.ttl' )
    concepts_to_binary_csv( concepts , binary_csv_output_filename ,
                            exclude_terms_flag = False )
    concepts_to_4col_csv( concepts , csv_output_filename )
    concepts_to_wide_csv( concepts , wide_csv_output_filename ,
                          exclude_terms_flag = False )
