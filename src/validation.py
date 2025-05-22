import warnings
import yaml

from ST_DM_CheckXML.XmlValidator import XmlValidator
from ST_DataModelBindingsXsData.dictionary.bas.fit import FitsFormat
from ST_DataModelBindingsXsData.interfaces.bas.fit import FitsFormatList
from ST_DM_CheckFitsStructure.common import (
    get_format_list_from_path,
    get_format_version,
)
from ST_DM_CheckFitsStructure.validator import FitsValidator
from ST_DM_FitsSchema.SchemaApi import get_dm_schema_file_path

def validate_xml(xml_file_name, dm_version="10.1.1"):
    """
    Validate XML file against LE3-ID XML DM

    Parameters:
    ----------
    xml_file_name : str
        XML file name to be validated
    dm_version : str
        Data model version to be used for validation
    """
    validator = XmlValidator(dm_version)
    return validator.validate(xml_file_name)


def validate_fits_warns(fits_file_name, format_id):
    bad_results = validate_fits(fits_file_name, format_id)
    if len(bad_results) > 0:
        warnings.warn(f"Fits validation fails: {fits_file_name}", UserWarning)
        for res in bad_results:
            warnings.warn(res.comment, UserWarning)


def validate_fits(fits_file_name, format_id):
    """
    Validate fits file against LE3-ID fits DM

    Parameters:
    ----------
    fits_file_name : str
        Fits file name to be validated
    format_id : str
        Format ID to be used for validation. e.g. "le3.id.vmpz.output.poscatalog"
    """
    fits_format_list: FitsFormatList = None

    # Get all existing products format in DM
    dmref = "euc-le3-id.xml"
    xml_descriptor_dm_path = get_dm_schema_file_path("instances/fit/{0}".format(dmref))
    # print(f"XML descriptor DM path: {xml_descriptor_dm_path}")
    fits_format_list = get_format_list_from_path(xml_descriptor_dm_path)
    # print(fits_format_list)

    # Get product DM for format_id
    fits_format: FitsFormat = get_format_version(
        format_list=fits_format_list, format_id=format_id, version="0.1"
    )

    # Validate fits
    fits_validator = FitsValidator(fits_format=fits_format,
                                   fits_file=fits_file_name,
                                   ignore_extra_keywords=False,
                                   extra_keywords=["BUNIT", "TUNIT1", "TUNIT2", "TNULL1"])

    results = fits_validator.validate()

    # Extract bad results only
    bad_results = []
    for result in results:
        if not result.result:
            bad_results.append(result)

    return bad_results

# saving the xml file path in the yaml file
config_file = "./src/config/XmlHeaderDetails.yaml"
with open(config_file, 'r') as file:
    data = yaml.safe_load(file)

xml_file = data.get("xml_filepath", None)
fits_file = data.get("fits_filepath", None)
product_id = data.get("product_id", None)

print(f"\nValidating XML file: {xml_file}\n")
validate_xml(xml_file, "10.1.3")

print(f"\nValidating FITS file: {fits_file}\n")
validate_fits_warns(fits_file, product_id)
