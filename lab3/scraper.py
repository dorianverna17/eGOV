import constants

# get_ministries_websites returns the websites of the ministries of Romania
# associated with the entries defined above.
def get_ministries_websites():
    import requests
    from bs4 import BeautifulSoup

    response = requests.get('https://www.gov.ro/ro/guvernul/organizare/ministere', headers=constants.headers)
    status_code = response.status_code
    if status_code != 200:
        print("Request Error: " + str(status_code))
        return

    ministers_dict = {}

    soup = BeautifulSoup(response.text, "html.parser")
    ministere = soup.find(class_="pageDescription")
    for m_entry in ministere:
        link_entry = m_entry.find("a")
        if link_entry == None or link_entry == -1:
            continue

        minister_link = link_entry.get("href")
        minister_name = link_entry.text

        print(minister_link + " " + minister_name)

        ministers_dict[minister_name] = minister_link

    return ministers_dict


# get_ministry_plan get a ministry url and name and searches its website for the latest
# public acquisition plan
def get_ministry_plan(url, name):
    import requests
    import sys
    import os
    import re

    from bs4 import BeautifulSoup

    response = requests.get(url, headers=constants.headers, verify=False)
    status_code = response.status_code
    if status_code != 200:
        print("Request Error: " + str(status_code))
        return

    # write page content to output directory
    soup = BeautifulSoup(response.text, "html.parser")
    output_file = "out/" + "_".join(re.split(" |/", soup.title.text)) + ".out"

    orig_stdout = sys.stdout
    f = open(output_file, 'w')
    sys.stdout = f

    print(response.text)

    # get the links where the Acquisition Plans are
    pap_links_file.write("Entries for ministry: " + name + '\n')
    entries = soup.find_all(string=re.compile("achizitii"))
    pap_links_file.write(str(entries) + '\n')

    sys.stdout = orig_stdout
    f.close()


# get a dictionary of ministries
ministries_urls = get_ministries_websites()
print(ministries_urls)

# create output directory
try:
    os.mkdir("out")
    print("Output directory created successfully!")
except FileExistsError:
    print("Directory already exists!")
except PermissionError:
    print("Permission denied.")
except Exception as e:
    print("Error occurred: {e}", e)

# get the acquisition plan for each ministry
pap_links_file = open("pap_links.out", 'w')
for ministry_name, ministry_url in ministries_urls.items():
    print("Getting Public Acquisitions Plan for ministry: " + ministry_name)
    pap = get_ministry_plan(ministry_url, ministry_name)

    # TODO - remove break
    break
pap_links_file.close()
