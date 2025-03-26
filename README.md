# FitsProcessor

## Functionality
Has the ability to create three different catalogs (position, shear, proxyshear) from a given huge catalog.
- Adds missing columns (values initialised with `np.zeroes()` for now) and deletes columns not required.
- Retains the unit and format from the original catalog, adds if missing.
- Added column reordering function (but it strips column info after execution. seems to be a bug with Astropy)

## Executing

### Step 1
Modify the contents of the `if __name__ == "__main__":` block according to requirements-

To generate the position catalog add:\
`fits_handler.generate_poscatalog(input_path=input_fits, output_path=output_fits, display_output=True)`

To generate the shear catalog add:\
`fits_handler.generate_shearcatalog(input_path=input_fits, output_path=output_fits, display_output=True)`

To generate the proxyshear catalog add:\
`fits_handler.generate_proxyshearcatalog(input_path=input_fits, output_path=output_fits, display_output=True)`

To just see the contents of a *.fits file add:\
`fits_handler.display_contents(input_path=input_fits)`

### Step 2

Save and run the script.\
The catalogs should now be generated!
