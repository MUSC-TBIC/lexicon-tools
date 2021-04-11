import logging as log

import os
import sys
import re

import argparse

from tqdm import tqdm

import csv

#############################################
## 
#############################################

mrconso_headers = { 'CUI' : 1 ,
                    'LAT' : 2 ,
                    'TS' : 3 ,
                    'STT' : 5 ,
                    'ISPREF' : 7 ,
                    'SAB' : 12 ,
                    'TTY' : 13 ,
                    'STR' : 15 ,
                    'SUPPRESS' : 17 }
mrsty_headers = { 'CUI' : 1 ,
                  'TUI' : 2 ,
                  'STN' : 3 ,
                  'STY' : 4 ,
                  'ATUI' : 5 ,
                  'CVF' : 6 }

rxnorm_headers = { 'RXCUI' : 1 ,
                   'RXAUI' : 8 ,
                   'SAB' : 12 ,
                   'TTY' : 13 ,
                   'CODE' : 14 ,
                   'STRING' : 15 ,
                   'SUPPRESS' : 17 }
rxrel_headers = { 'RXCUI1' : 1 ,
                  'RXAUI1' : 2 ,
                  'STYPE1' : 3 ,
                  'REL' : 4 ,
                  'RXCUI2' : 5 ,
                  'RXAUI2' : 6 ,
                  'STYPE2' : 7 ,
                  'RELA' : 8 }


node_map = { 'kbRoot' : 'http://www.ukp.informatik.tu-darmstadt.de/inception/1.0' ,
             'utsRoot' : 'https://uts.nlm.nih.gov/uts/umls/concept/' ,
             'rxNormRoot' : 'https://mor.nlm.nih.gov/RxNav/search?searchBy=RXCUI&searchTerm=' ,
             'CUI' : 'node1eoocu2ncx1' ,
             'Disease' : 'node1eoocu2ncx2' ,
             'Sign or Symptom' : 'node1eoocu2ncx3' ,
             'SemType' : 'node1eoocu3ncx2' ,
             'RXCUI' : 'node1eoocu2ncx1' ,
             'ATC ID' : 'node1eoocu2ncx2' }

#############################################
## 
#############################################

def initialize_arg_parser():
    parser = argparse.ArgumentParser( description = """
    """ )
    parser.add_argument( '-v' , '--verbose' ,
                         help = "print more information" ,
                         action = "store_true" )
    
    parser.add_argument( '--input-file' , default = None ,
                         dest = 'inputFile' ,
                         help = 'Input file to read the knowledgebase concepts from (used with csv format)' )
     
    parser.add_argument( '--input-dir' , default = None ,
                         dest = 'inputDir' ,
                         help = 'Input directory containing necessary .RRF files to read the knowledgebase concepts from (used with RxNorm and MRCONSO formats)' )
     
    parser.add_argument( '--input-format' , default = 'csv' ,
                         choices = [ 'csv' , 'RxNorm' , 'MRCONSO' ] ,
                         dest = 'inputFormat' ,
                         help = 'Input format for extracting concepts' )
    
    parser.add_argument( '--output-file' , default = None ,
                         dest = 'outputFile' ,
                         help = 'Output file to write to (if no file is provided, output goes to stdout)' )
    
    parser.add_argument( '--output-prefix' , default = None ,
                         dest = 'outputPrefix' ,
                         help = 'Prefix of path for output files (used by RxNorm input)' )
    
    parser.add_argument( '--output-suffix' , default = None ,
                         dest = 'outputSuffix' ,
                         help = 'Suffix of path for output files (used by RxNorm input)' )
    
    parser.add_argument( '--output-format' , default = 'ttl' ,
                         choices = [ 'ttl' ] ,
                         dest = 'outputFormat' ,
                         help = 'Output format the knowledgebase will be written as' )
        
    parser.add_argument( '--prefix-file' , default = None ,
                         dest = 'prefixFile' ,
                         help = 'File contents to insert before any other output' )
    
    parser.add_argument( '--suffix-file' , default = None ,
                         dest = 'suffixFile' ,
                         help = 'File contents to insert after all other output' )
    
    parser.add_argument( '--source-type' , default = None ,
                         choices = [ 'LNC' , 'MDR' , 'NCI' , 'SNOMEDCT_US' ] ,
                         dest = 'sourceType' ,
                         help = 'Source type to pull concepts from' )

    ##
    return parser

