import sys
import os
import datetime
import yaml
import argparse
import re
import xml.etree.ElementTree as ET
from xml.dom import minidom

sys.path.append('/cvmfs/euclid-dev.in2p3.fr/EDEN-3.1/opt/euclid/ST_DataModel/10.1.3/InstallArea/x86_64-conda_ry9-gcc11-o2g/python')
sys.path.append('/cvmfs/euclid-dev.in2p3.fr/EDEN-3.1/opt/euclid/ST_DataModel/10.1.3/InstallArea/x86_64-conda_ry9-gcc11-o2g/auxdir')

sys.path.append('/cvmfs/euclid-dev.in2p3.fr/EDEN-3.1/opt/euclid/ST_DataModelTools/10.2/InstallArea/x86_64-conda_ry9-gcc11-o2g/python')
sys.path.append('/cvmfs/euclid-dev.in2p3.fr/EDEN-3.1/opt/euclid/Elements/7.0.0/InstallArea/x86_64-conda_ry9-gcc11-o2g/python')

from xsdata.formats.dataclass.serializers import XmlSerializer
from xsdata.formats.dataclass.serializers.config import SerializerConfig
from xsdata.exceptions import SerializerError

from ST_DM_FilenameProvider.FilenameProvider import FileNameProvider

from ST_DataModelBindingsXsData.dictionary.bas import cat
from ST_DM_HeaderProvider.IdProvider import get_uuid_as_string
from ST_DataModelBindingsXsData.dictionary.sys import dss
from ST_DataModelBindingsXsData.dictionary.pro.le3.id import vmpz as vmpz_pro
from ST_DataModelBindingsXsData.dpd.le3.id.vmpz import out


from ST_DataModelBindingsXsData.dictionary.sys import (GenericHeader, ToBeChecked, ValidationStatus, Purpose)


#####################################

names_database = {
        'poscatalog': {'capitalised':'PosCatalog', 'shortname': 'Position', 'product': 'DpdWLPosCatalog', 'id': 'le3.id.vmpz.output.poscatalog'},
        'shearcatalog': {'capitalised':'ShearCatalog', 'shortname': 'Shear', 'product': 'DpdWLShearCatalog', 'id': 'le3.id.vmpz.output.shearcatalog'},
        'proxyshearcatalog': {'capitalised':'ProxyShearCatalog', 'shortname': 'ProxyShear', 'product': 'DpdWLProxyShearCatalog', 'id': 'le3.id.vmpz.output.proxyshearcatalog'}
    }

def extract_word_before_fits(filepath):
    """Extracts the word before ".fits" in the given file path.

    Parameters
    ----------
    filepath: str
        The file path from which to extract the word.

    Returns
    -------
    str
        The extracted word before ".fits" or None if not found."""
    
    match = re.search(r'\.([^.]+)\.fits$', filepath)
    return match.group(1) if match else None


