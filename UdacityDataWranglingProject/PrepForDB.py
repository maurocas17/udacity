#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
The purpose of this class is to prepare data for inserting to MongoDB.
The class parses the OSM map xml and only process tags node and way element.
Corrections are applied and each record is converted to a json format.

Below are the corrections done:
1.  If there is an invalid characters in k attribute, record is skipped
2.  If there is an empty k or v attribute, record is skipped
3.  If there are more than two colons (:) used as delimiter for k attribute, record is skipped
4.  Checks if there is a correction for the tag V attribute from
        the file generated from MapContentAudit, mapContentAudit_WithCorrections.csv, and  
        replaces v with corrected value from the file.
5.  There are 2 additional correction done to street attribute: 
        - converting abbreviated street type format.  i.e. St. to Street
        - appying proper case format when all are in lower case.  i.e. old sauyo road to Old Sauyo Road


The json/dictionary output for each node and way record will look like this:

{
"id": "2406124091",
"type: "node",
"visible":"true",
"created": {
          "version":"2",
          "changeset":"17206049",
          "timestamp":"2013-08-03T16:43:42Z",
          "user":"linuxUser16",
          "uid":"1219059"
        },
"pos": [41.9757030, -87.6921867],
"address": {
          "housenumber": "5157",
          "postcode": "60625",
          "street": "North Lincoln Ave"
        },
"amenity": "restaurant",
"cuisine": "mexican",
"name": "La Cabana De Don Luis",
"phone": "1 (773)-271-5176"
}


- for "way" specifically:

  <nd ref="305896090"/>
  <nd ref="1719825889"/>

should be turned into
"node_refs": ["305896090", "1719825889"]


The parsed records are saved to MongoDB using the generated json file via mongoimport command.

"""


import xml.etree.ElementTree as ET
import pprint
import re
import codecs
import json
import csv


streetSuffix = ["Street", "Avenue", "Lane", "Highway", "Boulevard", "Extension", "Drive", "Road"]
streetTypeMap = {"St": "Street", 
                "St.": "Street",
                "st.":"Street",
                "st":"Street",
                "street": "Street",
                "Ave": "Avenue",
                "Ave.": "Avenue",
                "AVenue": "Avenue",
                "Hiway": "Highway",
                "Hoighway": "Highway",
                "highway": "Highway",
                "Ext": "Extension",
                "Ext.": "Extension",
                "ext": "Extension",
                'road': "Road",
                'Dr': "Drive",
                "dr": "Drive",
                "rd":"Road"}

lower_street = re.compile(r'^([a-z]|_| |\.)*$')
lower = re.compile(r'^([a-z]|_)*$')
lower_colon = re.compile(r'^([a-z]|_)*:([a-z]|_)*$')
problemchars = re.compile(r'[=\+/&<>;\'"\?%#$@\,\. \t\r\n]')

CREATED = [ "version", "changeset", "timestamp", "user", "uid"]
DEBUG = False

def shape_element(element, corrections, corrected_values, onlyQC = False):
    node = {}
    createdAttr = {}
    pos = []
    node_refs = []
    address = {}
    if element.tag == "node" or element.tag == "way" :
        #process the node/way attributes
        for name, val in element.attrib.iteritems():
            if name in CREATED: createdAttr[name] = val
            elif name in ["lat", "lon"]:
                if len(pos) == 0:
                    try:
                        pos.append(float(element.attrib["lat"]))
                        pos.append(float(element.attrib["lon"]))
                    except: continue
            else: node[name] = val
        
        #process the child elements, expecting only tag and nd
        for elem in element.iter():
            if elem.tag == "tag":
                k = elem.attrib["k"].strip()
                v = elem.attrib["v"].strip()
                
                #do not include k with problem characters
                if problemchars.search(k): continue
                
                #do not include empty k and v
                if len(k) == 0 or len(v) == 0: continue
                
                k_arr = k.split(":")
                
                #for now only add tags with up to two identifiers
                if len(k_arr) > 2: continue
                
                
                kId = k_arr[1] if len(k_arr) == 2 else k_arr[0]

                correction = corrections.get(kId, None)
                corrected_v = v
                if correction != None:
                    corrected_v = correction.get(v, corrected_v)
                        
                if len(k_arr) == 2 and k_arr[0] in ["addr",""]: 
                    if kId == "street": corrected_v = getCorrectedStreetName(corrected_v)
                    address[k_arr[1]] = corrected_v
                else: node[k] = corrected_v
                
                if (DEBUG == True and corrected_v != v): corrected_values[v] = corrected_v
                
            elif elem.tag == "nd": node_refs.append(elem.attrib["ref"])
        
        if len(address) > 0: 
            #only process Quezon City?            
            if (onlyQC == True):
                postcode = address.get("postcode", None)
                city = address.get("city", None)
                if postcode != None and city != None and validPostCode(postcode) == False and  city.lower() != "quezon city": return None
                
            node["address"] = address
            
            
        if len(createdAttr) > 0: node["created"] = createdAttr
        if len(pos) > 0: node["pos"] = pos
        if len(node_refs) > 0: node["node_refs"] = node_refs
        node["type"] = element.tag
        
        return node
    else:
        return None


"""
    In the udacity sample code, this method returns a list, containing all the elements written
    in the json file.  I've modified this code to not return a list of elements and
    to remove maintaining a list of said elements because this is causing large memory
    usage that takes a long time for the python code to exit normally.
