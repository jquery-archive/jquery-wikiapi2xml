#!/usr/bin/python2.4

"""
createjQueryXMLDocs.py
David Serduke
Version 0.1.5
Last Modified: Dec. 18, 2007

Python script to convert the jQuery wiki documentation to an XML doc
"""

import re
import cgi
# import cgitb; cgitb.enable()
import sys
import urllib
from xml.dom import minidom

# debug assist function
# def debugAssist(msg = "", data = ""):
#   if data != "":
#     print data
#   raw_input(msg)

def printdebug(msg):
  if opts.verbose != "false" and infoNode != None:
    if opts.debug == "false":
      msgNode = doc.createElement("msg")
      msgNode.appendChild(doc.createTextNode(msg))
      infoNode.appendChild(msgNode)
    else:
      print msg
      # print >>sys.stderr, msg

# class to create static functions
class Callable:
  def __init__(self, func):
    self.__call__ = func

# handle passed in parameters
class Options:
  def __init__(self):
    form = cgi.FieldStorage()

    self.help = "false"
    self.supressContentType = "false" 
    self.startingUrl = "API"
    self.exporterUrl = "http://docs.jquery.com/Special:Export"
    self.forLinksUrl = ""
    self.version = ""
    self.convertLinks = "html"
    self.verbose = "false" 
    self.debug = "false"
    self.timestamp = "0"
    self.parseOptions(form)

  def parseOptions(self, form):
    keys = form.keys()
    if len(keys) == 0:
      self.help = "true"
    for key in keys:
      if key == "help":
        self.help = form.getvalue(key)
      elif key == "supresscontenttype":
        self.supressContentType = form.getvalue(key)
      elif key == "start":
        self.startingUrl = form.getvalue(key)
      elif key == "exporter":
        self.exporterUrl = form.getvalue(key)
      elif key == "forlinksurl":
        self.forLinksUrl = form.getvalue(key)
      elif key == "version":
        self.version = form.getvalue(key)
      elif key == "convertlinks":
        self.convertLinks = form.getvalue(key)
      elif key == "verbose":
        self.verbose = form.getvalue(key)
      elif key == "debug":
        self.debug = form.getvalue(key)

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
      printdebug(str(sys.exc_info()[0]) + ":" + str(sys.exc_info()[1]))
      return

    if (opts.timestamp < self.timestamp):
      opts.timestamp = self.timestamp

    # handle a redirect immediately, url and header will be saved from the initial call
    # example "#redirect [[API/1.2/Selectors]]
    if re.search(r"\#redirect", self.wiki, re.IGNORECASE):
      m = re.search(r"\#redirect \[\[(?P<dir>.*)\]\]", self.wiki, re.IGNORECASE)
      printdebug("Redirected to... " + m.group("dir"))
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

  def exportXML(self, parent):
    printdebug("Exporting '" + self.page.url + "'") 
    for child in self.children:
      if (child != None):
        child.exportXML(parent)

