import requests
import sys
import os
import re
import constants
import xlsxwriter

from bs4 import BeautifulSoup

try:
    from googlesearch import search
except ImportError: 
    print("No module named 'google' found")


# global variables
ministries_paaps = {} # dictionary of ministries that contain dictionaries of corresponding PAAPs

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

    ministries_paaps[search_query] = []

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
                paap_link = extractAcquisitionPlan(e)

                if paap_link[0] == '/':
                    paap_link = query_result[:9+query_result[9:].index("/")] + paap_link

                # each entry should be added to a dictionary of entries to
                # ensure there are no duplicates
                if paap_link in ministries_paaps[search_query]:
                    continue
                ministries_paaps[search_query] = ministries_paaps[search_query] + [paap_link]

                # write to file
                f.write(paap_link + '\n')

        print("\n\n")
    f.close()


# Create an xlsx document containing all the links to all the
# PAAPs, each tab representing the PAAPs for one Ministry

# Create an new Excel file and add a worksheet.
workbook = xlsxwriter.Workbook('demo.xlsx')

iter = 0
for ministry, paaps in ministries_paaps.items():
    worksheet = workbook.add_worksheet(constants.sheet_names[iter])
    
    # Widen the first column to make the text clearer.
    worksheet.set_column('A:A', 10)

    # Widen the first column to make the text clearer.
    worksheet.set_column('B:B', 100)

    # Add a bold format to use to highlight cells.
    bold = workbook.add_format({'bold': True})

    # Write some simple text.
    worksheet.write('A1', 'No.')

    # Write some simple text.
    worksheet.write('B1', 'Link Plan Achizitii Publice')

    for i in range(0, len(paaps)):
        worksheet.write("A" + str(i + 2), i+1)
        worksheet.write("B" + str(i + 2), paaps[i])

    iter += 1

workbook.close()
