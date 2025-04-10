# FitsProcessor

## Functionality

Has the ability to create three different catalogs (position, shear, proxyshear) from the sim fits file and the FitsDataModel xml file.

## Executing

See the `example_run.py` file, modify the `input_fits_path`, `output_dir` and `catalog` parameters according to requirements.

All the files that are required by the program (e.g. FitsDataModel.xml) should be in the 'raw' folder at the root of the project directory.

All the files generated from this program will be saved in the 'generated' folder present at the root of the project directory.

If you want to use a custom FitsDataModel xml file to generate the outputs, you can pass an additional `fitsDataModel_path` parameter in the `generate_catalog` function.

Run this modified `example_run.py` file and the catalogs should be generated!
