import yaml
from script import FitsProcessor

def load_config(config_path):
    """Load configuration from a YAML file."""
    with open(config_path, "r") as file:
        return yaml.safe_load(file)

if __name__ == "__main__":

    config = load_config("src/config/inputs.yaml")

    # get the input parameters from the config
    input_fits_path = config["input_fits_path"]
    output_dir = config["output_directory"]
    catalog_type = config["catalog_type"]
    fits_data_model = config["fits_data_model"]
    display_output = config["display_output"]

    # initializing the FitsProcessor
    fits_handler = FitsProcessor()

    # to display the contents of the FITS file (optional)
    # fits_handler.display_contents(input_fits_path=input_fits_path)

    # to generate the catalog
    fits_handler.generate_catalog(
        type=catalog_type,
        input_fits_path=input_fits_path,
        fitsDataModel_path=fits_data_model,
        output_path=output_dir,
        display_output=display_output,
    )