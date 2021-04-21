
import logging as log

from Authentication import *
import requests
import json
import argparse

import time

## TODO - allow this to be passed via command line or environment variable
## UMLS_API_TOKEN = 'NOT-A-REAL-TOKEN-ASDF-QWERTY'
UMLS_API_TOKEN = None

last_auth_time = None
last_auth_client = None

def init_authentication( api_key ):
   global last_auth_time , last_auth_client
   global auth_client
   now_time = time.time()
   ## Re-authorize every thirty minutes
   if( last_auth_time is None or
       ( now_time - last_auth_time ) > 30 * 60 ):
      if( last_auth_time is None ):
         log.debug( 'Authenticating with the UTS server' )
      else:
         log.debug( 'Re-authenticating with the UTS server' )
      last_auth_time = time.time()
      auth_client = Authentication( api_key )
      last_auth_client = auth_client
   else:
      auth_client = last_auth_client
   ###################################
   #get TGT for our session
   ###################################
   return auth_client

########################################################################
##
########################################################################

def search_umls( auth_client , version , identifier , source ,
                 input_type = 'sourceUi' ,
                 return_type = 'concept' ):
   log.debug( 'call to search_umls( ... , {} , ... )'.format( identifier ) )
   tgt = auth_client.gettgt()
   uri = "https://uts-ws.nlm.nih.gov"
   content_endpoint = "/rest/search/current?string="+str(identifier) + \
                                                    "&inputType="+str(input_type) + \
                                                    "&returnIdType="+str(return_type) + \
                                                    "&searchType=exact&sabs="+str(source)
   ##log( content_endpoint )
   ##ticket is the only parameter needed for this call - paging does not come into play because we're only asking for one Json object
   query = {'ticket':auth_client.getst(tgt)}
   r = requests.get(uri+content_endpoint,params=query)
   r.encoding = 'utf-8'
   items  = json.loads(r.text)
   jsonData = items["result"]
   ##uncomment the print statment if you want the raw json output, or you can just look at the documentation :=)
   #https://documentation.uts.nlm.nih.gov/rest/concept/index.html#sample-output
   #https://documentation.uts.nlm.nih.gov/rest/source-asserted-identifiers/index.html#sample-output
   ##log( json.dumps(items, indent = 4) )
   ############################
   classType = jsonData["classType"]
   if( len( jsonData["results"] ) > 1 ):
       log.debug( 'Multiple matches.  Only using the last for {}'.format( source ) )
   name = None
   cui = None
   for inner_results in jsonData["results"]:
      name = inner_results[ "name" ]
      cui = inner_results["ui"]
      ##
   if( cui == None ):
      print (json.dumps(items, indent = 4))
   return( cui )

def get_cui( auth_client , version , identifier , source ):
   log.debug( 'call to get_cui( ... , {} , ... )'.format( identifier ) )
   return( search_umls( auth_client , version , identifier , source ,
                        input_type = 'sourceUi' ,
                        return_type = 'concept' ) )

def get_concept_id( auth_client , version , identifier , source ):
   log.debug( 'call to get_concept_id( ... , {} , ... )'.format( identifier ) )
   return( search_umls( auth_client , version , identifier , source ,
                        input_type = 'concept' ,
                        return_type = 'sourceUi' ) )

