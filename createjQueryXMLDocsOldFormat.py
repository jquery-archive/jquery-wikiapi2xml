#!/usr/bin/python

"""
createjQueryXMLDocs.py
David Serduke

Python script to convert the jQuery wiki documentation to an XML doc
"""

import re
import cgi
# import cgitb; cgitb.enable()
import sys
import urllib
from xml.dom import minidom

# debug assist function
def debugAssist(msg = "", data = ""):
  if data != "":
    print data
  raw_input(msg);

def printdebug(msg):
  print >>sys.stderr, msg
  # print msg

# class to create static functions
class Callable:
  def __init__(self, func):
    self.__call__ = func;

# handle passed in parameters
class Options:
  def __init__(self):
    form = cgi.FieldStorage()

    self.exporterUrl = "http://docs.jquery.com/Special:Export";
    self.startingUrl = "API"
    self.version = "1.2"
    self.timestamp = "0"
    self.parseOptions(form)

  def parseOptions(self, form):
    for key in form.keys():
      if key == "start":
        self.startingUrl = form.getvalue(key);
      elif key == "exporter":
        self.exporterUrl = form.getvalue(key);
      elif key == "version":
        self.version = form.getvalue(key);

  def url(self, url):
    return self.exporterUrl + "/" + url

class XMLPage:
  def __init__(self, url, header = "Unheadered"):
    self.load(url)
    self.url = url
    self.header = header

  def load(self, url):
    url = opts.url(url)
    printdebug("Loading: " + url)
    try:
      u = urllib.urlopen(url)
      self.rawData = u.read()
      self.doc = minidom.parseString(self.rawData)
    
      self.title = self.get("title")
      self.timestamp = self.get("timestamp")
      self.wiki = self.get("text")
    except:
      self.wiki = ""
      printdebug("Error loading/parsing '" + url + "'")
      return

    if (opts.timestamp < self.timestamp):
      opts.timestamp = self.timestamp

    # handle a redirect immediately, url and header will be saved from the initial call
    # example "#redirect [[API/1.2/Selectors]]
    if re.search(r"\#redirect", self.wiki, re.IGNORECASE):
      printdebug("Redirected...")
      m = re.search(r"\#redirect \[\[(?P<dir>.*)\]\]", self.wiki, re.IGNORECASE)
      self.load(m.group("dir"))

  def get(self, tag):
    wikiNode = self.doc.getElementsByTagName(tag)[0]
    return wikiNode.childNodes[0].nodeValue

# node is the base abstract class for each item in the tree
class Node:
  def __init__(self, page):
    self.page = page
    self.children = []
    self.parse()

  def isPage(page):
    return page != None
  isPage = Callable(isPage)
    
  # figure out what type of page it is and return the appropriate Node subclass
  def factory(page):
    if Method.isPage(page):
      printdebug("'" + page.url + "' is a Method of " + page.header)
      return Method(page)
    if APIList.isPage(page):
      printdebug("'" + page.url + "' is an APIList of " + page.header)
      return APIList(page)
    if API.isPage(page):
      printdebug("'" + page.url + "' is an API of " + page.header)
      return API(page)
    printdebug("'" + page.url + "' is unknown")
    return None
  factory = Callable(factory)
    
  # the default parse method is to find more children, overwrite if necessary
  def parse(self):
    header = "Unheadered"
    # use regular expression for each Node subclass to find its children
    iter = self.getIterForChildren()
    if (iter == None):
      printdebug("Couldn't find any matches in " + self.page.title)
      return
    # loop through each child (or header) to recursively create the children
    for m in iter:
      url = m.group("url")
      h = m.group("header")
      if h != None:
        header = h
      if url != None:
        page = XMLPage(url, header)
        self.children.append(Node.factory(page))

  def getIterForChildren(self):
    return None

# the following Node subclasses are based on page types located in the wiki
# more can be created as necessary.  if a new one is created, an extra check
# will have to be added to Node.factory()
class API(Node):
  # example "* [[Core|jQuery Core]] ...
  def isPage(page):
    return re.search(r"\* \[\[", page.wiki)
  isPage = Callable(isPage)

  def getIterForChildren(self):
    return re.finditer(r"\* \[\[(?P<url>.+?)\|(?P<header>.+?)\]\]", self.page.wiki)

  def exportXML(self, doc, parent):
    for child in self.children:
      if (child != None):
        child.exportXML(doc, parent)

