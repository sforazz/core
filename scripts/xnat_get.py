#!/usr/bin/env python
"""
Downloads datasets (e.g. scans) from MBI-XNAT.

By default all scans in the provided session(s) are downloaded to the current
working directory unless they are filtered by the provided '--scan' option(s).
Both the session name and scan filters can be regular expressions, e.g.

    $ xnat-get MRH017_001_MR.* --scan ep2d_diff.*

The destination directory can be specified by the '--directory' option.
Each session will be downloaded to its own folder under the destination
directory unless the '--subject-dir' option is provided in which case the
sessions will be grouped under separate subject directories.

If there are multiple resources for a dataset on MBI-XNAT (unlikely) the one to
download can be specified using the '--format' option, otherwise the only
recognised neuroimaging format (e.g. DICOM, NIfTI, MRtrix format).

DICOM files (ONLY DICOM file) name can be stripped using the option 
--strip_name or -sn. If specified, the final name will be in the format 
000*.dcm.

The downloaded images can be automatically converted to NIfTI or MRtrix formats
using dcm2niix or mrconvert (if the tools are installed and on the system path)
by providing the '--convert_to' option and specifying the desired format.

    $ xnat-get TEST001_001_MR01 --scan ep2d_diff* --convert_to nifti_gz

User credentials can be stored in a ~/.netrc file so that they don't need to be
entered each time a command is run. If a new user provided or netrc doesn't
exist the tool will ask whether to create a ~/.netrc file with the given
credentials.
"""
import os.path
import argparse
import logging
from basecore.database.base import resource_exts
from basecore.database.xnat import get


logger = logging.getLogger('xnat-utils')
handler = logging.StreamHandler()
handler.setLevel(logging.INFO)
formatter = logging.Formatter("%(levelname)s - %(message)s")
handler.setFormatter(formatter)
logger.addHandler(handler)


conv_choices = [f.lower() for f in resource_exts if f != 'DICOM']
converter_choices = ('dcm2niix', 'mrconvert')

parser = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawTextHelpFormatter)
parser.add_argument('session_or_regex', type=str, nargs='+',
                    help=("Name or regular expression of the session(s) to "
                          "download the dataset from"))
parser.add_argument('--target', '-t', type=str, default=None,
                    help=("Path to download the scans to. If not provided the "
                          "current working directory will be used"))
parser.add_argument('--scans', '-x', type=str, default=None, nargs='+',
                    help=("Name of the scans to include in the download. If "
                          "not provided all scans from the session are "
                          "downloaded. Multiple scans can be specified"))
parser.add_argument('--resource', '-r', type=str, default=None,
                    help=("The name of the resource to download. Not "
                          "required if there is only one valid resource for "
                          "each given dataset (e.g. DICOM), which is "
                          "typically the case"))
parser.add_argument('--with_scans', '-w', type=str, default=None, nargs='+',
                    help=("Only download from sessions containing the "
                          "specified scans"))
parser.add_argument('--without_scans', '-o', type=str, default=None, nargs='+',
                    help=("Only download from sessions that don't contain the "
                          "specified scans"))
parser.add_argument('--convert_to', '-c', type=str, default=None,
                    choices=conv_choices,
                    help=("Runs a conversion script on the downloaded scans "
                          "to convert them to a given format if required"))
parser.add_argument('--converter', '-v', type=str, default=None,
                    choices=converter_choices,
                    help=("The conversion tool to convert the downloaded "
                          "datasets. Can be one of '{}'. If not provided and "
                          "both converters are available, dcm2niix "
                          "will be used for DICOM->NIFTI conversion and "
                          "mrconvert for other conversions".format(
                              "', '".join(converter_choices))))
parser.add_argument('--subject_dirs', '-d', action='store_true',
                    default=False, help=(
                        "Whether to organise sessions within subject "
                        "directories to hold the sessions in or not"))
parser.add_argument('--skip_downloaded', '-k', action='store_true',
                    help=("Whether to ignore previously downloaded "
                          "sessions (i.e. if there is a directory in "
                          "the target path matching the session name "
                          "it will be skipped"))
parser.add_argument('--before', '-b', default=None, type=str,
                    help=("Only select sessions before this date "
                          "(in Y-m-d format, e.g. 2018-02-27)"))
parser.add_argument('--after', '-a', default=None, type=str,
                    help=("Only select sessions after this date "
                          "(in Y-m-d format, e.g. 2018-02-27)"))
parser.add_argument('--project', '-p', type=str, default=None,
                    help=("The ID of the project to list the sessions "
                          "from. Useful when using general regular "
                          "expression syntax to limit results to "
                          "a particular project (usually for "
                          "performance)"))
parser.add_argument('--dont_match_scan_id', action='store_true',
                    default=False, help=(
                        "To disable matching on scan ID if the scan "
                        "type is None"))
parser.add_argument('--user', '-u', type=str, default=None,
                    help=("The user to connect to MBI-XNAT with"))
parser.add_argument('--strip_name', '-i', action='store_true', default=False,
                    help=("Whether to strip the default name of each dicom"
                          " file to have just a number. Ex. 0001.dcm. It will"
                          " work just on DICOM files, not NIFTI."))
parser.add_argument('--server', '-s', type=str, default=None,
                    help=("The XNAT server to connect to. If not "
                          "provided the first server found in the "
                          "~/.netrc file will be used, and if it is "
                          "empty the user will be prompted to enter an "
                          "address for the server. Multiple URLs "
                          "stored in the ~/.netrc file can be "
                          "distinguished by passing part of the URL"))
parser.add_argument('--no_netrc', '-n', action='store_true',
                    default=False,
                    help=("Don't use or store user access tokens in "
                          "~/.netrc. Useful if using a public account"))
args = parser.parse_args()


if args.target is None:
    download_dir = os.getcwd()
else:
    download_dir = os.path.expanduser(args.target)

get(args.session_or_regex, download_dir, scans=args.scans,
    resource_name=args.resource, with_scans=args.with_scans,
    without_scans=args.without_scans, convert_to=args.convert_to,
    converter=args.converter, subject_dirs=args.subject_dirs,
    user=args.user, strip_name=args.strip_name, server=args.server,
    use_netrc=(not args.no_netrc),
    match_scan_id=(not args.dont_match_scan_id),
    skip_downloaded=args.skip_downloaded,
    project_id=args.project, before=args.before, after=args.after)
