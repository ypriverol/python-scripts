###########################################################################
# Biological example of phosphopeptide-scoring
###########################################################################
from filecmp import cmp

from pyopenms import *
import csv
import re


def convertToRichMSSpectrum(input_):
    rs = MSSpectrum()
    for p in input_:
        rp = Peak1D()
        rp.setMZ(p.getMZ())
        rp.setIntensity(p.getIntensity())
        rs.push_back(rp)
    return rs


def convertToMSSpectrum(input_):
    spectrum = MSSpectrum()
    for p in input_:
        rp = Peak1D()
        rp.setMZ(p.getMZ())
        rp.setIntensity(p.getIntensity())
        spectrum.push_back(rp)
    return spectrum


"""
Two phospho scorers, the interface is available through the "score" function:

- Input:
  - PeptideHit (pyopenms.PeptideHit)
  - Spectrum (pyopenms.MSSpectrum)
  - [Scorer massDelta]

- Output:
    [ Score, NewSequence ]
"""


class PhosphoScorerAScore:
    def score(self, phit, spectrum):
        rs = convertToRichMSSpectrum(spectrum)
        newhit = AScore().compute(phit, rs)
        return [newhit.getScore(), newhit.getSequence()]


pepxml_file = "20120413_EXQ5_KiSh_SA_LabelFree_HeLa_pY_pervandate_rep2_consensus_fdr.idxml"
mzml_file = "20120413_EXQ5_KiSh_SA_LabelFree_HeLa_pY_pervandate_rep2.mzml"
output = "sample_ascore_output.csv"
fh = open(output, "w")
writer = csv.writer(fh)

# Cutoff for filtering peptide hits by their score
cutoff_score = 0.75

#
# Data I/O : load the pep.xml file and the mzXML file
#
protein_ids = []
peptide_ids = []
IdXMLFile().load(pepxml_file, protein_ids, peptide_ids)
exp = MSExperiment()
FileHandler().loadExperiment(mzml_file, exp)
look = SpectrumLookup()
look.readSpectra(exp, "((?<SCAN>)\d+$)")


def compute_spectrum_bins(exp):
    rt_bins = {}
    for s in exp:
        if s.getMSLevel() == 1:
            continue
        tmp = rt_bins.get(int(s.getRT()), [])
        tmp.append(s)
        rt_bins[int(s.getRT())] = tmp
    return rt_bins


def get_spectrum(scan_number, exp, look):
    index = look.findByScanNumber(scan_number)
    return exp.getSpectrum(index)


def mapPeptideIdsToSpectra(peptide_ids, exp, look):
    hit_mapping = {}
    for i, pid in enumerate(peptide_ids):
        spectrum_id = pid.getMetaValue("spectrum_reference")
        scan_nr = int(spectrum_id[spectrum_id.rfind('=') + 1:])
        spectrum = get_spectrum(scan_nr, exp, look)
        hit_mapping[i] = spectrum
    return hit_mapping


#
# Filter the search results and create the mapping of search results to spectra
#
# filtered_ids = [p for p in peptide_ids if p.getHits()[0].getScore() >
#                 cutoff_score]
# # For teaching purposes, only ids betwen 1200 and 1600 s in RT are kept
# # (also the spectra are filtered)
# filtered_ids = [
#     p
#     for p in filtered_ids
#     if p.getMetaValue("RT") > 1200 and p.getMetaValue("RT") < 1600
# ]
filtered_ids = peptide_ids

print
"==========================================================================="
print
"Filtered: kept %s ids below the cutoff score of %s out of %s" % (
    len(filtered_ids),
    cutoff_score,
    len(peptide_ids),
)
hit_mapping = mapPeptideIdsToSpectra(filtered_ids, exp, look)

#
# Iterate through all peptide hits, extract the corresponding spectra and hand
# it to a scoring function.
#

# Writer CSV header
print
"Will print the original, search-engine sequence," \
" the AScore sequence and the PhosphoScorerSimple sequence"

writer.writerow(
    [
        "Search-Engine Score",
        "AScore",
        "AScore sequence",
        "Simple Scorer sequence",
        "Old Sequence",
        "# Sites",
    ]
)
for i in range(len(filtered_ids)):
    # Retrieve the input data:
    #  - the peptide hit from the search engine (we take the first hit here)
    #  - the corresponding spectrum
    phit = filtered_ids[i].getHits()[0]
    spectrum = hit_mapping[i]
    nr_sites = phit.getSequence().toString().count("Phospho")

    # Skip non-phospho hits
    if nr_sites == 0:
        continue

    ascore_result = PhosphoScorerAScore().score(phit, spectrum)

    # Store the resulting hit in our CSV file
    row = [
        phit.getScore(), ascore_result[0], ascore_result[1].toString(), phit.getSequence().toString(), nr_sites,
    ]
    writer.writerow(row)

fh.close()
