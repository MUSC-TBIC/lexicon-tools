import os
import sys

from mock import patch

import tempfile

import json

import lex_gen

#############################################
## Early initialization and set-up
#############################################

def test_default_init_args():
    test_args = [ 'lex_gen.py' ,
                  '--input-file' , 'in/tiny_problems.csv' ,
                  '--source-type' , 'problems' ,
                  '--batch-name' , 'testBatch001' ]
    with patch.object( sys , 'argv' , test_args ):
        args = lex_gen.init_args( sys.argv[ 1: ] )
        assert args.inputDir == 'in'
        assert args.inputFile == 'in/tiny_problems.csv'
        assert args.sourceType == 'problems'
        assert args.maxDistance == -1
        assert args.batchName == 'testBatch001'
        assert args.partialsDir == 'partials'
        assert args.outputDir == 'out'

#############################################
## Extracting concepts
#############################################

def test_extract_concepts_from_tiny_problems():
    csv_concepts = lex_gen.concepts_from_csv( 'in/tiny_problems.csv' )
    assert len( csv_concepts ) == 3


def test_extract_concepts_from_tiny_problems_with_gaps():
    csv_concepts = lex_gen.concepts_from_csv( 'in/tiny_missing_cuis.csv' )
    assert len( csv_concepts ) == 4