def init_args( command_line_args ):
    ##
    parser = initialize_arg_parser()
    args = parser.parse_args( command_line_args )
    ##
    bad_args_flag = False
    ##
    if( args.inputFormat == 'csv' and args.outputFile is not None ):
        open( args.outputFile , 'w' ).close()
    elif( args.inputFormat == 'RxNorm' ):
        for outputInfix in [ 'Ingredients' , 'Brands' ]:
            open( '{}{}{}'.format( args.outputPrefix ,
                                   outputInfix ,
                                   args.outputSuffix ) , 
                  'w' ).close()
    ##
    if( bad_args_flag ):
        log.error( "I'm bailing out of this run because of errors mentioned above." )
        exit( 1 )
    ##
    return args

#############################################
## 
#############################################

def dump_lines( outputFile , line ):
    if( outputFile is None ):
        print( '{}'.format( line ) )
    else:
        with open( outputFile , 'a' ) as out_fp:
            out_fp.write( '{}\n'.format( line ) )


def parse_csv( csvFile , outputFile ):
    current_id = 4
    kb_stats = { 'total_concepts' : 0 }
    with open( csvFile , 'r' ) as fp:
        csv_dict_reader = csv.DictReader( fp , dialect = 'excel-tab' )
        for fields in csv_dict_reader:
            class_type = fields[ 'Class' ]
            root_type = fields[ 'RootType' ]
            sub_type = fields[ 'SubType' ]
            cui = fields[ 'CUI' ]
            if( cui == '' ):
                this_node = '{}#node1eoocu2ncx{}'.format( node_map[ 'kbRoot' ] ,
                                                          current_id )
                current_id += 1
            else:
                this_node = 'https://uts.nlm.nih.gov/uts/umls/concept/{}'.format( cui )
            if( sub_type == '' ):
                parent_type = class_type
                parent_node = '{}#{}'.format( node_map[ 'kbRoot' ] ,
                                              node_map[ parent_type ] )
                this_type = root_type
            else:
                parent_type = root_type
                parent_node = node_map[ parent_type ]
                this_type = sub_type
            node_map[ this_type ] = this_node
            dump_lines( outputFile ,
                        '<{}> a :Class;'.format( this_node ) )
            if( cui != '' ):
                dump_lines( outputFile ,
                            '  <{}#{}> "{}";'.format( node_map[ 'kbRoot' ] ,
                                                      node_map[ 'CUI' ] ,
                                                      cui ) )
            dump_lines( outputFile ,
                        '  :label "{}"@en;'.format( this_type ) )
            dump_lines( outputFile ,
                        '  :subClassOf <{}> .\n'.format( parent_node ) )
            kb_stats[ 'total_concepts' ] += 1
    ##
    return( kb_stats )

def generate_ttl_for_atc( args , rxcui , src_code , src_string , parents = None ):
    parent_type = ''
    if( len( src_code ) == 3 ):
        parent_type = src_code[ 0:1 ]
        parent_node = node_map[ parent_type ]
    for outputInfix in [ 'Ingredients' , 'Brands' ]:
        outputFile = '{}{}{}'.format( args.outputPrefix ,
                                      outputInfix ,
                                      args.outputSuffix )
        this_node = node_map[ src_code ]
        dump_lines( outputFile , 
                    '<{}> a :Class;'.format( this_node ) )
        dump_lines( outputFile , 
                     '  <{}#{}> "{}";'.format( node_map[ 'kbRoot' ] ,
                                               node_map[ 'RXCUI' ] ,
                                               rxcui ) )
        if( parent_type == '' ):
            dump_lines( outputFile , 
                        '  :label "{}"@en .\n'.format( src_string ) )
        else:
            dump_lines( outputFile , 
                        '  :label "{}"@en;'.format( src_string ) )
            dump_lines( outputFile , 
                        '  :subClassOf <{}> .\n'.format( parent_node ) )
            
