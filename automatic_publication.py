#!/usr/bin/env python
import os
import subprocess

import requests
import cx_Oracle
import argparse

os.environ["ORACLE_HOME"] = "/Users/yperez/local-apps/oracle-client/instantclient_19_3/"


def get_private_projects(server, username, password):
    """
    Get the private projects from Oracle database
    :param server: Oracle server
    :param username: Oracle username
    :param password: Oracle user password
    :return:
    """

    connection = cx_Oracle.connect(username, password, server)
    pride_projects = []

    cursor = connection.cursor()
    for row in cursor.execute("""SELECT ACCESSION FROM PROJECT WHERE IS_PUBLIC=0"""):
        print(row)
        pride_projects.append(row[0])

    return pride_projects


def main():

    parser = argparse.ArgumentParser(description='Automatically lunch publication jobs for datasets in EuropePMC')
    parser.add_argument('--oracle_server', dest='oracle_server', required=True, help='Oracle server url')
    parser.add_argument('--oracle_user', dest='oracle_user', required=True, help='Oracle server username')
    parser.add_argument('--oracle_password', dest='oracle_password', required=True, help='Oracle server user password')
    parser.add_argument('--skip_projects', dest='skip_projects', required=False,
                        help='Skip the following projects because they have errors')
    args = parser.parse_args()

    private_projects = get_private_projects(args.oracle_server, args.oracle_user, args.oracle_password)

    skip_projects = []
    if (args.skip_projects is not None):
        f = open(args.skip_projects, "r")
        for x in f:
            skip_projects.append(x.strip())

    for line in private_projects:
        req = requests.get(
            'https://www.ebi.ac.uk/europepmc/webservices/rest/search?query=' + line.strip() + "&format=json")
        project = req.json()
        if (project['hitCount'] != 0):
            doi = ''
            pmid = ''
            if (project['resultList']['result'][0].get('pmid')):
                pmid = project['resultList']['result'][0]['pmid']
            if (project['resultList']['result'][0].get('doi')):
                doi = project['resultList']['result'][0]['doi']

            if (pmid is not None and len(pmid.strip()) > 0 and (line.strip() not in skip_projects)):
                print("PROJECT\t" + line.strip() + "\tPMID\t" + pmid + "\t DOI\t" + doi)
                subprocess.check_call("./runPublication.sh -a %s -p %s -f" % (line.strip(), pmid), shell=True)
            elif((line.strip() in skip_projects)):
                print("Skiping Project -- " + line.strip())


if __name__ == '__main__':
    main()
