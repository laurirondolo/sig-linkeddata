'''
Created on 5 dec. 2017

@author: bakkej1
'''
import time	 #For Delay
from datetime import datetime
import urllib3
from bs4 import BeautifulSoup
import json
import pprint

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

#VARIABLES
seed_page ='https://www.taxonic.com'
crawl_limit = 200
extract_limit = 20
database = "medewerkers-quote.json"
id = 0

#CONSTANTS
frontier = []
crawled = []
jsonList = []

http = urllib3.PoolManager()
pp = pprint.PrettyPrinter(indent=2)

def find_medewerkers(soup):
	medewerkers = soup.find_all("div", class_="wpex-carousel-entry-title entry-title")
	medewerkers_str = []
	for i in medewerkers: 
		#undo comments to return nested list
#		 name = i.find("a")['title']
		URI = i.find("a", href=True)['href']
#		 medewerker = [name, URI]
#		 medewerkers_str.append(medewerker)
		medewerkers_str.append(URI)
	return medewerkers_str


def find_KwaliteitenErvaring(soup, identifier):
	items = []
	tag = soup.find_all("div", class_="wpb_wrapper")
	for i in tag:
		if i.find(string=identifier) : 
			stringified = str(i).splitlines()
			for i in stringified :
				if i.startswith("<li") :
					start= i.find(">")
					end = i.find("</")
					item = i[start+1:end]
					items.append(item)
	return list(set(items))
	
def find_Beschrijving(soup):
	items = []
	wpb_containers = soup.find_all('div', class_='wpb_wrapper')
	wpb_containers[1].find('blockquote').decompose()
	paragraphs = wpb_containers[1].find_all('p')
	for i in paragraphs:
		items.append(i.text)
	
	return " ".join(items)

def find_Quote(soup):
	quote = str(soup.blockquote.p.text)
	result = (quote.encode('ascii','ignore')).decode("utf-8")
	return result.strip()
	
	
def download_page(url):
	try:
		headers_ = {}
		headers_['User-Agent'] = "Mozilla/5.0 (X11; Linux i686) AppleWebKit/537.17 (KHTML, like Gecko) Chrome/24.0.1312.27 Safari/537.17"
		response = http.request("GET", url, headers=headers_)
		respData = response.data.decode('utf-8')
		return respData
	except Exception as e:
		print("why")
		print(str(e))

def remove_duplicates(array):
	array_set = set(array)
	array = []
	for i in array_set:
		array.append(i)
	return array

#URL parsing for incomplete or duplicate URLs
def url_parse(url):
	try:
		from urllib.parse import urlparse
	except ImportError:
		from urlparse import urlparse
	url = url  
	s = urlparse(url)
	seed_page_n = seed_page
	i = 0
	flag = 0
	while i<=9:
		if url == "/":
			url = seed_page_n
			flag = 0  
		elif not s.scheme:
			url = "http://" + url
			flag = 0
		elif "#" in url:
			url = url[:url.find("#")]
			flag = 0
		elif "?" in url:
			url = url[:url.find("?")]
			flag = 0
		elif s.netloc == "":
			url = seed_page + s.path
			flag = 0
		elif url[len(url)-1] == "/":
			url = url[:-1]
			flag = 0  
		else:
			url = url
			flag = 0
			break
		
		i = i+1
		s = urlparse(url)   #Parse after every loop to update the values of url parameters
	return (url,flag)

def extension_scan(url):
	a = ['.png','.jpg','.jpeg','.gif','.tif','.txt', '.svg']
	j = 0
	while j < (len(a)):
		if a[j] in url:
			flag = 1
			break
		else:
			flag = 0
			j = j+1

	return flag

def get_links(soup):
	linkList = []
	rawLinks = soup.find_all("a", href=True)
	for i in rawLinks :
		linkList.append(url_parse(i['href'])[0])
	linkList = remove_duplicates(linkList)
	return linkList
		
def update_frontier(new_links):
	global frontier

	unknown_links = list(set(new_links))
	print("new_Links_len: ", len(unknown_links))

	for i in unknown_links :
		frontier.append(i)
	print("frontier_len_old: ", len(frontier))
	frontier = list(set(frontier))
	print("frontier_len_new: ", len(frontier))

	return frontier
 
def employee_scrape(url, soup):
	global id
	_name = soup.find("h1").text
	_title = soup.find("div", id="staff-single-position").text
	_image = soup.find("img", class_="staff-single-media-img")
	_quote = find_Quote(soup)
	_beschrijving = find_Beschrijving(soup)
	_clients = find_KwaliteitenErvaring(soup, "Opdrachtgevers:")
	_talents = find_KwaliteitenErvaring(soup, "Kennis en vaardigheden:")

	entity = dict(id=id, url=str(url), quote=str(_quote), beschrijving=str(_beschrijving), name=str(_name), title=_title, depiction=_image["src"], clients=_clients, talents=_talents)

	print(entity)
	id+=1
	return entity

def Crawl():
	
	frontier = [seed_page]
	extracted = 0
	
	while len(crawled) < crawl_limit :
#	 while extracted < extract_limit:

		if frontier == []:
			break
		print("Current page: " + str(frontier[0]))
		
		next_up = frontier.pop(0)
		next_up,flag = url_parse(next_up)
		flag += extension_scan(next_up)
		
		if flag == 1 :
			pass
		else :
			if next_up in crawled :
				print("already crawled")
				pass
			else:
				crawled.append(next_up)
				while True :
					try :
						t1 = time.time()
						soup = BeautifulSoup(download_page(next_up), "lxml")
						t2 = time.time()
						
						#Shortcut to the pages containing employee information
						medewerkers = find_medewerkers(soup)
						for i in medewerkers :
							frontier.append(i)
						t3 = time.time()
						
						if str(next_up).startswith("https://www.taxonic.com/medewerker"):
							jsonList.append(employee_scrape(next_up, soup))
							extracted+=1

						t4 = time.time()
						
						#Server friendly by sending http requests at least 0.75 seconds apart
						if t2-t1 in range(0,1) :
							time.sleep(0.75 - (t4-t1))
							
						print("\nTime taken to:")
						print("Download: " + str(t2-t1))
						print("Find medewerkers: " + str(t3-t2))
						print("Extract data: " + str(t4-t3) + "\n")
						 
						break
					except Exception as e :
						print(str(e))
						pass
						break


#start the crawl
Crawl()

#store data extracted in a json file
with open(database, 'w', encoding='utf-8') as f2:
	json.dump(jsonList, f2, ensure_ascii=False)
	