class APIList(Node):
  # example {{APIList|{{APIListHeader|Basics}} {{:Selectors/id}} ...
  def isPage(page):
    return re.search(r"\{\{APIList\|", page.wiki)
  isPage = Callable(isPage)

  def getIterForChildren(self):
    return re.finditer(r"\{\{\:(?P<url>.+?)\}\}|\{\{APIListHeader\|(?P<header>.+?)\}\}", self.page.wiki)

  def exportXML(self, parent):
    global subcat

    printdebug("Exporting '" + self.page.url + "'") 
    node = doc.createElement("cat")
    node.setAttribute("value", self.page.url) 
    parent.appendChild(node)
    # new cat so reset subcat
    subcat = { 'name':'', 'node':None }
    printdebug("Reset subcat to None")
    for child in self.children:
      if (child != None):
        child.exportXML(node)

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

  def getCodeLink(self, str):
    m = re.match(r"\{\{Code\|(?P<link>.+?)\|(?P<name>.+?)\}\}", str)
    return m

  def getSquareBracketLink(self, str):
    m = re.match(r"\[\[(?P<link>.+?)(\|(?P<name>.+?))?\]\]", str)
    return m

  def getPartName(self, str):
    m = re.match(r"\|(?P<name>.+?)\=", str)
    return m

  def parseParts(self, section):
    i = 0
    optionNames = [ "name", "type", "desc", "default" ]
    optionCount = 0
    name = None
    value = None
    str = self.getWiki()
    isNowiki = False # pass on things inside a <nowiki>...</nowiki>

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
      while isNowiki or (str[i] != "|" and str[i:i+2] != "}}"):
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
          m = self.getSquareBracketLink(str[i:])
          mlink = m.group("link")
          mname = m.group("name")
          if mname == None or mname == "":
            mname = mlink
          p = re.compile(r" ")
          mlink = p.sub("_", mlink)
          mlink = opts.forLinksUrl + mlink
          value += "[[" + mlink + "|" + mname + "]]"
          i += m.end()
          continue
        if str[i:i+2] == "{{":
          m = self.getCodeLink(str[i:])
          if m != None and value != None:
            #at some point perhaps handle <dir> from re
            # value += "[[" + m.group("link") + "|" + m.group("name") + "]]"
            value += m.group("name")
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
        if opts.verbose == "super":
          printdebug(section + '=> "' + name + '" = "' + value + '"')
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

  def handleAPIOptionExample(self):
    length = self.parseParts("example")
    return length

  def findLink(self, str):
    # search for [[Ajax_Events|Ajax Events]] type wiki links (they were normalized on initial parsing)
    m = re.search(r"\[\[(?P<link>.+?)\|(?P<name>.+?)]\]", str)
    if m == None:
      return None
    return { 'link':m.group("link"), 'name':m.group("name"), 'before':str[:m.start()], 'after':str[m.end():] }

  def parseAndAttachApproriateNodes(self, parent, str):
    i = 0
    result = self.findLink(str)
    # while there are wiki links in the "text node" convert them
    while result != None:
      parent.appendChild(doc.createTextNode(result['before']))
      if opts.convertLinks == "node":
        a = doc.createElement("a")
        a.setAttribute("href", result['link'])
        a.appendChild(doc.createTextNode(result['name']))
        parent.appendChild(a)
      elif opts.convertLinks == "html":
        parent.appendChild(doc.createCDATASection("<a href='" + result['link'] + "'>" + result['name'] + "</a>"))
      else:
        parent.appendChild(doc.createTextNode("[[" + result['link'] + "|" + result['name'] + "]]"))
      
      str = result['after']
      result = self.findLink(str)
    parent.appendChild(doc.createTextNode(str))

  def exportXML(self, parent):
    global subcat
    entry = { 'num':0 }
    arg = { 'num':0, 'index':None, 'node':None }
    option = { 'num':0, 'node':None }
    example = { 'num':0, 'node':None }

    # special case for when there was an error retrieving document
    if self.page.wiki == "":
      return

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
          # create element as 'entry' initially till get a 'type' part then change it
          node = doc.createElement("entry")
          node.setAttribute("timestamp", self.page.timestamp)
          if self.page.header == "Unheadered" and subcat['node'] != None:
            # have left a subcat so reset
            subcat = { 'name':'', 'node':None }
            printdebug("Reset subcat to None")
          ## != "Documentation" because in the wiki some people are using it as a general header
          elif self.page.header != "Unheadered" and self.page.header != "Documentation" and self.page.header != subcat['name']:
            # new subcat so create
            n = doc.createElement("subcat")
            subcat['name'] = self.page.header 
            subcat['node'] = n
            n.setAttribute('value', subcat['name'])
            parent.appendChild(n)
            printdebug("Set subcat to " + subcat['name'])
          # if there is a subcat then append to that, otherwise go right to parent
          if subcat['node'] != None:
            subcat['node'].appendChild(node)
          else:
            parent.appendChild(node)

        # change the tagName of the node based on its type (expect function, selector, or property)
        if part['name'] == "type":
          node.tagName = part['value']

        # set various attributes to the method node
        elif part['name'] == "name" or part['name'] == "cat" or part['name'] == "return":
          node.setAttribute(part['name'], part['value'])

        elif part['name'].startswith("arg"):
          # handle arguments
          m = re.match(r"arg(?P<index>.)(?P<def>.*)", part['name'])
          if arg['num'] != part['num'] or arg['index'] != m.group("index"):
            # if this is a bran new argument, make a new node
            arg['num'] = part['num']
            arg['index'] = m.group("index")
            arg['node'] = doc.createElement("params")
            node.appendChild(arg['node'])
          if m.group("def") == "desc":
            n = doc.createElement("desc")
            self.parseAndAttachApproriateNodes(n, part['value'])
            arg['node'].appendChild(n)
          elif m.group("def") == "":
            arg['node'].setAttribute("name", part['value'])
          else: # type and optional are two known values
            arg['node'].setAttribute(m.group("def"), part['value'])

        else:
          # anything else that is in there append it to as its own node
          n = doc.createElement(part['name'])
          self.parseAndAttachApproriateNodes(n, part['value'])
          node.appendChild(n)
          
      elif part['section'] == "option":
        # handle method entry options
        if option['num'] != part['num']:
          # if we have a bran new option (not a loop through of the same entry)
          option['num'] = part['num']
          option['node'] = doc.createElement("option")
          node.appendChild(option['node'])

        if part['name'] != "desc":
          option['node'].setAttribute(part['name'], part['value'])
        else:
          n = doc.createElement(part['name'])
          self.parseAndAttachApproriateNodes(n, part['value'])
          option['node'].appendChild(n)
          
      elif part['section'] == "example":
        # handle method entry example
        if example['num'] != part['num']:
          # if we have a bran new example (not a loop through of the same entry)
          example['num'] = part['num']
          example['node'] = doc.createElement("example")
          node.appendChild(example['node'])

        n = doc.createElement(part['name'])
        self.parseAndAttachApproriateNodes(n, part['value'])
        example['node'].appendChild(n)
      
