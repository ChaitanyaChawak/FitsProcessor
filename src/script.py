from astropy.io import fits
from astropy.table import Table
import numpy as np
from datetime import datetime
import json
from helpers import *
import subprocess

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

    def create_xml(self, fits_file):
        """
        Run the xmlgenerator.py script to create and save the catalog.

        Parameters:
        -----------
        fits_file : str
            Path to the input FITS file.
        """
        try:
            subprocess.run(
                ["python", "./src/xmlgenerator.py", fits_file, "--output_dir", "./generated/"],
                check=True
            )
            # print(f"Catalog created and saved in generated/ dir.")
        except subprocess.CalledProcessError as e:
            print(f"Error creating XML: {e}")

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
        Checks if the columns in the existing FITS files have the proper format as compared to the catalog.
        Only updates and converts the format if necessary. Does not handle the unit.
        
        Parameters:
        -----------
        column : class object
            Astropy class object of the input FITS file <class 'astropy.io.fits.column.ColDefs'>
        catalog_info : dict
            Dictionary of dictionaries containing information about the columns in the catalog.
            {'column1': {'format': 'D'}}
            
        Returns:
        --------
        new_col : list
            A list of astropy class objects of the input FITS file <class 'astropy.io.fits.column.ColDefs'>
        """
        new_column = []
        for colname in column.names:
            col = column[colname]
            col_format = col.format
            col_unit = col.unit
            column_data = col.array  # Get the column data
            
            # If unit is not specified, set it as per catalog_info
            if col_unit in ('', None): col.unit = catalog_info[colname]['unit']

            # Check and update the format if it's missing or incorrect
            if col_format in ('', None):
                col.format = catalog_info[colname]['format']
            elif col_format != catalog_info[colname]['format']:
                # Format is different, update it
                col.format = catalog_info[colname]['format']
                print(f"\nUpdating column {colname} format from {col_format} to {col.format}\n")
                
                # Convert the column data to the new format
                if col.format == "K":  # 64-bit signed integer
                    column_data = column_data.astype(np.int64)
                elif col.format == "J":  # 32-bit signed integer
                    column_data = column_data.astype(np.int32)
                elif col.format == "E":  # 32-bit float
                    column_data = column_data.astype(np.float32)
                elif col.format == "D":  # 64-bit float
                    column_data = column_data.astype(np.float64)
                else:
                    raise ValueError(f"Unsupported target format: {col.format}")

            # Update the column with the converted data
            col = fits.Column(name=colname, format=col.format, unit=col.unit, array=column_data)

            new_column.append(col)
        
        return new_column

    
    def process_header(self, header, required_keywords):
        """
        Process the header to ensure it contains only the required keywords.

        Parameters:
        -----------
        header : astropy.io.fits.Header
            The header to be processed.
        required_keywords : list
            List of dictionaries containing the required keywords with their attributes.
        """
        # Remove excess keywords
        existing_keywords = list(header.keys())
        required_names = [kw["name"] for kw in required_keywords if "name" in kw]

        # print(f"Existing keywords: {existing_keywords}")
        # print(f"Required keywords: {required_names}")

        for key in existing_keywords:
            if key not in required_names and key not in ["SIMPLE", "BITPIX", "NAXIS", "EXTEND", "TTYPE22", "TTYPE23", "TTYPE24", "TFORM22", "TFORM23", "TFORM24"]:
                # print(f"Removing keyword: {key}")
                del header[key]

        # Add missing keywords and set the type
        for kw in required_keywords:
            name = kw.get("name")
            if name:
                # Set the value of the keyword based on its type
                value = None
                if "type" in kw and kw["type"] is not None:
                    keyword_type = kw["type"].lower()
                    if keyword_type == "string":
                        value = ""

                # Add the keyword to the header if it doesn't exist
                if name not in header:
                    header[name] = value

                # Set the comment if provided
                if "comment" in kw and kw["comment"]:
                    header.comments[name] = kw["comment"]


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
            
            # Rename specific columns for the 'proxyshear' product ID
            if product_id == "le3.id.vmpz.output.proxyshearcatalog":
                rename_map = {
                    "SHE_RA": "RIGHT_ASCENSION",
                    "SHE_DEC": "DECLINATION",
                    "SHE_G1": "G1",
                    "SHE_G2": "G2",
                    "SHE_WEIGHT": "WEIGHT"
                }

                for old_name, new_name in rename_map.items():
                    if old_name in column_names:
                        # If the new name already exists, delete it
                        if new_name in column_names:
                            columns.del_col(new_name)
                            column_names.remove(new_name)

                        # Rename the column
                        col_index = column_names.index(old_name)
                        columns[col_index].name = new_name
                        column_names[col_index] = new_name


            ## get the column info from the json file
            json_file = f'./generated/extracted_data_{product_id}.json'

            with open(json_file, 'r') as file:
                json_data = json.load(file)
            
            # extract the column list from the 'table_hdu' section
            table_hdu_info = json_data.get("table_hdu", {})
            columns_info = {}
            
            # check if 'columns' exists in the 'table_hdu'
            if "columns" in table_hdu_info:
                for column in table_hdu_info["columns"]:
                    unit = column.get("unit")
                    if unit == "NA" and (product_id == "le3.id.vmpz.output.poscatalog" or product_id == "le3.id.vmpz.output.proxyshearcatalog"):
                        unit = None
                    column_name = column.get("name")
                    column_info = {
                        "format": column.get("format"),
                        "unit": unit,
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

            # print(f"Columns to add : {[col.name for col in columns_to_add]}")
            # print(f"Columns already present : {[col.name for col in columns]}")

            # Combine existing and new columns
            all_columns = fits.ColDefs(columns + columns_to_add)

            reordered_columns = [col for col_name in catalog_colnames
                                for col in all_columns
                                if col.name == col_name]

            # Create a new HDU with the reordered columns
            new_hdu = fits.BinTableHDU.from_columns(reordered_columns)

            table_hdu_info = json_data.get("table_hdu", {})
            table_hdu_name = table_hdu_info.get("name")

            new_hdu.header['EXTNAME'] = table_hdu_name

            self.process_header(primary_hdu.header, json_data.get("generic_hdu", [])["header_keywords"])
            self.process_header(new_hdu.header, json_data.get("table_hdu", [])["header_keywords"])

            # print(new_hdu)
  
            output_hdu = fits.HDUList([primary_hdu, new_hdu])
            output_path = output_path + f'{product_id}.fits'
            output_hdu.writeto(output_path, overwrite=True)

            self.close_fits()
            del self.hdu_list

            print(f"\033[1mFits file generated successfully and saved in './generated/' dir .\033[0m \n")

            if display_output:
                print("\033[1mTo display output\033[0m \n")
                self.display_contents(input_fits_path=output_path)
            
            # create the XML file using the xmlgenerator.py logic
            self.create_xml(output_path)

            end_time = datetime.now()
            
            # calculate the time taken
            elapsed_time = end_time - start_time
            print(f"Execution time: {elapsed_time.total_seconds():.4f} seconds")

        except Exception as e:
            print(f"\033[1mError generating the catalog for {product_id} : {e}\033[0m \n")
