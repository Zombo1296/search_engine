#!/usr/local/bin/python2.7
__author__ = "Bohan Zhang"


import cgi
import cgitb
cgitb.enable(display=1)

print "Content-Type: text/html"
print

INDEX_DIR = "IndexFiles.index"

import sys, os, lucene

from java.nio.file import Paths
from org.apache.lucene.analysis.standard import StandardAnalyzer
from org.apache.lucene.index import DirectoryReader
from org.apache.lucene.queryparser.classic import QueryParser
from org.apache.lucene.store import SimpleFSDirectory
from org.apache.lucene.search import IndexSearcher
from org.apache.lucene.index import IndexReader,Term
from bs4 import BeautifulSoup
from org.apache.lucene.util import BytesRefIterator
from org.apache.lucene.index import TermsEnum
import urllib2
import math
import random

#the function which returns silhouette coefficient, it uses lucene to find all matched documents, then use given k to divide matched documents into k clusters
#then calculate the average silhouette coefficient of all vectors
#k-means is used to cluster documents
#tf*idf is used for creating the vector space
#euclidean distance is used to measure the similarity between each data point and the centroid
def getSilhouette(reader,searcher, analyzer,searchTerm,K):
		#get user's query and initiate some dictionaries
		command = searchTerm
		#for each word, record how many matched documents contains it
		termOccurrence={}
		#inversed document frequency for each word
		idf={}
		#term frequency for each word in each matched document
		tf={}
		#the product of tf and idf for each word in each matched document
		tfidf={}
		#the number of words for each matched document
		docLength={}
		#for each kind of word in each document,record how many times it appeared in the document
		termOccurrenceInADoc={}
		#record every kind of word in matched documents as key, the value of this dictionary doesn't matter
		allWords={}
		
		#parse the user query
		query = QueryParser("contents", analyzer).parse(command)
		scoreDocs = searcher.search(query, 50).scoreDocs
		#the total number of matched documents
		totalDocs = 0

		#for each matched document,calculate its all term's term normalized term frequency
		for scoreDoc in scoreDocs:
			totalDocs = totalDocs+1
			#get url and term vectors of the matched document
			doc = searcher.doc(scoreDoc.doc)
			vectors = reader.getTermVector(scoreDoc.doc,"contents")
			enum = vectors.iterator()
			url = doc.get("url")
			#record the url of matched document, create a nested dictionary for term occurence of a word in a document
			termOccurrenceInADoc[url]={}
			#record the url of matched document, create a nested dictionary for term frequency
			tf[url]={}
			#for each term in matched document, record each term's occurence and calculate the total word count of the document
			for term in BytesRefIterator.cast_(enum):
				term2 = term.utf8ToString()
				#record the term
				allWords[term2]=1
				#increase the termOccurence by one
				if termOccurrence.has_key(term2):
					termOccurrence[term2]=termOccurrence[term2]+1
				else:
					termOccurrence[term2]=1
				dpEnum = enum.postings(None)
				dpEnum.nextDoc()
				#get occurence of the term
				freq = dpEnum.freq()
				#add the occurence of the term into the total word count of the document
				if docLength.has_key(url):
					docLength[url]=docLength[url]+freq
				else:
					docLength[url]=freq
				#record occurence of this term in the according docuement
				termOccurrenceInADoc[url][term2]=freq
			#for each term in each document,divide its occurence by the total length of the document to get the normalized term frequency
			for key in termOccurrenceInADoc[url]:
				tf[url][key]=termOccurrenceInADoc[url][key]/float(docLength[url])
		#calculate idf for each term
		for key in termOccurrence:
			idf[key]=math.log(float(totalDocs)/termOccurrence[key],10)
		#calculate the product of tf and idf for each term in each document
		for key in tf:
			tfidf[key]={}
			for word in allWords:
				if tf[key].has_key(word):
					tfidf[key][word]=tf[key][word]*idf[word]
		k = K
		#this is used to record the attributes of all centroids
		centroids={}
		#this is used to record all urls of each cluster
		clusters={}
		#copy the tfidf dictionary, because I need to delete some keys to make sure I choose different initial centroids
		copy=tfidf.copy()
		#randomly choose k vectors as initial centroid
		for counter in range(1,k+1):
			if len(copy)==0:
				break
			key=random.choice(copy.keys())
			centroids[counter]=tfidf[key].copy()
			clusters[counter]={}
			del copy[key]
		#this dictionary is used to record clusters during last iteration, it will be used to compare to new clusters to judge if clusters changed
		oldClusters = {}
		#I will do at most 100 iterations, if clusters no longer change before 100 iterations, break the loop
		for counter2 in range(1,101):	
			#for each vector, find its closest centroid, put it into the according cluster
			for key in tfidf:
				counter = 1
				#for each centroid, calculte the euclidean distance between it and the vector, find the centroid with shortest eucliden distance
				for centroid in centroids:
					#for the first centroid, simply treat it as closest for now
					if counter == 1:
						closestDistance = 0
						for attribute in tfidf[key]:
							closestDistance=closestDistance+(tfidf[key].get(attribute,0)-centroids[centroid].get(attribute,0))**2
						closestDistance = math.sqrt(closestDistance)
						closestCentroid = centroid
					#for other centroids, check if their euclidean distance is shorter than temporary closest, if yes, replace closest centroid
					else:
						temp = 0
						for attribute in tfidf[key]:
							temp=temp+(tfidf[key].get(attribute,0)-centroids[centroid].get(attribute,0))**2
						temp = math.sqrt(temp)
						if temp < closestDistance:
							closestDistance = temp
							closestCentroid = centroid
					counter = counter+1
				#put the url of document into new cluster, the value of the dictionary doesn't matter
				clusters[closestCentroid][key]=1
			#after finishing calculating new clusters, clean old centroids
			centroids={}
			#for each cluster, calculate the new centroid
			for cluster in clusters:
				docNumber = 0
				#initialize nested dictionary for each cluster's centroid
				centroids[cluster]={}
				#for every vector in a cluster, add them togeter
				for document in clusters[cluster]:
					docNumber = docNumber+1
					for term in allWords:
						centroids[cluster][term]=centroids[cluster].get(term,0)+tfidf[document].get(term,0)
				#if the cluster is not empty, divide the sum of all vectors by the number of vectors, the result is the new centroid
				if docNumber == 0:
					newCentroid=random.choice(tfidf.keys())
					centroids[cluster]=tfidf[newCentroid].copy()
				else:
					for term in allWords:
						centroids[cluster][term]=float(centroids[cluster][term])/docNumber
			#if this is not the first iteration, compare new clusters with old clusters, if they are completely same, break the loop
			if counter2 != 1:
				completelySame = True
				for cluster in clusters:
					for document in clusters[cluster]:
						if oldClusters[cluster].has_key(document) == False:
							completelySame = False
							break
				if completelySame == True:
					break
			#copy every new cluster, compare them with newer clusters of next iteration
			for cluster in clusters:
				oldClusters[cluster] = clusters[cluster].copy()
				clusters[cluster].clear()
		#calculate average silhouette coefficient of all vectors
		silhouette = 0
		numberOfDocuments = 0
		#if no document found or only one cluster is there, treat silhouette as 0
		if len(clusters)<=1:
			return 0
		averageSI = 0
		counter3 = 0
		#for each vector,calculate the average euclidean distance between it and other vectors in the same cluster (I call it ai)
		#and calculate the lowest average euclidean distance between it and other vectors in another cluster (I call it lowestBi)
		#then use ai and lowestBi to calculate silhouette coefficient for each vector
		for key in clusters:
			if len(clusters[key]) != 0:
				for key2 in clusters[key]:
					si = 0
					#if there is only one vector in this cluster, treat this vector's silhouette coefficient as 0
					if len(clusters[key])==1:
						si=0
					else:
						ai=0
						bi={}
						biCounter = {}
						counter1 = 0
						#for other vectors, if they are in the current vector's cluster, add euclidean distance into ai
						#if they are in other cluster, find the cluster, add euclidean distance(value) and cluster(key) into bi
						for otherVector in tfidf:
							if otherVector != key2:
								if clusters[key].has_key(otherVector): 
									euclidean = 0
									for attribute in tfidf[otherVector]:
										euclidean=euclidean+(tfidf[otherVector].get(attribute,0)-tfidf[key2].get(attribute,0))**2
									euclidean = math.sqrt(euclidean)
									ai=ai+euclidean
									counter1 = counter1 + 1
								else:
									thisCluster = 0
									#find which cluster this vector belongs to
									for key3 in clusters:
										if clusters[key3].has_key(otherVector):
											thisCluster = key3
											break
									euclidean = 0
									for attribute in tfidf[otherVector]:
										euclidean=euclidean+(tfidf[otherVector].get(attribute,0)-tfidf[key2].get(attribute,0))**2
									euclidean = math.sqrt(euclidean)
									bi[thisCluster]=bi.get(thisCluster,0)+euclidean
									biCounter[thisCluster]=biCounter.get(thisCluster,0)+1
						ai = ai/float(counter1)
						lowestBi = 0
						counter4 = 1
						#find the lowest average euclidean distance between this vector and other clusters
						for key3 in bi:
							bi[key3]=bi[key3]/float(biCounter[key3])
							if counter4 == 1:
								lowestBi = bi[key3]
							else:
								if bi[key3]<lowestBi:
									lowestBi=bi[key3]
							counter4 = counter4 + 1
						#now we have ai and lowest bi, calculate the silhouette coefficient of this vector
						if ai == 0 or lowestBi == 0:
							si = 0
						else:
							if ai < lowestBi:
								si = 1 - ai/lowestBi
							elif ai == lowestBi:
								si = 0
							else:
								si = lowestBi/ai - 1
					averageSI = averageSI + si
					counter3 = counter3 + 1
		#calculate the average silhouette coefficient of all vectors
		averageSI = averageSI/float(counter3)
		return averageSI

