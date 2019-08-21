
import logging as log

import os

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


def create_token():
    token = etree.Element( "token" )
    token.set( 'canonical' , 'United States' )
    token.set( 'DOCNO' , '276145' )
    ###
    variant = etree.Element( 'variant' )
    variant.set( 'base' , 'United States' )
    token.append( variant )
    ###
    variant = etree.Element( 'variant' )
    variant.set( 'base' , 'United States of America' )
    token.append( variant )
    ###
    variant = etree.Element( 'variant' )
    variant.set( 'base' , 'the United States of America' )
    token.append( variant )
    return( token )

def create_concept_mapper_template():
    root = etree.Element( "synonym" )
    return( root )

def open_concept_mapper_dict( filename ):
    if( False and os.path.exists( filename ) ):
        with open( filename , 'r' ) as fp:
            tree = etree.parse( fp )
        root = tree.getroot()
        root.append( create_token() )
    else:
        root = create_concept_mapper_template()
        root.append( create_token() )
    ##
    new_tree = etree.ElementTree( root )
    new_tree.write( filename ,
                    xml_declaration = True ,
                    encoding = 'UTF-8' ,
                    pretty_print = True )

if __name__ == "__main__":
    open_concept_mapper_dict( '/tmp/sample.dict' )
