import time
import os
import shutil
import json
import locale
from sys import platform

if platform == 'darwin':
    from multiprocess import Pool
else:
    from multiprocessing import Pool

import boto3

from utils.Config import Config
from utils.ArguParser import ArguParser
from utils.CfnTrail import CfnTrail
from utils.CrossAccountsValidator import CrossAccountsValidator
from utils.SuppressionsManager import SuppressionsManager
from utils.Tools import _info, _warn
import constants as _C
from utils.AwsRegionSelector import AwsRegionSelector
from Screener import Screener

def number_format(num, places=2):
    return locale.format_string("%.*f", (places, num), True)

scriptStartTime = time.time()
_cli_options = ArguParser.Load()

debugFlag = _cli_options['debug']
# feedbackFlag = _cli_options['feedback']
# testmode = _cli_options['dev']
testmode = _cli_options['ztestmode']
filters = _cli_options['tags']
crossAccounts = _cli_options['crossAccounts']
workerCounts = _cli_options['workerCounts']
beta = _cli_options['beta']
suppress_file = _cli_options['suppress_file']
sequential = _cli_options['sequential']

# print(crossAccounts)
DEBUG = True if debugFlag in _C.CLI_TRUE_KEYWORD_ARRAY or debugFlag is True else False
testmode = True if testmode in _C.CLI_TRUE_KEYWORD_ARRAY or testmode is True else False
crossAccounts = True if crossAccounts in _C.CLI_TRUE_KEYWORD_ARRAY or crossAccounts is True else False
beta = True if beta in _C.CLI_TRUE_KEYWORD_ARRAY or beta is True else False
_cli_options['crossAccounts'] = crossAccounts

# <TODO> analyse the impact profile switching
_AWS_OPTIONS = {
    'signature_version': Config.AWS_SDK['signature_version']
}

Config.init()
Config.set('_AWS_OPTIONS', _AWS_OPTIONS)
Config.set('DEBUG', DEBUG)

# Load suppressions if a file is provided (AFTER Config.init())
if suppress_file:
    suppressions_manager = SuppressionsManager()
    if suppressions_manager.load_suppressions(suppress_file):
        Config.set('suppressions_manager', suppressions_manager)
Config.set('beta', beta)

_AWS_OPTIONS = {
    'signature_version': Config.AWS_SDK['signature_version']
}

Config.set("_SS_PARAMS", _cli_options)
Config.set("_AWS_OPTIONS", _AWS_OPTIONS)

defaultSessionRegion = 'us-east-1'

boto3args = {'region_name': defaultSessionRegion}
profile = _cli_options['profile']
if not profile == False:
    boto3args['profile_name'] = profile
    # boto3.setup_default_session(profile_name=profile)

defaultBoto3 = boto3.Session(**boto3args)

rolesCred = {}
if crossAccounts == True:
    _info('Cross Accounts requested, validating necessary configurations...')
    cav = CrossAccountsValidator()
    cav.checkIfNonDefaultRegionsInParams(_cli_options['regions'])
    cav.setIamGlobalEndpointTokenVersion()
    cav.runValidation()
    cav.resetIamGlobalEndpointTokenVersion()
    if cav.isValidated() == False:
        print('CrossAccountsFlag=True but failed to validate, exit...')
        exit()
    
    if cav.checkIfIncludeThisAccount() == True:
        rolesCred['default'] = {}
    
    tmp = cav.getCred()
    rolesCred.update(tmp)
else:
    rolesCred = {'default': {}}

## Cleanup existing static resources if any
for file in os.listdir(_C.ADMINLTE_DIR):
    if file.isnumeric() == True:
        shutil.rmtree(_C.ADMINLTE_DIR + '/' + file)

acctLoop = 0
CfnTrailObj = CfnTrail()