#the function which displays the final results, it uses lucene to find all matched documents, then use given k to divide matched documents into k clusters
#k-means is used to cluster documents
#tf*idf is used for creating the vector space
#euclidean distance is used to measure the similarity between each data point and the centroid		
def run(reader,searcher, analyzer,searchTerm,K):
		#get user's query and initiate some dictionaries
		command = searchTerm
		#for each word, record how many matched documents contains it
		termOccurrence={}
		#inversed document frequency for each word
		idf={}
		#term frequency for each word in each matched document
		tf={}
		#the product of tf and idf for each word in each matched document
		tfidf={}
		#the number of words for each matched document
		docLength={}
		#for each kind of word in each document,record how many times it appeared in the document
		termOccurrenceInADoc={}
		#record every kind of word in matched documents as key, the value of this dictionary doesn't matter
		allWords={}
		
		#parse the user query
		query = QueryParser("contents", analyzer).parse(command)
		scoreDocs = searcher.search(query, 50).scoreDocs
		#the total number of matched documents
		totalDocs = 0

		#for each matched document,calculate its all term's term normalized term frequency
		for scoreDoc in scoreDocs:
			totalDocs = totalDocs+1
			#get url and term vectors of the matched document
			doc = searcher.doc(scoreDoc.doc)
			vectors = reader.getTermVector(scoreDoc.doc,"contents")
			enum = vectors.iterator()
			url = doc.get("url")
			#record the url of matched document, create a nested dictionary for term occurence of a word in a document
			termOccurrenceInADoc[url]={}
			#record the url of matched document, create a nested dictionary for term frequency
			tf[url]={}
			#for each term in matched document, record each term's occurence and calculate the total word count of the document
			for term in BytesRefIterator.cast_(enum):
				term2 = term.utf8ToString()
				#record the term
				allWords[term2]=1
				#increase the termOccurence by one
				if termOccurrence.has_key(term2):
					termOccurrence[term2]=termOccurrence[term2]+1
				else:
					termOccurrence[term2]=1
				dpEnum = enum.postings(None)
				dpEnum.nextDoc()
				#get occurence of the term
				freq = dpEnum.freq()
				#add the occurence of the term into the total word count of the document
				if docLength.has_key(url):
					docLength[url]=docLength[url]+freq
				else:
					docLength[url]=freq
				#record occurence of this term in the according docuement
				termOccurrenceInADoc[url][term2]=freq
			#for each term in each document,divide its occurence by the total length of the document to get the normalized term frequency
			for key in termOccurrenceInADoc[url]:
				tf[url][key]=termOccurrenceInADoc[url][key]/float(docLength[url])
		#calculate idf for each term
		for key in termOccurrence:
			idf[key]=math.log(float(totalDocs)/termOccurrence[key],10)
		#calculate the product of tf and idf for each term in each document
		for key in tf:
			tfidf[key]={}
			for word in allWords:
				if tf[key].has_key(word):
					tfidf[key][word]=tf[key][word]*idf[word]
		k = K
		#this is used to record the attributes of all centroids
		centroids={}
		#this is used to record all urls of each cluster
		clusters={}
		#copy the tfidf dictionary, because I need to delete some keys to make sure I choose different initial centroids
		copy=tfidf.copy()
		#randomly choose k vectors as initial centroid
		for counter in range(1,k+1):
			if len(copy)==0:
				break
			key=random.choice(copy.keys())
			centroids[counter]=tfidf[key].copy()
			clusters[counter]={}
			del copy[key]
		#this dictionary is used to record clusters during last iteration, it will be used to compare to new clusters to judge if clusters changed
		oldClusters = {}
		#I will do at most 100 iterations, if clusters no longer change before 100 iterations, break the loop
		for counter2 in range(1,101):	
			#for each vector, find its closest centroid, put it into the according cluster
			for key in tfidf:
				counter = 1
				#for each centroid, calculte the euclidean distance between it and the vector, find the centroid with shortest eucliden distance
				for centroid in centroids:
					#for the first centroid, simply treat it as closest for now
					if counter == 1:
						closestDistance = 0
						for attribute in tfidf[key]:
							closestDistance=closestDistance+(tfidf[key].get(attribute,0)-centroids[centroid].get(attribute,0))**2
						closestDistance = math.sqrt(closestDistance)
						closestCentroid = centroid
					#for other centroids, check if their euclidean distance is shorter than temporary closest, if yes, replace closest centroid
					else:
						temp = 0
						for attribute in tfidf[key]:
							temp=temp+(tfidf[key].get(attribute,0)-centroids[centroid].get(attribute,0))**2
						temp = math.sqrt(temp)
						if temp < closestDistance:
							closestDistance = temp
							closestCentroid = centroid
					counter = counter+1
				#put the url of document into new cluster, the value of the dictionary doesn't matter
				clusters[closestCentroid][key]=1
			#after finishing calculating new clusters, clean old centroids
			centroids={}
			#for each cluster, calculate the new centroid
			for cluster in clusters:
				docNumber = 0
				#initialize nested dictionary for each cluster's centroid
				centroids[cluster]={}
				#for every vector in a cluster, add them togeter
				for document in clusters[cluster]:
					docNumber = docNumber+1
					for term in allWords:
						centroids[cluster][term]=centroids[cluster].get(term,0)+tfidf[document].get(term,0)
				#if the cluster is not empty, divide the sum of all vectors by the number of vectors, the result is the new centroid
				if docNumber == 0:
					newCentroid=random.choice(tfidf.keys())
					centroids[cluster]=tfidf[newCentroid].copy()
				else:
					for term in allWords:
						centroids[cluster][term]=float(centroids[cluster][term])/docNumber
			#if this is not the first iteration, compare new clusters with old clusters, if they are completely same, break the loop
			if counter2 != 1:
				completelySame = True
				for cluster in clusters:
					for document in clusters[cluster]:
						if oldClusters[cluster].has_key(document) == False:
							completelySame = False
							break
				if completelySame == True:
					break
			#copy every new cluster, compare them with newer clusters of next iteration
			for cluster in clusters:
				oldClusters[cluster] = clusters[cluster].copy()
				clusters[cluster].clear()
		#after finishing clustering,print every cluster,three terms with highest tfidf and every website of that cluster
		counter2 = 1
		for key in clusters:
			#print three terms with highest tfidf, treat them as labels
			if len(clusters[key]) != 0:
				print "cluster",counter2
				print "(3 words with highest tf*idf (labels): "
				for counter in range(1,4):
					if not bool(centroids[key]):
						break
					highestTFIDF = max(centroids[key].items(),key=lambda x: x[1])[0]
					print highestTFIDF.encode('ascii','ignore')
					del centroids[key][highestTFIDF]			
				print ")<br>"
				counter2 = counter2 + 1
			#for each cluster, print all websites
			#If the file has an HTML TITLE list the title
			#If the file has no title but the body begins with an HTML H1, H2, or H3, list that
			#Otherwise use the first three words of the text
			for key2 in clusters[key]:
				soup = BeautifulSoup(urllib2.urlopen(key2))
				print "<a href=\""+key2+"\">"
				if soup.find("title"):
					print soup.find("title").string.encode('ascii','ignore')+"</a><br>"
				elif soup.find("h1"):
					print soup.find("h1").string.encode('ascii','ignore')+"</a><br>"
				elif soup.find("h2"):
					print soup.find("h2").string.encode('ascii','ignore')+"</a><br>"
				elif soup.find("h3"):
					print soup.find("h3").string.encode('ascii','ignore')+"</a><br>"
				else:
					text = soup.get_text().encode("utf-8")
					array = text.split()
					print array[0]," ",array[1]," ",array[2]+"</a><br>"						
								

