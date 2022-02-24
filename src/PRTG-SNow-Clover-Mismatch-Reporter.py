import configparser
import json
import os
import re

import pysnow
import requests
import pandas as pd


# Module information.
__author__ = 'Anthony Farina'
__copyright__ = 'Copyright (C) 2022 Anthony Farina'
__credits__ = ['Anthony Farina']
__maintainer__ = 'Anthony Farina'
__email__ = 'farinaanthony96@gmail.com'
__license__ = 'MIT'
__version__ = '1.0.0'
__status__ = 'Released'


# Config file variables for easy referencing.
CONFIG = configparser.ConfigParser()
CONFIG_PATH = '/../configs/PRTG-SNow-Clover-Mismatch-Reporter-config.ini'
CONFIG.read(os.path.dirname(os.path.realpath(__file__)) + CONFIG_PATH)

# Customer information global variables.
CUSTOMER_NAME = CONFIG['Customer Info']['name']

# PRTG API global variables.
PRTG_URL = CONFIG['PRTG Info']['server-url']
PRTG_API_URL = PRTG_URL + CONFIG['PRTG Info']['table']
PRTG_USERNAME = CONFIG['PRTG Info']['username']
PRTG_PASSWORD = CONFIG['PRTG Info']['password']

# ServiceNow global variables.
SNOW_INSTANCE = CONFIG['ServiceNow Info']['instance']
SNOW_USERNAME = CONFIG['ServiceNow Info']['username']
SNOW_PASSWORD = CONFIG['ServiceNow Info']['password']
SNOW_CLOVER_PATH = CONFIG['ServiceNow Info']['clover-table']

# Regular expression global variables.
MAC_REGEX = re.compile(CONFIG['Regex']['mac-address'])
IPV4_REGEX = re.compile(CONFIG['Regex']['ipv4'])
PRTG_CLOVER_NAME_REGEX = re.compile(CONFIG['Regex']['prtg-clover-name'])
PRTG_CLOVER_SERIAL_REGEX = re.compile(CONFIG['Regex']['prtg-clover-serial'])
SNOW_CLOVER_NAME_REGEX = re.compile(CONFIG['Regex']['snow-clover-name'])
SNOW_CLOVER_SERIAL_REGEX = re.compile(CONFIG['Regex']['snow-clover-serial'])