def get_atoms( auth_client , version , identifier , source ):
   log.debug( 'call to get_atoms( ... , {} , ... )'.format( identifier ) )
   current_page = 1
   last_page = 1
   tgt = auth_client.gettgt()
   uri = "https://uts-ws.nlm.nih.gov"
   content_endpoint = "/rest/content/current/CUI/"+str(identifier) + "/atoms?" + \
                      "sabs=" + str( source ) + \
                      "&ttys=PT,HT"
   ##log( 'Content Endpoint\n\n{}\n'.format( content_endpoint ) )
   codes_list = []
   ############################
   while( current_page <= last_page ):
      ##content_endpoint = "/rest/search/current?string=" + str(identifier) + "inputType=sourceUi&pageNumber=1"
      ##ticket is the only parameter needed for this call - paging does not come into play because we're only asking for one Json object
      query = { 'ticket' : auth_client.getst(tgt) , 'pageNumber' : current_page }
      r = requests.get(uri+content_endpoint,params=query)
      r.encoding = 'utf-8'
      #log( 'Text\n\n{}\n'.format( r.text ) )
      try:
         items  = json.loads(r.text)
      except ValueError as e :
         current_page +=1
         continue
      jsonData = items["result"]
      ##uncomment the print statment if you want the raw json output, or you can just look at the documentation :=)
      #https://documentation.uts.nlm.nih.gov/rest/concept/index.html#sample-output
      #https://documentation.uts.nlm.nih.gov/rest/source-asserted-identifiers/index.html#sample-output
      ##log( 'JSON Dump\n\n{}\n'.format( json.dumps(items, indent = 4) ) )
      if( current_page == 1 ):
         last_page = items[ "pageCount" ]
         ##log( 'Page {} of {}'.format( current_page , last_page ) )
      ##
      ##log( 'Inner Results\n\n' )
      for inner_results in jsonData:
         source_code_url = inner_results[ 'code' ].split( '/' )
         source_code = source_code_url[ len( source_code_url ) - 1 ]
         codes_list.append( source_code )
         ##log( source_code )
      current_page +=1
   return( codes_list )

def get_family_tree( auth_client , version , identifier ,
                     relation_type , root_source = 'SNOMEDCT_US' ):
   log.debug( 'call to get_family_tree( ... , {} , ... )'.format( identifier ) )
   current_page = 1
   last_page = 1
   tgt = auth_client.gettgt()
   uri = "https://uts-ws.nlm.nih.gov"
   content_endpoint = "/rest/content/current/source/" + str( root_source ) + "/"+str(identifier) + "/" + str( relation_type )
   ##log( '{}'.format( content_endpoint )
   atoms_set = set()
   ############################
   while( current_page <= last_page ):
      ##content_endpoint = "/rest/search/current?string=" + str(identifier) + "inputType=sourceUi&pageNumber=1"
      ##ticket is the only parameter needed for this call - paging does not come into play because we're only asking for one Json object
      query = { 'ticket' : auth_client.getst(tgt) , 'pageNumber' : current_page }
      r = requests.get(uri+content_endpoint,params=query)
      r.encoding = 'utf-8'
      ##log( r.text )
      try:
         items  = json.loads(r.text)
      except ValueError as e :
         current_page +=1
         continue
      jsonData = items["result"]
      if( jsonData is None ):
         return( atoms_set )
      ##uncomment the print statment if you want the raw json output, or you can just look at the documentation :=)
      #https://documentation.uts.nlm.nih.gov/rest/concept/index.html#sample-output
      #https://documentation.uts.nlm.nih.gov/rest/source-asserted-identifiers/index.html#sample-output
      ##log( json.dumps(items, indent = 4) )
      if( current_page == 1 ):
         last_page = items[ "pageCount" ]
         ##log( 'Page {} of {}'.format( current_page , last_page ) )
      ##
      for inner_results in jsonData:
         atomic_ui = inner_results[ "ui" ]
         ##log( '\t{}'.format( relation_label ) )
         ##if( target_relation_label is not None and
         ##    relation_label != target_relation_label ):
         ##   continue
         ##name = inner_results[ "relatedIdName" ]
         ##cui_url = inner_results[ "relatedId" ]
         ##cui = cui_url.split( '/' )[ -1 ]
         ##cui_dict[ cui ] = name
         atoms_set.add( atomic_ui )
         ##log( '\t{}'.format( atomic_ui ) )
      current_page +=1
   return( atoms_set )

