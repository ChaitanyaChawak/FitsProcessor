import yaml
import requests
import os
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
    product_id = config["product_id"]
    fits_data_model = config["fits_data_model"]
    data_model = config["data_model"]
    display_output = config["display_output"]

    headers = {"PRIVATE-TOKEN": f"{config['PAT']}"}

    ################
    ## DATA MODEL ##
    ################

    DM_tags_url = config["gitlab_DM_tags_url"]
    response = requests.get(DM_tags_url, headers=headers)
    response.raise_for_status()
    DM_tags = response.json()
    DM_all_tags = [tag["name"] for tag in DM_tags]
    data_model_url = None

    ## handling the 3 cases of DataModel input

    if data_model == "latest":
        tag = DM_all_tags[0]
        # construct the URL for the latest tag
        data_model_url = f"{config['gitlab_DM_base_url']}/-/archive/{tag}/ST_DataModel-{tag}.zip"

    elif data_model in DM_all_tags:
        tag = data_model
        # construct the URL for the provided tag
        data_model_url = f"{config['gitlab_DM_base_url']}/-/archive/{tag}/ST_DataModel-{tag}.zip"
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
        import zipfile
        with zipfile.ZipFile(zip_file_path, "r") as zip_ref:
            zip_ref.extractall(output_dir)


    #####################
    ## FITS DATA MODEL ##
    #####################

    FitsDM_tags_url = config["gitlab_FitsDM_tags_url"]
    response = requests.get(FitsDM_tags_url, headers=headers)
    response.raise_for_status()
    FitsDM_tags = response.json()
    FitsDM_all_tags = [tag["name"] for tag in FitsDM_tags]
    fits_data_model_url = None

    ## handling the 3 cases of FitsDataModel input

    if fits_data_model == "latest":
        tag = FitsDM_all_tags[0]
        # construct the URL for the latest tag
        fits_data_model_url = f"{config['gitlab_FitsDM_base_url']}/-/archive/{tag}/ST_FitsDataModel-{tag}.zip"

    elif fits_data_model in FitsDM_all_tags:
        tag = fits_data_model
        # construct the URL for the provided tag
        fits_data_model_url = f"{config['gitlab_FitsDM_base_url']}/-/archive/{tag}/ST_FitsDataModel-{tag}.zip"
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
        import zipfile
        with zipfile.ZipFile(zip_file_path, "r") as zip_ref:
            zip_ref.extractall(output_dir)

        fits_data_model_path = f'generated/ST_FitsDataModel-{tag}/ST_DM_FitsSchema/auxdir/ST_DM_FitsSchema/instances/fit/euc-le3-id.xml'
        
        if not os.path.exists(fits_data_model_path):
            raise ValueError(f"ST_DM_FitsSchema/instances/fit/euc-le3-id.xml does not exist in ST_FitsDataModel version {tag}.")

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
