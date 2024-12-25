import requests
import sys
import os
import re
import constants
from bs4 import BeautifulSoup

try:
    from googlesearch import search
except ImportError: 
    print("No module named 'google' found")


# create output directory
try:
    os.mkdir("out_crawler")
    print("Output directory created successfully!")
except FileExistsError:
    print("Directory already exists!")
except PermissionError:
    print("Permission denied.")
except Exception as e:
    print("Error occurred: {e}", e)


# Form a list of queries to search for
queries = []
for ministry in constants.ministries:
    ministry_query = "Plan achizitii publice " + ministry
    queries.append(ministry_query)


def isAcquisitionPlan(entry):
    if "achizitii" in entry and "public" in entry and (".pdf" in entry or ".xlsx" in entry):
        return True
    elif "achiziții" in entry and "public" in entry and (".pdf" in entry or ".xlsx" in entry):
        return True
    elif "Achiziții" in entry and "public" in entry and (".pdf" in entry or ".xlsx" in entry):
        return True
    elif "pap" in entry and (".pdf" in entry or ".xlsx" in entry):
        return True
    return False


def extractAcquisitionPlan(entry):
    start_href_index = entry.index("href=")
    end_href_index = entry[start_href_index+7:].index("\"")
    end_href_index += start_href_index + 7

    return entry[start_href_index+6:end_href_index]


# Loop over the queries constructed
for search_query in queries:
    print("Results for query: " + search_query)
    output_file = "out_crawler/" + "_".join(search_query.split(' ')) + ".out"
    f = open(output_file, 'w')
    for query_result in search(search_query, tld="co.in", num=3, stop=3, pause=2):
        print(query_result)

        response = requests.get(query_result, headers=constants.headers, verify=False)
        status_code = response.status_code
        if status_code != 200:
            print("Request Error: " + str(status_code))
            continue

        # write page content to output directory
        soup = BeautifulSoup(response.text, "html.parser")
        
        entries = soup.find_all(href=True)
        
        entries = map(str, entries)
        for e in entries:
            if isAcquisitionPlan(e):
                # print(e)

                papp_link = extractAcquisitionPlan(e)

                if papp_link[0] == '/':
                    papp_link = query_result[:9+query_result[9:].index("/")] + papp_link

                f.write(papp_link + '\n')

        print("\n\n")
    f.close()
