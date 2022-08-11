from __future__ import print_function
import re
import sys
import time
import argparse
from pyopenms import *
from tqdm import tqdm


def eprint(*args, **kwargs):
    print(*args, file=sys.stderr, **kwargs)


class AscoreAnalyzer:
    def __init__(self, spec_file, ident_file, out_file, hit_depth=1, target_fdr=1., n_to_profile=0,
                 profile_file_name="profile.tsv", **kwargs):
        """
        AscoreAnalyzer provides a wrapper to load Spectra from MzML files
        and peptide identifications from Comet from pepXML files. It then
        zips them together, and matches hits to spectra based on retention
        time and M/Z (guessing must occur since OpenMS does not retain scan
        information when loading identifications). This class then handles
        Ascore and allows printing TSVs.
        """

        # Result properties
        self.out_file = out_file
        self.results = []

        # Load spectra
        exp = MSExperiment()
        MzMLFile().load(spec_file, exp)
        self.spectra = exp.getSpectra()
        # OpenMS does not retain scan indices, so we inject them here.
        [spec.setMetaValue("index", ind + 1) for ind, spec in enumerate(self.spectra)]
        self.spectra = [spec for spec in self.spectra if spec.getMSLevel() == 2]
        self.spectra.sort(key=lambda spec: spec.getRT())

        # Load identifications
        eprint(
            """
            #################################################
            Note:
            The following warnings are from OpenMs. We do not
            specify modifications and allow the XML parser to
            infer them on its own. Please read the warnings
            and make sure nothing appears off.
            ################################################# 
            """
        )
        self.hit_depth = hit_depth
        self.peptide_records = []
        self.protein_records = []
        IdXMLFile().load(ident_file, self.protein_records, self.peptide_records)
        self.peptide_records.sort(key=lambda pep: pep.getRT())

        # AScore Init
        self.ascore = AScore()
        ascore_params = self.ascore.getParameters()
        for key, val in kwargs.items():
            ascore_params.setValue(key, val)
        self.ascore.setParameters(ascore_params)

    def generate_hits(self, record):
        nsupplied = 0
        was_supplied = {}
        for hit in record.getHits():
            stripped_sequence = re.sub("\[[^A-Z]+\]", "", hit.getSequence().toBracketString())
            if not was_supplied.get(stripped_sequence, 0):
                was_supplied[stripped_sequence] = 1
                nsupplied += 1
                yield hit

            if nsupplied == self.hit_depth:
                break

    def generate_pairs(self):
        spec_ind = 0
        record_ind = 0
        while spec_ind < len(self.spectra) and record_ind < len(self.peptide_records):

            # Extract scan number from respective elements
            spec_scan = self.spectra[spec_ind].getMetaValue("index")
            record_scan = int(
                re.search("(?<=scan\=)[0-9]+",
                          self.peptide_records[record_ind].getMetaValue('spectrum_reference')).group()
            )
            # print(spec_scan, record_scan)
            if spec_scan == record_scan:
                for hit in self.generate_hits(self.peptide_records[record_ind]):
                    yield self.spectra[spec_ind], hit
                spec_ind += 1
                record_ind += 1

            elif record_scan > spec_scan:
                spec_ind += 1

            else:
                record_ind += 1

    def calculate_score_threshold(self):
        hit_array = np.concatenate([[h for h in self.generate_hits(r)] for r in self.peptide_records])
        scores = np.array([h.getScore() for h in hit_array])
        labels = np.array([
            any(["decoy".encode("utf8") in acc for acc in h.extractProteinAccessionsSet()]) for h in hit_array
        ]).astype(float)

        sorted_ind = np.argsort(scores)
        scores = scores[sorted_ind]
        labels = labels[sorted_ind]

        fpr = (np.cumsum(labels) + 1) / np.arange(1, len(labels) + 1)
        for ind in np.arange(0, len(labels) - 1)[::-1]:
            fpr[ind] = min(fpr[ind], fpr[ind + 1])

        self.score_threshold = scores[min(len(fpr) - 1, np.searchsorted(fpr, self.target_fdr))]

    # def passes_score_threshold(self, match):
    #     return match.getScore() < self.score_threshold

    def analyze(self):
        for spectrum, hit in tqdm(self.generate_pairs()):
            nphospho = hit.getSequence().toString().count("Phospho")
            if nphospho > 0:
                ascore_hit = self.ascore.compute(hit, spectrum)
                scores = [str(ascore_hit.getMetaValue("AScore_{}".format(i))) for i in range(1, 3 + 1)]
                self.results.append((spectrum.getMetaValue("index"),
                                     ascore_hit.getSequence().toBracketString(),
                                     nphospho, ascore_hit.getMetaValue("AScore_pep_score"),
                                     ";".join(scores)))

    def to_tsv(self):
        with open(self.out_file, "w") as dest:
            dest.write("\t".join(["Scan", "Peptide", "NPhospho", "PepScore", "Ascores"]))
            dest.write("\n")
            for res in self.results:
                dest.write("\t".join([str(e) for e in res]))
                dest.write("\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Maps OpenMS' implementation of Ascore accross Comet identifications.",
        prog="OpenMS-Ascore Wrapper"
    )
    parser.add_argument("--hit_depth", default=4, type=int,
                        help="Number of unique peptide hits to analyze per spectrum. "
                             "May be less if not enough hits can be found.")
    parser.add_argument("--fragment_mass_tolerance", default=.05, type=float,
                        help="Mass tolerance for matching spectra peaks with theoretical "
                             "peaks. In Da.")
    parser.add_argument("--max_peptide_length", default=50, type=int,
                        help="Maximum length peptide hit to consider.")
    parser.add_argument("spec_file", type=str,
                        help="MS Spectra file supplied as MZML")
    parser.add_argument("ident_file", type=str,
                        help="idXML hits supplied as pepXML")
    parser.add_argument("out_file", type=str,
                        help="Destination for ascores")
    args = vars(parser.parse_args())

    # Algorithm script
    run_start = time.time()
    eprint("--> OpenMS-Ascore Wrapper started on: {}".format(time.ctime()))

    eprint("--> Loading MzML and pepXML files...")
    analyzer = AscoreAnalyzer(**args)
    eprint("--> MzML and idXML parsing complete on: {}".format(time.ctime()))

    eprint("--> Calculating Ascores...")
    analyzer.analyze()
    eprint("--> Ascore calculations complete on: {}".format(time.ctime()))

    eprint("--> Writing output...")
    analyzer.to_tsv()
    eprint("--> OpenMS-Ascore Wrapper completed on: {}".format(time.ctime()))
    eprint("--> Total runtime: {:.1f} seconds".format(time.time() - run_start))
