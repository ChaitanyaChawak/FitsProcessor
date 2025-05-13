import sys
import datetime
import yaml


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




# Files handling
#####################################


def create_catalog(fits_file):
    """Creates the output catalog bindings.

    Inputs
    ------
    fits_file: str
        The name of the fits file to be wrapped in the binding.
    Returns
    -------
    object:
        The output catalog bindings.

    """
    # Create the appropriate data product binding
    dpd = out.euc_le3_id_vmpz_pos_catalog.DpdWLPosCatalog()
    #out.euc_le3_id_vmpz_proxy_shear_catalog.DpdWLProxyShearCatalog()
    #out.euc_le3_id_vmpz_shear_catalog.DpdWLShearCatalog()


    # Add the generic header to the data product
    dpd.Header = create_generic_header('DpdWLPosCatalog')

    

    dpd.Data = __create_simple_data(vmpz_pro.PosCatalogWL)


    # Add the catalog descriptions
    ## Cat
    description = cat.CatalogDescription()
    description.PathToCatalogFile = "DpdWLPosCatalog.Data.PosCatalog.DataContainer.FileName"
    description.CatalogType = "NOT_PROXY"
    description.CatalogOrigin = "OTHERS"
    description.CatalogOrigin = "MEASURED_WIDE"
    description.CatalogName = "Le3-Id-Vmpz-Output-Position-Catalog"
    #Le3-Id-Vmpz-Output-Shear-Catalog
    #Le3-Id-Vmpz-Output-ProxyShear-Catalog
    description.CatalogFormatHDU = 1
    dpd.Data.CatalogDescription.append(description)


    # Add the files
    dpd.Data.PosCatalog = __create_fits_storage(
        vmpz_pro.PosCatalogFile,
        fits_file,
        "le3.id.vmpz.output.poscatalog",
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

def filename_provider(instance_id=None, release=None):
    """Creates a filename provider binding.

    Returns
    -------
    object
        The filename provider binding.

    """
    filename = FileNameProvider().get_allowed_filename(
        processing_function='le3',
        type_name='PosCatalog',
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

# def createFromDocument(xml, stub):
#     parser = XmlParser(context=XmlContext())
#     return parser.from_string(xml, stub)

# def read_spatial_coverage(le3_id_vmpz_out_xml_text):
#     mer_cat_dpd = createFromDocument(le3_id_vmpz_out_xml_text, out.DpdMerFinalCatalog)
#     return mer_cat_dpd.Data.SpatialCoverage


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
    config_file = "src/config/XmlHeaderDetails.yaml"

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
    """Load configuration from a YAML file."""
    with open(config_path, "r") as file:
        return yaml.safe_load(file)
    

def main(argv=None):  # IGNORE:C0111
    generated_fits = 'generated/le3.id.vmpz.output.poscatalog.fits'
    # xml_file_name = 'generated/poscatalog.xml'

    filename = filename_provider()
    xml_file_name = f'generated/{filename}'

    vmpz_dpd = create_catalog(generated_fits)
    
    save_product_metadata(vmpz_dpd, xml_file_name)
    
    print('Done')
    return 0
    
    
if __name__ == "__main__":
    sys.exit(main())
