from astropy.io import fits
from astropy.table import Table
import numpy as np
import json
import yaml
from helpers import *
import subprocess
import sys
import os
import time
import warnings
from tqdm import tqdm
import console

class FitsProcessor:
    def __init__(self):
        self.hdu_list = None
        self.chunk_bytes = 64 * 1024**2  # Output bytes processed per chunk (64 MB)

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
        except Exception as e:
            console.error(f"Error opening FITS file: {e}")

    def close_fits(self):
        """
        Close the FITS file.

        Parameters:
        -----------
        None

        """
        if self.hdu_list:
            self.hdu_list.close()

    def create_xml(self, fits_file, product_id):
        """
        Run the xmlgenerator.py script to create and save the catalog.

        Parameters:
        -----------
        fits_file : str
            Path to the input FITS file.
        product_id : str
            FitsDataModel product ID of the FITS file.

        Returns:
        --------
        (xml_path, fits_path) : tuple of str
            Final paths of the XML file and of the (renamed) FITS file, or None if the XML could not be generated.
        """
        result = subprocess.run(
            [sys.executable, "./src/xmlgenerator.py", fits_file, "--output_dir", "./generated/",
             "--product_id", product_id],
            capture_output=True, text=True
        )
        if result.returncode != 0:
            lines = [line.strip() for line in (result.stderr + result.stdout).splitlines() if line.strip()]
            reason = lines[-1] if lines else f"exit status {result.returncode}"
            if "No module named" in reason:
                reason += " (the EDEN environment is required)"
            console.error(f"XML not generated: {reason}")
            return None

        # xmlgenerator.py saves the final file paths in the yaml file
        with open("./src/config/XmlHeaderDetails.yaml", 'r') as file:
            data = yaml.safe_load(file)
        return data['xml_filepath'], data['fits_filepath']

    def display_contents(self, input_fits_path, max_rows=100):
        """
        Display the contents of the FITS file (limited rows for large files).

        Parameters:
        -----------
        input_fits_path : str
            Path of the input FITS file.
        max_rows : int, optional, default = 100
            Number of table rows to display.

        """
        try:
            self.open_fits(input_fits_path)

            print(f"\n{console.bold('Content info')}")
            self.hdu_list.info()

            print(f"\n{console.bold('Primary header')}")
            print(self.hdu_list[0].header.tostring(sep="\n").rstrip())
            print(f"\n{console.bold('Table header')}")
            print(self.hdu_list[1].header.tostring(sep="\n").rstrip())

            print(f"\n{console.bold('Column info')}")
            print(self.hdu_list[1].columns)

            print(f"\n{console.bold(f'Content data (first {max_rows} rows)')}")
            evt_data = Table(self.hdu_list[1].data[:max_rows])
            print(evt_data)

            self.close_fits()
            self.hdu_list = None

        except Exception as e:
            console.error(f"Error displaying the contents of the FITS file: {e}")

    def load_rename_map(self, product_id, mapping_file="./src/config/column_mappings.yaml"):
        """
        Load the input -> catalog column renames for a product from the config.

        Parameters:
        -----------
        product_id : str
            Product ID, e.g. 'le3.id.vmpz.output.poscatalog'
        mapping_file : str, optional
            Path to the YAML file containing the rename maps.

        Returns:
        --------
        rename_map : dict
            {input_column_name: catalog_column_name}
        """
        with open(mapping_file, 'r') as file:
            mappings = yaml.safe_load(file) or {}
        return mappings.get(product_id) or {}

    def build_column_plan(self, input_columns, rename_map, columns_info):
        """
        Match the catalog columns against the input columns.
        Extra input columns are dropped and the catalog column order is used.

        Parameters:
        -----------
        input_columns : astropy.io.fits.ColDefs
            Columns of the input table.
        rename_map : dict
            {input_column_name: catalog_column_name}
        columns_info : dict
            Dictionary of dictionaries containing information about the columns in the catalog.
            {'column1': {'format': 'D', 'unit': 'deg', 'comment': '...'}}

        Returns:
        --------
        plan : list
            List of (catalog_column_name, input_column or None), in catalog order.
        """
        input_by_name = {col.name: col for col in input_columns}
        source = {name: col for name, col in input_by_name.items() if name in columns_info}
        # A renamed column takes precedence over an input column that already has the catalog name
        for old_name, new_name in rename_map.items():
            if old_name in input_by_name and new_name in columns_info:
                source[new_name] = input_by_name[old_name]

        return [(name, source.get(name)) for name in columns_info]

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

        protected_keywords = ["SIMPLE", "BITPIX", "NAXIS", "EXTEND", "XTENSION",
                             "TFIELDS", "PCOUNT", "GCOUNT", "NAXIS1", "NAXIS2"]

        for key in existing_keywords:
            if (key not in required_names and
                key not in protected_keywords and
                not key.startswith(('TTYPE', 'TFORM', 'TUNIT'))):
                try:
                    del header[key]
                except KeyError:
                    pass

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

    def apply_header_values(self, header, values, required_keywords, hdu_label, other_keywords=()):
        """
        Set header keyword values given in the configuration (e.g. NSIDE, ORDERING).
        Only keywords required by the FitsDataModel are set; configured values take precedence over the input file.

        Parameters:
        -----------
        header : astropy.io.fits.Header
            The header to be updated.
        values : dict
            {keyword: value} from the configuration.
        required_keywords : list
            List of dictionaries containing the required keywords with their attributes.
        hdu_label : str
            'primary' or 'table', used in messages.
        other_keywords : list, optional
            Required keywords of the other HDU, used to point out keywords given in the wrong section.
        """
        required_names = {kw["name"] for kw in required_keywords if kw.get("name")}
        other_names = {kw["name"] for kw in other_keywords if kw.get("name")}
        other_label = 'table' if hdu_label == 'primary' else 'primary'
        for key, value in (values or {}).items():
            key = str(key).upper()
            if key in required_names:
                header[key] = value
            elif key in other_names:
                console.warn(f"header_values.{hdu_label}.{key} belongs under header_values.{other_label}, ignored")
            else:
                console.warn(f"header_values.{hdu_label}.{key} is not a keyword of this product in the FitsDataModel, ignored")

    def empty_keywords(self, header, required_keywords):
        """Returns the required keywords that have no value in the header."""
        return [kw["name"] for kw in required_keywords
                if kw.get("name") and kw["name"] in header and header[kw["name"]] in (None, "")]

    def write_catalog(self, input_fits_path, output_file_path, column_plan, columns_info,
                      table_hdu_name, primary_keywords, table_keywords, header_values=None):
        """
        Write the catalog FITS file by streaming the input table in row chunks.
        The input is read once and the output written once, so memory use is bounded
        by chunk_bytes. NaN values are replaced with zeros and columns are converted
        to the catalog format. The output is written to a temporary file and only
        moved into place once complete; the input file is never modified.

        Parameters:
        -----------
        input_fits_path : str
            Path of the input FITS file.
        output_file_path : str
            Path of the output FITS file.
        column_plan : list
            List of (catalog_column_name, input_column or None) from build_column_plan.
        columns_info : dict
            Catalog column information (format, unit, comment).
        table_hdu_name : str
            EXTNAME of the output table HDU.
        primary_keywords, table_keywords : list
            Required header keywords of the primary and table HDUs.
        header_values : dict, optional
            {'primary': {keyword: value}, 'table': {keyword: value}} to set in the output headers.
        """
        header_values = header_values or {}
        tmp_path = output_file_path + ".tmp"

        try:
            with fits.open(input_fits_path, memmap=True, mode='readonly') as hdul:
                primary_header = hdul[0].header.copy()
                input_hdu = hdul[1]
                if not isinstance(input_hdu, fits.BinTableHDU):
                    raise ValueError("The specified HDU does not contain a binary table.")
                if input_hdu.header.get('PCOUNT', 0) or primary_header.get('NAXIS', 0):
                    raise NotImplementedError("Variable-length columns or primary HDU data are not supported.")

                total_rows = input_hdu.header['NAXIS2']
                data_offset = hdul.fileinfo(1)['datLoc']
                # ColDefs.dtype is native-endian; on-disk FITS data is big-endian
                input_dtype = np.dtype(input_hdu.columns.dtype).newbyteorder('>')

                # Build the output table header (no data rows allocated)
                coldefs = []
                for col_name, input_col in column_plan:
                    unit = columns_info[col_name]['unit']
                    if unit is None and input_col is not None:
                        unit = input_col.unit
                    coldefs.append(fits.Column(name=col_name, format=columns_info[col_name]['format'], unit=unit))

                output_hdu = fits.BinTableHDU.from_columns(fits.ColDefs(coldefs), nrows=0)
                output_header = output_hdu.header
                output_header['EXTNAME'] = table_hdu_name
                output_header['NAXIS2'] = total_rows

                self.process_header(primary_header, primary_keywords)
                self.process_header(output_header, table_keywords)
                # Keep the table HDU name even if the product's keyword list does not include EXTNAME
                if table_hdu_name and 'EXTNAME' not in output_header:
                    output_header['EXTNAME'] = table_hdu_name

                self.apply_header_values(primary_header, header_values.get('primary'), primary_keywords, 'primary', table_keywords)
                self.apply_header_values(output_header, header_values.get('table'), table_keywords, 'table', primary_keywords)
                empty_primary = self.empty_keywords(primary_header, primary_keywords)
                empty_table = self.empty_keywords(output_header, table_keywords)
                if empty_primary or empty_table:
                    console.warn("Required header keywords without a value (set them under 'header_values' in inputs.yaml):")
                    if empty_primary:
                        console.info_list("primary", empty_primary)
                    if empty_table:
                        console.info_list("table", empty_table)

                for i, (col_name, _) in enumerate(column_plan, start=1):
                    comment = columns_info[col_name].get('comment')
                    if comment:
                        output_header.comments[f'TTYPE{i}'] = comment

                # Render the headers once; report astropy's comment truncation as a single message
                with warnings.catch_warnings(record=True) as caught:
                    warnings.simplefilter("always", fits.verify.VerifyWarning)
                    header_bytes = (primary_header.tostring() + output_header.tostring()).encode('ascii')
                if any("truncated" in str(w.message) for w in caught):
                    console.warn("Some column comments are longer than a FITS card allows and were truncated")

                output_width = output_header['NAXIS1']
                output_dtype = np.dtype(output_hdu.columns.dtype).newbyteorder('>')
                if output_dtype.itemsize != output_width:
                    raise ValueError("Unexpected table row layout.")

                input_rows = np.memmap(input_fits_path, dtype=input_dtype, mode='r',
                                       offset=data_offset, shape=(total_rows,))
                chunk_rows = max(1, self.chunk_bytes // output_width)
                num_chunks = (total_rows + chunk_rows - 1) // chunk_rows

                buffer = np.zeros(chunk_rows, dtype=output_dtype)  # missing columns stay zero
                nan_columns = set()

                with open(tmp_path, 'wb') as outfile:
                    outfile.write(header_bytes)

                    for chunk_idx in tqdm(range(num_chunks), desc="Writing", bar_format=console.BAR_FORMAT,
                                          ncols=console.term_width()):
                        start_row = chunk_idx * chunk_rows
                        end_row = min(start_row + chunk_rows, total_rows)
                        n_rows = end_row - start_row
                        chunk = buffer[:n_rows]
                        source = input_rows[start_row:end_row]

                        for col_name, input_col in column_plan:
                            if input_col is None:
                                continue
                            values = source[input_col.name]
                            if input_col.bscale not in (None, 1) or input_col.bzero not in (None, 0):
                                values = values * (input_col.bscale or 1) + (input_col.bzero or 0)

                            if values.dtype.kind == 'f':
                                if output_dtype[col_name].kind != 'f':
                                    values = values.astype(values.dtype.newbyteorder('='))
                                    nan_mask = np.isnan(values)
                                    if nan_mask.any():
                                        values[nan_mask] = 0
                                        nan_columns.add(col_name)
                                    chunk[col_name] = values
                                else:
                                    chunk[col_name] = values
                                    col_data = chunk[col_name]
                                    nan_mask = np.isnan(col_data)
                                    if nan_mask.any():
                                        col_data[nan_mask] = 0
                                        nan_columns.add(col_name)
                            else:
                                chunk[col_name] = values

                        outfile.write(chunk.data)

                    # Pad the data section to a full FITS block
                    outfile.write(b'\0' * (-total_rows * output_width % 2880))

                del input_rows

            os.replace(tmp_path, output_file_path)
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

        return nan_columns

    def generate_catalog(self, product_id, input_fits_path, output_path=None, fitsDataModel_path=None, display_output=False, PAT=False,
                         header_values=None):
        """
        Generate the desired CATALOG

        Parameters:
        -----------
        product_id : str
            Product ID, e.g. 'le3.id.vmpz.output.poscatalog'
        input_fits_path : str
            Path of the input FITS file.
        output_path : str, optional, default = None
            Directory where the generated '<product_id>.fits' is saved.
        fitsDataModel_path : str, optional, default = None
            Path of the FitsDataModel xml.
        display_output : bool, optional, default = False
            Display the contents of the generated FITS file.
        PAT : bool, optional, default = False
            If True, only the FITS file is generated (no XML).
        header_values : dict, optional, default = None
            Values for required header keywords: {'primary': {keyword: value}, 'table': {keyword: value}}.

        Returns:
        --------
        output_file_path : str
            Path of the generated FITS file, or None if the generation failed.
        """

        start_time = time.perf_counter()
        total_steps = 3 if PAT else 4

        try:
            if output_path is None:
                console.error("Please provide an output path to save the file.")
                return

            # generate the json data file from FitsDataModel xml
            console.step(1, total_steps, "Loading the FitsDataModel")
            FitsFormat_ids = get_all_fits_format_ids(fitsDataModel_path=fitsDataModel_path)
            if product_id not in FitsFormat_ids:
                raise ValueError(f"Provided catalog type '{product_id}' is not in the FitsDataModel.")

            extract_data_for_id(product_id, fitsDataModel_path=fitsDataModel_path)

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
                    if unit == "NA" and product_id in ["le3.id.vmpz.output.poscatalog",
                                                       "le3.id.vmpz.output.proxyshearcatalog"]:
                        unit = None
                    column_name = column.get("name")
                    columns_info[column_name] = {
                        "format": column.get("format"),
                        "unit": unit,
                        "comment": column.get("comment")
                    }

            # match the input columns with the catalog columns (this is the order in which the columns should appear)
            rename_map = self.load_rename_map(product_id)
            with fits.open(input_fits_path, memmap=True, mode='readonly') as hdul:
                input_columns = hdul[1].columns
                total_rows = hdul[1].header['NAXIS2']
            column_plan = self.build_column_plan(input_columns, rename_map, columns_info)

            used = {input_col.name for _, input_col in column_plan if input_col is not None}
            missing_from_input = [name for name, input_col in column_plan if input_col is None]
            excess_in_input = [name for name in input_columns.names if name not in used]
            renamed = [(input_col.name, name) for name, input_col in column_plan
                       if input_col is not None and input_col.name != name]

            converted = [f"{input_col.name} ({input_col.format}→{columns_info[name]['format']})"
                         for name, input_col in column_plan
                         if input_col is not None and input_col.format != columns_info[name]['format']]

            console.info("Catalog", f"{table_hdu_info.get('name')}  ·  {len(column_plan)} columns")
            console.success("FitsDataModel loaded")

            console.step(2, total_steps, "Matching columns")
            console.info("Input", f"{total_rows:,} rows × {len(input_columns)} columns")
            if renamed:
                console.info("Renamed", f"{renamed[0][0]} → {renamed[0][1]}")
                for old_name, new_name in renamed[1:]:
                    console.item(f"{old_name} → {new_name}")
            if missing_from_input:
                console.info_list("Added (zeros)", missing_from_input)
            if excess_in_input:
                console.info_list("Dropped", excess_in_input)
            if converted:
                console.info_list("Converted", converted)
            console.success(f"{len(column_plan) - len(missing_from_input)} of {len(column_plan)} catalog columns found in the input")

            console.step(3, total_steps, "Writing the FITS file")
            output_file_path = output_path + f'{product_id}.fits'
            nan_columns = self.write_catalog(
                input_fits_path,
                output_file_path,
                column_plan,
                columns_info,
                table_hdu_info.get("name"),
                json_data.get("generic_hdu", {}).get("header_keywords", []),
                table_hdu_info.get("header_keywords", []),
                header_values
            )
            if nan_columns:
                console.info_list("NaN → 0", sorted(nan_columns))
            output_size = os.path.getsize(output_file_path)
            console.success(f"FITS file written ({console.format_size(output_size)})")

            if display_output:
                print(f"\n{console.bold('Output preview')}")
                self.display_contents(input_fits_path=output_file_path)

            # create the XML file using the xmlgenerator.py logic
            xml_file_path = None
            if not PAT:
                console.step(4, total_steps, "Generating the XML file")
                xml_paths = self.create_xml(output_file_path, product_id)
                if xml_paths:
                    xml_file_path, output_file_path = xml_paths
                    console.success("XML file generated and FITS file renamed to match")

            elapsed_time = time.perf_counter() - start_time

            if xml_file_path:
                xml_row = xml_file_path
            elif PAT:
                xml_row = console.yellow("not generated (needs the EDEN environment)")
            else:
                xml_row = console.red("not generated (see the error above)")
            console.box("Done  \\( ﾟヮﾟ)/", [
                ("FITS", console.bold(output_file_path)),
                ("XML", console.bold(xml_row) if xml_file_path else xml_row),
                ("Rows", f"{total_rows:,} × {len(column_plan)} columns"),
                ("Size", console.format_size(output_size)),
                ("Time", console.format_duration(elapsed_time)),
            ])

            return output_file_path

        except Exception as e:
            console.error(f"Error generating the catalog for {product_id}: {e}")
