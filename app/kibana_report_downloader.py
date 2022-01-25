import os
import shutil
import requests
import datetime
import glob
import time
import json
from codecs import encode, decode
import getopt, sys
import urllib.parse

# Command Line based globals
report_file = ""
data_folder = ""
wip_folder = ""
wip_remove_flag = False
kibanaEndpoint = ""
startDateGBL = ""
endDateGBL = ""

# CONST
additional_split = 8
headers_dict = {
                    "Cookie": "",
                    "kbn-xsrf": "true",
                    "cache-control": 'no-cache',
                    "content-type": 'application/json',
                    "pragma": 'no-cache'}

#########################################################################################################
# Misc. setup functions
#########################################################################################################
def configSession(sessionToken):
    headers_dict["Cookie"] = "uaa-auth=" + sessionToken

def setupDataFolder(data_folder_location):
    isExist = os.path.exists(data_folder_location)
    if not isExist:
        os.makedirs(data_folder_location)

def setupWIPFolder(data_folder_location):
    isExist = os.path.exists(wip_folder )
    if not isExist:
        os.makedirs(wip_folder)

def removeWIPFolder():
    isExist = os.path.exists(wip_folder)
    if isExist:
        shutil.rmtree(wip_folder, ignore_errors=True)

def mergeMultipleFiles(report_filename):

   def isolator(dzin):
    rez = None;
    # first get rid of the extension
    a = dzin.split('.');
    # front part is in a[0], split again on ^ ignoring prefix part
    b = a[0].split('^')[1:];
    # this will let the string be as long as needed
    for item in b:
        # zfill takes a string numeric and pads it
        if rez is None:
            rez = item.zfill(4);
        else:
            rez = rez + item.zfill(4);  
    if rez is None:
        raise Exception("unable to properly parse " + dzin);
    return rez;
 
   merge_files = sorted(
       filter( 
         os.path.isfile,
         glob.glob(wip_folder + "\\" + report_filename + "*.csv") 
       )
      ,key = isolator
   );

   header_saved = False
   with open(data_folder + "\\" + report_filename + ".csv",'w', encoding="utf8") as fout:
      for fname in merge_files:
         with open(fname, encoding="utf8") as fin:
            header = next(fin)
            if not header_saved:
               fout.write(header)
               header_saved = True
            for line in fin:
               fout.write(line)


#########################################################################################################
# Takes a start and end date and an interval to equally make a new array of dates
#########################################################################################################
def time_trunc_str(dt):
   us = str(dt.microsecond)
   f = us[:3] if len(us) > 3 else us
   z = "%d-%02d-%02dT%02d:%02d:%02d.%03dZ" % (dt.year, dt.month, dt.day, dt.hour, dt.minute, dt.second, int(f))
   return z;
   
def time_trunc(dt):
   df = '%Y-%m-%dT%H:%M:%S.%fZ'; 
   return datetime.datetime.strptime(time_trunc_str(dt),df);
   
def splitDatesEquallyByInterval(start_date_range, end_date_range, intv):

   print()
   print(start_date_range)
   print(end_date_range)
   print()
   
   results   = [];
   date_form = '%Y-%m-%dT%H:%M:%S.%fZ'
   start = datetime.datetime.strptime(start_date_range, date_form);
   end   = datetime.datetime.strptime(end_date_range  , date_form);
   diff  = (end - start ) / intv;
   bump  = datetime.timedelta(milliseconds=1);

   for i in range(0,intv,1):
      results.append(
         [
             time_trunc(start + (diff * i)) + bump
            ,time_trunc((start + (diff * (i + 1))))
         ]
      );
      
   results[0][0]  = start;
   results[-1][1] = end;

   for i in range(len(results)): 
      results[i][0] = time_trunc_str(results[i][0])
      results[i][1] = time_trunc_str(results[i][1])

   return results;


#########################################################################################################
# Takes canned POST string from Kibana UI and replaces the hardcoded date values
#########################################################################################################
def injectNewDateValues(reportURL, newStartDT, newEndDT):
  tempURL = urllib.parse.unquote(reportURL)
  startlocationIdx = tempURL.index("(range:('@timestamp':(format:strict_date_optional_time,gte:'",)
  endlocationIdx = tempURL.index(')))),', startlocationIdx ) + len(')))),')
  existingStr = tempURL[startlocationIdx:endlocationIdx]
  newdateRangeStr = "(range:('@timestamp':(format:strict_date_optional_time,gte:'" +  newStartDT + "',lte:'" + newEndDT + "')))),"
  tempURL = tempURL.replace(existingStr, newdateRangeStr)
  return tempURL


