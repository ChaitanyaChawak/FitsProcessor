from astropy.io import fits
from astropy.table import Table
import numpy as np
from datetime import datetime


class FitsProcessor:
    def __init__(self):
        self.hdu_list = None

    def open_fits(self, input_path):
        """
        Open the FITS file.

        Parameters:
        -----------
        input_path : str
            Path of the input FITS file.
        
        """
        try:
            self.hdu_list = fits.open(input_path, memmap=True)
            print("\033[1mOpening the FITS file . . .\033[0m \n")
        except Exception as e:
            print(f"\033[1mError opening FITS file : {e}\033[0m \n")

    def save_as_new(self, output_path):
        """
        Save the modified FITS file to a new location.

        Parameters:
        -----------
        output_path : str
            The path where the modified FITS file should be saved.

        """
        if self.hdu_list is None:
            print("\033[1mNo FITS file loaded.\033[0m \n")
            return
        
        try:
            self.hdu_list.writeto(output_path, overwrite=True)
            print(f"\033[1mModified FITS file saved to {output_path}.\033[0m \n")
        except Exception as e:
            print(f"\033[1mError saving FITS file : {e}\033[0m \n")

    def close_fits(self):
        """
        Close the FITS file.
        
        Parameters:
        -----------
        None

        """
        if self.hdu_list:
            self.hdu_list.close()
            print("\033[1mFITS file closed.\033[0m \n")

    def display_contents(self, input_path):
        """
        Display the contents of the FITS file.

        Parameters:
        -----------
        input_path : str
            Path of the input FITS file.

        """        
        try:
            self.open_fits(input_path)

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


    
    def generate_poscatalog(self, input_path, output_path=None, display_output=False):
        """
        Generate the POS_CATALOG from the input FITS file.

        Parameters:
        -----------
        input_path : str
            Path of the input FITS file.
        display_output : bool, optional, default = False
            display the output after catalog generation (if set to True)
        save_file : bool, optional, default = False
            save the output to the given destination after catalog generation (if set to True)
        output_path : str, optional, default = None
            path where the output catalog is to be saved
        
        """
        start_time = datetime.now()

        try:
            if output_path is None:
                print("\033[1mError: Please provide an output path to save the file.\033[0m \n")
                return
            
            self.open_fits(input_path)

            hdu = self.hdu_list[1]
            primary_hdu = self.hdu_list[0]
            
            ## Step1 : 
            ## get the column names form the input catalog

            if isinstance(hdu, fits.BinTableHDU):
                columns = hdu.columns
                print(columns)
                column_names = [col.name for col in columns]
                # print(f"Columns in input : {column_names}")
            
            else:
                print("The specified HDU does not contain a binary table.")
                return []

            ## Step 2 :
            ## see if the columns are according the requirements

            poscatalog_info =   {
                                'RIGHT_ASCENSION': {'format': 'D', 'unit': 'deg'},
                                'DECLINATION': {'format': 'D', 'unit': 'deg'},
                                'POS_TOM_BIN_ID': {'format': 'J', 'unit': None},
                                'PHZ_WEIGHT': {'format': 'E', 'unit': None}
                                }
            
            poscatalog_colnames = list(poscatalog_info.keys()) #this is the order in which the columns should appear
            # print(f"Columns required : {poscatalog_colnames}")


            # Convert both lists to set to count the frequency of each element
            set_input = set(column_names)
            set_poscatalog = set(poscatalog_colnames)
            
            # Elements missing from input
            missing_from_input = list(set_poscatalog - set_input)
            
            # Excess elements in input
            excess_in_input = list(set_input - set_poscatalog)

            print(f"Missing : {missing_from_input}")
            print(f"Excess : {excess_in_input}")

            ## Step 3 :
            ## modify the columns (add/remove if required)

            for item in excess_in_input:
                columns.del_col(item)

            length_rows = hdu.header['NAXIS2']
            original_extname = hdu.header.get('EXTNAME', 'BINTABLE')

            columns = self.check_column_properties(columns, poscatalog_info)

            columns_to_add = []
            for item in missing_from_input:
                data = np.zeros(length_rows)
                format = poscatalog_info[item]['format']
                unit = poscatalog_info[item]['unit']
                newcol = fits.Column(name=item, format=format, unit=unit, array=data)
                columns_to_add.append(newcol)

            # print(f"Removed excess columns and added the missing ones ! \n")

            all_columns = columns + fits.ColDefs(columns_to_add)
            
            new_hdu = fits.BinTableHDU.from_columns(all_columns)
            new_hdu.header['EXTNAME'] = original_extname

            output_hdu = fits.HDUList([primary_hdu, new_hdu])
            output_hdu.writeto(output_path, overwrite=True)

            self.close_fits()
            del self.hdu_list


            if display_output:
                print("\033[1mTo display output\033[0m \n")
                self.display_contents(input_path=output_path)

            end_time = datetime.now()
            
            # Calculate the time taken
            elapsed_time = end_time - start_time
            print(f"Execution time: {elapsed_time.total_seconds():.4f} seconds")

        except Exception as e:
            print(f"\033[1mError generating the POS_CATALOG : {e}\033[0m \n")
        
        
    
    def generate_shearcatalog(self, input_path, output_path=None, display_output=False):
        """
        Generate the SHEAR_CATALOG from the input FITS file.

        Parameters:
        -----------
        input_path : str
            Path of the input FITS file.
        display_output : bool, optional, default = False
            display the output after catalog generation (if set to True)
        save_file : bool, optional, default = False
            save the output to the given destination after catalog generation (if set to True)
        output_path : str, optional, default = None
            path where the output catalog is to be saved
        
        """
        start_time = datetime.now()

        try:

            if output_path is None:
                print("\033[1mError: Please provide an output path to save the file.\033[0m \n")
                return
            
            self.open_fits(input_path)

            hdu = self.hdu_list[1]
            primary_hdu = self.hdu_list[0]
            
            ## Step1 : 
            ## get the column names form the input catalog

            if isinstance(hdu, fits.BinTableHDU):
                columns = hdu.columns
                column_names = [col.name for col in columns]
                # print(f"Columns in input : {column_names}")
            
            else:
                print("The specified HDU does not contain a binary table.")
                return []

            ## Step 2 :
            ## see if the columns are according the requirements

            shearcatalog_info =     {
                                    'OBJECT_ID': {'format': 'K', 'unit': None},
                                    'SHE_RA': {'format': 'D', 'unit': 'deg'},
                                    'SHE_DEC': {'format': 'D', 'unit': 'deg'},
                                    'SHE_E1_CORRECTED': {'format': 'E', 'unit': None},
                                    'SHE_E2_CORRECTED': {'format': 'E', 'unit': None},
                                    'SHE_E1': {'format': 'E', 'unit': None},
                                    'SHE_E2': {'format': 'E', 'unit': None},
                                    'SHE_M11': {'format': 'E', 'unit': None},
                                    'SHE_M12': {'format': 'E', 'unit': None},
                                    'SHE_M21': {'format': 'E', 'unit': None},
                                    'SHE_M22': {'format': 'E', 'unit': None},
                                    'SHE_C1': {'format': 'E', 'unit': None},
                                    'SHE_C2': {'format': 'E', 'unit': None},
                                    'SHE_PSF_E1': {'format': 'E', 'unit': None},
                                    'SHE_PSF_E2': {'format': 'E', 'unit': None},
                                    'SHE_PSF_R2': {'format': 'E', 'unit': None},
                                    'SHE_ALPHA1': {'format': 'E', 'unit': None},
                                    'SHE_ALPHA2': {'format': 'E', 'unit': None},
                                    'SHE_WEIGHT': {'format': 'E', 'unit': None},
                                    'PHZ_MEDIAN': {'format': 'E', 'unit': None},
                                    'PHZ_MODE_1': {'format': 'E', 'unit': None},
                                    'PHZ_MODE_2': {'format': 'E', 'unit': None},
                                    'TOM_BIN_ID': {'format': 'J', 'unit': None},
                                    'ALT_TOM_BIN_ID': {'format': 'J', 'unit': None}
                                    }
            
            shearcatalog_colnames = list(shearcatalog_info.keys()) #this is the order in which the columns should appear
            # print(f"Columns required : {shearcatalog_colnames}")


            # Convert both lists to set to count the frequency of each element
            set_input = set(column_names)
            set_shearcatalog = set(shearcatalog_colnames)
            
            # Elements missing from input
            missing_from_input = list(set_shearcatalog - set_input)
            
            # Excess elements in input
            excess_in_input = list(set_input - set_shearcatalog)

            # print(f"Missing : {missing_from_input}")
            # print(f"Excess : {excess_in_input}")

            ## Step 3 :
            ## modify the columns (add/remove if required)

            for item in excess_in_input:
                columns.del_col(item)

            # evt_data = Table(temp)
            length_rows = hdu.header['NAXIS2']
            original_extname = hdu.header.get('EXTNAME', 'BINTABLE')

            # check if all the column properties are present in the remaining data before adding new cols
            columns = self.check_column_properties(columns, shearcatalog_info)

            columns_to_add = []
            for item in missing_from_input:
                data = np.zeros(length_rows)
                format = shearcatalog_info[item]['format']
                unit = shearcatalog_info[item]['unit']
                newcol = fits.Column(name=item, format=format, unit=unit, array=data)
                columns_to_add.append(newcol)

            # print(f"Removed excess columns and added the missing ones ! \n")
            all_columns = columns + fits.ColDefs(columns_to_add)

            # save the output
            new_hdu = fits.BinTableHDU.from_columns(all_columns)
            new_hdu.header['EXTNAME'] = original_extname

            output_hdu = fits.HDUList([primary_hdu, new_hdu])
            output_hdu.writeto(output_path, overwrite=True)
            
            # self.save_as_new(output_path)
            self.close_fits()
            del self.hdu_list


            if display_output:
                print("\033[1mTo display output\033[0m \n")
                self.display_contents(input_path=output_path)

            end_time = datetime.now()
            
            # Calculate the time taken
            elapsed_time = end_time - start_time
            print(f"Execution time: {elapsed_time.total_seconds():.4f} seconds")


        except Exception as e:
            print(f"\033[1mError generating the SHEAR_CATALOG : {e}\033[0m \n")

        
    def generate_proxyshearcatalog(self, input_path, output_path=None, display_output=False):
        """
        Generate the PROXYSHEAR_CATALOG from the input FITS file.

        Parameters:
        -----------
        input_path : str
            Path of the input FITS file.
        display_output : bool, optional, default = False
            display the output after catalog generation (if set to True)
        save_file : bool, optional, default = False
            save the output to the given destination after catalog generation (if set to True)
        output_path : str, optional, default = None
            path where the output catalog is to be saved
        
        """
        start_time = datetime.now()

        try:
            self.open_fits(input_path)

            hdu = self.hdu_list[1]
            primary_hdu = self.hdu_list[0]
            
            ## Step1 : 
            ## get the column names form the input catalog

            if isinstance(hdu, fits.BinTableHDU):
                columns = hdu.columns
                column_names = [col.name for col in columns]
                # print(f"Columns in input : {column_names}")
            
            else:
                print("The specified HDU does not contain a binary table.")
                return []

            ## Step 2 :
            ## see if the columns are according the requirements

            if output_path is None:
                print("\033[1mError: Please provide an output path to save the file.\033[0m \n")
                return

            proxyshearcatalog_info =    {
                                        'RIGHT_ASCENSION': {'format': 'D', 'unit': 'deg'},
                                        'DECLINATION': {'format': 'D', 'unit': 'deg'},
                                        'G1': {'format': 'E', 'unit': None},
                                        'G2': {'format': 'E', 'unit': None},
                                        'TOM_BIN_ID': {'format': 'J', 'unit': None},
                                        'WEIGHT': {'format': 'E', 'unit': None}
                                        }
            
            proxyshearcatalog_colnames = list(proxyshearcatalog_info.keys()) #this is the order in which the columns should appear
            # print(f"Columns required : {proxyshearcatalog_colnames}")


            # Convert both lists to set to count the frequency of each element
            set_input = set(column_names)
            set_proxyshearcatalog = set(proxyshearcatalog_colnames)
            
            # Elements missing from input
            missing_from_input = list(set_proxyshearcatalog - set_input)
            
            # Excess elements in input
            excess_in_input = list(set_input - set_proxyshearcatalog)

            # print(f"Missing : {missing_from_input}")
            # print(f"Excess : {excess_in_input}")

            ## Step 3 :
            ## modify the columns (add/remove if required)

            for item in excess_in_input:
                columns.del_col(item)

            length_rows = hdu.header['NAXIS2']
            original_extname = hdu.header.get('EXTNAME', 'BINTABLE')

            # check if all the column properties are present in the remaining data before adding new cols
            
            columns = self.check_column_properties(columns, proxyshearcatalog_info)

            columns_to_append = []

            for item in missing_from_input:
                data = np.zeros(length_rows)
                format = proxyshearcatalog_info[item]['format']
                unit = proxyshearcatalog_info[item]['unit']
                newcol = fits.Column(name=item, format=format, unit=unit, array=data)
                columns_to_append.append(newcol)

            all_columns = columns + fits.ColDefs(columns_to_append)

            new_hdu = fits.BinTableHDU.from_columns(all_columns)
            new_hdu.header['EXTNAME'] = original_extname

            output_hdu = fits.HDUList([primary_hdu, new_hdu])
            output_hdu.writeto(output_path, overwrite=True)

            # self.save_as_new(output_path)
            self.close_fits()
            del self.hdu_list


            if display_output:
                print("\033[1mTo display output\033[0m \n")
                self.display_contents(input_path=output_path)

            end_time = datetime.now()
            
            # Calculate the time taken
            elapsed_time = end_time - start_time
            print(f"Execution time: {elapsed_time.total_seconds():.4f} seconds")


        except Exception as e:
            print(f"\033[1mError generating the PROXYSHEAR_CATALOG : {e}\033[0m \n")

      
        

if __name__ == "__main__":

    # input file path and the output path
    input_fits = 'path/to/input.fits'
    output_fits = 'path/to/save/generated.fits'

    fits_handler = FitsProcessor()

    fits_handler.display_contents(input_path=input_fits)
    fits_handler.generate_shearcatalog(input_path=input_fits, output_path=output_fits, display_output=True)


