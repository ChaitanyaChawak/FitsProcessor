from script import FitsProcessor

# input file path and the output dir
input_fits_path = 'path/to/input.fits'
output_dir = 'generated/'
catalog_type = 'PROXYSHEAR' # (either 'POS' or 'SHEAR' or 'PROXYSHEAR')

fits_handler = FitsProcessor()

# to display the contents of a fits file
fits_handler.display_contents(input_path=input_fits_path)

# to generate the catalog
fits_handler.generate_catalog(type=catalog_type, input_fits_path=input_fits_path, output_path=output_dir, display_output=True)
