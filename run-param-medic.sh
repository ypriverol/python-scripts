#!/bin/bash

# Check if the correct number of arguments were provided
if [ $# -ne 1 ]; then
    echo "Usage: run-param-medic.sh <input_file>"
    exit 1
fi

# Check if the input file exists
if [ ! -f "$1" ]; then
    echo "Error: $1 is not a valid file"
    exit 1
fi

# Convert raw file to mzML 
echo "Converting the raw file into mzML"
ThermoRawFileParser.sh -i=$1  -o=./ -f=2

# Replace the psi term of the software msconvert with thermorawfileparser 
echo "Replacing psi term for msconvert to ThermoRawFileParser"
sed 's/1003145/1000615/g' ${1%.raw}.mzML >> ${1%.raw}-fixed.mzML

# Run param medic to guess precursor and fragment tolerances
echo "Runing param medic to predic the precursor and fragment tolerances"
crux param-medic ${1%.raw}-fixed.mzML --overwrite T --pm-charges 2,3,4 --pm-min-peak-pairs 20

echo "Deleting the intermidiate files"
rm -rfv ${1%.raw}.mzML ${1%.raw}-fixed.mzML

echo "Modified file created: ${1%.*}_modified.${1##*.}"