# Retrieves and returns a dictionary of dictionaries of all Clovers
# currently in PRTG and records their site, name, MAC address, IPv4
# address, and serial number. For the top-level dictionary, the keys
# are the Clover's MAC address and the values are dictionaries that
# hold the information retrieved from PRTG.
def get_prtg_clovers() -> dict[dict]:
    # First, we need to get Clover device IPv4 addresses from PRTG, but
    # we can only get that information from a 'devices' API call to
    # PRTG. Prepare and send the PRTG API request to get Clover
    # devices. Then convert the response to JSON.
    prtg_devices_resp = requests.get(
        url=PRTG_API_URL,
        params={
            'content': 'devices',
            'columns': 'probe,group,name,objid,host',
            'filter_group': '@sub(Clover)',
            'sortby': 'probe',
            'output': 'json',
            'count': '50000',
            'username': PRTG_USERNAME,
            'password': PRTG_PASSWORD
        }
    )
    prtg_devices = json.loads(prtg_devices_resp.text)

    # Make a dictionary to store a Clover's PRTG ID and IPv4 address
    # from PRTG. The keys are the Clover's PRTG ID and the values are
    # their IPv4 address.
    prtg_device_ips_dict = dict()
    for clover in prtg_devices['devices']:
        prtg_device_ips_dict[clover['objid']] = clover['host']

    # Make a dictionary to store Clover device information. The keys
    # are the Clover's MAC address and the values are dictionaries that
    # hold their information.
    prtg_clover_dict = dict()

    # Use the PRTG API to get all "Sys Descr" sensors for Clovers.
    # These sensors store the Clover's serial number in the
    # "message_raw" column. We can extract the Clover's name, site, MAC
    # address, and serial number from this call.
    prtg_clovers_resp = requests.get(
        url=PRTG_API_URL,
        params={
            'content': 'sensors',
            'columns': 'name,probe,device,message,status,parentid',
            'filter_name': '@sub(Descr)',
            'sortby': 'probe',
            'output': 'json',
            'count': '50000',
            'username': PRTG_USERNAME,
            'password': PRTG_PASSWORD
        }
    )
    prtg_clovers = json.loads(prtg_clovers_resp.text)

    # Iterate through all Clover devices from the above PRTG API
    # response and create complete Clover dictionaries that include
    # their site, name, MAC address, IPv4 address, and serial number.
    for clover in prtg_clovers['sensors']:
        # Check if this Clover's name is formatted incorrectly in PRTG.
        # Skip this Clover if so.
        if not PRTG_CLOVER_NAME_REGEX.match(clover['device_raw']):
            print('Clover ' + clover['probe'] + ' ' + clover['device_raw'] +
                  ' is named incorrectly in PRTG.')
            continue

        # Extract this Clover's name, site, MAC address, and serial
        # number. We have the parentid of this Clover device as well,
        # so we can extract this Clover's IPv4 address using the Clover
        # device IP dictionary from earlier.
        clover_site = clover['probe'].replace('(LTE Only)', '').strip()
        clover_name = re.sub('\\[[A-Za-z]+[0-9]{3}]',
                             '',
                             clover['device_raw'].strip()
                             ).strip()
        clover_mac = clover['device_raw'].strip()[-17:]
        clover_ip = prtg_device_ips_dict[clover['parentid']]

        # Check if this Clover's serial number is not available in
        # PRTG. If it isn't, the serial number's value will be
        # "Unavailable" in its dictionary.
        clover_serial = clover['message_raw'][-14:] \
            if PRTG_CLOVER_SERIAL_REGEX.match(clover['message_raw']) \
            else 'Unavailable'

        # Make a new Clover record and add it to the output Clover
        # dictionary. The key is the Clover's MAC address and the value
        # is the Clover information.
        new_clover_record = {
            'site': clover_site,
            'name': clover_name,
            'mac': clover_mac,
            'ip': clover_ip,
            'serial': clover_serial
        }
        prtg_clover_dict[clover_mac] = new_clover_record

    return prtg_clover_dict


# This method takes a dictionary of dictionaries that holds Clover
# device information and compares it to the Clovers in ServiceNow. It
# will return a list of dictionaries that contains all Clovers that do
# not match.
def find_snow_clover_mismatches(clover_records: dict[dict]) -> list[dict]:
    # Connect to the ServiceNow instance.
    snow = pysnow.Client(instance=SNOW_INSTANCE,
                         user=SNOW_USERNAME,
                         password=SNOW_PASSWORD
                         )

    # Get all Clovers from their table in SNow.
    snow_clover_table = snow.resource(api_path=SNOW_CLOVER_PATH)
    snow_clover_query = (pysnow.QueryBuilder().
                         field('name').order_ascending().
                         AND().field('company.name').equals(CUSTOMER_NAME)
                         )
    snow_clover_resp = snow_clover_table.get(
        query=snow_clover_query,
        fields=['name',
                'mac_address',
                'ip_address',
                'serial_number',
                'u_active_contract'
                ]
    )
    snow_clovers = snow_clover_resp.all()

    # Loop through all Clovers in SNow to check for mismatches.
    mismatched_clovers_list = list()
    for snow_clover in snow_clovers:
        # Check if this Clover is retired. If it is, skip it.
        if snow_clover['u_active_contract'] == 'false':
            continue

        # Prepare SNow Clover object for comparing.
        snow_clover_record = new_clover_record_snow(snow_clover)

        # See if this SNow Clover exists in PRTG. If it doesn't, add it
        # to the mismatch list.
        try:
            prtg_clover = clover_records[snow_clover_record['mac']]
        except KeyError:
            snow_clover_record['mismatch_reason'] += \
                'MAC address from SNow not found in PRTG; '
            mismatched_clovers_list.append(snow_clover_record)
            continue

        # Format the Clover's name from PRTG like the name in SNow to
        # compare it properly.
        prtg_name = prtg_clover['site'] + ' Clover ' + \
            prtg_clover['name'][:-17].replace(' ', '')

        # Check if the names don't match.
        if prtg_name != snow_clover_record['name']:
            snow_clover_record['mismatch_reason'] += 'Names do not match; '

        # Check if the IPv4 addresses don't match.
        if prtg_clover['ip'] != snow_clover_record['ip']:
            snow_clover_record['mismatch_reason'] += 'IPs do not match; '

        # Check if the serial numbers don't match.
        if prtg_clover['serial'] != snow_clover_record['serial']:
            # Make sure the mismatch reason is set correctly in case
            # the serial number is not available from PRTG.
            snow_clover_record['mismatch_reason'] += 'S/Ns do not match; ' \
                if prtg_clover['serial'] != 'Unavailable' \
                else 'S/N unavailable from PRTG; '

        # Check if this Clover is mismatched. If it is, add it to the
        # mismatch list.
        if snow_clover_record['mismatch_reason'] != '':
            mismatched_clovers_list.append(snow_clover_record)

    return mismatched_clovers_list