#########################################################################################################
#
#########################################################################################################
def watch4ReportCompletion(job_id, counter): 
    
    notDone = True

    while notDone == True:
        url = kibanaEndpoint + '/api/reporting/jobs/list?page=0&ids=' + job_id
        response = requests.get(url, headers=headers_dict)
        data = response.json()
        if data[0]["_source"]["status"] == 'completed':
            notDone = False
        else: 
            print("Waiting for increment: " + str(counter))
    
    return


#########################################################################################################
#
#########################################################################################################
def downloadReportandCheckFileSize(report_name, counter, job_id): 
    
    url = kibanaEndpoint + '/api/reporting/jobs/download/' + job_id
    response = requests.get(url, headers=headers_dict)
    filename = report_name + "^" + str(counter) + ".csv"
    abs_file_path = wip_folder + "\\" + filename
    open(abs_file_path, 'wb').write(response.content)
    print("Downloaded increment: " + str(counter))

    file_size = os.path.getsize(abs_file_path) / (1024*1024) #in MB
    if file_size> 19.5:
        if os.path.isfile(abs_file_path):
            os.remove(abs_file_path)
        return False
    else:
        return True


#########################################################################################################
# 
#########################################################################################################

def reportExtractor(report_name, counter, report_url, newStartDT, newEndDT):
    report_url = injectNewDateValues(report_url, newStartDT, newEndDT)

    # Unfortunately I could not get the native COPY POST URL (which uses query parameters) to work.
    # Based on this I mimicked the Kibana UI and changed the query parameters to a JSON body object.
    payload = { "jobParams": '' }
    searchTerm = 'csv?jobParams='
    jobParamLocation = report_url.index(searchTerm) + len(searchTerm)
    jobServiceLocation = report_url.index('/api/')
    ReportSubdomain = report_url[0:jobServiceLocation]
    payload["jobParams"] = report_url[jobParamLocation:]
    body = json.dumps(payload, separators=(',', ':'))
    new_reportURL = report_url[0:report_url.index('/generate/csv') + len('/generate/csv')]

    # Request the data
    response = requests.post(new_reportURL, headers=headers_dict, data=body)
    if response.status_code == 200:
        data = response.json()
        watch4ReportCompletion(data["job"]["id"],counter)
        if downloadReportandCheckFileSize(report_name, counter, data["job"]["id"]) == False:
            print("Download too big, break things down further.")
            report_ranges = splitDatesEquallyByInterval(newStartDT, newEndDT, additional_split)
            subcounter = 0
            for rangeitem in report_ranges:
                subcounter += 1
                reportExtractor(report_name + "^" + str(counter), subcounter, report_url, rangeitem[0], rangeitem[1])
            
    return

#########################################################################################################
# Start
#########################################################################################################


argumentList = sys.argv[1:]
options = "w:d:r:s:e:a:k:"
long_options = ["del_wip=", "data_folder=", "report_file=", "start_date=", "end_date=", "auth=", "kibana_api="]
 
try:
    # Parsing argument
    arguments, values = getopt.getopt(argumentList, options, long_options)
     
    # checking each argument
    for currentArgument, currentValue in arguments:
 
        if currentArgument in ("-w", "--del_wip"):
            if currentValue.lower == "true":
                wip_remove_flag = True
             
        elif currentArgument in ("-d", "--data_folder"):
            data_folder = os.path.abspath(currentValue)
            wip_folder = os.path.abspath(data_folder + "\\wip")

        elif currentArgument in ("-r", "--report_file"):
            report_file = currentValue

        elif currentArgument in ("-s", "--start_date"):
            startDateGBL = currentValue

        elif currentArgument in ("-e", "--end_date"):
            endDateGBL = currentValue

        elif currentArgument in ("-a", "--auth"):
            configSession(currentValue)

        elif currentArgument in ("-k", "--kibana_api"):
            kibanaEndpoint = currentValue
             
except getopt.error as err:
    # output error, and return with an error code
    print (str(err))

setupDataFolder(data_folder)
setupWIPFolder(data_folder)

with open(report_file) as f:
    report_data = json.load(f)

print()
print('Report start period: ' + startDateGBL)
print('Report end period:' + endDateGBL)
print()

for reports in report_data:
    counter = 0
    report_ranges = splitDatesEquallyByInterval(startDateGBL, endDateGBL, reports["datesplit"])
    print()
    print(reports["name"] + " : Splits=" + str(reports["datesplit"]))
    print("------------------------------------------------------------------------")

    for rangeitem in report_ranges:
        counter += 1
        reportExtractor(reports["name"], counter, reports["url"], rangeitem[0], rangeitem[1])
    mergeMultipleFiles(reports["name"])
    if wip_remove_flag == True:
        removeWIPFolder()
