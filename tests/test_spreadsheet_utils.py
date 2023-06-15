import os
import sys

from mock import patch

import tempfile

import json

import lex_gen
import spreadsheet_utils as csv_u

#############################################
## Extracting concepts
#############################################

def test_extract_concepts_from_tiny_problems():
    csv_concepts = lex_gen.concepts_from_csv( 'in/tiny_problems.csv' )
    cui_dict , concepts = csv_u.parse_focused_problems_tsv( input_filename = 'in/tiny_problems.csv' ,
                                                            concepts = {} ,
                                                            max_distance = -1 )
    assert len( cui_dict ) == 2
    assert len( concepts ) == 2


def test_extract_concepts_from_tiny_problems_with_gaps():
    csv_concepts = lex_gen.concepts_from_csv( 'in/tiny_missing_cuis.csv' )
    cui_dict , concepts = csv_u.parse_focused_problems_tsv( input_filename = 'in/tiny_missing_cuis.csv' ,
                                                            concepts = {} ,
                                                            max_distance = -1 )
    assert len( cui_dict ) == 2
    assert len( concepts ) == 2


