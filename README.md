# PRTG-SNow-Clover-Mismatch-Reporter

## Summary
Generates an Excel sheet of mismatched devices between PRTG and ServiceNow.

_Note: If you have any questions or comments you can always use GitHub discussions, or email me at farinaanthony96@gmail.com._

#### Why
Provides an insight into the integrity and accuracy of devices in ServiceNow compared to the devices seen in PRTG.

## Requirements
- Python >= 3.9.5
- configparser ~= 5.0.2
- pysnow ~= 0.7.17
- requests ~= 2.25.1
- pandas ~= 1.2.4

## Usage
- Add any additional filtering logic to the API URLs to get specific devices if desired.
    - _Make sure you configure filtering options accordingly. Available options for filtering can be found on the PRTG API:
      https://www.paessler.com/manuals/prtg/live_multiple_object_property_status#advanced_filtering_

- Add additional device properties to make records include more information about a device.

- Edit the config.ini file with relevant PRTG / ServiceNow access information and regex.

- Simply run the script using Python:
  `python PRTG-SNow-Clover-Mismatch-Reporter.py`

## Compatibility
Should be able to run on any machine with a Python interpreter. This script was only tested on a Windows machine running Python 3.9.5.

## Disclaimer
The code provided in this project is an open source example and should not
be treated as an officially supported product. Use at your own risk. If you
encounter any problems, please log an
[issue](https://github.com/CC-Digital-Innovation/PRTG-SNow-Clover-Mismatch-Reporter/issues).

## Contributing
1. Fork it!
2. Create your feature branch: `git checkout -b my-new-feature`
3. Commit your changes: `git commit -am 'Add some feature'`
4. Push to the branch: `git push origin my-new-feature`
5. Submit a pull request ツ

## History
- version 1.0.1 - 2022/02/24
    - Updated copyright year
    - Adjusted comment length in config file
- version 1.0.0 - 2022/02/23
    - (initial release)

## Credits
Anthony Farina <<farinaanthony96@gmail.com>>
