# Search Engine Practice

Implement a document clustering to the basic search engine and my attempt to write a web crawler

## Getting Started

These instructions will get you a copy of the project up and running on your local machine for development and testing purposes. See deployment for notes on how to deploy the project on a live system.

### Installing

Please install Pylucene via http://www.apache.org/dyn/closer.lua/lucene/pylucene/
and Python 2.x (x >= 3.5) or Python 3.x (x >= 3)
You may also need to run
```
pip3 install package-names
```
to install some Python packages 

## Deployment

To run the backend program,load python2.7 module first, then type 
```
python crawler.py
```
Please note that there must be a folder named "files" in the same directory with crawler. 
To change the starting page, page number to download and domain, modify the variables in the last five lines of crawler.py
Please note that to call BuildSearchEngine function, the last argument of the first call must be True,
The last argument of other calls must be False

## Running the tests

Put words you want to search in "query words" form box. 

To manually input k, uncheck the checkbox, then input k in the right checkbox. Click search botton

(K stands for the number of clusters which clustering aims to partition n observations into. Each observation belongs to the cluster with the nearest mean, serving as a prototype of the cluster. This results in a partitioning of the data space into Voronoi cells. From Wiki)

To let program choose k, check the checkbox,then click search botton. 

Please note that search takes some time, automatically choose K might take more time because the program tries several different k

The index has about 500 webpages which were collected from my undergraduate university website, 
KFC official website, Steam official website, Apple official website and Nike official website. 

### Break down into end to end tests

When user searches for a query, the engine divides result pages into a certain number of clusters based on k-means algorithm. For implementation, for each word in each matched document, calculate the product of term frequency and inversed document frequency, for n terms, create n-dimension vector space, assign each matched document a vector, each dimension is the product of term frequency and inversed document frequency of a word. Use k-means algorithm to cluster these vectors. Use euclidean distance for measuring similarity between vectors in k-means algorithm. For each cluster, list three words with highest tf*idf as labels. I also provided an option to choose k automatically. If this option is selected, my program will try 3,4,5,6 separately as k, see which k can generate a result with higher silhouette coefficient. That's why k will be considered the best k between 3-6. 

## Built With

* [Pylucene](http://lucene.apache.org/pylucene/) - Python extension for accessing Java Lucene

## Authors

* **Bohan Zhang** - *Initial work* - [Zombo1296](https://github.com/Zombo1296)

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details

## Acknowledgments

* Hat tip to anyone who's code was used
* Inspiration from web search learning blogs 