if __name__ == '__main__':
	#initialize VM
	lucene.initVM(vmargs=['-Djava.awt.headless=true'])
	#get user's input
	form = cgi.FieldStorage()
	searchTerm = form.getvalue('search')
	K = form.getvalue('kValue')
	#open index
	base_dir = os.path.dirname(os.path.abspath(sys.argv[0]))
	directory = SimpleFSDirectory(Paths.get(os.path.join(base_dir, INDEX_DIR)))
	reader = DirectoryReader.open(directory)
	searcher = IndexSearcher(reader)
	analyzer = StandardAnalyzer()
	print "results for query: ",searchTerm,"<br>"
	#if checkbox was checked, try 2,3,4,5,6 for k, see which one's clusters have higher silhouette coefficient
	#then use that number as k to search one more time to get final results
	if form.getvalue('autoK'):
		bestK = 0
		highestSilhouette = 0
		for counter in range(3,7):
			if counter == 2:
				highestSilhouette = getSilhouette(reader,searcher, analyzer,searchTerm,counter)
				bestK = counter
			else:
				silhouette = getSilhouette(reader,searcher, analyzer,searchTerm,counter)
				if silhouette > highestSilhouette:
					highestSilhouette = silhouette
					bestK = counter
		print "best K:",bestK,"silhouette coefficient:",highestSilhouette,"<br>"
		run(reader,searcher, analyzer,searchTerm,bestK)
	#if checkbox was not checked, get user's input for k then search the index
	else:
		#check the value of K
		if(K is None):
			print "please input K"
		else:
			run(reader,searcher, analyzer,searchTerm,int(K))
	del searcher
