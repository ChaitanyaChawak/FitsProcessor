# FitsProcessor

A program to create three different catalogs (position, shear, proxyshear) from the sim fits file and the FitsDataModel xml.

## Installation

To install the package, clone the repository, navigate to the project directory and run:

```bash
pip install .
```

## Configuration

Before running the program, modify the `src/config/inputs.yaml` file to specify the input parameters. Make sure that it has the following parameters:
- input_fits_path
- output_directory
- catalog_type
- fits_data_model
- display_output

All the files that are required by the program (e.g. FitsDataModel.xml) should be in the 'raw' folder at the root of the project directory.

All the files generated from this program will be saved in the 'generated' folder present at the root of the project directory.

## Executing

After configuring the inputs, run the program using:

```bash
python src/example_run.py
```

This will generate the catalogs based on the specified inputs.