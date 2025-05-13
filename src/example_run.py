import yaml
import requests
import os
import zipfile
from script import FitsProcessor
import re

def load_config(config_path):
    """Load configuration from a YAML file.

    Parameters:
    -----------
    config_path : str
        Path to the YAML configuration file.
    """
    with open(config_path, "r") as file:
        return yaml.safe_load(file)
    
def is_path_provided(path):
    """Check if the path is provided.
    
    Parameters:
    -----------
    path : str
        Path to check.
    """
    #match the path with a regex to check if it is a valid path
    if path=="latest" or re.match(r'^\d{1,5}\.\d{1,5}\.\d{1,5}$', path):
        return False
    else:
        return True

if __name__ == "__main__":

    config = load_config("src/config/inputs.yaml")

    # get the input parameters from the config else use a default
    input_fits_path = config.get("input_fits_path", None)  # Default path if not provided
    output_dir = "./generated/"
    product_id = config.get("product_id", None)  # Default product ID if not provided
    fits_data_model = config.get("fits_data_model", "latest")  # Default to latest if not provided
    # data_model = config.get("data_model", "latest")  # Default to latest if not provided
    display_output = config.get("display_output", False)  # Default to False if not provided


    # sanity checks for the input parameters
    if input_fits_path is None:
        raise ValueError("Input FITS path is required. Please provide a valid path.")
    if not os.path.exists(input_fits_path):
        raise FileNotFoundError(f"Input FITS file '{input_fits_path}' does not exist.")
    if not product_id:
        raise ValueError("Product ID is required. Please provide a valid product ID.")
    
    '''
    ################
    ## DATA MODEL ##
    ################

    if not is_path_provided(data_model):

        if "PAT" not in config or config["PAT"] == "<gitlab_personal_access_token>" or config["PAT"] == "":
            raise ValueError("Personal Access Token (PAT) is required. Please provide a valid PAT in the config file.")
        headers = {"PRIVATE-TOKEN": f"{config['PAT']}"}

        DM_tags_url = "https://gitlab.euclid-sgs.uk/api/v4/projects/ST-DM%2FST_DataModel/repository/tags"
        response = requests.get(DM_tags_url, headers=headers)
        response.raise_for_status()
        DM_tags = response.json()
        DM_all_tags = [tag["name"] for tag in DM_tags]
        data_model_url = None

        ## handling the 3 cases of DataModel input

        if data_model == "latest":
            tag = DM_all_tags[0]
            # construct the URL for the latest tag
            data_model_url = f"https://gitlab.euclid-sgs.uk/ST-DM/ST_DataModel/-/archive/{tag}/ST_DataModel-{tag}.zip"

        elif data_model in DM_all_tags:
            tag = data_model
            # construct the URL for the provided tag
            data_model_url = f"https://gitlab.euclid-sgs.uk/ST-DM/ST_DataModel/-/archive/{tag}/ST_DataModel-{tag}.zip"
        elif os.path.exists(data_model) and data_model.endswith(".xml"):
            # if the path is a valid XML file, use it directly
            data_model = data_model
        else:
            raise ValueError(f"Invalid data_model: {data_model}. Must be 'latest', a valid tag, or a path to an XML file.")

        # download and extract the DataModel zip from the data_model_url
        if data_model_url is not None:
            response = requests.get(data_model_url, headers=headers)
            response.raise_for_status()

            # Save the zip file locally
            zip_file_path = os.path.join(output_dir, f"ST_DataModel-{tag}.zip")
            with open(zip_file_path, "wb") as zip_file:
                zip_file.write(response.content)

            # Extract the zip file
            with zipfile.ZipFile(zip_file_path, "r") as zip_ref:
                zip_ref.extractall(output_dir)

    '''

    #####################
    ## FITS DATA MODEL ##
    #####################

    if not is_path_provided(fits_data_model):

        if "PAT" not in config or config["PAT"] == "<gitlab_personal_access_token>" or config["PAT"] == "":
            raise ValueError("Personal Access Token (PAT) is required. Please provide a valid PAT in the config file.")
        headers = {"PRIVATE-TOKEN": f"{config['PAT']}"}

        FitsDM_tags_url = "https://gitlab.euclid-sgs.uk/api/v4/projects/ST-DM%2FST_FitsDataModel/repository/tags"
        response = requests.get(FitsDM_tags_url, headers=headers)
        response.raise_for_status()
        FitsDM_tags = response.json()
        FitsDM_all_tags = [tag["name"] for tag in FitsDM_tags]
        fits_data_model_url = None

        ## handling the 3 cases of FitsDataModel input

        if fits_data_model == "latest":
            tag = FitsDM_all_tags[0]
            # construct the URL for the latest tag
            fits_data_model_url = f"https://gitlab.euclid-sgs.uk/ST-DM/ST_FitsDataModel/-/archive/{tag}/ST_FitsDataModel-{tag}.zip"

        elif fits_data_model in FitsDM_all_tags:
            tag = fits_data_model
            # construct the URL for the provided tag
            fits_data_model_url = f"https://gitlab.euclid-sgs.uk/ST-DM/ST_FitsDataModel/-/archive/{tag}/ST_FitsDataModel-{tag}.zip"
        elif os.path.exists(fits_data_model) and fits_data_model.endswith(".xml"):
            # if the path is a valid XML file, use it directly
            fits_data_model_path = fits_data_model
        else:
            raise ValueError(f"Invalid fits_data_model: {fits_data_model}. Must be 'latest', a valid tag, or a path to an XML file.")

        # download and extract the FitsDataModel zip from the fits_data_model_url
        if fits_data_model_url is not None:
            response = requests.get(fits_data_model_url, headers=headers)
            response.raise_for_status()

            # Save the zip file locally
            zip_file_path = os.path.join(output_dir, f"ST_FitsDataModel-{tag}.zip")
            with open(zip_file_path, "wb") as zip_file:
                zip_file.write(response.content)

            # Extract the zip file
            with zipfile.ZipFile(zip_file_path, "r") as zip_ref:
                zip_ref.extractall(output_dir)

            # get the path to the fits_data_model xml file
            fits_data_model_path = f'./generated/ST_FitsDataModel-{tag}/ST_DM_FitsSchema/auxdir/ST_DM_FitsSchema/instances/fit/euc-le3-id.xml'
            
            if not os.path.exists(fits_data_model_path):
                raise ValueError(f"ST_DM_FitsSchema/instances/fit/euc-le3-id.xml does not exist in ST_FitsDataModel version '{tag}'.")


    if is_path_provided(fits_data_model):
        fits_data_model_path = fits_data_model

    # initializing the FitsProcessor
    fits_handler = FitsProcessor()

    # to generate the catalog
    fits_handler.generate_catalog(
        product_id=product_id,
        input_fits_path=input_fits_path,
        fitsDataModel_path=fits_data_model_path,
        output_path=output_dir,
        display_output=display_output,
    )
