#! /usr/bin/env python
# coding: utf-8
import sys
import urllib
import urlparse
from bs4 import BeautifulSoup

def parseDatasetDetails(html_page):
    soup = BeautifulSoup(html_page,'lxml')
    table = soup.find("div", attrs={"id":"primarycontent"})
    trs = table.find_all("tr")
    total_desc = dict()
    for tr in trs:
        tds = tr.find_all("td")
        if len(tds) == 0: continue
        if len(tds) == 2:
            desc = tds[0].text
            value = tds[1].text.replace(';', ' ').strip() # remove ; that might interfere with output delimeters
            total_desc[desc] = value

    return total_desc

def main():

    sys.stderr.write('Loading main page')

    cxidb_base_url = "http://cxidb.org/"
    cxidb_browse_url = "browse.html"

    response = urllib.urlopen(urlparse.urljoin(cxidb_base_url, cxidb_browse_url))
    the_page = response.read()

    soup = BeautifulSoup(the_page,'lxml')
    table = soup.find("div", attrs={"id":"primarycontent"})

    lines = [li for li in table.find("ul").find_all("li")]
    ids_ref = [li.find("a")['href'] for li in lines ]
    ids_text = [li.find("a").find("span").text for li in lines ]
    ids_desc = [li.find("a") for li in lines ]

    ids_text = [' '.join(s.split()) for s in ids_text ] # Fix spaces in ids_text
    for i,s in enumerate(ids_desc):                     # Fix ids_desc
        s = s.text.replace(s.find("span").text,'')      # remove "id xx"
        s = ' '.join(s.split())                         # Fix spaces
        s = s.replace('- ','',1).strip()                # remove ' - ' in the begining
        ids_desc[i] = s

    fields = []
    details = []

    for i in range(len(ids_text)):  #Get details

        sys.stderr.write('\rLoading page %d of %d'%(i+1,len(ids_text)))

        details.append([])
        details_url = urlparse.urljoin(cxidb_base_url, ids_ref[i])
        response = urllib.urlopen(details_url)
        dataset_page = response.read()
        dataset_details = parseDatasetDetails(dataset_page)

        for k in fields:
            if k in dataset_details:
                details[i].append(dataset_details[k])
            else:
                details[i].append('')
        for k in dataset_details:
            if k not in fields:
                fields.append(k)
                details[i].append(dataset_details[k])

    sys.stderr.write('\nPrinting results\n')

    # Print first line
    sys.stdout.write('Id;Link;')
    for j in range(len(fields)):
        sys.stdout.write('%s;'%(fields[j].replace(':','').encode('utf8','replace')))
    sys.stdout.write('\n')

    # Print details
    for i in range(len(ids_text)):
        sys.stdout.write('%s;'%ids_text[i])
        sys.stdout.write('%s;'%urlparse.urljoin(cxidb_base_url, ids_ref[i]))
        for j in range(len(fields)):
            if j < len(details[i]):
                sys.stdout.write('%s;'%details[i][j].encode('utf8','replace'))

        sys.stdout.write('\n')

    # for i,s in enumerate(idx_desc):
    #     print ids_text[i],s

if __name__ == '__main__':
    main()