for acctId, cred in rolesCred.items():
    acctLoop = acctLoop + 1
    flagSkipPromptForRegionConfirmation = True
    if acctLoop == 1:
        flagSkipPromptForRegionConfirmation = False
    
    tcred = cred.copy()
    tcred['region_name'] = defaultSessionRegion
    aid = acctId
    if acctId == 'default':
        aid = 'Current Account'
    
    
    if acctId != 'default':
        newSess = boto3.session.Session(**tcred)
        Config.set('ssBoto', newSess)
    else:
        Config.set('ssBoto', defaultBoto3)

    
    Config.set('scanned', {'resources': 0, 'rules': 0, 'exceptions': 0})
    if _cli_options['regions'] == None:
        print("--regions option is not present. Generating region list...")
        
        regions = AwsRegionSelector.prompt_for_region(flagSkipPromptForRegionConfirmation)
        if not regions or len(regions.split(',')) == 0:
            print("No valid region(s) selected. Exiting.")
            exit()
        
        # Set back to cli options
        _cli_options['regions'] = regions
    
    services = _cli_options['services'].split(',')
    regions = _cli_options['regions'].split(',')
    
    Config.set('PARAMS_REGION_ALL', False)
    if regions[0] == 'ALL':
        Config.set('PARAMS_REGION_ALL', True)
        # regions = AwsRegionSelector.get_all_enabled_regions(True)
        ## Can pass in True for RegionSelector to skip prompt
        regions = AwsRegionSelector.get_all_enabled_regions(flagSkipPromptForRegionConfirmation)
    
    
    if acctLoop == 1:
        Config.set('REGIONS_SELECTED', regions)
        
    frameworks = []
    if len(_cli_options['frameworks']) > 0:
        frameworks = _cli_options['frameworks'].split(',')
    
    tempConfig = _AWS_OPTIONS.copy();
    tempConfig['region'] = regions[0]
    
    Config.setAccountInfo(tempConfig)
    acctInfo = Config.get('stsInfo')
    print("")
    print("=================================================")
    print("Processing the following account id: " + acctInfo['Account'])
    print("=================================================")
    print("")
    
    ## Build List of Accounts for dropdown...
    if acctLoop == 1:
        listOfAccts = []
        if acctId == 'default':
            listOfAccts.append(acctInfo['Account'])
        
        for tacctId, tcred in rolesCred.items():
            if tacctId != 'default':
                listOfAccts.append(tacctId)
            
        Config.set('ListOfAccounts', listOfAccts)
    
    contexts = {}
    charts = {}
    serviceStat = {}
    # GLOBALRESOURCES = []
    
    oo = Config.get('_AWS_OPTIONS')
    
    ## Added mpeid to CFStack
    mpeid = None
    otherParams = _cli_options.get('others', None)
    if otherParams is not None:
        try:
            oparams = json.loads(otherParams)
            mpeInfo = oparams.get('mpe', None)
            if mpeInfo is not None:
                mpeid = mpeInfo.get('id', None)
        except json.JSONDecodeError as e:
            print("Unable to read --others parameters, invalid JSON format provided")
            print(f"Error decoding JSON: {e}")
            exit()

    if testmode == False:
        cfnAdditionalStr = None
        if mpeid is not None: 
            cfnAdditionalStr = " --mpeid:{}".format(mpeid)
        CfnTrailObj.boto3init(cfnAdditionalStr)
        CfnTrailObj.createStack()
    
    overallTimeStart = time.time()
    # os.chdir('__fork')
    directory = '__fork'
    if not os.path.exists(directory):
        os.mkdir(directory)
    
    files_in_directory = os.listdir(directory)
    filtered_files = [file for file in files_in_directory if (file.endswith(".json") or file=='all.csv')]
    for file in filtered_files:
        path_to_file = os.path.join(directory, file)
        os.remove(path_to_file)
    
    with open(directory + '/tail.txt', 'w') as fp:
        pass
    
    special_services = {'iam', 's3'}
    input_ranges = {}

    ## Make IAM and S3 to be separate pool
    if 'iam' in services:
        input_ranges['iam'] = ('iam', regions, filters)

    input_ranges.update({service: (service, regions, filters) for service in services if service not in special_services})

    if 's3' in services:
        input_ranges['s3'] = ('s3', regions, filters)

    input_ranges = list(input_ranges.values())

    if sequential:
        # Run sequentially to avoid macOS hanging issues
        for input_range in input_ranges:
            Screener.scanByService(*input_range)
    else:
        # Run in parallel (default behavior)
        pool = Pool(processes=int(workerCounts))
        pool.starmap(Screener.scanByService, input_ranges)
        pool.close()

    # if testmode == False:
        # CfnTrailObj.deleteStack()
    
    ## <TODO>
    ## parallel logic to be implement in Python
    scanned = {
        'resources': 0,
        'rules': 0,
        'exceptions': 0,
        'timespent': 0
    }
    
    inventory = {}
    
    hasGlobal = False
    for file in os.listdir(_C.FORK_DIR):
        if file[0] == '.' or file == _C.SESSUID_FILENAME or file == 'tail.txt' or file == 'error.txt' or file == 'empty.txt' or file == 'all.csv' or file[0:10] == 'CustomPage':
            continue
        f = file.split('.')
        if len(f) == 2:
            if f[0] not in contexts:
                contexts[f[0]] = {}
            contexts[f[0]]['results'] = json.loads(open(_C.FORK_DIR + '/' + file).read())
        elif f[1] == "charts":
            ## Create and consolidate charts findings
            if f[0] not in contexts:
                contexts[f[0]] = {}
            contexts[f[0]]['charts'] = json.loads(open(_C.FORK_DIR + '/' + file).read())
        else:
            cnt, rules, exceptions, timespent = list(json.loads(open(_C.FORK_DIR + '/' + file).read()).values())
            
            serviceStat[f[0]] = cnt
            scanned['resources'] += cnt
            scanned['rules'] += rules
            scanned['exceptions'] += exceptions
            scanned['timespent'] += timespent
            if f[0] in Config.GLOBAL_SERVICES:
                hasGlobal = True
    
    # if testmode == True:
    #   exit("Test mode enable, script halted")
    
    timespent = round(time.time() - overallTimeStart, 3)
    scanned['timespent'] = timespent
    Config.set('SCREENER-SUMMARY', scanned)
    
    print("Total Resources scanned: " + str(number_format(scanned['resources'])) + " | No. Rules executed: " + str(number_format(scanned['rules'])))
    print("Time consumed (seconds): " + str(timespent))
    
    # Cleanup
    # os.chdir(_C.HTML_DIR)
    ACCTDIR = Config.get('HTML_ACCOUNT_FOLDER_FULLPATH')
    
    filetodel = ACCTDIR + '/error.txt'
    if os.path.exists(filetodel):
        os.remove(filetodel)
        
    filetodel = ACCTDIR + '/all.csv'
    if os.path.exists(filetodel):
        os.remove(filetodel)
    
    directory = _C.ADMINLTE_DIR
    files_in_directory = os.listdir(directory)
    filtered_folders = [folder for folder in files_in_directory if folder.endswith("XX")]
    for folder in filtered_folders:
        path_to_folder = os.path.join(directory, folder)
        shutil.rmtree(path_to_folder)

    os.chdir(_C.ROOT_DIR)
    filetodel = _C.ROOT_DIR + '/output.zip'
    if os.path.exists(filetodel):
        os.remove(filetodel)
    
    
    ## Generate output
    uploadToS3 = False
    
    ## <TODO>
    ## Might be able breakdown the function further to leverage on multi-processing
    
    Config.set('cli_services', serviceStat)
    Config.set('cli_regions', regions)
    Config.set('cli_frameworks', frameworks)
    
    Screener.generateScreenerOutput(contexts, hasGlobal, regions, uploadToS3)
    
    # os.chdir(_C.FORK_DIR)
    filetodel = _C.FORK_DIR + '/tail.txt'
    if os.path.exists(filetodel):
        os.remove(filetodel)
    # os.system('rm -f tail.txt')
    
    src = _C.FORK_DIR + '/error.txt'
    if os.path.exists(src):
        dest = ACCTDIR + '/error.txt'
        os.rename(src, dest)
        
    src = _C.FORK_DIR + '/all.csv'
    if os.path.exists(src):
        dest = ACCTDIR + '/all.csv'
        os.rename(src, dest)
    

