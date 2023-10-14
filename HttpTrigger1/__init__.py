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
secondary_fqdn = None
admin_username = None
admin_password = None
primary_ip = None
secondary_ip = None
psn_nodes_list = []


# Function to initialize global variables
def initialize_globals():
    global API_AUTH, API_HEADER, primary_fqdn, secondary_fqdn, admin_username, admin_password, primary_ip, secondary_ip, psn_nodes_list
    if API_AUTH is None:
        app_config_connection_string = os.environ[
            'AppConfigConnectionString']  # Azure App Configuration connection string
        config_client = AzureAppConfigurationClient.from_connection_string(app_config_connection_string)

        admin_username = get_app_config_parameter(config_client, "admin_username")
        admin_password = get_app_config_parameter(config_client, "admin_password")  # Ensure this parameter is stored securely

        API_AUTH = (admin_username, admin_password)
        API_HEADER = {'Content-Type': 'application/json', 'Accept': 'application/json'}

        primary_fqdn = get_app_config_parameter(config_client, "primary_fqdn")
        secondary_fqdn = get_app_config_parameter(config_client, "secondary_fqdn")

        primary_ip = get_app_config_parameter(config_client, "primary_ip")
        secondary_ip = get_app_config_parameter(config_client, "secondary_ip")

# Fetching PSN nodes using label psn
        label = "psn"
        all_settings = list(config_client.list_configuration_settings())
        psn_nodes_list = [setting.value for setting in all_settings if setting.label and label in setting.label]


# Function to get an app config parameter
def get_app_config_parameter(config_client, key):
    try:
        value = config_client.get_configuration_setting(key).value
        return value
    except Exception as e:
        raise Exception(f"Error getting '{{key}}' from App Configuration: {str(e)}")


# Function to set node as primary
def set_node_as_primary(primary_ip):
    initialize_globals()  # Ensure that the globals are initialized

    urls = f'https://{primary_ip}/api/v1/deployment/primary'
    data = {}  # You may need to specify data for the POST request here

    set_node_primary = requests.post(urls, headers=API_HEADER, auth=API_AUTH, data=json.dumps(data), verify=False)

    if set_node_primary.status_code == 200:
        return {f"Node set as primary. API response: {set_node_primary.content}"}
    else:
        return {f"Failed to set the node as primary. API response: {set_node_primary.content}"}


# Function to set secondary node
def set_node_as_secondary(primary_ip):
    initialize_globals()  # Ensure that the globals are initialized

    roles_enabled = ["SecondaryAdmin", "SecondaryMonitoring"]
    service_enabled = ["Session", "Profiler", "pxGrid"]

    url = f'https://{primary_ip}/api/v1/deployment/node'
    data = {
        "allowCertImport": True,
        "fqdn": secondary_fqdn,
        "userName": API_AUTH[0],  # Use the same username as the primary node
        "password": API_AUTH[1],  # Use the same password as the primary node
        "roles": roles_enabled,
        "services": service_enabled,
    }

    resp = requests.post(url, headers=API_HEADER, auth=API_AUTH, data=json.dumps(data), verify=False)

    if resp.status_code == 200:
        return f"Node set as secondary. API response: {resp.content}"
    else:
        return f"Failed to set the node as secondary. API response: {resp.content}"


# Function to set PSN nodes

def register_psn_node(psn_node_fqdn):
    initialize_globals()  # Ensure that the globals are initialized

    service_enabled = ["Session", "Profiler"]
    url = f'https://{primary_ip}/api/v1/deployment/node'

    data = {
        "allowCertImport": True,
        "fqdn": psn_node_fqdn,
        "userName": API_AUTH[0],  # Use the same username as the primary node
        "password": API_AUTH[1],  # Use the same password as the primary node
        "services": service_enabled
    }

    resp = requests.post(url, headers=API_HEADER, auth=API_AUTH, data=json.dumps(data), verify=False)

    # Log the result
    logging.info('Register psn response: {}, {}'.format(resp.status_code, resp.text))

    if resp.status_code == 200:
        logging.info("Register " + psn_node_fqdn + " node is successful, API response is {}".format(resp.text))
        return {
            "task_status": "Done"
        }


