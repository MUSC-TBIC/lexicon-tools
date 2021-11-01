import logging as log

import os
import sys

import argparse

import csv

from tqdm import tqdm

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

def initialize_arg_parser():
    parser = argparse.ArgumentParser( description = """
    """ )
    parser.add_argument( '-v' , '--verbose' ,
                         help = "print more information" ,
                         action = "store_true" )
    
    parser.add_argument( '--input-file' , required = True ,
                         dest = 'inputFile' ,
                         help = 'A csv file specifying concepts to extract' )

    parser.add_argument( '--batch-name' , required = True ,
                         dest = 'batchName' ,
                         help = 'Batch name or ID used to identify different runs of the same configuration files (e.g., batch001, batch123, testBatch)' )
    
    parser.add_argument( '--output-dir' , default = 'out' ,
                         dest = 'outputDir' ,
                         help = 'Output directory for writing dictionaries' )
    ##
    return parser


def init_args( command_line_args ):
    ##
    parser = initialize_arg_parser()
    args = parser.parse_args( command_line_args )
    ##
    bad_args_flag = False
    ## Make sure inputs are all available
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
    ##
    if( bad_args_flag ):
        log.error( "I'm bailing out of this run because of errors mentioned above." )
        exit( 1 )
    ##
    return args


if __name__ == "__main__":
    ##
    log.basicConfig()
    formatter = log.Formatter( '%(asctime)s %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s' )
    ## TODO - make the date format easier to read
    #datefmt = '%Y-%m-%d %H:%M:%S'
    log.getLogger().setLevel( log.DEBUG )
    log.getLogger().handlers[0].setFormatter( formatter )
    log.debug( "Verbose output." )
    ##
    args = init_args( sys.argv[ 1: ] )
    ##
    dict_output_filename = os.path.join( args.outputDir ,
                                         'conceptMapper_{}.xml'.format( args.batchName ) )
    log.info( 'ConceptMapper Out:\t{}'.format( dict_output_filename ) )
    ##
    root = etree.Element( "synonym" )
    with open( args.inputFile , 'r' ) as in_fp:
        in_tsv = csv.DictReader( in_fp , dialect = 'excel' )
        variant_string_col = 'Symptom variants'
        key_col = "Sign and Symptom"
        cui_col = "UMLS CUI"
        variants_col = "Synonym"
        for cols in tqdm( in_tsv ,
                          desc = 'Reading in initial concept specs' ,
                          leave = True ,
                          file = sys.stdout ):
            try:
                preferred_term = cols[ key_col ]
            except KeyError as e:
                ## Note the typo has not yet been fixed in the upstream
                ## datasource: SIgn vs. Sign
                key_col = "SIgn and Symptom"
                preferred_term = cols[ key_col ]
            if( preferred_term == '' ):
                continue
            cui = cols[ cui_col ]
            if( cui == '' ):
                cui = 'C0000000'
            variants = []
            if( len( cols ) > 2 ):
                if( variants_col is None ):
                    1
                else:
                    variants = cols[ variants_col ].split( ',' )
            ###
            token = etree.Element( "token" )
            token.set( 'canonical' , preferred_term )
            token.set( 'conceptType' , 'CUI' )
            token.set( 'conceptCode' , cui )
            variant = etree.Element( 'variant' )
            variant.set( 'base' , preferred_term )
            token.append( variant )
            for variant_term in variants:
               variant = etree.Element( 'variant' )
               variant_term = variant_term.strip()
               variant.set( 'base' , variant_term )
               token.append( variant )
            ##
            root.append( token )
            ####
    new_tree = etree.ElementTree( root )
    new_tree.write( dict_output_filename ,
                    xml_declaration = True ,
                    encoding = 'UTF-8' ,
                    pretty_print = True )
