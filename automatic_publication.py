#!/usr/bin/env python
import os
import subprocess

import requests
import sys

import cx_Oracle
import argparse

os.environ["ORACLE_HOME"] = "/Users/yperez/local-apps/oracle-client/instantclient_19_3/"



def get_private_projects(server, username, password):

    # Connect as user "hr" with password "welcome" to the "orclpdb1" service running on this computer.
    connection = cx_Oracle.connect(username, password, server)
    pride_projects = []

    cursor = connection.cursor()
    for row in cursor.execute("""SELECT ACCESSION FROM PROJECT WHERE IS_PUBLIC=0"""):
        print(row)
        pride_projects.append(row[0])

    return pride_projects

def log(msg, level=1, abort=False):
    if level <= globals['verbose'] or abort:
        if abort:
            sys.stdout = sys.stderr
            print()
        print(msg)
    if abort:
        sys.exit(1)


def main():

    # Parse the parameters of the script
    parser = argparse.ArgumentParser(description='Automatically lunch publication jobs for datasets in EuropePMC')
    parser.add_argument('--oracle_server', dest='oracle_server', required=True, help='Oracle server url')
    parser.add_argument('--oracle_user', dest='oracle_user', required=True, help='Oracle server username')
    parser.add_argument('--oracle_password', dest='oracle_password', required=True, help='Oracle server user password')
    args = parser.parse_args()

    private_projects = get_private_projects(args.oracle_server, args.oracle_user, args.oracle_password)

    for line in private_projects:
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