def create_catalog(fits_file):
    """Creates the output catalog bindings.

    Parameters
    ------
    fits_file: str
        The name of the fits file to be wrapped in the binding.

    Returns
    -------
    object:
        The output catalog bindings.

    """
    catalog_name = extract_word_before_fits(fits_file)
    # print(f"Catalog name: {catalog_name}")
    

    if catalog_name not in names_database:
        raise ValueError(f"Invalid catalog name: {catalog_name}. Expected one of {list(names_database.keys())} for generating the xml.")
    
    # saving the product_id in the yaml file
    config_file = "./src/config/XmlHeaderDetails.yaml"
    with open(config_file, 'r') as file:
        data = yaml.safe_load(file)
    data['product_id'] = names_database[catalog_name]['id']
    with open(config_file, 'w') as file:
        yaml.dump(data, file)

    # Create the appropriate data product binding based on the catalog name
    if catalog_name == 'poscatalog':
        dpd = out.euc_le3_id_vmpz_pos_catalog.DpdWLPosCatalog()
    elif catalog_name == 'shearcatalog':
        dpd = out.euc_le3_id_vmpz_shear_catalog.DpdWLShearCatalog()
    elif catalog_name == 'proxyshearcatalog':
        dpd = out.euc_le3_id_vmpz_proxy_shear_catalog.DpdWLProxyShearCatalog()

    # Add the generic header to the data product
    dpd.Header = create_generic_header(names_database[catalog_name]['product'])

    #create simple data for the catalog based on the catalog name
    if catalog_name == 'poscatalog':
        dpd.Data = __create_simple_data(vmpz_pro.PosCatalogWL)
    elif catalog_name == 'shearcatalog':
        dpd.Data = __create_simple_data(vmpz_pro.WLShearCatalog)
    elif catalog_name == 'proxyshearcatalog':
        dpd.Data = __create_simple_data(vmpz_pro.ProxyShearCatalogWL)
        
    
    # Add the catalog descriptions
    description = cat.CatalogDescription()
    description.PathToCatalogFile = f"{names_database[catalog_name]['product']}.Data.{names_database[catalog_name]['capitalised']}.DataContainer.FileName"
    # description.PathToCatalogFile = f"DpdWLPosCatalog.Data.PosCatalog.DataContainer.FileName"
    description.CatalogType = "NOT_PROXY"
    description.CatalogOrigin = "OTHERS"
    description.CatalogOrigin = "MEASURED_WIDE"
    description.CatalogName = f"Le3-Id-Vmpz-Output-{names_database[catalog_name]['shortname']}-Catalog"
    description.CatalogFormatHDU = 1
    dpd.Data.CatalogDescription.append(description)


    # Add the files for the catalog bas based on the catalog name
    if catalog_name == 'poscatalog':
        dpd.Data.PosCatalog = __create_fits_storage(
            vmpz_pro.PosCatalogFile,
            fits_file,
            names_database[catalog_name]['id'],
            "0.1")
    elif catalog_name == 'shearcatalog':
        dpd.Data.ShearCatalog = __create_fits_storage(
            vmpz_pro.WLShearCatalogFile,
            fits_file,
            names_database[catalog_name]['id'],
            "0.1")
    elif catalog_name == 'proxyshearcatalog':   
        dpd.Data.ProxyShearCatalog = __create_fits_storage(
            vmpz_pro.ProxyShearCatalogWLFile,
            fits_file,
            names_database[catalog_name]['id'],
            "0.1")

    return dpd

def save_product_metadata(product, xml_file_name):
    """Saves an XML instance of a given data product.

    The XML instance will not be saved if the product does not validate the
    XML Schema.

    Parameters
    ----------
    product: object
        The product metadata information that should be saved.
    xml_file_name: str
        The name of the XML file where the product metadata will be saved.

    """

    config = SerializerConfig(pretty_print=True, encoding="UTF-8")
    serializer = XmlSerializer(config=config)

    try:
        with open(xml_file_name, "w") as f:
            serializer.write(f, product)
    except SerializerError as e:
       print("The product does not validate the XML Schema definition and "
                     "it will not be saved.")
       raise e


################################################################################

def filename_provider(instance_id=None, release=None, product=None):
    """Creates a filename provider binding.

    Parameters
    ----------
    instance_id: str, optional
        The instance ID. Default is None.
    release: str, optional
        The release version. Default is None.
    product: str
        The product name. Default is None.
        The product name should be one of the keys in the names_database dictionary.

    Returns
    -------
    object
        The filename provider binding.

    """
    product = extract_word_before_fits(product)
    filename = FileNameProvider().get_allowed_filename(
        processing_function='le3',
        type_name=f'{names_database[product]["capitalised"]}',
        instance_id=instance_id or '',
        release=release or '00.00',
        extension='.xml')

    return filename

def __create_simple_data(binding_class):
    data = binding_class()
    return data

