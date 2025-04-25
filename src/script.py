from astropy.io import fits
from astropy.table import Table
import numpy as np
from datetime import datetime
import json
from helpers import *

class FitsProcessor:
    def __init__(self):
        self.hdu_list = None

    def open_fits(self, input_fits_path):
        """
        Open the FITS file.

        Parameters:
        -----------
        input_fits_path : str
            Path of the input FITS file.
        
        """
        try:
            self.hdu_list = fits.open(input_fits_path, memmap=True)
            # print("\033[1mOpening the FITS file . . .\033[0m \n")
        except Exception as e:
            print(f"\033[1mError opening FITS file : {e}\033[0m \n")

    def close_fits(self):
        """
        Close the FITS file.
        
        Parameters:
        -----------
        None

        """
        if self.hdu_list:
            self.hdu_list.close()
            # print("\033[1mFITS file closed.\033[0m \n")

    def display_contents(self, input_fits_path):
        """
        Display the contents of the FITS file.

        Parameters:
        -----------
        input_fits_path : str
            Path of the input FITS file.

        """        
        try:
            self.open_fits(input_fits_path)

            print("\033[1mContent info :\033[0m \n")
            self.hdu_list.info()

            print("\033[1mHeader info :\033[0m \n")
            header1 = self.hdu_list[0].header
            header2 = self.hdu_list[1].header

            print(header1)
            print(header2)

            print("\033[1mColumn info :\033[0m \n")
            print(self.hdu_list[1].columns)

            print("\033[1mContent data :\033[0m \n")
            evt_data = Table(self.hdu_list[1].data)
            print(evt_data)

            self.close_fits()
            del self.hdu_list


        except Exception as e:
            print(f"\033[1mError displaying the contents of the FITS file : {e}\033[0m \n")

    def check_column_properties(self, column, catalog_info):
        """
        Checks if the columns in the existing FITS files have the proper unit and format as compared to the catalog. Only adds if it is missing. Does not convert. Returns new column object.

        Parameters:
        -----------
        column : class object
            Astropy class object of the input FITS file <class 'astropy.io.fits.column.ColDefs'>
        catalog_info : dict
            Dictionary of dictionaries containing information about the columns in the catalog. {'column1' : {'format' : 'D', 'unit' : 'deg'}}
        
        """
        for colname in column.names:
            col = column[colname]
            col_format = col.format
            col_unit = col.unit

            if col_format in ('', None): col.format = catalog_info[colname]['format']
            if col_unit in ('', None): col.unit = catalog_info[colname]['unit']
            
        return column


    def generate_catalog(self, product_id, input_fits_path, output_path=None, fitsDataModel_path=None, display_output=False):
        """
        Generate the desired CATALOG (either 'POS' or 'SHEAR' or 'PROXYSHEAR') from the input FITS file.

        Parameters:
        -----------
        product_id : str
            The product_id of catalog to be genrated (either 'POS' or 'SHEAR' or 'PROXYSHEAR')
        input_fits_path : str
            Path of the input FITS file.
        display_output : bool, optional, default = False
            display the output after catalog generation (if set to True)
        output_path : str, optional, default = None
            path where the output catalog is to be saved
        fitsDataModel_path : str, optional, default = None
            optional argument to get the fitsDataModel xml of a Data Product

        """
        start_time = datetime.now()

        try:
            # basic checks for the input params
            
            if output_path is None:
                print("\033[1mError: Please provide an output path to save the file.\033[0m \n")
                return

            # generate the json data file from FitsDataModel xml
            FitsFormat_ids = get_all_fits_format_ids(fitsDataModel_path=fitsDataModel_path)

            if product_id not in FitsFormat_ids:
                raise ValueError(f"Provided catalog type '{product_id}' is not in the FitsDataModel. \nDid you mean to use one of these? \n{FitsFormat_ids}")

            extract_data_for_id(product_id, fitsDataModel_path=fitsDataModel_path)

            # access the input fits file
            self.open_fits(input_fits_path)

            hdu = self.hdu_list[1]
            primary_hdu = self.hdu_list[0]

            # get the column names form the input catalog
            if isinstance(hdu, fits.BinTableHDU):
                columns = hdu.columns
                # print(columns)
                column_names = [col.name for col in columns]
                # print(f"Columns in input : {column_names}")
            else:
                print("The specified HDU does not contain a binary table.")
                return []


            ## get the column info from the json file
            json_file = f'generated/extracted_data_{product_id}.json'

            with open(json_file, 'r') as file:
                json_data = json.load(file)
            
            # extract the column list from the 'table_hdu' section
            table_hdu_info = json_data.get("table_hdu", {})
            columns_info = {}
            
            # check if 'columns' exists in the 'table_hdu'
            if "columns" in table_hdu_info:
                for column in table_hdu_info["columns"]:
                    column_name = column.get("name")
                    column_info = {
                        "format": column.get("format"),
                        "unit": column.get("unit"),
                        "comment": column.get("comment")
                    }
                    columns_info[column_name] = column_info


            catalog_colnames = list(columns_info.keys()) #this is the order in which the columns should appear
            # print(f"Columns required : {catalog_colnames}")


            # convert both lists to set to count the frequency of each element
            set_input = set(column_names)
            set_catalog = set(catalog_colnames)
            
            # Elements missing from input
            missing_from_input = list(set_catalog - set_input)
            
            # Excess elements in input
            excess_in_input = list(set_input - set_catalog)

            # print(f"Missing : {missing_from_input}")
            # print(f"Excess : {excess_in_input}")


            # modify the columns (add/remove if required) and then order them according to the FitsDataModel xml [this is done in-memory]
            for item in excess_in_input:
                columns.del_col(item)

            length_rows = hdu.header['NAXIS2']

            columns = self.check_column_properties(columns, columns_info)

            columns_to_add = []
            for item in missing_from_input:
                data = np.zeros(length_rows)
                format = columns_info[item]['format']
                unit = columns_info[item]['unit']
                newcol = fits.Column(name=item, format=format, unit=unit, array=data)
                columns_to_add.append(newcol)

            # print(f"Removed excess columns and added the missing ones ! \n")

            all_columns = columns + fits.ColDefs(columns_to_add)
            
            reordered_columns = [col for col_name in catalog_colnames
                                for col in all_columns
                                if col.name == col_name]

            # Create a new HDU with the reordered columns
            new_hdu = fits.BinTableHDU.from_columns(reordered_columns)

            table_hdu_info = json_data.get("table_hdu", {})
            table_hdu_name = table_hdu_info.get("name")

            new_hdu.header['EXTNAME'] = table_hdu_name
  
            output_hdu = fits.HDUList([primary_hdu, new_hdu])
            output_path = output_path + f'{product_id}.fits'
            output_hdu.writeto(output_path, overwrite=True)

            self.close_fits()
            del self.hdu_list


            if display_output:
                print("\033[1mTo display output\033[0m \n")
                self.display_contents(input_fits_path=output_path)

            print(f"\n\033[1mCatalog {product_id} generated successfully and saved to {output_path}.\033[0m \n")
            end_time = datetime.now()
            
            # calculate the time taken
            elapsed_time = end_time - start_time
            print(f"Execution time: {elapsed_time.total_seconds():.4f} seconds")

        except Exception as e:
            print(f"\033[1mError generating the catalog for {product_id} : {e}\033[0m \n")
