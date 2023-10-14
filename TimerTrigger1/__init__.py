import datetime
import time
import requests
import json
import os
import logging
import azure.functions as func
from azure.appconfiguration import AzureAppConfigurationClient

# Global variables
API_AUTH = None
API_HEADER = None
primary_fqdn = None
admin_username = None
admin_password = None
primary_ip = None
function_url = None

# Function to initialize global variables
def initialize_globals():
    global API_AUTH, API_HEADER, primary_fqdn, secondary_fqdn, admin_username, admin_password, primary_ip, secondary_ip, function_url
    if API_AUTH is None:
        app_config_connection_string = os.environ['AppConfigConnectionString']  # Azure App Configuration connection string
        config_client = AzureAppConfigurationClient.from_connection_string(app_config_connection_string)

        admin_username = get_app_config_parameter(config_client, "admin_username")
        admin_password = get_app_config_parameter(config_client, "admin_password")  # Ensure this parameter is stored securely

        API_AUTH = (admin_username, admin_password)
        API_HEADER = {'Content-Type': 'application/json', 'Accept': 'application/json'}
        
        primary_fqdn = get_app_config_parameter(config_client, "primary_fqdn")
        primary_ip = get_app_config_parameter(config_client, "primary_ip")

        function_url = get_app_config_parameter(config_client, "function_url")

# Function to get an app config parameter
def get_app_config_parameter(config_client, key):
    try:
        value = config_client.get_configuration_setting(key).value
        return value
    except Exception as e:
        raise Exception(f"Error getting '{{key}}' from App Configuration: {str(e)}")


def main(mytimer: func.TimerRequest) -> None:
    utc_timestamp = datetime.datetime.utcnow().replace(
        tzinfo=datetime.timezone.utc).isoformat()

    if mytimer.past_due:
        logging.info('The timer is past due!')

    logging.info('Python timer trigger function ran at %s', utc_timestamp)


    # Ensure that the globals are initialized
    initialize_globals()

    # # Rest of your code for checking node status
    # nodes_to_check = [primary_ip, secondary_ip]
    # nodes_list = [primary_ip, secondary_ip]
    data = {}
    # for ip in nodes_to_check:
    url = f'https://{primary_ip}/api/v1/deployment/node'
    try:
        resp = requests.get(url, headers=API_HEADER, auth=API_AUTH, data=json.dumps(data), verify=False)
        logging.info(f'API response for {primary_ip} is {resp.text}')
        if resp.status_code == 200:
            node_info = resp.json()  
            node_status = node_info['response'][0]['nodeStatus']
            node_role = node_info['response'][0]['roles']
            node_fqdn = node_info['response'][0]['fqdn']
            
            if node_status == "Connected" and "Standalone" in node_role and node_fqdn == primary_fqdn:
                logging.info(f'ISE - {primary_ip} meets the conditions for setting as primary, active role {node_role}')
                ExecuteFunction = requests.get(function_url)
                logging.info(f'API response for {function_url} is {ExecuteFunction.text}')

            else:
                logging.info(f'ISE - {primary_ip} does not meet the conditions for executing the HTTP Trigger function')
        else:
            logging.info(f'ISE - {primary_ip} is not reachable or returned a non-200 status code')

    except Exception as e:
        logging.error(f'Exception: {e}', exc_info=True)
        logging.error(f'Exception occurred while executing get node details API for {primary_ip}')
        retries -= 1

# Call the main function for the Azure Function
if __name__ == "__main__":
    main(func.TimerRequest())