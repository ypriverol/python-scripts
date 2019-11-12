import argparse

import networkx
import obonet as obonet
import requests
from pymongo import MongoClient
import re


def get_projects(mongo_uri):
    client = MongoClient(mongo_uri)
    db = client.pridepro
    return db.pride_projects.find({})


def process_software_information(project, software_accession, name):

    software_list = project['softwareList']
    data_protocol = project['dataProtocol']
    sample_protocol = project['sampleProtocol']
    if 'description' in project:
         description = project['description']

    if re.search(" " + name + " ", data_protocol, re.IGNORECASE):
        print(project['accession'], " " ,name)


def init_obo_ms_ontology():

    url = 'https://raw.githubusercontent.com/HUPO-PSI/psi-ms-CV/master/psi-ms.obo'
    graph = obonet.read_obo(url)

    # Number of nodes
    print(len(graph))

    # Number of edges
    graph.number_of_edges()

    # Mapping from term ID to name
    id_to_name = {id_: data.get('name') for id_, data in graph.nodes(data=True)}
    return graph

def get_subterms(graph, accession):

    # Find all superterms of species. Note that networkx.descendants gets
    # superterms, while networkx.ancestors returns subterms.
    return  networkx.ancestors(graph, accession)


def main():

    # Parse the parameters of the script
    parser = argparse.ArgumentParser(description='Analysing PRIDE projects metadata for missing fields')
    parser.add_argument('--mongo_uri', dest='mongo_uri', required=True, help='MongoDB uri in production')
    args = parser.parse_args()

    projects = get_projects(args.mongo_uri)

    ms_ontology = init_obo_ms_ontology()
    ontology_softwares = get_subterms(ms_ontology, "MS:1001456")

    for project in projects:
        for software_accession in ontology_softwares:
            software_ols = ms_ontology.node[software_accession]
            process_software_information(project, software_accession, software_ols['name'])

    for line in projects:
        req = requests.get('https://www.ebi.ac.uk/europepmc/webservices/rest/search?query=' + line.strip() + "&format=json")
        project = req.json()
        if (project['hitCount'] != 0):
            doi  = ''
            pmid = ''
            if(project['resultList']['result'][0].get('pmid')):
                pmid = project['resultList']['result'][0]['pmid']
            if (project['resultList']['result'][0].get('doi')):
                doi = project['resultList']['result'][0]['doi']

            if(pmid is not None and len(line.strip()) > 0):
                print("PROJECT\t" + line.strip() + "\tPMID\t" + pmid + "\t DOI\t" + doi)
                subprocess.check_call("./runPublication.sh -a %s -p %s -f" % (line.strip(), pmid), shell=True)


if __name__ == '__main__':
    main()