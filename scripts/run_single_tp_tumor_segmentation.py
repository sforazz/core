import os
import argparse
import shutil
from basecore.workflows.registration import single_tp_registration
from basecore.workflows.segmentation import single_tp_tumor_segmentation
from basecore.workflows.bet import brain_extraction
from basecore.workflows.datahandler import (
    xnat_datasink, single_tp_registration_datasource, cinderella_tp0_datasource,
    single_tp_segmentation_datasource)
from basecore.database.pyxnat import get
from basecore.database.base import get_subject_list


if __name__ == "__main__":

    PARSER = argparse.ArgumentParser()

    PARSER.add_argument('--input_dir', '-i', type=str,
                        help=('Exisisting directory with the subject(s) to process'))
    PARSER.add_argument('--work_dir', '-w', type=str,
                        help=('Directory where to store the results.'))
    PARSER.add_argument('--run_registration', '-reg', action='store_true',
                        help=('Whether or not to run registration before segmentation.'
                              ' Default is False.'))
    PARSER.add_argument('--run_bet', '-bet', action='store_true',
                        help=('Whether or not to run brain extraction before registration.'
                              ' Default is False.'))
    PARSER.add_argument('--gtv_seg_model_dir', '-gtv_md', type=str, default='None',
                        help=('Directory with the model parameters, trained with nnUNet.'))
    PARSER.add_argument('--tumor_seg_model_dir', '-tumor_md', type=str, default='None',
                        help=('Directory with the model parameters, trained with nnUNet.'))
    PARSER.add_argument('--clean-cache', '-c', action='store_true',
                        help=('To remove all the intermediate files. Enable this only '
                              'when you are sure that the workflow is running properly '
                              'otherwise it will always restart from scratch. '
                              'Default False.'))
    PARSER.add_argument('--xnat-sink', '-xs', action='store_true',
                        help=('Whether or not to upload the processed files to XNAT. '
                              'Default is False'))
    PARSER.add_argument('--xnat-source', action='store_true',
                        help=('Whether or not to source data from XNAT. '
                              'Default is False'))
    PARSER.add_argument('--xnat-url', '-xurl', type=str, default='https://central.xnat.org',
                        help=('If xnat-sink, the url of the server must be provided here. '
                              'Default is https://central.xnat.org'))#
    PARSER.add_argument('--xnat-pid', '-xpid', type=str,
                        help=('If xnat-sink, the project ID o the server where to upload '
                              'the results must be provided here.'))
    PARSER.add_argument('--xnat-user', '-xuser', type=str,
                        help=('If xnat-sink, the username on the server must be provided here.'))
    PARSER.add_argument('--xnat-pwd', '-xpwd', type=str,
                        help=('If xnat-sink, the password on the server must be provided here.'))

    ARGS = PARSER.parse_args()

    if ARGS.run_registration or ARGS.xnat_source:
        BASE_DIR = ARGS.input_dir
    else:
        BASE_DIR = os.path.join(ARGS.input_dir, 'registration_results',
                                'results')
    NIPYPE_CACHE_BASE = os.path.join(ARGS.work_dir, 'nipype_cache')
    RESULT_DIR = os.path.join(ARGS.work_dir, 'segmentation_results')
    CLEAN_CACHE = ARGS.clean_cache

    if os.path.isdir(BASE_DIR) and not ARGS.xnat_source:
        sub_list = os.listdir(BASE_DIR)
    elif ARGS.xnat_source and not ARGS.run_registration:
        BASE_DIR = os.path.join(BASE_DIR, 'xnat_cache')
        sub_list = get_subject_list(
            ARGS.xnat_pid, user=ARGS.xnat_user, pwd=ARGS.xnat_pwd,
            url=ARGS.xnat_url)
    elif ARGS.xnat_source and ARGS.run_registration:
        raise NotImplementedError('XNAT data source is currently supported only for tumor '
                                  'segmentation ONLY, i.e. it assumes that you already '
                                  'performed brain extraction and registration and that '
                                  'those results were pushed to XNAT.')
    

    for sub_id in sub_list:
        print('Processing subject {}'.format(sub_id))
        NIPYPE_CACHE = os.path.join(NIPYPE_CACHE_BASE, sub_id)
        if ARGS.run_registration:
            if ARGS.run_bet:
                datasource, sessions, reference = cinderella_tp0_datasource(sub_id, BASE_DIR)
                bet_workflow = brain_extraction(
                    sub_id, datasource, sessions, RESULT_DIR, NIPYPE_CACHE, reference,
                    t10=False)
            else:
                datasource, sessions = single_tp_registration_datasource(
                    sub_id, os.path.join(ARGS.work_dir, 'bet_results', 'results'))
                bet_workflow = None

            reg_workflow = single_tp_registration(
                sub_id, datasource, sessions, reference, RESULT_DIR,
                NIPYPE_CACHE, bet_workflow=bet_workflow)
        else:
            if ARGS.xnat_source:
                get(ARGS.xnat_pid, BASE_DIR, user=ARGS.xnat_user, pwd=ARGS.xnat_pwd,
                    url=ARGS.xnat_url, processed=True, subjects=[sub_id])
            datasource, sessions, reference = single_tp_segmentation_datasource(
                sub_id, BASE_DIR)
            reg_workflow = None
            bet_workflow = None

        seg_workflow = single_tp_tumor_segmentation(
            datasource, sub_id, sessions, ARGS.gtv_seg_model_dir,
            ARGS.tumor_seg_model_dir, RESULT_DIR, NIPYPE_CACHE, reference,
            reg_workflow=reg_workflow, bet_workflow=bet_workflow)

        seg_workflow.run(plugin='Linear')
        if ARGS.xnat_sink:
            print('Uploading the results to XNAT with the following parameters:')
            print('Server: {}'.format(ARGS.xnat_url))
            print('Project ID: {}'.format(ARGS.xnat_pid))
            print('User ID: {}'.format(ARGS.xnat_user))

            xnat_datasink(ARGS.xnat_pid, sub_id, os.path.join(RESULT_DIR, 'results'),
                          ARGS.xnat_user, ARGS.xnat_pwd, url=ARGS.xnat_url, processed=True)

            print('Uploading successfully completed!')
        if CLEAN_CACHE:
            shutil.rmtree(NIPYPE_CACHE)

    print('Done!')