adminlteDir = _C.ADMINLTE_ROOT_DIR

# Copy the standalone server script to the adminlte directory before zipping
server_script_src = os.path.join(_C.ROOT_DIR, 'start_report_server.py')
server_script_dest = os.path.join(adminlteDir, 'start_report_server.py')
batch_script_src = os.path.join(_C.ROOT_DIR, 'start_report_server.bat')
batch_script_dest = os.path.join(adminlteDir, 'start_report_server.bat')

if os.path.exists(server_script_src):
    shutil.copy2(server_script_src, server_script_dest)
    print("📦 Added standalone report server to output package")

if os.path.exists(batch_script_src):
    shutil.copy2(batch_script_src, batch_script_dest)
    print("📦 Added Windows batch file for easy server startup")

# Create README for the standalone server
readme_content = """# AWS Service Screener Report

## Viewing the Report

This package contains your AWS Service Screener report. You have multiple options to view it:

### Option 1: Standalone Web Server (Recommended)

**For Linux/Mac/CloudShell:**
```bash
python3 start_report_server.py
```

**For Windows:**
- Double-click `start_report_server.bat`, OR
- Open Command Prompt and run: `python start_report_server.py`

This will:
- Start a local web server (usually on port 8000)
- Automatically open your browser to view the report
- Handle all CORS and file access issues
- Work on any system with Python 3.x installed

### Option 2: Custom Port
If port 8000 is already in use:
```bash
python3 start_report_server.py 8080
```

### Option 3: Direct File Access (Limited)
If you have a local web server already running:
- Open index.html directly in your browser
- Note: Some features may not work due to CORS restrictions

## Troubleshooting

- **Port already in use**: Try a different port (see Option 2 above)
- **Python not found**: Make sure Python 3.x is installed
- **Permission denied**: Make sure you've extracted all files properly
- **Windows users**: If double-clicking the .bat file doesn't work, try running from Command Prompt

## Report Structure

- `index.html` - Main report dashboard
- Account folders (numbered) - Individual account reports
- `start_report_server.py` - Cross-platform web server script
- `start_report_server.bat` - Windows launcher (double-click to run)
- `README.md` - This file

## System Requirements

- Python 3.x (most systems have this pre-installed)
- Any modern web browser
- No additional dependencies required

For more information, visit: https://github.com/vforvarun/aws-service-screener
"""