# Converts the provided SNow Clover record to a more friendly format
# into a returned dictionary. Validates the record and updates the
# "mismatch_reason" entry for any invalid formats to the relevant
# fields (name, MAC address, IPv4 address, and serial number).
def new_clover_record_snow(snow_clover_record: dict) -> dict:
    # Declare and initialize the dictionary to return from the provided
    # SNow Clover record.
    return_clover_record = {
        'name': snow_clover_record['name'],
        'mac': snow_clover_record['mac_address'],
        'ip': snow_clover_record['ip_address'],
        'serial': snow_clover_record['serial_number'],
        'mismatch_reason': ''
    }

    # Check if the name field is formatted correctly.
    if not SNOW_CLOVER_NAME_REGEX.match(return_clover_record['name']):
        return_clover_record['mismatch_reason'] += \
            'SNow name not formatted correctly; '

    # Check if the MAC address field is formatted correctly.
    if not MAC_REGEX.match(return_clover_record['mac']):
        return_clover_record['mismatch_reason'] += \
            'SNow MAC not formatted correctly; '

    # Check if the IPv4 address field is formatted correctly.
    if not IPV4_REGEX.match(return_clover_record['ip']):
        return_clover_record['mismatch_reason'] += \
            'SNow IP not formatted correctly; '

    # Check if the serial number field is formatted correctly.
    if not SNOW_CLOVER_SERIAL_REGEX.match(return_clover_record['serial']):
        return_clover_record['mismatch_reason'] += \
            'SNow S/N not formatted correctly; '

    return return_clover_record


# Generates an Excel sheet in this script's path of all Clovers from
# the provided list of dictionaries.
def make_mismatch_report(mismatched_clovers: list[dict]) -> None:
    # Loop through the provided list of dictionaries and convert it to
    # a list of lists. Pandas' dataframes don't like lists of
    # dictionaries.
    output_list = list()
    for clover_record in mismatched_clovers:
        # Loop through dictionary values and add them all to a list.
        clover_record_values = list()
        for value in clover_record.values():
            clover_record_values.append(value)

        # Add the values list to the output list.
        output_list.append(clover_record_values)

    # Generate the Excel sheet report of mismatched Clovers.
    output = pd.DataFrame(output_list,
                          columns=[
                              'Name in ServiceNow',
                              'MAC Address',
                              'IPv4 Address',
                              'Serial Number',
                              'Mismatch Reason'
                          ]
                          )
    output = output.sort_values(by='Name in ServiceNow')
    output.to_excel('clover-mismatches.xlsx', index=None, header=True)


# The main method that runs the script. It has no input arguments.
if __name__ == '__main__':
    # Get Clovers from PRTG.
    all_prtg_clovers = get_prtg_clovers()

    # Get mismatched Clovers in SNow.
    mismatched_snow_clovers = find_snow_clover_mismatches(all_prtg_clovers)

    # Generate an Excel sheet report of mismatched Clovers.
    make_mismatch_report(mismatched_snow_clovers)
