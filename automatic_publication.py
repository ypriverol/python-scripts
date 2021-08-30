#!/usr/bin/env python

import requests
import psycopg2
import argparse



def get_private_projects(server, database, user, password):
    """
    Get the private projects from postgres database
    :param server: postgres server
    :param username: postgres username
    :param password: postgres user password
    :return:
    """

    connection = psycopg2.connect(user=user,
                                  password=password,
                                  host=server,
                                  port="5432",
                                  database=database)
    cursor = connection.cursor()
    pride_projects = []

    cursor = connection.cursor()
    cursor.execute("select accession from pridearch.project where is_public=0")
    for row in cursor.fetchall():
        print(row)
        pride_projects.append(row[0])

    return pride_projects


def main():

    parser = argparse.ArgumentParser(description='Automatically lunch publication jobs for datasets in EuropePMC')
    parser.add_argument('--server', dest='server', required=True, help='postgres server url')
    parser.add_argument('--database', dest='database', required=True, help='database name')
    parser.add_argument('--user', dest='user', required=True, help='postgres server username')
    parser.add_argument('--password', dest='password', required=True, help='postgres server user password')
    parser.add_argument('--skip_projects', dest='skip_projects', required=False,
                        help='Skip the following projects because they have errors')
    args = parser.parse_args()

    private_projects = get_private_projects(args.server, args.database, args.user, args.password)

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
                print(line.strip() + "\t" + pmid)
                # subprocess.check_call("./runPublication.sh -a %s -p %s -f" % (line.strip(), pmid), shell=True)
            elif((line.strip() in skip_projects)):
                print("Skiping Project -- " + line.strip())

if __name__ == '__main__':
    main()
