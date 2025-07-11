# FitsProcessor

A program to create three different catalogs (position, shear, proxyshear) from the sim fits file and the FitsDataModel xml.

![screenshot](screenshot.png)

## Installation

To install the package, clone the repository, navigate to the project directory and run:

```bash
pip install .
```

### Using Docker
If you have Docker installed already, you can download the Image for FitsProcessor from the DockerHub using the command
```bash
docker pull cchawak/fitsprocessor:v1.0 
```

Once the image is downloaded, you can run it using
```bash
docker run --rm -it cchawak/fitsprocessor:v1.0
```

This will open up a bash terminal allowing access to the container.

One final step before entering the execution phase is the activation of the venv. Run the following in the default dir (which should be '/workdir')
```bash
source .venv/bin/activate
```

## Configuration

Before running the program, modify the `src/config/inputs.yaml` file to specify the following parameters:
- input_fits_path
- product_id \
(Example: 'le3.id.vmpz.output.shearcatalog'; 'le3.id.vmpz.output.poscatalog'; 'le3.id.vmpz.output.proxyshearcatalog')
- fits_data_model \
(Example: 'latest' OR '<specific_version>' (e.g. '9.2.3') OR '<path_to_file>' (e.g. 'raw/FitsDataModel.xml'))
- display_output fits (bool)
- PAT (the Personal Access Token for your Gitlab account - with at least read permission)

The generic header configuration for the XML will be set as per the default values in `src/config/XmlHeaderDetails.yaml`. Modify only the 'header.default' values if necessary.

All the files that are required by the program (e.g. FitsDataModel.xml) should be in the 'raw' folder at the root of the project directory.

All the files generated from this program will be saved in the 'generated' folder present at the root of the project directory.

If PAT is being used to run the program, only the FITS data product will be generated. Generation of the corresponding XML file requires an access to the EDEN environment.

## Executing

After configuring the inputs, run the program using:

```bash
python src/example_run.py
```
This will generate the final product (fits + xml).

To run the validation script (for both fits and xml files) execute the following in EDEN environment:

```bash
ERun ST_DataModelTools 10.1.8 python src/validation.py
```

> NOTE : By default the last generated product by the `src/example_run.py` will be considered for validation. To choose a custom product, change the 'fits_filepath' and 'xml_filepath' parameters in the `src/config/XmlHeaderDetails.yaml` file.