def __create_fits_storage(binding_class, file_name, file_format, version):
    """Creates a fits file storage binding.

    Parameters
    ----------
    binding_class: class
        The fits file binding class.
    file_name: str
        The fits file name.
    file_format: str
        The fits file format.
    version: str
        The fits file format version.

    Returns
    -------
    object
        The fits file storage binding.

    """
    # Create the appropriate fits file storage binding
    storage = binding_class()

    # Fill it with the given values
    storage.format = file_format
    if version != "":
        storage.version = version
    storage.DataContainer = create_data_container(file_name)

    return storage


def create_data_container(file_name, file_status="PROPOSED"):
    """Creates a data container binding.

    Parameters
    ----------
    file_name: str
        The data file name.
    file_status: str, optional
        The status of the file: PROPOSED, PROCESSING, COMMITTED, VALIDATED,
        ARCHIVED or DELETED. Default is PROPOSED.

    Returns:
    --------
    object
        The data container binding.

    """
    # Create the data container binding
    data_container = dss.DataContainer()

    # Fill it with the given values
    data_container.FileName = file_name
    data_container.filestatus = file_status

    return data_container


def create_generic_header(product_type):
    """Creates a generic header binding.

    Parameters
    ----------
    product_type: str
        The product type.

    Returns
    -------
    object
        The generic header binding.

    """
    # path to the configuration file and read it
    config_file = "./src/config/XmlHeaderDetails.yaml"

    # Load the existing YAML file
    with open(config_file, 'r') as file:
        data = yaml.safe_load(file)

    
    # get the time
    now = datetime.datetime.now(datetime.timezone.utc)
    try:
        new_time = now.replace(year=now.year + 2)
    except ValueError:
        new_time = now.replace(year=now.year + 2, day=28)

    exp_time = new_time.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"
    creation_time = now.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"

    # Add a new element
    data['header.default.ExpirationDate'] = exp_time
    data['header.default.CreationDate'] = creation_time

    # Save the updated data back to the YAML file
    with open(config_file, 'w') as file:
        yaml.dump(data, file)


    conf = load_config(config_file)

    GenericHeaderContent = GenericHeader()
    GenericHeaderContent.ProductId = get_uuid_as_string()
    GenericHeaderContent.ProductType = product_type
    GenericHeaderContent.SoftwareName = conf.get("header.default.SoftwareName")
    GenericHeaderContent.SoftwareRelease = conf.get("header.default.SoftwareRelease")
    GenericHeaderContent.EuclidPipelineSoftwareRelease = conf.get(
        "header.default.EuclidPipelineSoftwareRelease"
    )
    GenericHeaderContent.ProdSDC = conf.get("header.default.ProdSDC")
    GenericHeaderContent.DataSetRelease = conf.get("header.default.DataSetRelease")
    GenericHeaderContent.Purpose = Purpose(conf.get("header.default.Purpose"))
    GenericHeaderContent.PlanId = get_uuid_as_string()
    GenericHeaderContent.PPOId = get_uuid_as_string()
    GenericHeaderContent.PipelineDefinitionId = conf.get(
        "header.default.PipelineDefinitionId"
    )
    GenericHeaderContent.PpoStatus = conf.get("header.default.PpoStatus")
    GenericHeaderContent.ManualValidationStatus = ValidationStatus(
        conf.get("header.default.ManualValidationStatus"))
    GenericHeaderContent.ProductNotifiedToBeChecked = ToBeChecked(
        conf.get("header.default.ProductNotifiedToBeChecked"))
    GenericHeaderContent.AutomatedValidationStatus = ValidationStatus(
        conf.get("header.default.AutomatedValidationStatus"))
    GenericHeaderContent.ExpirationDate = conf.get("header.default.ExpirationDate")
    GenericHeaderContent.ToBePublished = int(
        conf.get("header.default.ToBePublished")
    )
    GenericHeaderContent.Published = int(conf.get("header.default.Published"))
    GenericHeaderContent.Curator = conf.get("header.default.Curator")
    GenericHeaderContent.CreationDate = conf.get("header.default.CreationDate")

    return GenericHeaderContent


def load_config(config_path):
    """Load configuration from a YAML file.
    Parameters
    ----------
    config_path : str
        Path to the YAML configuration file.
    """
    with open(config_path, "r") as file:
        return yaml.safe_load(file)

