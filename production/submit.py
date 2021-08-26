import os
import sys
#from input_crab_data import dataset_files
import yaml
import datetime
from fnmatch import fnmatch
from argparse import ArgumentParser
from httplib import HTTPException
from multiprocessing import Process

from CRABClient.UserUtilities import config, ClientException, getUsernameFromCRIC
from CRABAPI.RawCommand import crabCommand
from CRABClient.ClientExceptions import ClientException

#from .production_tag import production_tag # Get from a text file
# Get from git tag (tbd)
production_tag = "vTEST2" # Specify by hand
requestname_base = "pfnano"
output_site = "T3_US_FNALLPC"
output_lfn_base = "/store/group/lpcpfnano/{username}/{production_tag}".format(
                                                    username=getUsernameFromCRIC(), 
                                                    production_tag=production_tag)

if __name__ == '__main__':

    def submit(config):
        try:
            crabCommand('submit', config=config)
        except HTTPException as hte:
            print "Failed submitting task: %s" % (hte.headers)
            print hte
        except ClientException as cle:
            print "Failed submitting task: %s" % (cle)

    parser = ArgumentParser()
    parser.add_argument('-y', '--yaml', default = 'samples_datatest.yaml', help = 'File with dataset descriptions')
    args = parser.parse_args()

    with open(args.yaml) as f:
        doc = yaml.load(f) # Parse YAML file
        defaults = doc['defaults'] if 'defaults' in doc else {}

        for sample in sorted(doc["samples"].keys()):
            info = doc["samples"][sample]
            print("\n\n*** Sample {} ***".format(sample))

            for dataset_shortname, dataset in info['datasets'].iteritems():            
                print("Submitting {}: {}".format(dataset_shortname, dataset))

                isMC = info.get("isMC", defaults.get("isMC", None))
                if isMC == None:
                    raise ValueError("Please specify parameter isMC")

                this_config = config()

                this_config.section_('General')
                this_config.General.transferOutputs = True
                this_config.General.transferLogs = True
                this_config.General.workArea = "crab/{}/{}/{}".format(requestname_base, production_tag, info["year"])
                this_config.General.requestName = "{}_{}_{}".format(requestname_base, info["year"], dataset_shortname)

                this_config.section_('JobType')
                this_config.JobType.pluginName = 'Analysis'
                this_config.JobType.psetName = os.path.expandvars(info.get("pset", defaults.get("pset", None)))
                this_config.JobType.maxJobRuntimeMin = 3000
                this_config.JobType.allowUndistributedCMSSW = True
                this_config.JobType.numCores = 4
                this_config.JobType.maxMemoryMB = 4000
                #this_config.JobType.outputFiles = ["_".join("nano", "mc" if isMC else "data")]
                #this_config.JobType.outputFiles = ["nanoskim.root", "hists.root"]
                #this_config.JobType.outputFiles = ['_'.join(['DijetSkim', 'mc' if isMC else 'data', production_tag])+'.root']
                #this_config.JobType.sendPythonFolder  = True
                globaltag = info.get(
                        'globaltag',
                        defaults.get('globaltag', None)
                )
                this_config.JobType.pyCfgParams = [
                        'isMC={}'.format(isMC), 
                        'reportEvery=1000',
                        'tag={}'.format(production_tag),
                        'globalTag={}'.format(globaltag),
                ]

                this_config.section_('User')
                this_config.section_('Site')
                this_config.Site.storageSite = output_site

                this_config.section_('Data')
                this_config.Data.publication = False
                this_config.Data.outLFNDirBase = "{}/{}".format(output_lfn_base, sample)
                this_config.Data.outputDatasetTag = dataset_shortname
                # Outputs land at outLFNDirBase/outputDatasetTag
                this_config.Data.inputDBS = 'global'
                this_config.Data.inputDataset = dataset
                splitting_mode = info.get(
                    "splitting", 
                    defaults.get("splitting", "Automatic")
                    )
                if not splitting_mode in ["Automatic", "FileBased", "LumiBased"]:
                    raise ValueError("Unrecognized splitting mode: {}".format(splitting_mode))
                this_config.Data.splitting = splitting_mode

                if not isMC:
                        this_config.Data.lumiMask = info.get(
                                'lumimask', 
                                defaults.get('lumimask', None)
                        )
                else:
                        this_config.Data.lumiMask = ''

                unitsPerJob = info.get("unitsPerJob", defaults.get("unitsPerJob", None))
                if unitsPerJob is not None:
                    this_config.Data.unitsPerJob = unitsPerJob

                totalUnits = info.get("totalUnits", defaults.get("totalUnits", None))
                if totalUnits is not None:
                    this_config.Data.totalUnits = totalUnits

                allowInvalid = info.get("allowInvalid", False)
                if allowInvalid:
                  config.Data.allowNonValidInputDataset = True
                
                print this_config
                p = Process(target=submit, args=(this_config,))
                p.start()
                p.join()
                #submit(this_config)
            print("*** Done with Sample {} ***\n\n".format(sample))

