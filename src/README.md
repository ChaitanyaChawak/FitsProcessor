All the program scripts are stored in this `src` folder present at the root of the project directory.

File descriptions:

- `config/`\
Contains files describing the configurable parameters required for the package to run

- `example_run.py`\
Run this file to generate the catalogs

- `helpers.py`\
Contains functions that help in information extraction from the FitsDataModel schema file

- `script.py`\
Defines the main class and the primary functions for the generation of the data product fits file. The input columns are renamed ( as per _'src/config/column_mappings.yaml'_ ), matched, reordered and converted to the format given in the FitsDataModel; missing columns are added with zeros, extra columns are dropped and NaN values are replaced with zeros. The input file is streamed in chunks, so files larger than the available memory can be processed, and it is never modified. The output is saved in the _'generated'_ directory as <product_id>.fits

- `xmlgenerator.py`\
Generates the xml file corresponding to the generated product fits file. Takes input from _'src/config/XmlHeaderDetails.yaml'_. Also renames the fits file to match the xml filename.

- `validation.py`\
Script to validate the generated xml and fits files. If this is run immediately after _'src/example_run.py'_, it will consider the latest generated products for validation. In case custom products need to validated, modify the 'xml_filepath' and 'fits_filepath' parameters in _'src/config/XmlHeaderDetails.yaml'_
