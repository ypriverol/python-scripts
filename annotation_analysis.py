import argparse
import csv
import requests

import networkx
import obonet as obonet
from pymongo import MongoClient
import re

CSV_HEADER = {
    "ProjectAccession":"0",
    "Instrument":"1",
    "Quantification Method":"2",
    "Software":"3",
    "PTM":"4",
    "Species":"5",
    "Publication_ids":"6"
}

def get_projects(mongo_uri):
    client = MongoClient(mongo_uri)
    db = client.pridepro
    return db.pride_projects.find({})

def get_annotation_file():
    response = requests.get("https://raw.githubusercontent.com/PRIDE-Utilities/pride-ontology/master/pride-annotations/pride_projects.csv")
    cr = csv.reader(response.content.decode('utf-8').splitlines(), delimiter=',')
    my_list = list(cr)
    for row in my_list:
        print (row)
    return my_list

def process_software_information(project, software_accession, name):

    data_protocol = project['dataProtocol']
    description = ""
    if 'description' in project:
         description = project['description']

    if re.search(" " + name + " ", data_protocol, re.IGNORECASE):
        print(project['accession'], " " , name)
    elif re.search(" " + name + " ", description, re.IGNORECASE):
        print(project['accession'], " ", name)

def process_instrument_information(project, instrument_accession, name):

    sample_protocol = project['sampleProtocol']
    if 'description' in project:
         description = project['description']

    if re.search(" " + name + " ", sample_protocol, re.IGNORECASE):
        print(project['accession'], " " ,name)
    elif re.search(" " + name + " ", description, re.IGNORECASE):
        print(project['accession'], " ", name)

def process_quantification_information(project, quantification_accession, name):

    sample_protocol = project['sampleProtocol']
    description = ""
    if 'description' in project:
        description = project['description']

    if re.search(" " + name + " ", sample_protocol, re.IGNORECASE):
        print(project['accession'], " ", name)
    elif re.search(" " + name + " ", description, re.IGNORECASE):
        print(project['accession'], " ", name)

def read_obo_file_from_url(url):
    graph = obonet.read_obo(url)
    # Number of nodes
    print(len(graph))
    # Number of edges
    graph.number_of_edges()
    # Mapping from term ID to name
    id_to_name = {id_: data.get('name') for id_, data in graph.nodes(data=True)}
    return graph


def init_obo_ms_ontology():
    url = 'https://raw.githubusercontent.com/HUPO-PSI/psi-ms-CV/master/psi-ms.obo'
    return read_obo_file_from_url(url)


def get_subterms(graph, accession):

    # Find all superterms of species. Note that networkx.descendants gets
    # superterms, while networkx.ancestors returns subterms.
    return  networkx.ancestors(graph, accession)


def init_obo_pride_ontology():
    url = 'https://raw.githubusercontent.com/PRIDE-Utilities/pride-ontology/master/pride_cv.obo'
    return read_obo_file_from_url(url)

def main():

    # Parse the parameters of the script
    parser = argparse.ArgumentParser(description='Analysing PRIDE projects metadata for missing fields')
    parser.add_argument('--mongo_uri', dest='mongo_uri', required=True, help='MongoDB uri in production')
    parser.add_argument('--new_file', dest='new_file', required=True, help='File with new proposed annotations')
    args = parser.parse_args()

    projects_annotations = get_annotation_file()

    projects = get_projects(args.mongo_uri)

    ms_ontology = init_obo_ms_ontology()
    ontology_softwares = get_subterms(ms_ontology, "MS:1001456")
    ontology_instruments = get_subterms(ms_ontology, "MS:1000031")

    pride_ontology = init_obo_pride_ontology()
    quantification_types = get_subterms(pride_ontology, "PRIDE:0000309")

    for project in projects:
        for software_accession in ontology_softwares:
            software_ols = ms_ontology.node[software_accession]
            process_software_information(project, software_accession, software_ols['name'])

    print("Time to Analyze the instruments !!!!\n\n")
    for project in projects:
        for instrument_accession in ontology_instruments:
            instrument_ols = ms_ontology.node[instrument_accession]
            process_instrument_information(project, instrument_accession, instrument_ols['name'])

    print("Time to Analyze the quantification type!!! \n\n")
    for project in projects:
        for quantification_accession in quantification_types:
            quantification_ols = ms_ontology.node[quantification_accession]
            process_quantification_information(project, quantification_accession, quantification_ols['name'])

    projects_writer = csv.writer(args.new_file, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL)

    for row in projects_annotations:
        projects_writer.writerow(row)


if __name__ == '__main__':
    main()