def generate_ttl_for_brand( outputFile , rxcui , src_string , parents ):
    dump_lines( outputFile , 
                '<{}{}> a :Class;'.format( node_map[ 'rxNormRoot' ] ,
                                           rxcui ) )
    dump_lines( outputFile ,
                '  <{}#{}> "{}";'.format( node_map[ 'kbRoot' ] ,
                                          node_map[ 'RXCUI' ] ,
                                          rxcui ) )
    if( len( parents ) > 0 ):
        dump_lines( outputFile , 
                    '  :label "{}"@en;'.format( src_string ) )
    else:
        dump_lines( outputFile ,
                    '  :label "{}"@en.\n'.format( src_string ) )
    for i in range( 0 , len( parents ) ):
        suffix = ';'
        if( i == len( parents ) - 1 ):
            suffix = ' .\n'
        dump_lines( outputFile , 
                    '  :subClassOf <{}>{}'.format( parents[ i ] ,
                                                   suffix ) )


def generate_ttl_for_ingr( outputFile , rxcui , src_code , src_string ):
    parent_code = src_code[ 0:3 ]
    dump_lines( outputFile , 
                '<{}{}> a :Class;'.format( node_map[ 'rxNormRoot' ] ,
                                           rxcui ) )
    dump_lines( outputFile ,
                '  <{}#{}> "{}";'.format( node_map[ 'kbRoot' ] ,
                                          node_map[ 'RXCUI' ] ,
                                          rxcui ) )
    dump_lines( outputFile , 
                '  :label "{}"@en;'.format( src_string ) )
    ## If we wanted to map all ingredients to their brandnames, this
    ## is where we could add the BN as an alternate label
    ##if( rxcui in rxcui2brand_cui ):
    ##    for brand_cui in rxcui2brand_cui[ rxcui ]:
    ##        print( '  :label "{}"@en;'.format( brandcui2brand_string_map[ brand_cui ] ) )
    dump_lines( outputFile, 
                '  :subClassOf <{}> .\n'.format( node_map[ parent_code ] ) )