def get_parents( auth_client , version , identifier , source ,
                 atoms = [] ):
   log.debug( 'call to get_parents( ... , {} , ... )'.format( identifier ) )
   if( atoms == [] ):
      atoms = get_atoms( auth_client , version , identifier ,
                         source = source )
   parent_atoms = set()
   parent_cuis = set()
   for atomic_ui in atoms:
      for parent in get_family_tree( auth_client , version , #'9468002' , #'A10134087' ,
                                     atomic_ui ,
                                     relation_type = 'parents' ):
         parent_atoms.add( parent )
   for parent_aui in parent_atoms:
      cui = get_cui( auth_client , version , parent_aui , source )
      parent_cuis.add( cui )
   return( parent_cuis )

########################################################################
##
########################################################################

def get_cuis_atom( auth_client , version , identifier , atom_type ):
   log.debug( 'call to get_cuis_atom( ... , {} , {} )'.format( identifier , atom_type ) )
   current_page = 1
   last_page = 1
   tgt = auth_client.gettgt()
   uri = "https://uts-ws.nlm.nih.gov"
   atom_string = ''
   if( atom_type != '' ):
       atom_string = "/atoms{}".format( str( atom_type ) )
   content_endpoint = "/rest/content/current/CUI/"+str(identifier) + atom_string
   ##print( '{}'.format( content_endpoint ) )
   if( atom_type == '/preferred' ):
      all_atoms = None
   else:
      all_atoms = set()
   ############################
   while( current_page <= last_page ):
      ##content_endpoint = "/rest/search/current?string=" + str(identifier) + "inputType=sourceUi&pageNumber=1"
      ##ticket is the only parameter needed for this call - paging does not come into play because we're only asking for one Json object
      query = { 'ticket' : auth_client.getst(tgt) , 'pageNumber' : current_page }
      r = requests.get(uri+content_endpoint,params=query)
      r.encoding = 'utf-8'
      ##log( r.test )
      try:
         items  = json.loads(r.text)
      except ValueError as e :
         current_page +=1
         continue
      if( 'error' in items ):
         log.error( 'Query failed due to reported error:  {}'.format( items[ 'error' ] ) )
         break
      if( 'result' not in items ):
         continue
      jsonData = items["result"]
      ##uncomment the print statment if you want the raw json output, or you can just look at the documentation :=)
      #https://documentation.uts.nlm.nih.gov/rest/concept/index.html#sample-output
      #https://documentation.uts.nlm.nih.gov/rest/source-asserted-identifiers/index.html#sample-output
      ##log( json.dumps(items, indent = 4) )
      if( current_page == 1 ):
         last_page = items[ "pageCount" ]
         ##log( 'Page {} of {}'.format( current_page , last_page ) )
      if( last_page > 1 ):
         log.debug( 'Page {} of {}'.format( current_page , last_page ) )
      ##
      if( atom_type == '/preferred' ):
         name = jsonData[ "name" ]
         ##log( '{}\t{}'.format( str( identifier ) , name ) )
         return( name )
      elif( atom_type == '' ):
          semantic_types = jsonData[ 'semanticTypes' ]
          for sem_type in semantic_types:
              tui = sem_type[ 'uri' ].split( '/' )[ -1 ]
              return( tui )
      else:
          for inner_results in jsonData:
              name = inner_results[ "name" ]
              all_atoms.add( name )
              ##log( '{}\t{}'.format( identifier , name ) )
      current_page +=1
   return( all_atoms )

def get_cuis_preferred_atom( auth_client , version , identifier ):
   log.debug( 'call to get_cui_preferred_atom( . , {} , {} )'.format( version , identifier ) )
   return( get_cuis_atom( auth_client , version , identifier , atom_type = '/preferred' ) )

def get_cuis_eng_atom( auth_client , version , identifier ):
   log.debug( 'call to get_cui_eng_atom( . , {} , {} )'.format( version , identifier ) )
   return( get_cuis_atom( auth_client , version , identifier , atom_type = '?language=ENG' ) )