def add_spatial_coverage(xml_file_name):
    """
    Create a catalog, save it as an XML file, and add the <SpatialCoverage> element
    before <CatalogDescription> in the <Data> section of the XML file.

    Parameters:
    -----------
    fits_file : str
        Path to the input FITS file.
    output_dir : str, optional
        Directory to save the generated XML file. Default is "generated/".
    """
    try:
        # Step 3: Parse the saved XML file
        tree = ET.parse(xml_file_name)
        root = tree.getroot()

        # Step 4: Find the <Data> element
        data_element = root.find("Data")
        if data_element is None:
            print("Error: <Data> element not found in the XML file.")
            return

        # Step 5: Create the <SpatialCoverage> element
        spatial_coverage = ET.Element("SpatialCoverage")
        polygon = ET.SubElement(spatial_coverage, "Polygon")

        # Define the vertices
        vertices = [
            {"C1": "0.0", "C2": "0.0"},
        ]

        for vertex in vertices:
            vertex_element = ET.SubElement(polygon, "Vertex")
            ET.SubElement(vertex_element, "C1").text = vertex["C1"]
            ET.SubElement(vertex_element, "C2").text = vertex["C2"]

        # Step 6: Insert <SpatialCoverage> before <CatalogDescription>
        catalog_description = data_element.find("CatalogDescription")
        if catalog_description is not None:
            data_element.insert(list(data_element).index(catalog_description), spatial_coverage)
        else:
            print("Error: <CatalogDescription> element not found in <Data>.")
            return

        # Step 7: Convert the modified XML tree to a string
        xml_string = ET.tostring(root, encoding="unicode")

        # Step 8: Pretty-print the XML using minidom
        pretty_xml = minidom.parseString(xml_string).toprettyxml(indent="  ")
        # Remove unnecessary blank lines
        lines = [line for line in pretty_xml.splitlines() if line.strip()]
        lines = "\n".join(lines)

        # Step 9: Write the formatted XML back to the file
        with open(xml_file_name, "w", encoding="UTF-8") as f:
            f.write(lines)

        print(f"Catalog created and saved to {xml_file_name} with <SpatialCoverage> added.")
    except Exception as e:
        print(f"Error creating catalog or adding <SpatialCoverage>: {e}")

 

def main(fits_file, output_dir="./generated/"):
    """
    Main function to create and save the catalog.

    Parameters:
    -----------
    fits_file : str
        Path to the input FITS file.
    output_dir : str, optional
        Directory to save the generated XML file. Default is "generated/".
    """
    try:
        
        # Create the catalog
        dpd = create_catalog(fits_file)

        # Save the product metadata to an XML file
        filename = filename_provider(product=fits_file)
        xml_file_name = f"{output_dir}{filename}"
        save_product_metadata(dpd, xml_file_name)
        add_spatial_coverage(xml_file_name)

        # renaming the fits file to the xml file name
        os.rename(fits_file, xml_file_name.replace(".xml", ".fits"))

        # saving the xml and fits file paths in the yaml file
        config_file = "./src/config/XmlHeaderDetails.yaml"
        with open(config_file, 'r') as file:
            data = yaml.safe_load(file)
        data['xml_filepath'] = xml_file_name
        data['fits_filepath'] = xml_file_name.replace(".xml", ".fits")
        with open(config_file, 'w') as file:
            yaml.dump(data, file)


        # print(f"Catalog created and saved to {xml_file_name}")
    except Exception as e:
        print(f"Error creating catalog: {e}")

if __name__ == "__main__":
    # Parse command-line arguments
    parser = argparse.ArgumentParser(description="Create and save a catalog from a FITS file.")
    parser.add_argument("fits_file", type=str, help="Path to the input FITS file.")
    parser.add_argument("--output_dir", 
                        type=str, 
                        default="./generated/", 
                        help="Directory to save the generated XML file."
                        )
    args = parser.parse_args()

    # Call the main function with the provided arguments
    main(args.fits_file, args.output_dir)