def main(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('Python HTTP trigger function processed a request.')

    try:
        retries = 10  # Polling rate to restrict function execution

        # Ensure that the globals are initialized
        initialize_globals()


        # Initialize primary_node_ready with a default value
        primary_node_ready = False

        # Initialize secondary_node_ready with a default value
        secondary_node_ready = False
        
        # Initialize primary_node_admin with a default value
        primary_node_admin = False

        # Rest of your code for checking node status
        nodes_to_check = [primary_ip, secondary_ip]
        nodes_list = [primary_ip, secondary_ip]
        data = {}
        for ip in nodes_to_check:
            url = f'https://{ip}/api/v1/deployment/node'
            try:
                resp = requests.get(url, headers=API_HEADER, auth=API_AUTH, data=json.dumps(data), verify=False)
                logging.info(f'API response for {ip} is {resp.text}')
                if resp.status_code == 200:
                    node_info = resp.json()
                    node_status = node_info['response'][0]['nodeStatus']
                    node_role = node_info['response'][0]['roles']
                    node_fqdn = node_info['response'][0]['fqdn']

                    if node_status == "Connected" and "Standalone" in node_role and node_fqdn == primary_fqdn:
                        logging.info(f'ISE - {ip} meets the conditions for setting as primary, active role {node_role}')
                        primary_node_ready = True
                    elif node_status == "Connected" and "PrimaryAdmin" in node_role and node_fqdn == primary_fqdn:
                        logging.info(f'ISE - {ip} already set as primary, active role {node_role}')
                        primary_node_admin = True
                    elif node_status == "Connected" and "Standalone" in node_role and node_fqdn == secondary_fqdn:
                        logging.info(
                            f'ISE - {ip} meets the conditions for setting as secondary, active role {node_role}')
                        secondary_node_ready = True
                    else:
                        logging.info(f'ISE - {ip} does not meet the conditions for setting as primary or secondary')
                else:
                    logging.info(f'ISE - {ip} is not reachable or returned a non-200 status code')

            except Exception as e:
                logging.error(f'Exception: {e}', exc_info=True)
                logging.error(f'Exception occurred while executing get node details API for {ip}')
                retries -= 1

        # Set the primary node

        if primary_node_ready:
            start_time = time.time()
            set_primary_response = set_node_as_primary(primary_ip)
            elapsed_time = time.time() - start_time
            remaining_time = max(0, 100 - elapsed_time)

            if remaining_time > 0:
                logging.info(f'Set Node as Primary Response: {set_primary_response}')
                logging.info(f'Waiting for {remaining_time} seconds before setting as secondary...')
                time.sleep(remaining_time)

        # Set the secondary node

        if primary_node_ready or primary_node_admin and secondary_node_ready:
            #  if (node_status == "Connected" and "PrimaryAdmin" in node_role and node_fqdn == primary_fqdn) and secondary_node_ready:
            set_secondary_response = set_node_as_secondary(primary_ip)
            logging.info('Set Node as Secondary Response: ' + set_secondary_response)

        # Register PSN nodes to the Primary Node
        if primary_node_ready or primary_node_admin:
            for psn_node_fqdn in psn_nodes_list:
                register_psn_response = register_psn_node(psn_node_fqdn)
                logging.info(' Register Node as PSN response: %s', register_psn_response)


        return func.HttpResponse("Setting ISE Nodes function execution done. Please check the logs for more info. ")

    except Exception as e:
        logging.error(f'Exception: {e}', exc_info=True)
        logging.error('An error occurred in the main function.')


# Call the main function for the Azure Function
if __name__ == "__main__":
    main(func.HttpRequest('GET', ''))