def get_typed_relation( auth_client , version , identifier , target_relation_type , target_relation_label ):
   log.debug( 'call to get_typed_relation( ... , {} , {} , {} )'.format( identifier , target_relation_type , target_relation_label ) )
   current_page = 1
   last_page = 1
   tgt = auth_client.gettgt()
   uri = "https://uts-ws.nlm.nih.gov"
   content_endpoint = "/rest/content/current/CUI/"+str(identifier) + "/" + str(target_relation_type)
   ##log( '{}'.format( content_endpoint ) )
   cui_dict = {}
   ############################
   while( current_page <= last_page ):
      ##content_endpoint = "/rest/search/current?string=" + str(identifier) + "inputType=sourceUi&pageNumber=1"
      ##ticket is the only parameter needed for this call - paging does not come into play because we're only asking for one Json object
      query = { 'ticket' : auth_client.getst(tgt) , 'pageNumber' : current_page }
      r = requests.get(uri+content_endpoint,params=query)
      r.encoding = 'utf-8'
      ##log( '{}'.format( r.text ) )
      try:
         items  = json.loads(r.text)
      except ValueError as e :
         current_page +=1
         continue
      jsonData = items["result"]
      ##uncomment the print statment if you want the raw json output, or you can just look at the documentation :=)
      #https://documentation.uts.nlm.nih.gov/rest/concept/index.html#sample-output
      #https://documentation.uts.nlm.nih.gov/rest/source-asserted-identifiers/index.html#sample-output
      ##log( '{}'.format( json.dumps(items, indent = 4) ) )
      if( current_page == 1 ):
         last_page = items[ "pageCount" ]
         ##log( 'Page {} of {}'.format( current_page , last_page ) )
      ##
      for inner_results in jsonData:
         relation_label = inner_results[ "relationLabel" ]
         ##log( '\t{}'.format( relation_label ) )
         if( target_relation_label is not None and
             relation_label != target_relation_label ):
            continue
         name = inner_results[ "relatedIdName" ]
         cui_url = inner_results[ "relatedId" ]
         cui = cui_url.split( '/' )[ -1 ]
         cui_dict[ cui ] = name
      current_page +=1
   return( cui_dict )

def get_rbs( auth_client , version , identifier ):
   log.debug( 'call to get_rbs( ... , {} )'.format( identifier ) )
   return( get_typed_relation( auth_client , version , identifier ,
                               target_relation_type = 'relations' ,
                               target_relation_label = 'RB' ) )

def get_rns( auth_client , version , identifier ):
   log.debug( 'call to get_rns( ... , {} )'.format( identifier ) )
   return( get_typed_relation( auth_client , version , identifier ,
                               target_relation_type = 'relations' ,
                               target_relation_label = 'RN' ) )

def get_ros( auth_client , version , identifier ):
   log.debug( 'call to get_ros( ... , {} )'.format( identifier ) )
   return( get_typed_relation( auth_client , version , identifier ,
                               target_relation_type = 'relations' ,
                               target_relation_label = 'RO' ) )

########################################################################
##
########################################################################

def get_all_umls_descendants( auth_client , head_cui ,
                              concepts ,
                              exclude_list , already_included = None ):
    descendant_cuis = get_rbs( auth_client , 'current' , head_cui )
    log.debug( 'Grabbed RBs. descendant cui n = {}'.format( len( descendant_cuis ) ) )
    include_list = []
    for descendant_cui in descendant_cuis:
        if( descendant_cui in exclude_list or
            descendant_cui in concepts or
            ( already_included is not None and
              descendant_cui in already_included ) ):
            continue
        include_list.append( descendant_cui )
        include_list += get_all_umls_descendants( auth_client , descendant_cui ,
                                                  concepts ,
                                                  exclude_list ,
                                                  include_list )
    return include_list

def get_all_snomed_descendants( auth_client , head_concept_id ,
                                exclude_list ):
    descendant_concept_ids = get_family_tree( auth_client , 'current' ,
                                              head_concept_id ,
                                              relation_type = 'children' )
    include_list = []
    for descendant_concept_id in descendant_concept_ids:
        descendant_cui = get_cui( auth_client , 'current' , descendant_concept_id , 'SNOMEDCT_US' )
        if( descendant_cui in exclude_list ):
            continue
        include_list.append( descendant_cui )
        include_list += get_all_snomed_descendants( auth_client , descendant_concept_id ,
                                                    exclude_list )
    return include_list

