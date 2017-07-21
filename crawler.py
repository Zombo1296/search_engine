#!/usr/local/bin/python2.7
__author__ = "Bohan Zhang"
__copyright__ = "Copyright (C) 2017 Bohan Zhang"
__license__ = "MIT License"
__version__ = "1.0"

from HTMLParser import HTMLParser  
from bs4 import BeautifulSoup
import urllib2 
import urllib
import urlparse
import re
import robotparser

INDEX_DIR = "IndexFiles.index"

import sys, os, lucene, threading, time
from datetime import datetime

from java.nio.file import Paths
from org.apache.lucene.analysis.miscellaneous import LimitTokenCountAnalyzer
from org.apache.lucene.analysis.standard import StandardAnalyzer
from org.apache.lucene.analysis import CharArraySet
from org.apache.lucene.document import Document, Field, FieldType
from org.apache.lucene.index import \
    FieldInfo, IndexWriter, IndexWriterConfig, IndexOptions
from org.apache.lucene.store import SimpleFSDirectory

#this function is for removing tags in webpage text
def removeTag(file):
	a = file.read()
	soup = BeautifulSoup(a)
	text = soup.get_text().encode("utf-8")
	return text


			
# a class called LinkParser that inherits some
# methods from HTMLParser which is why it is passed into the definition
class LinkParser(HTMLParser):

	# This is a function that HTMLParser normally has
	# but we are adding some functionality to it
	def handle_starttag(self, tag, attrs):
		if tag == 'a':
			for (key, value) in attrs:
				if key == 'href':
					newUrl = value
					if domain2 in newUrl and newUrl not in hashtable2:
						if rp2.can_fetch("*",newUrl):
							# And add it to our colection of links:
							self.links = self.links + [newUrl]
							hashtable2[newUrl]=1

	# This is a new function that we are creating to get links
	def getLinks(self, url,domain,hashtable,rp):
		global domain2
		global hashtable2
		global rp2
		domain2 = domain
		hashtable2=hashtable
		rp2=rp
		self.links = []
		self.baseUrl = url
		response = urllib2.urlopen(url)
		htmlBytes = response.read()
		htmlString = htmlBytes.decode("utf-8")
		self.feed(htmlString)
		return htmlString, self.links,hashtable2

	#create hashtable
	def createHashTable(self,table):
		global hashtable
		hashtable=table

#main function for building search engine
def BuildSearchEngine(start, maxPages,domain,first):  
	#only initiate VM if it's the first being called
	if first == True:
		lucene.initVM(vmargs=['-Djava.awt.headless=true'])
	print ('lucene'), lucene.VERSION
	if not os.path.exists("IndexFiles.index"):
		os.mkdir("IndexFiles.index")
	store = SimpleFSDirectory(Paths.get("IndexFiles.index"))
	config = IndexWriterConfig(StandardAnalyzer(StandardAnalyzer.STOP_WORDS_SET))
	#if first time being called, create new index, otherwise only append new pages into old index
	if first == True:
		config.setOpenMode(IndexWriterConfig.OpenMode.CREATE)
	else:
		config.setOpenMode(IndexWriterConfig.OpenMode.APPEND)
	writer = IndexWriter(store, config)
	
	#configure settings for pages being saved
	t1 = FieldType()
	t1.setStored(True)
	t1.setTokenized(False)
	t1.setIndexOptions(IndexOptions.DOCS_AND_FREQS)
	t2 = FieldType()
	t2.setStored(False)
	t2.setTokenized(True)
	t2.setStoreTermVectors(True)
	t2.setStoreTermVectorOffsets(True)
	t2.setStoreTermVectorPositions(True)
	t2.setIndexOptions(IndexOptions.DOCS_AND_FREQS_AND_POSITIONS_AND_OFFSETS)
	
	pagesToVisit = [start]
	hashtable=dict()
	hashtable[start]=1
	numberVisited = 0
	rp = robotparser.RobotFileParser()
	robotFileLocation = "http://www."+domain+"/robots.txt"
	rp.set_url(robotFileLocation)
	rp.read()
	# The main loop. Create a LinkParser and get all the links on the page.
	while numberVisited < maxPages and pagesToVisit != []:
			numberVisited = numberVisited +1
			# Start from the beginning of our collection of pages to visit:
			url = pagesToVisit[0]
			pagesToVisit = pagesToVisit[1:]
		try:
			print(numberVisited, "Visiting:", url)
			parser = LinkParser()
			data, links,hashtable = parser.getLinks(url,domain,hashtable,rp)
			# Add the pages that we visited to the end of our collection
			# of pages to visit:
			print(" **Success!**")
			path = "files/a.html"
			urllib.urlretrieve(url,path)
			file = open("files/a.html")
			contents = removeTag(file);
			file.close()
			file = open("files/a.html","w")
			file.write(contents)
			file.close()
			file = open("files/a.html")
			contents = file.read()
			file.close()
			doc = Document()
			doc.add(Field("name", "a.html", t1))
			doc.add(Field("path", "files", t1))
			#index the url
			doc.add(Field("url", url, t1))
			if len(contents) > 0:
				doc.add(Field("contents", contents.decode("utf-8").replace(u"\u2019","'").replace(u"\u2018","'").replace(u"\ufe0f","'").replace(u"\u20e3","'"), t2))
			else:
				print ("warning: no content in %s") % filename
			writer.addDocument(doc)
			pagesToVisit = pagesToVisit + links
		except Exception,e:
			print Exception,":",e
			print(" **Failed!**")
	writer.commit()
	writer.close()

#for the first call of the BuildSearchEngine, the last argument must be True
#if not the first call, the last argument must be False
#first argument is starting page,second is the number of pages to collect, third is the restriction domain,last indicates if it's the first time to call the function	
BuildSearchEngine("http://und.edu",100,"und.edu",True)
BuildSearchEngine("http://store.steampowered.com",100,"steampowered.com",False)
BuildSearchEngine("http://www.kfc.com",100,"kfc.com",False)
BuildSearchEngine("http://www.apple.com",100,"apple.com",False)
BuildSearchEngine("http://www.nike.com",100,"nike.com",False)
