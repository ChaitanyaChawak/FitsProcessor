This diretory contains the files describing configurable parameters required for the package to run.

- `inputs.yaml`\
Modify the contents of this file as per the requirements before executing _'src/example_run.py'_. The optional `header_values` section sets the values of header keywords required by the FitsDataModel (any required keyword left without a value is listed in the output).

- `column_mappings.yaml`\
Input column name -> catalog column name renames, per product ID. Add an entry here if the input file uses different column names than the FitsDataModel.

- `XmlHeaderDetails.yaml`\
Contains:
    - The default header details required to generate the product XML file.
    - Filepaths to the XML and Fits files that are required by _'src/validation.py'_.
    