########################################################################
##
########################################################################

def get_first_umls_children( auth_client , head_cui ,
                             exclude_list , get_grandchildren = False ):
    descendant_cuis = get_rbs( auth_client , 'current' , head_cui )
    include_list = []
    for descendant_cui in descendant_cuis:
        if( descendant_cui in exclude_list ):
            continue
        include_list.append( descendant_cui )
        if( get_grandchildren ):
            include_list += get_first_umls_children( auth_client , descendant_cui ,
                                                     exclude_list , False )
    return include_list

def get_first_rxnorm_ancestors( auth_client , head_concept_id ):
    descendant_concept_ids = get_family_tree( auth_client , 'current' ,
                                              head_concept_id ,
                                              relation_type = 'ancestors' ,
                                              root_source = 'RXNORM' )
    include_list = []
    for descendant_concept_id in descendant_concept_ids:
        descendant_cui = get_cui( auth_client , 'current' , descendant_concept_id , 'RXNORM' )
        include_list.append( descendant_cui )
    return include_list

########################################################################
##
########################################################################

def get_rxcui_umls_cui( rxcui_str ):
    base_uri = 'https://rxnav.nlm.nih.gov/REST/'
    content_endpoint = "rxcui/" + rxcui_str + "/property.json?propName=UMLSCUI"
    ##log( '{}{}'.format( base_uri , content_endpoint ) )
    #query = {'ticket':auth_client.getst(tgt)}
    r = requests.get( base_uri + content_endpoint )#,params=query)
    r.encoding = 'utf-8'
    ##log( '{}\n---------------\n'.format( r ) )
    items  = json.loads(r.text)
    all_cuis = set()
    groupData = items[ "propConceptGroup" ][ "propConcept" ]
    ##log( '{}\n---------------\n{}'.format( items , groupData ) )
    for group in groupData:
        umls_cui = group[ 'propValue' ]
        #add_dictionary_entry( umls_cui , name )
        all_cuis.add( umls_cui )
    return all_cuis

def get_rxclass_members( rxclass_str ):
    base_uri = 'https://rxnav.nlm.nih.gov/REST/'
    relaSrc = 'ATC'
    if( rxclass_str == 'D009294' ):
        relaSrc = 'MESH'
    ##
    content_endpoint = "rxclass/classMembers.json?classId=" + rxclass_str + "&relaSource=" + relaSrc
    #log( '{}{}'.format( base_uri , content_endpoint ) )
    #query = {'ticket':auth_client.getst(tgt)}
    r = requests.get( base_uri + content_endpoint )#,params=query)
    r.encoding = 'utf-8'
    #log( '{}\n---------------\n'.format( r ) )
    items  = json.loads(r.text)
    all_cuis = set()
    groupData = items[ "drugMemberGroup" ][ "drugMember" ]
    ##log( '{}\n---------------\n{}'.format( items , groupData ) )
    for group in groupData:
        if( 'minConcept' in group ):
            concept = group[ "minConcept" ]
            rx_cui = concept[ 'rxcui' ]
            name = concept[ 'name' ]
            all_cuis.add( rx_cui )
    return all_cuis

########################################################################
##
########################################################################


if __name__ == "__main__":
      auth_client = init_authentication( UMLS_API_TOKEN )
      ##log( '{}'.format( get_cuis_preferred_atom( auth_client , 'current' , 'C0000731' ) ) )
      print( '{}'.format( get_cuis_atom( auth_client , 'current' , 'C0000731' , '' ) ) )
      ##log( '{}'.format( get_cuis_atom( auth_client , 'current' , 'C0000731' ,
      ##                                   atom_type = '?language=ENG' ) ) )