class APIList(Node):
  # example {{APIList|{{APIListHeader|Basics}} {{:Selectors/id}} ...
  def isPage(page):
    return re.search(r"\{\{APIList\|", page.wiki)
  isPage = Callable(isPage)

  def getIterForChildren(self):
    return re.finditer(r"\{\{\:(?P<url>.+?)\}\}|\{\{APIListHeader\|(?P<header>.+?)\}\}", self.page.wiki)

  def exportXML(self, doc, parent):
    node = doc.createElement("cat")
    node.setAttribute("value", self.page.url) 
    parent.appendChild(node)
    for child in self.children:
      if (child != None):
        child.exportXML(doc, node)

class Method(Node):
  def __init__(self, page):
    self.parts = []
    self.num = 0
    Node.__init__(self, page)

  # example {{APIHeader| ...
  def isPage(page):
    return re.search(r"\{\{APIHeader\|", page.wiki)
  isPage = Callable(isPage)

  def findNextSection(self):
    return re.search(r"\{\{(?P<type>API+.*?)\s*\|", self.getWiki())

  # the class has no children so override parse to find the important info
  def parse(self):
    self.index = 0
    m = self.findNextSection()
    while m != None:
      self.index += m.end() - 1 # minus 1 to point at the pipe
      try:
        func = eval("self.handle" + m.group("type"))
      except:
        func = None
      else:
        self.index += func()
        
      m = self.findNextSection()

  def getWiki(self):
    return self.page.wiki[self.index:]

  def getCodeReplacement(self, str):
    m = re.match("\{\{Code\|(?P<dir>.+?)\|(?P<replacement>.+?)\}\}", str)
    return m

  def getPartName(self, str):
    m = re.match("\|(?P<name>.+?)\=", str)
    return m

  def parseParts(self, section):
    i = 0
    optionNames = [ "name", "type", "desc", "default" ];
    optionCount = 0
    name = None
    value = None
    str = self.getWiki()
    isNowiki = False # pass on things inside a <nowiki>...</nowiki>
    isInsideSq = False # pass on things inside [[...]]

    self.num += 1

    while str[i] == "|":
      if section == "option":
        # special case for starting option sections since they are different
        name = optionNames[optionCount]
        optionCount += 1
        value = ""
        i += 1
      else:
        # handle starting entry and example sections here
        m = self.getPartName(str[i:])
        if m == None:
          name = None
          # go find the next part
          i += 1
          while str[i] != "|" and str[i:i+2] != "}}":
            i += 1
        else:
          name = m.group("name")
          value = ""
          i += m.end()

      # find the next pipe
      while isNowiki or isInsideSq or (str[i] != "|" and str[i:i+2] != "}}"):
        # debugAssist("Enter...", "'" + str[i:i+50] + "'")
        if str[i:].startswith("<nowiki>"):
          i += 8
          isNowiki = True
          continue
        if str[i:].startswith("</nowiki>"):
          i += 9
          isNowiki = False
          continue
        if str[i:].startswith("[["):
          isInsideSq = True
        if str[i:].startswith("]]"):
          isInsideSq = False

        if str[i:i+2] == "{{":
          m = self.getCodeReplacement(str[i:])
          if m != None and value != None:
            #at some point perhaps handle <dir> from re
            value += m.group("replacement")
            i += m.end()
          else:
            # delete curly brace templates we don't understand for now
            while str[i:i+2] != "}}":
              # value += str[i]
              i += 1
            # value += "}}"
          continue

        if value != None:
          value += str[i]
        i += 1

      if value != None:
        if len(value) > 0 and value[-1] == '\n':
          value = value[:-1]
        # printdebug(section + '=> "' + name + '" = "' + value + '"')
        self.parts.append( { 'section':section, 'num':self.num, 'name':name, 'value':value } )

    return i

  def handleAPIEntry(self):
    length = self.parseParts("entry")
    return length
  
  def handleAPIExample(self):
    length = self.parseParts("example")
    return length

  def handleAPIOption(self):
    length = self.parseParts("option")
    return length

  def exportXML(self, doc, parent):
    entry = { 'num':0 }
    arg = { 'num':0, 'index':None, 'node':None }
    option = { 'num':0, 'node':None }
    example = { 'num':0, 'node':None }

    # special case for when there was an error retrieving document
    if self.page.wiki == "":
      return;

    printdebug("Exporting '" + self.page.url + "'") 

    for part in self.parts:
      # printdebug(" -- Section '" + part['section'] + "' part '" + part['name'] + "'") 
      if part['section'] == "entry":
        # handle method entry
        if entry['num'] != part['num']:
          # if we have a bran new entry (not a loop through of the same entry)
          entry['num'] = part['num']
          arg['num'] = 0
          arg['index'] = None
          node = doc.createElement("method")
          node.setAttribute("timestamp", self.page.timestamp)
          n = doc.createElement("header")
          n.appendChild(doc.createTextNode(self.page.header))
          node.appendChild(n)
          parent.appendChild(node)

        # set various attributes to the method node
        if part['name'] == "name" or part['name'] == "cat" or part['name'] == "author":
          node.setAttribute(part['name'], part['value'])
        elif part['name'] == "return":
          # turn return in to type (for backwards compatibility)
          node.setAttribute("type", part['value'])
        elif part['name'] == "type":
          # turn type in to is (to avoid a conflict with the type/return value)
          node.setAttribute("is", part['value'])
        elif part['name'] == "desc":
          # turn desc in to short (for backwards compatibility)
          node.setAttribute("short", part['value'])

        elif part['name'] == "longdesc":
          # turn longdesc in to desc (for backwards compatibility)
          n = doc.createElement("desc")
          n.appendChild(doc.createTextNode(part['value']))
          node.appendChild(n)

        elif part['name'].startswith("arg"):
          # handle arguments
          m = re.match(r"arg(?P<index>.)(?P<def>.*)", part['name'])
          if arg['num'] != part['num'] or arg['index'] != m.group("index"):
            # if this is a bran new argument, make a new node
            arg['num'] = part['num']
            arg['index'] = m.group("index")
            arg['node'] = doc.createElement("params")
            node.appendChild(arg['node'])
          if m.group("def") == "":
            arg['node'].setAttribute("name", part['value'])
          elif m.group("def") == "type":
            arg['node'].setAttribute("type", part['value'])
          elif m.group("def") == "optional":
            arg['node'].setAttribute("optional", part['value'])
          elif m.group("def") == "desc":
            n = doc.createElement("desc")
            n.appendChild(doc.createTextNode(part['value']))
            arg['node'].appendChild(n)

        else:
          # anything else that is in there append it to as its own node
          n = doc.createElement(part['name'])
          n.appendChild(doc.createTextNode(part['value']))
          node.appendChild(n)
          
      elif part['section'] == "option":
        # handle method entry options
        if option['num'] != part['num']:
          # if we have a bran new option (not a loop through of the same entry)
          option['num'] = part['num']
          option['node'] = doc.createElement("options")
          node.appendChild(option['node'])

        if part['name'] != "desc":
          option['node'].setAttribute(part['name'], part['value'])
        else:
          n = doc.createElement(part['name'])
          n.appendChild(doc.createTextNode(part['value']))
          option['node'].appendChild(n)
          
      elif part['section'] == "example":
        # handle method entry example
        if example['num'] != part['num']:
          # if we have a bran new example (not a loop through of the same entry)
          example['num'] = part['num']
          example['node'] = doc.createElement("examples")
          node.appendChild(example['node'])

        if (part['name'] == "html"):
          # turn html in to before (for backwards compatibility)
          n = doc.createElement("before")
        else:  
          n = doc.createElement(part['name'])
        n.appendChild(doc.createTextNode(part['value']))
        example['node'].appendChild(n)
      
opts = Options()

def main():
  #print "Content-Type: text/html\n"

  page = XMLPage(opts.startingUrl)
  nodeTree = Node.factory(page)
  impl = minidom.getDOMImplementation()
  doc = impl.createDocument(None, "docs", None)
  doc.documentElement.setAttribute("version", opts.version)
  doc.documentElement.setAttribute("timestamp", opts.timestamp)
  nodeTree.exportXML(doc, doc.documentElement)
  print doc.toxml()

if (__name__ == '__main__'):
  main()

