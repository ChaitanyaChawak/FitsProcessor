import xml.etree.ElementTree as ET
import json

def get_all_fits_format_ids(fitsDataModel_path=None):
    """
    Gets a list of all the FitsFormat IDs from the FitsDataModel xml file

    Parameters:
    -----------
    fitsDataModel_path : str, optional, default = None
        optional argument to get the fitsDataModel xml of a Data Product

    Returns:
    -----------
    List of all the FitsFormat IDs
    
    """
    # check if the path is present else define what consider as the FitsDataModel xml
    if fitsDataModel_path is None:
        fitsDataModel_path = 'raw/FitsDataModel.xml'

    tree = ET.parse(fitsDataModel_path)
    root = tree.getroot()

    fits_formats = root.findall(".//FitsFormat")
    ids = [fits_format.get("id") for fits_format in fits_formats if fits_format.get("id") is not None]
    return ids

def extract_keywords(header_keyword_list):
    """
    Extracts header keywords from a GenericHDU or TableHDU

    Parameters:
    -----------
    header_keyword_list : list
        List of all the Header Keywords

    Returns:
    -----------
    List of dictionaries containing the information about the header (name, unit, comment). Defaults to null if not provided.
    
    """
    keywords = []
    for keyword in header_keyword_list:
        keyword_info = {
            "name": keyword.get("name"),
            "unit": keyword.get("unit"),
            "comment": keyword.get("comment")
        }
        keywords.append(keyword_info)
    return keywords

def extract_data_for_id(fits_format_id, fitsDataModel_path=None):
    """
    Extracts data corresponding to a particular FitsFormat ID from the Data Model XML file and dumps it to a JSON file.

    Parameters:
    -----------
    fits_format_id : str
        FitsFormat ID corresponding to which the data needs to be extracted from the XML
    fitsDataModel_path : str, optional, default = None
        optional argument to get the fitsDataModel xml of a Data Product

    """
    # check if the path is present else define what consider as the FitsDataModel xml
    if fitsDataModel_path is None:
        fitsDataModel_path = 'raw/FitsDataModel.xml'

    tree = ET.parse(fitsDataModel_path)
    root = tree.getroot()
    
    # Find the FitsFormat element by 'id' attribute
    fits_format = root.find(f".//FitsFormat[@id='{fits_format_id}']")

    if fits_format is not None:
        fits_format_info = {
            "id": fits_format.get("id"),
            "version": fits_format.get("version")
        }

        # Extract GenericHDU information
        generic_hdu_info = {}
        generic_hdu = fits_format.find(".//GenericHDU")
        if generic_hdu is not None:
            generic_hdu_info["name"] = generic_hdu.get("name")
            header_keyword_list = generic_hdu.find(".//HeaderKeywordList")
            if header_keyword_list is not None:
                generic_hdu_info["header_keywords"] = extract_keywords(header_keyword_list)

        # Extract TableHDU information
        table_hdu_info = {}
        table_hdu = fits_format.find(".//TableHDU")
        if table_hdu is not None:
            table_hdu_info["name"] = table_hdu.get("name")
            header_keyword_list = table_hdu.find(".//HeaderKeywordList")
            if header_keyword_list is not None:
                table_hdu_info["header_keywords"] = extract_keywords(header_keyword_list)

            # Extract column data
            columns = []
            column_list = table_hdu.find(".//ColumnList")
            if column_list is not None:
                for column in column_list.findall("Column"):
                    column_info = {
                        "name": column.get("name"),
                        "unit": column.get("unit"),
                        "format": column.get("format"),
                        "comment": column.get("comment")
                    }
                    columns.append(column_info)
            table_hdu_info["columns"] = columns

        # Combine all information
        extracted_data = {
            "fits_format": fits_format_info,
            "generic_hdu": generic_hdu_info,
            "table_hdu": table_hdu_info
        }

        # Save the extracted data as a JSON file
        output_filename = f"./generated/extracted_data_{fits_format_id}.json"
        with open(output_filename, "w") as json_file:
            json.dump(extracted_data, json_file, indent=4)

        print(f"Data successfully extracted and saved as '{output_filename}'.")
    else:
        print(f"No FitsFormat with id '{fits_format_id}' found in the XML.")
