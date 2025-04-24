# FitsProcessor

A program to create three different catalogs (position, shear, proxyshear) from the sim fits file and the FitsDataModel xml.

## Installation

To install the package, clone the repository, navigate to the project directory and run:

```bash
pip install .
```

## Configuration

Before running the program, modify the `src/config/inputs.yaml` file to specify the following parameters:
- input_fits_path
- product_id \
(Example: 'le3.id.vmpz.output.shearcatalog'; 'le3.id.vmpz.output.poscatalog'; 'le3.id.vmpz.output.proxyshearcatalog')
- data_model \
(Example: 'latest' OR '<specific_version>' (e.g. '9.2.3') OR '<path_to_file>' (e.g. 'raw/DataModel.xml'))
- fits_data_model \
(Example: 'latest' OR '<specific_version>' (e.g. '9.2.3') OR '<path_to_file>' (e.g. 'raw/FitsDataModel.xml'))
- display_output fits (bool)
- PAT (the Personal Access Token for your Gitlab account - with at least read permission)

All the files that are required by the program (e.g. FitsDataModel.xml) should be in the 'raw' folder at the root of the project directory.

All the files generated from this program will be saved in the 'generated' folder present at the root of the project directory.

## Executing

After configuring the inputs, run the program using:

```bash
python src/example_run.py
```

This will generate the catalogs based on the specified inputs.
