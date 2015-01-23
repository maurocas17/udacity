#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
    The purpose of this class is to identify possible problems for the
    k and v attribute of the tag element.
    
    Below are the checks done:
    1.  If k=="street", check v for if:
            a.  has problem words like corner, Along, etc
            b.  has characters like comma
            c.  are all in lower case
            d.  might be duplicate
    2.  If postcode, if it's a valid Quezon City postcode
    
    Note that only k attributes that has up to two identifiers like "addr:street" 
    is checked, the rest are ignored.
    
    All are written to mapContentAudit.csv with the following headers: Comment, Tag K, Tag V
    Sample:
    Comment,            Tag K,        Tag Value
    Spelling Check,       street,        15th
    Duplicate,            street,        15th Avenue
    Has problem words,    street,        "4th Avenue, corner C. Cordero"
    Has problem chars,    street,        "537 EDSA, Cubao"

    The mapContentAudit.csv is copied to mapContentAudit_WithCorrections.csv
    The records are checked manually.  
    A new column "Correction" is added to mapContentAudit_WithCorrections.csv.
        and corrections for each v value are entered into this column.
        
    Note that corrections are only done for street and city.
    The correction file is use as input to PrepForDB
    
    

"""
import xml.etree.ElementTree as ET
import re
import pickle
import csv

streetduplicate = {
                   u'Ara\xf1eta AVenue': "Araneta Avenue"
                   ,'C.M. Recto Ave.': "Claro M. Recto Ave."
                   ,"Jose Laurel Street": 'Jose P. Laurel'
                   ,"Kabisang Imo": "Kabesang Imo"
                   ,"L. SUmulong Circle": "Sen. L. Sumulong Memorial Circle"
                   ,"Sen L Sumulong Mem Circle": "Sen. L. Sumulong Memorial Circle"
                   ,'Sen L Sumulong Mem Circle cor M L Quezon St': "Sen. L. Sumulong Memorial Circle"
                   ,"F Dela Rosa":'F. B. dela Rosa'
                   ,"Jose Laurel Street": "Jose P. Laurel"
                   ,"Luna Mercias":"Luna Mencias"
                   ,"Mac Arthur Hiway": "Mac Arthur Highway"
                   ,"Marcos Hoighway": "Marcos Highway"
                   ,"Nabigla Secod":"Nabigla Seconary Link"
                   ,"Orrigas Ave Ext": "Ortigas Avenue Extension"
                   ,"Ortigas Ave. Ext.": "Ortigas Avenue Extension"
                   ,"Quirina Hiway": "Quirino Highway"
                   ,'Quirino Hiway': "Quirino Highway" 
                   ,'Quirno Highway': "Quirino Highway"
                   ,"Santola Road": "Santolan Road"
                   ,'Sen. Jose Vera': 'Sen. Jose O. Vera'
                   ,'Sen. Lorenzo Sumulong Memorial Circle': 'Sen. L. Sumulong Memorial Circle'
                   ,'Sumulong Circle':'Sen. L. Sumulong Memorial Circle'
                   ,'T.M. Kalaw': 'Teodoro M. Kalaw Sr. Avenue'
                   ,'Talitip Road': 'Taliptip Road'
                   ,"United Avenue": "United Nations Avenue"
                   ,"Tomast Morato": "Tomas Morato"
                   , u'Espa\xf1a': "Espana"
                   , u'Espa\xf1a Boulevard': "Espana"
                   , "Epifanio de los Santos Avenue": "EDSA"
                   , "Epifanio Delos Santos Avenue": "EDSA"
                   , "Epifanio de Los Santos Avenue": "EDSA"
                   }      
problemchars = re.compile(r'[=\+/&<>;\'"?%#$@,]')
problemwords = re.compile("([C|c]or(ner)?)|(Along)|(Infront)|(Intersection)|([S|s]ubdivision)|(Intramuros)|(Mall)|(Department)")

def auditTag(filename):
    tags = {}
    if filename == "tagKV.pickle":
        with open(filename, "rb") as ifile:
            tags = pickle.load(ifile)
    else:    
        with open(filename, "r") as osm_file:
            for _, elem in ET.iterparse(osm_file):
                if elem.tag in ["node", "way"]:
                    for elem1 in elem.iter("tag"):
                        k = elem1.attrib["k"].strip()
                        v = elem1.attrib["v"].strip()
                        tag = tags.get(k, set())
                        tag.add(v)
                        tags[k] = v
    
    with open("mapcontentAudit.csv", "wb") as csvfile:
        fieldnames = ["Comment", "Tag K", "Tag Value"]
        writer = csv.DictWriter(csvfile, fieldnames)
        writer.writeheader()
        for k, vset in tags.iteritems():
            print "\nchecking values for k: ", k
            k = k.split(":")
            if len(k) > 2:
                print "\nignoring k, for now we are only checking up to 2 identifier"
                continue
            
            row = {}
            kId = k[1] if len(k) == 2 else k[0]
            prev = None
            for v in sorted(vset, key=lambda v: getKey(kId, v)):
                comment = ""
                aNumber = False
                if kId == "street": 
                    comment = auditStreet(v)
                elif kId == "postcode": 
                    comment = validPostCode(v)
                    aNumber = True
                #all are in lower case
                elif v.lower() == v: 
                    aNumber = isANumber(v)
                    if aNumber == False:  comment = "Lower Case"
                
                
                #might be duplicate
                cleanedVal = getKey(kId, v)
                if comment == "" and aNumber == False and prev is not None and cleanedVal.find(prev) > -1:
                    comment = "Duplicate"
                else: prev = cleanedVal
                    
                if aNumber == False and comment == "": comment = "Spelling Check"
                
                row[fieldnames[0]] = comment
                row[fieldnames[1]] = kId
                row[fieldnames[2]] = v

                try:
                    if comment != "":  writer.writerow(row)
                except:
                    print "Ignored: ", row

def getKey(k, v):
    value = v
    if k.find("street") > -1:
        value = streetduplicate.get(v,v)
        
    value = value.replace(".","").replace(" ","").lower()
    return value
    
        
def validPostCode(postcode):
    try:
        postnumber = int(postcode)
        if postnumber < 1100 or postnumber >= 1200: return "Not a Quezon City postcode"
        else: return ""
    except:
        return "Not a Number"
    

def isANumber(val):
    try:
        int(val)
        return True
    except:        
        return False

def auditStreet(street):
    comment = ""
    if problemwords.search(street):
        comment = "Has problem words"
    elif problemchars.search(street): 
        comment = "Has problem chars"

    return comment
    
        

if __name__ == "__main__":
    auditTag("tagKV.pickle")