def parse_rxnorm( args ):
    kb_stats = { 'total_concepts' : 0 ,
                 'brand_concepts' : 0 ,
                 'brands_skipped' : 0 ,
                 'ingredient_concepts' : 0 }
    ##
    current_id = 3
    ##
    rxauis = set()
    leaf_meds = {}
    atc_nodes = {}
    ##
    rxcui2src_code_map = {}
    rxaui2src_code_map = {}
    rxaui2rxcui_map = {}
    rxaui2src_string_map = {}
    brandcui2brand_string_map = {}
    rxcui2brand_cui = {}
    brandcui2rxcui = {}
    ##
    rxnconso_file = os.path.join( args.inputDir , 'RXNCONSO.RRF' )
    ##################################################################
    ## Gather all concepts related to the top two levels of the ATC1-4
    ## ontology
    with open( rxnconso_file , 'r' ) as fp:
        csv_dict_reader = csv.reader( fp , delimiter = '|' )
        for cols in csv_dict_reader:
            ## Skip any suppressed rows
            if( cols[ rxnorm_headers[ 'SUPPRESS' ] - 1 ] in [ 'O' , 'Y' , 'E' ] ):
                continue
            ## Only look at preferred terms for the given source type
            if( cols[ rxnorm_headers[ 'SAB' ] - 1 ] == 'ATC' and
                cols[ rxnorm_headers[ 'TTY' ] - 1 ] == 'PT' ):
                rxcui = cols[ rxnorm_headers[ 'RXCUI' ] - 1 ]
                rxaui = cols[ rxnorm_headers[ 'RXAUI' ] - 1 ]
                src_code = cols[ rxnorm_headers[ 'CODE' ] - 1 ]
                ## Skip any concepts deeper in the hierarchy than two
                ## levels down
                if( len( src_code ) > 3 ):
                    continue
                src_string = cols[ rxnorm_headers[ 'STRING' ] - 1 ]
                rxaui2src_code_map[ rxaui ] = src_code
                rxaui2rxcui_map[ rxaui ] = rxcui
                rxaui2src_string_map[ rxaui ] = src_string
                safe_string = re.sub( ' ' , '%20' , src_string )
                this_node = 'https://mor.nlm.nih.gov/RxClass/search?query={}&searchBy=class&sourceIds=&drugSources=atc1-4'.format( safe_string )
                node_map[ src_code ] = this_node
                rxauis.add( rxaui )
    ## Iterate through the extracted top-level concepts to write them
    ## out to both ingredients and brands files
    for rxaui in tqdm( rxaui2src_code_map ):
        rxcui = rxaui2rxcui_map[ rxaui ]
        src_code = rxaui2src_code_map[ rxaui ]
        src_string = rxaui2src_string_map[ rxaui ]
        kb_stats[ 'total_concepts' ] += 1
        generate_ttl_for_atc( args = args , 
                              rxcui = rxcui ,
                              src_code = src_code ,
                              src_string = src_string )
    ##################################################################
    ## Collect all the brand names
    with open( rxnconso_file , 'r' ) as fp:
        csv_dict_reader = csv.reader( fp , delimiter = '|' )
        for cols in csv_dict_reader:
            ## Skip any suppressed rows
            if( cols[ rxnorm_headers[ 'SUPPRESS' ] - 1 ] in [ 'O' , 'Y' , 'E' ] ):
                continue
            if( cols[ rxnorm_headers[ 'SAB' ] - 1 ] == 'RXNORM' and
                cols[ rxnorm_headers[ 'TTY' ] - 1 ] == 'BN' ):
                brandcui = cols[ rxnorm_headers[ 'RXCUI' ] - 1 ]
                src_string = cols[ rxnorm_headers[ 'STRING' ] - 1 ]
                brandcui2brand_string_map[ brandcui ] = src_string
    ##################################################################
    ## 
    rxnrel_file = os.path.join( args.inputDir , 'RXNREL.RRF' )
    with open( rxnrel_file , 'r' ) as fp:
        csv_dict_reader = csv.reader( fp , delimiter = '|' )
        for cols in csv_dict_reader:
            cui_or_aui = cols[ rxrel_headers[ 'STYPE1' ] - 1 ]
            specific_relation = cols[ rxrel_headers[ 'RELA' ] - 1 ]
            ## Figure out which entry is the brand and which is the
            ## ingredient
            if( specific_relation == 'has_tradename' and
                cui_or_aui == 'CUI' ):
                brand_rxcui = cols[ rxrel_headers[ 'RXCUI1' ] - 1 ]
                ingr_rxcui = cols[ rxrel_headers[ 'RXCUI2' ] - 1 ]
            elif( specific_relation == 'tradename_of' and
                  cui_or_aui == 'CUI' ):
                ingr_rxcui = cols[ rxrel_headers[ 'RXCUI1' ] - 1 ]
                brand_rxcui = cols[ rxrel_headers[ 'RXCUI2' ] - 1 ]
            else:
                continue
            ## Then link the two in our maps
            if( brand_rxcui in brandcui2brand_string_map ):
                if( ingr_rxcui not in rxcui2brand_cui ):
                    rxcui2brand_cui[ ingr_rxcui ] = set()
                rxcui2brand_cui[ ingr_rxcui ].add( brand_rxcui )
                if( brand_rxcui not in brandcui2rxcui ):
                    brandcui2rxcui[ brand_rxcui ] = set()
                brandcui2rxcui[ brand_rxcui ].add( ingr_rxcui )
            else:
                ##log.warn( 'Brand not present in mapping file:  {}'.format( brand_rxcui ) )
                kb_stats[ 'brands_skipped' ] += 1
                continue
    ##################################################################
    with open( rxnconso_file , 'r' ) as fp:
        csv_dict_reader = csv.reader( fp , delimiter = '|' )
        for cols in csv_dict_reader:
            if( cols[ rxnorm_headers[ 'SAB' ] - 1 ] == 'ATC' and
                ( cols[ rxnorm_headers[ 'TTY' ] - 1 ] == 'IN' or
                  cols[ rxnorm_headers[ 'TTY' ] - 1 ] == 'MIN' ) ):
                rxcui = cols[ rxnorm_headers[ 'RXCUI' ] - 1 ]
                rxaui = cols[ rxnorm_headers[ 'RXAUI' ] - 1 ]
                src_code = cols[ rxnorm_headers[ 'CODE' ] - 1 ]
                src_string = cols[ rxnorm_headers[ 'STRING' ] - 1 ]
                rxaui2src_code_map[ rxaui ] = src_code
                rxcui2src_code_map[ rxcui ] = src_code
                kb_stats[ 'total_concepts' ] += 1
                kb_stats[ 'ingredient_concepts' ] += 1
                generate_ttl_for_ingr( outputFile = '{}{}{}'.format( args.outputPrefix ,
                                                                     'Ingredients' ,
                                                                     args.outputSuffix ) ,
                                       rxcui = rxcui ,
                                       src_code = src_code ,
                                       src_string = src_string )
                rxauis.add( rxaui )
    ##################################################################
    ## Write brand names to the kb
    for brand_cui in tqdm( sorted( brandcui2brand_string_map ) ):
        brand_string = brandcui2brand_string_map[ brand_cui ]
        kb_stats[ 'total_concepts' ] += 1
        kb_stats[ 'brand_concepts' ] += 1
        ## Just in case we have a brand med unrelated to an IN/MIN
        ## entry, we still want to print it but we have to set the
        ## parents to empty
        parents = []
        if( brand_cui in brandcui2rxcui ):
            parent_cuis = brandcui2rxcui[ brand_cui ]
            for parent_cui in parent_cuis:
                if( parent_cui in rxcui2src_code_map ):
                    src_code = rxcui2src_code_map[ parent_cui ]
                    if( len( src_code ) > 3 ):
                        parent_type = src_code[ 0:3 ]
                    else:
                        parent_type = src_code
                    parent_node = node_map[ parent_type ]
                    if( parent_node not in parents ):
                        parents.append( parent_node )
        generate_ttl_for_brand( outputFile = '{}{}{}'.format( args.outputPrefix ,
                                                              'Brands' ,
                                                              args.outputSuffix ) ,
                                rxcui = brand_cui ,
                                src_string = brand_string ,
                                parents = parents )
    ##
    return( kb_stats )