readme_path = os.path.join(adminlteDir, 'README.md')
with open(readme_path, 'w') as f:
    f.write(readme_content)

shutil.make_archive('output', 'zip', adminlteDir)

print("Pages generated, download \033[1;42moutput.zip\033[0m to view")
print("CloudShell user, you may use this path: \033[1;42m =====> \033[0m /tmp/aws-service-screener/output.zip \033[1;42m <===== \033[0m")
print("")
print("📦 The output.zip includes a standalone web server script!")
print("💡 After extracting: run 'python3 start_report_server.py' to view the report")

scriptTimeSpent = round(time.time() - scriptStartTime, 3)
print("@ Thank you for using {}, script spent {}s to complete @".format(Config.ADVISOR['TITLE'], scriptTimeSpent))

if beta:
    print("")
    print("\033[93m[-- ..... --] BETA MODE ENABLED [-- ..... --] \033[0m")
    print("Current Beta Features:")
    print("\033[96m  01/ Concurrent Mode on Evaluator (Attempt to improve performance) \033[0m")
    print("\033[96m  02/ API Buttons on each service html \033[0m")
    print("\033[93m[-- ..... --] THANK YOU FOR TESTING BETA FEATURES [-- ..... --] \033[0m")

print("\n👋 Script completed successfully!")
