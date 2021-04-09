import logging as log

import os
import sys

import argparse

from csv import DictReader

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
                         help = 'Input file to read the knowledgebase concepts from' )
     
    parser.add_argument( '--input-format' , default = 'csv' ,
                         choices = [ 'csv' , 'RxNorm' , 'MRCONSO' ] ,
                         dest = 'inputFormat' ,
                         help = 'Input format for extracting concepts' )
    
    parser.add_argument( '--output-file' , default = None ,
                         dest = 'outputFile' ,
                         help = 'Output file to write to (if no file is provided, output goes to stdout)' )
    
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
    
    ##
    return parser

def init_args( command_line_args ):
    ##
    parser = initialize_arg_parser()
    args = parser.parse_args( command_line_args )
    ##
    bad_args_flag = False
    ##
    if( args.outputFile is not None ):
        open( args.outputFile , 'w' ).close()
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
    node_map = { 'root' : 'http://www.ukp.informatik.tu-darmstadt.de/inception/1.0' ,
                 'CUI' : 'node1eoocu2ncx1' ,
                 'Disease' : 'node1eoocu2ncx2' ,
                 'Sign or Symptom' : 'node1eoocu2ncx3' }
    current_id = 4
    with open( csvFile , 'r' ) as fp:
        csv_dict_reader = DictReader( fp , dialect = 'excel-tab' )
        for fields in csv_dict_reader:
            class_type = fields[ 'Class' ]
            root_type = fields[ 'RootType' ]
            sub_type = fields[ 'SubType' ]
            cui = fields[ 'CUI' ]
            if( cui == '' ):
                this_node = '{}#node1eoocu2ncx{}'.format( node_map[ 'root' ] ,
                                                          current_id )
                current_id += 1
            else:
                this_node = 'https://uts.nlm.nih.gov/uts/umls/concept/{}'.format( cui )
            if( sub_type == '' ):
                parent_type = class_type
                parent_node = '{}#{}'.format( node_map[ 'root' ] ,
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
                            '  <{}#{}> "{}";'.format( node_map[ 'root' ] ,
                                                      node_map[ 'CUI' ] ,
                                                      cui ) )
            dump_lines( outputFile ,
                        '  :label "{}"@en;'.format( this_type ) )
            dump_lines( outputFile ,
                        '  :subClassOf <{}> .\n'.format( parent_node ) )


if __name__ == "__main__":
    ##
    args = init_args( sys.argv[ 1: ] )
    ##
    ##########################
    if( args.prefixFile is not None ):
        with open( args.prefixFile , 'r' ) as in_fp:
            for line in in_fp:
                line = line.rstrip()
                dump_lines( args.outputFile , line )
    ##
    ##########################
    if( args.inputFormat is 'csv' ):
        parse_csv( args.inputFile , args.outputFile )
    ##
    ##########################
    if( args.suffixFile is not None ):
        with open( args.suffixFile , 'r' ) as in_fp:
            for line in in_fp:
                line = line.rstrip()
                dump_lines( args.outputFile , line )

