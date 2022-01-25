# Kibana Report Downloader
A simple python script that allows the downloading of Kibana reports based on a configurable timeframe and output file size.

## Reasoning for its creation

The logs supporting my application are only available to me via a Kibana interface which is tied to a Cloud Foundry implementation. The Kibana instance is configured to limit the download file size and quietly truncate at 20MB. Based on this, I needed a way to easily split my report request up into chunks to work within the 20MB download limit but to also reconstruct the chunks back into a single report file.

## Initial Goals

 - Automate Kibana report extraction to support my auditing and archiving requirements.
 - Make the code simple to understand to instill trust in its usage.
 - Avoid using 3rd party dependencies if possible (i.e., focus on using base Python features)
 - Provide a solution that can be easily enhanced as time allows.

## Script execution steps

 1. Clone this repository.
 2. pip install requirements.txt (i.e., pip install -r requirements.txt)
 3. *Suggested step* Create another git repository to store your custom Kibana report definitions.
 4.  Cache your Kibana report definitions in a .json file(s) based on the [sample .json](/docs/sample_report.json) file format.
 5. Obtain an active Kibana security token (right now this means the value of uaa-auth).
 6. Run the Kibana report downloader script.

## Obtaining Kibana report definitions

1.	Log in to Kibana (I’m using v 7.9.3)
2.	Click Discover
3.	Click Open
4.	Find your report and open it
5.	Click Share, CSV Reports, “Copy POST URL”
6.	Save each report definition in a .json file

## Usage Example (against Kibana running in cloud.gov)

**Example:** 

python kibana_report_downloader.py --del_wip=false --data_folder=.\data --report_file=.\reports\test.json --start_date=2021-12-01T00:00:00.000Z --end_date=2021-12-31T23:59:59.999Z --kibana_api=https://logs.fr.cloud.gov --auth=*put value of uaa-auth here*

 - **del_wip** = true/false flag to determine if the work-in-progress folder should be deleted after report concatenation. It can be useful to keep if you want to debug the processing results.
 - **data_folder** = folder path to where the downloaded report(s) should be saved. 
 - **report_file** = file path to the .json file storing the Kibana report definitions to execute (1 or more).
 - **start_date** = The start date that will be injected into report requests.
 - **end_date** = The end date that will be injected into report requests.
 - **kibana_api** = The endpoint to use to download reports (*future* sniff this value out of report URLs)
 - **auth** = The value of uaa-auth which provides access to Kibana from the script (*future* find another way to obtain authentication information)

## Future goals

Please see the the issue tracker.

## Disclaimer

The software is provided "as is", without warranty of any kind, express or implied, including but not limited to the warranties of merchantability, fitness for a particular purpose and noninfringement. In no event shall the authors or copyright holders be liable for any claim, damages, or other liability, whether in an action of contract, tort or otherwise, arising from, out of or in connection with the software or the use or other dealings in the software.