def write_semtype_concept( outputFile , sem_type , sem_string ):
    safe_string = re.sub( ' ' , '%20' , sem_string )
    this_node = 'https://uts.nlm.nih.gov/semanticnetwork.html#{};0;0;2020AB'.format( safe_string )
    node_map[ sem_type ] = this_node
    dump_lines( outputFile , '<{}> a :Class;'.format( this_node ) )
    dump_lines( outputFile , '  :label "{}"@en .\n'.format( sem_string ) )


def write_lab_test_concept( outputFile , cui , preferred_term , sem_type ):
    this_node = '{}{}'.format( node_map[ 'utsRoot' ] ,
                               cui )
    node_map[ cui ] = this_node
    dump_lines( outputFile , '<{}> a :Class;'.format( this_node ) )
    dump_lines( outputFile , '  <{}#{}> "{}";'.format( node_map[ 'kbRoot' ] ,
                                                       node_map[ 'CUI' ] ,
                                                       cui ) )
    dump_lines( outputFile , '  :label "{}"@en;'.format( preferred_term ) )
    parent_node = node_map[ sem_type ]
    dump_lines( outputFile , '  :subClassOf <{}> .\n'.format( parent_node ) )


def parse_mrconso( inputDir , sourceType , outputFile ):
    current_id = 3
    cui2semtype_map = {}
    kb_stats = { 'total_concepts' : 0 }
    ##
    ##tier1_semtypes = { 'T059' : 'Laboratory Procedure' ,
    ##                   'T034' : 'Laboratory or Test Result' }
    tier1_semtypes = { 'T059' : 'Laboratory Procedure' }
    for sem_type in tier1_semtypes:
        kb_stats[ 'total_concepts' ] += 1
        write_semtype_concept( outputFile , sem_type , tier1_semtypes[ sem_type ] )
    ##################################################################
    mrsty_file = os.path.join( inputDir , 'MRSTY.RRF' )
    with open( mrsty_file , 'r' ) as fp:
        csv_dict_reader = csv.reader( fp , delimiter = '|' )
        for cols in csv_dict_reader:
            cui = cols[ mrsty_headers[ 'CUI' ] - 1 ]
            sem_type = cols[ mrsty_headers[ 'TUI' ] - 1 ]
            if( sem_type in tier1_semtypes ):
                if( cui in cui2semtype_map ):
                    log.warn( 'Already in map:  {} -> {} + {}'.format( cui , 
                                                                       sem_type ,
                                                                       cui2semtype_map ) )
                else:
                    cui2semtype_map[ cui ] = sem_type
    ##################################################################
    mrconso_file = os.path.join( inputDir , 'MRCONSO.RRF' )
    with open( mrconso_file , 'r' ) as fp:
        csv_dict_reader = csv.reader( fp , delimiter = '|' )
        for cols in csv_dict_reader:
            cui = cols[ mrconso_headers[ 'CUI' ] - 1 ]
            if( cui in cui2semtype_map and
                cols[ mrconso_headers[ 'LAT' ] - 1 ] == 'ENG' and
                ##cols[ mrconso_headers[ 'TS' ] - 1 ] == 'P' and
                ##cols[ mrconso_headers[ 'STT' ] - 1 ] == 'PF' and
                cols[ mrconso_headers[ 'TTY' ] - 1 ] == 'PT' and
                ##cols[ mrconso_headers[ 'ISPREF' ] - 1 ] == 'Y' and
                cols[ mrconso_headers[ 'SAB' ] - 1 ] == sourceType and
                cols[ mrconso_headers[ 'SUPPRESS' ] - 1 ] in [ 'N' , '' ] ):
                preferred_term = cols[ mrconso_headers[ 'STR' ] - 1 ]
                sem_type = cui2semtype_map[ cui ]
                kb_stats[ 'total_concepts' ] += 1
                write_lab_test_concept( outputFile , cui , preferred_term , sem_type )
    ##
    return( kb_stats )


