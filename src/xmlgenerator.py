import sys
import os
import datetime
import yaml
import argparse
import console
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

# Products supported by the XML generation, keyed by their FitsDataModel product ID.
# To add a product, add an entry with:
#   capitalised : type name used for the file name and in PathToCatalogFile (Data.<capitalised>.DataContainer.FileName)
#   shortname   : used in the CatalogName (Le3-Id-Vmpz-Output-<shortname>-Catalog)
#   product     : data product type written in the generic header
#   dpd, data, file : binding classes from ST_DataModelBindingsXsData for the data product, its Data and its FITS file
#   file_field  : name of the Data field that holds the FITS file
#   extra_data  : any other Data fields to set
names_database = {
    'le3.id.vmpz.output.poscatalog': {
        'capitalised': 'PosCatalog', 'shortname': 'Position', 'product': 'DpdWLPosCatalog',
        'dpd': out.euc_le3_id_vmpz_pos_catalog.DpdWLPosCatalog,
        'data': vmpz_pro.PosCatalogWL, 'file': vmpz_pro.PosCatalogFile,
        'file_field': 'PosCatalog', 'extra_data': {}},
    'le3.id.vmpz.output.shearcatalog': {
        'capitalised': 'ShearCatalog', 'shortname': 'Shear', 'product': 'DpdWLShearCatalog',
        'dpd': out.euc_le3_id_vmpz_shear_catalog.DpdWLShearCatalog,
        'data': vmpz_pro.WLShearCatalog, 'file': vmpz_pro.WLShearCatalogFile,
        'file_field': 'ShearCatalog', 'extra_data': {'SheEstimationMethod': 'Generic'}},
    'le3.id.vmpz.output.proxyshearcatalog': {
        'capitalised': 'ProxyShearCatalog', 'shortname': 'ProxyShear', 'product': 'DpdWLProxyShearCatalog',
        'dpd': out.euc_le3_id_vmpz_proxy_shear_catalog.DpdWLProxyShearCatalog,
        'data': vmpz_pro.ProxyShearCatalogWL, 'file': vmpz_pro.ProxyShearCatalogWLFile,
        'file_field': 'ProxyShearCatalog', 'extra_data': {}},
}

def get_product_info(product_id):
    """Returns the names_database entry of a product, with a clear error if XML generation is not set up for it."""
    if product_id not in names_database:
        raise ValueError(f"XML generation is not set up for '{product_id}'. Add it to names_database in src/xmlgenerator.py "
                         f"(supported: {', '.join(names_database)}).")
    return names_database[product_id]


def create_catalog(product_id, file_name):
    """Creates the output catalog bindings.

    Parameters
    ------
    product_id: str
        The FitsDataModel product ID, e.g. 'le3.id.vmpz.output.poscatalog'
    file_name: str
        The name of the generated file
    Returns
    -------
    object:
        The output catalog bindings.

    """
    info = get_product_info(product_id)

    # saving the product_id in the yaml file
    config_file = "./src/config/XmlHeaderDetails.yaml"
    with open(config_file, 'r') as file:
        data = yaml.safe_load(file)
    data['product_id'] = product_id
    with open(config_file, 'w') as file:
        yaml.dump(data, file)

    # Create the data product binding
    dpd = info['dpd']()

    # Add the generic header to the data product
    dpd.Header = create_generic_header(info['product'])

    # create simple data for the catalog
    dpd.Data = __create_simple_data(info['data'])

    # Add the catalog descriptions
    description = cat.CatalogDescription()
    description.PathToCatalogFile = f"Data.{info['capitalised']}.DataContainer.FileName"
    description.CatalogType = "NOT_PROXY"
    description.CatalogOrigin = "OTHERS"
    description.CatalogOrigin = "MEASURED_WIDE"
    description.CatalogName = f"Le3-Id-Vmpz-Output-{info['shortname']}-Catalog"
    description.CatalogFormatHDU = 1
    dpd.Data.CatalogDescription.append(description)

    # Add the file for the catalog and any product-specific fields
    setattr(dpd.Data, info['file_field'], __create_fits_storage(
        info['file'],
        file_name,
        product_id,
        "0.1"))
    for field, value in info['extra_data'].items():
        setattr(dpd.Data, field, value)

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
        The product ID. Default is None.
        The product ID should be one of the keys in the names_database dictionary.

    Returns
    -------
    object
        The filename provider binding.

    """
    filename = FileNameProvider().get_allowed_filename(
        processing_function='le3',
        type_name=f'{get_product_info(product)["capitalised"]}',
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
    fits_file_name = file_name.replace('.xml', '.fits')
    data_container.FileName = fits_file_name
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
    # GenericHeaderContent.PlanId = get_uuid_as_string()
    GenericHeaderContent.PlanId = conf.get("header.default.PlanId")
    # GenericHeaderContent.PPOId = get_uuid_as_string()
    GenericHeaderContent.PPOId = conf.get("header.default.PPOId")
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

        # print(f"Catalog created and saved to {xml_file_name} with <SpatialCoverage> added.")
    except Exception as e:
        print(f"Error creating catalog or adding <SpatialCoverage>: {e}")

 

def main(fits_file, output_dir="./generated/", product_id=None):
    """
    Main function to create and save the catalog.

    Parameters:
    -----------
    fits_file : str
        Path to the input FITS file.
    output_dir : str, optional
        Directory to save the generated XML file. Default is "generated/".
    product_id : str, optional
        FitsDataModel product ID. Default is the FITS file name without '.fits' (i.e. '<product_id>.fits').
    """
    try:
        if product_id is None:
            product_id = os.path.basename(fits_file)[:-len(".fits")]

        filename = filename_provider(product=product_id)
        xml_file_name = f"{output_dir}{filename}"

        # Create the catalog
        dpd = create_catalog(product_id, filename)

        # Save the product metadata to an XML file
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


        console.success(f"XML file generated: {xml_file_name}")
        return True

    except Exception as e:
        console.error(f"Error creating catalog: {e}")
        return False

if __name__ == "__main__":
    # Parse command-line arguments
    parser = argparse.ArgumentParser(description="Create and save a catalog from a FITS file.")
    parser.add_argument("fits_file", type=str, help="Path to the input FITS file.")
    parser.add_argument("--output_dir", 
                        type=str, 
                        default="./generated/", 
                        help="Directory to save the generated XML file."
                        )
    parser.add_argument("--product_id",
                        type=str,
                        default=None,
                        help="FitsDataModel product ID (default: the FITS file name without '.fits')."
                        )
    args = parser.parse_args()

    # Call the main function with the provided arguments (non-zero exit status on failure)
    sys.exit(0 if main(args.fits_file, args.output_dir, args.product_id) else 1)