"""
def process_map(file_in, pretty = None, onlyQC = False):
    # You do not need to change this file
    if (onlyQC == True):
        file_out = "{0}_qc.json".format(file_in)
    else:   
        file_out = "{0}.json".format(file_in)
    
    
    
    corrections = {}
    with open("mapcontentAudit_WithCorrection.csv", "rb") as infile:
        if infile: 
            csvReader = csv.DictReader(infile)
            prevK = None
            correctionMap = {}
            for row in csvReader:
                k = row["Tag K"]
                v = row["Tag Value"]
                correction  = row["Correction"].strip()
                
                if len(correction) > 0:
                    if prevK != k:
                        if prevK != None: corrections[prevK] = correctionMap
                        correctionMap = corrections.get(k, {})
                    
                    #DictReader does not support unicode characters, so convert to unicode
                    correctionMap[toUnicode(v)] = toUnicode(correction)
                    prevK = k
            
            if prevK !=  None: corrections[prevK] = correctionMap
                
    print "\n****** CORRECTIONS **************"                
    pprint.pprint(corrections)
                
    corrected_values = {}
    with codecs.open(file_out, "w") as fo:
        for _, element in ET.iterparse(file_in):
            el = shape_element(element, corrections, corrected_values, onlyQC)
            if el:
                if pretty:
                    fo.write(json.dumps(el, indent=2)+"\n")
                else:
                    fo.write(json.dumps(el) + "\n")
    
     
    if DEBUG == True:
        print "\n****** CORRECTED TAG V **************" 
        pprint.pprint(corrected_values)
    

def toUnicode(val):
    isAscii = len(val.decode('ascii', 'ignore')) == len(val)  
    if isAscii == False:   
        val = unicode(val, "latin-1")
    return val

def validPostCode(postcode):
    try:
        postnumber = int(postcode)
        if postnumber < 1100 or postnumber >= 1200: return False
        else: return True
    except:
        return False

def getCorrectedStreetName(v):
    
    #Correct for abbreviated street type, if any.
    #i.e. St. to Street    
    vArr = v.split()
    if (len(vArr) > 1):
        vlast = vArr[len(vArr)-1]
        vlastCorrect = streetTypeMap.get(vlast, None)
        if (vlastCorrect is not None):
            vArr[len(vArr)-1] = vlastCorrect

    #correct if all are in lower case                
    if lower_street.match(v):
        for i,  v1 in enumerate(vArr):
            v1 = v1.replace(v1[:1], v1[:1].upper())
            vArr[i] = v1
                
        v = " ".join(vArr)

    return v
    
if __name__ == "__main__":
    # NOTE: if you are running this code on your computer, with a larger dataset, 
    # call the process_map procedure with pretty=None. The pretty=True option adds 
    # additional spaces to the output, making it significantly larger.
    process_map('qc.osm')
    print "End of process"