if __name__ == "__main__":
    ##
    args = init_args( sys.argv[ 1: ] )
    ##
    ##########################
    if( args.prefixFile is not None ):
        with open( args.prefixFile , 'r' ) as in_fp:
            for line in in_fp:
                line = line.rstrip()
                if( args.inputFormat in [ 'csv' , 'MRCONSO' ] ):
                    dump_lines( args.outputFile , line )
                elif( args.inputFormat == 'RxNorm' ):
                    for outputInfix in [ 'Ingredients' , 'Brands' ]:
                        dump_lines( '{}{}{}'.format( args.outputPrefix ,
                                                     outputInfix ,
                                                     args.outputSuffix ) ,
                                    line )
    ##
    ##########################
    if( args.inputFormat == 'csv' ):
        kb_stats = parse_csv( args.inputFile , args.outputFile )
    elif( args.inputFormat == 'RxNorm' ):
        kb_stats = parse_rxnorm( args )
    elif( args.inputFormat == 'MRCONSO' ):
        kb_stats = parse_mrconso( args.inputDir , args.sourceType , args.outputFile )
    else:
        log.error( 'Unrecognized input format:  {}'.format( args.inputFormat ) )
    ##
    ##########################
    if( args.suffixFile is not None ):
        with open( args.suffixFile , 'r' ) as in_fp:
            for line in in_fp:
                line = line.rstrip()
                dump_lines( args.outputFile , line )
    ##
    ##########################
    print( 'Unique Concepts:\t{}'.format( kb_stats[ 'total_concepts' ] ) )
    if( args.inputFormat == 'RxNorm' ):
        print( 'Ingredient Concepts:\t{}'.format( kb_stats[ 'ingredient_concepts' ] ) )
        print( 'Brand Concepts:\t{}'.format( kb_stats[ 'brand_concepts' ] ) )
        print( ' -- Skipped:\t{}'.format( kb_stats[ 'brands_skipped' ] ) )
