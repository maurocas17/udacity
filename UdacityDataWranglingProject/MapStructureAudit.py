#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
The purpose of this class is to get a overall view of the OSM xml structure.
Below are the actions/processes taken:
    1.  All the attributes of the node, way and relation element,
        whether they conform to the expected data type.
    2.  Checks whether k has problem characters.
    3.  Checks whether k and v is empty
    4.  Checks whether node references in way tag has corresponding nodes.
    5.  Keeps track of all the element/tags, print their total at the end
    6.  Print out the total unique users/contributors
    7.  Saves the k and v attribute values in a tagKV.pickle file.  
        This file is an input to MapContentAudit.py for further evaluation
        

Output of this class when evaluating qc.osm

*******************INVALID ATTRIBUTE VALUES / DATA TYPE**********************
[{'k': 'Holdap', 'node': 'tag', 'v': ''},
 {'k': 'amenity', 'node': 'tag', 'v': '\n'},
 {'k': 'street signs', 'node': 'tag', 'v': 'Jeepney Stop'},
 {'k': 'street signs', 'node': 'tag', 'v': 'No Parking'},
 {'k': 'street signs', 'node': 'tag', 'v': 'No Blowing of Horns'},
 {'k': 'street signs', 'node': 'tag', 'v': 'No Parking'},
 {'k': 'street signs', 'node': 'tag', 'v': 'Magsaysay cor Katipunan'},
 {'k': 'street signs', 'node': 'tag', 'v': 'Jeepney Stop'},
 {'k': 'street signs', 'node': 'tag', 'v': 'Jeepney Stop'},
 {'k': 'street signs', 'node': 'tag', 'v': 'T.M. Kalaw cor Quirino'},
 {'k': 'street signs', 'node': 'tag', 'v': 'Jeepney Stop'},
 {'k': 'street signs', 'node': 'tag', 'v': 'Jeepney Stop'},
 {'k': 'street signs', 'node': 'tag', 'v': 'Velasquez cor Quirino'},
 {'k': 'street signs', 'node': 'tag', 'v': 'Jeepney Stop'},
 {'k': 'street signs', 'node': 'tag', 'v': 'Lakandula cor E. Delos Santos'},
 {'k': 'street signs', 'node': 'tag', 'v': 'Lakandula cor E. Delos Reyes'},
 {'k': 'street signs', 'node': 'tag', 'v': 'Jeepney Stop'},
 {'k': 'Partner In Ministry',
  'node': 'tag',
  'v': 'Polo Methodist Church Of Valenzuela'},
 {'k': 'House No.', 'node': 'tag', 'v': '1'},
 {'k': 'MR.QUICKIE', 'node': 'tag', 'v': 'MR. QUICKEE'},
 {'k': 'Years in Business', 'node': 'tag', 'v': '50+ Years'},
 {'k': 'building', 'node': 'tag', 'v': ''},
 {'k': 'building', 'node': 'tag', 'v': ''},
 {'k': 'addr:street', 'node': 'tag', 'v': ''},
 {'k': 'fee', 'node': 'tag', 'v': ''},
 {'k': 'Adjacent To',
  'node': 'tag',
  'v': 'St. Stephen Ecumenical Learning School'}]

*******************UNKNOWN  NODE REFERENCE**********************
set([])

*******************TAG/ELEMENTS**********************
{'bounds': 1,
 'member': 12658,
 'meta': 1,
 'nd': 1111882,
 'node': 888720,
 'note': 1,
 'osm': 1,
 'relation': 942,
 'tag': 348762,
 'way': 192076}

no. of unique users 934

Writing tagKV.pickle for K and V attributes

         
"""


import xml.etree.ElementTree as ET
import pprint
import re
import pickle

problemchars = re.compile(r'[=\+/&<>;\'"\?%#$@\,\. \t\r\n]')

from datetime import datetime
def isTimestamp(val):
    try:
        datetime.strptime(val, "%Y-%m-%dT%H:%M:%SZ")
        return True
    except:
        return False
    
def isANumber(val):
    try:
        int(val)
        return True
    except:        
        return False
    
def isAFloat(val):
    try:
        float(val)
        return True
    except:
        return False

def auditMap(filename):
        tags = {}
        users = {}
        nodeIds = set()
        unknownNodeIds = set()
        tagKV = {}
        invalids = []
        
        for _, element in ET.iterparse(filename):
            
            #keep track of tags
            tag_ctr = tags.get(element.tag,0)
            tags[element.tag] = tag_ctr + 1
            
            #validate data type            
            eInvalid = {}
            eInvalid["node"] = element.tag
            if element.tag in ["node", "way", "relation"]:
                id1 = element.attrib["id"]
                lat = element.attrib.get("lat", None)
                lon = element.attrib.get("lon", None)
                ver = element.attrib["version"]
                timestamp = element.attrib["timestamp"]
                changeset = element.attrib["changeset"]
                uid = element.attrib["uid"]
                
                #keep track of users
                n = users.get(uid, 0)
                users[uid] = n + 1
                
                if (isANumber(id1)  == False or isANumber(ver)  == False or isTimestamp(timestamp) == False or isANumber(changeset)  == False
                    or isANumber(uid)  == False or len(element.attrib["user"].strip()) == 0):
                    eInvalid.update(element.attrib)
                elif (element.tag == "node" and (isAFloat(lat)  == False or  isAFloat(lon) == False)):
                    eInvalid.update(element.attrib)
                elif element.tag == "node": nodeIds.add(id1)
                
            elif element.tag == "nd":
                if element.attrib["ref"] not in nodeIds: unknownNodeIds.add(element.attrib["ref"])
                
            elif element.tag == "tag":
                k = element.attrib["k"].strip()
                v = element.attrib["v"].strip()
                 
                #check if k has problem characters?
                if problemchars.search(k): eInvalid.update(element.attrib)
                
                elif (len(k) == 0 or len(v) == 0):
                    eInvalid.update(element.attrib)
                else:
                    values = tagKV.get(k, set())
                    values.add(v)
                    tagKV[k] = values
                    
                    """
                    kArr = k.split(":")
                    if (len(kArr)==2 and kArr[0] in ["addr",""]):
                        if kArr[1] == "street": streets.add(v)
                        if kArr[1] == "postcode":
                            totalPostalCode.add(v)
                            if validPostCode(v) == False: invalidPostalCodes.add(v)
                    elif kArr[0] == "postal_code":
                        totalPostalCode.add(v)
                        if validPostCode(v) == False: invalidPostalCodes.add(v)
                    """
            if len(eInvalid) > 1: invalids.append(eInvalid)
        
        print "\n*******************INVALID ATTRIBUTE VALUES / DATA TYPE**********************"                
        pprint.pprint(invalids)
        
        print "\n*******************UNKNOWN  NODE REFERENCE**********************"                
        pprint.pprint(unknownNodeIds)
        
        print "\n*******************TAG/ELEMENTS**********************"                
        pprint.pprint(tags)
        
        
        print "\nno. of unique users", len(users)

        #tagKV.pickle will be further evaluated in MapContentAudit.py        
        print "\nWriting tagKV.pickle for K and V attributes"
        with open("tagKV.pickle", "wb") as output:
            pickle.dump(tagKV, output)
        
        """        
        import StreetInspect
        StreetInspect.auditStreet(streets)
        
        print "Total Postal Code: ", len(totalPostalCode)
        print "\nTotal Invalid Postal Codes: ", len(invalidPostalCodes)
        pprint.pprint(invalidPostalCodes)
        """
    

if __name__ == "__main__":
    auditMap("qc.osm")
