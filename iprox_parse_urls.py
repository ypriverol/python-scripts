import argparse
from bs4 import BeautifulSoup

# Create a command-line argument parser
parser = argparse.ArgumentParser(description="Extract URLs from an XML file")
parser.add_argument("xml_file", help="Path to the input XML file")

# Parse the command-line arguments
args = parser.parse_args()

# Read the XML data from the input file
with open(args.xml_file, 'r') as xml_file:
    xml_data = xml_file.read()

# Parse the XML data
soup = BeautifulSoup(xml_data, 'xml')

# Find all DatasetFile elements
dataset_files = soup.find_all('DatasetFile')

# Extract the URLs from cvParam tags within DatasetFile elements
urls = []

for dataset_file in dataset_files:
    cv_param = dataset_file.find('cvParam', {'name': 'Associated raw file URI'})
    if cv_param:
        url = cv_param['value']
        urls.append(url)

for url in urls:
    print(url)

# Write the URLs to a file
output_file = 'urls.txt'
with open(output_file, 'w') as file:
    file.write('\n'.join(urls))