opts = None
doc = None
infoNode = None
# global subcat since it's a hack either way
subcat = { 'name':'', 'node':None }

def loadAndDisplayHelp():
  u = urllib.urlopen("http://dev.jquery.com/view/trunk/tools/wikiapi2xml/README")
  text = u.read()
  if opts.supressContentType == "false":
    print "Content-Type: text/plain\n"
  print text

def main():
  global opts, doc, infoNode

  opts = Options()

  if opts.help == "true":
    loadAndDisplayHelp()
    return
  if opts.supressContentType == "false":
    if opts.debug == "false":
      print "Content-Type: text/xml\n"
    else:
      print "Content-Type: text/plain\n"

  impl = minidom.getDOMImplementation()
  doc = impl.createDocument(None, "docs", None)
  if opts.verbose != "false":
    infoNode = doc.createElement("info")
    doc.documentElement.appendChild(infoNode)
  page = XMLPage(opts.startingUrl)
  nodeTree = Node.factory(page)
  doc.documentElement.setAttribute("startdoc", opts.startingUrl)
  doc.documentElement.setAttribute("timestamp", opts.timestamp)
  if opts.version != "":
    doc.documentElement.setAttribute("version", opts.version)
  if nodeTree == None:
    errorNode = doc.createElement("error")
    errorNode.appendChild(doc.createTextNode("Error parsing initial page."))
    doc.documentElement.appendChild(errorNode)
  else:
    nodeTree.exportXML(doc.documentElement)

  if opts.verbose == "false":
    print doc.toxml()
  else:
    print doc.toprettyxml()

if (__name__ == '__main__'):
  main()

