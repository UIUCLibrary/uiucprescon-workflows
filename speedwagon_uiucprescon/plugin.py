"""plugin.

Define what workflows are part of this plugin.
"""

import typing
import os

import speedwagon
from speedwagon.tasks.system import AbsSystemTask
from speedwagon.config import (
    WorkflowSettingsYAMLResolver,
    WorkflowSettingsYamlExporter,
    WorkflowSettingsManager,
    WORKFLOWS_SETTINGS_YML_FILE_NAME,
    StandardConfigFileLocator,
)

# Active workflows
from .workflow_get_marc import GenerateMarcXMLFilesWorkflow
from .workflow_capture_one_to_dl_compound_and_dl import (
    CaptureOneToDlCompoundAndDLWorkflow,
)
from .workflow_completeness import CompletenessWorkflow
from .workflow_convert_capone_pres_to_digital_lib_jp2 import (
    ConvertTiffPreservationToDLJp2Workflow,
)
from .workflow_hathi_limited_to_dl_compound import (
    HathiLimitedToDLWorkflow,
)
from .workflow_hathiprep import HathiPrepWorkflow
from .workflow_make_checksum import (
    MakeChecksumBatchSingleWorkflow,
    MakeChecksumBatchMultipleWorkflow,
)
from .workflow_make_jp2 import MakeJp2Workflow
from .workflow_medusa_preingest import MedusaPreingestCuration
from .workflow_ocr import OCRWorkflow
from .workflow_validate_hathi_metadata import (
    ValidateImageMetadataWorkflow,
)
from .workflow_verify_checksums import (
    ChecksumWorkflow,
    VerifyChecksumBatchSingleWorkflow,
)
from .workflow_zip_packages import ZipPackagesWorkflow

# Deprecated workflows

from .workflow_capture_one_to_hathi import (
    CaptureOneToHathiTiffPackageWorkflow,
)
from .workflow_convert_tiff_to_hathi_jp2 import (
    ConvertTiffToHathiJp2Workflow,
)
from .workflow_make_checksum import (
    RegenerateChecksumBatchSingleWorkflow,
    RegenerateChecksumBatchMultipleWorkflow,
)

from .workflow_validate_metadata import ValidateMetadataWorkflow

active_workflows: typing.List[typing.Type[speedwagon.Workflow[typing.Any]]] = [
    CaptureOneToDlCompoundAndDLWorkflow,
    ChecksumWorkflow,
    CompletenessWorkflow,
    ConvertTiffPreservationToDLJp2Workflow,
    GenerateMarcXMLFilesWorkflow,
    HathiLimitedToDLWorkflow,
    HathiPrepWorkflow,
    MakeChecksumBatchSingleWorkflow,
    MakeChecksumBatchMultipleWorkflow,
    MakeJp2Workflow,
    MedusaPreingestCuration,
    OCRWorkflow,
    ValidateImageMetadataWorkflow,
    ValidateMetadataWorkflow,
    VerifyChecksumBatchSingleWorkflow,
    ZipPackagesWorkflow,
]

deprecated_workflows: typing.List[
    typing.Type[speedwagon.Workflow[typing.Any]]
] = [
    CaptureOneToHathiTiffPackageWorkflow,
    ConvertTiffToHathiJp2Workflow,
    RegenerateChecksumBatchSingleWorkflow,
    RegenerateChecksumBatchMultipleWorkflow,
]


# class TesseractConfigSetupTask(AbsSystemTask):
#     """Configure Tesseract data location."""
#
#     def __init__(self) -> None:
#         """Create a new TesseractConfigSetupTask object."""
#         super().__init__()
#         self.config_file_location_strategy = StandardConfigFileLocator(
#             config_directory_prefix=CONFIG_DIRECTORY_NAME
#         )
#
#     def get_config_file(self) -> str:
#         """Get config file path."""
#         return os.path.join(
#             self.config_file_location_strategy.get_app_data_dir(),
#             WORKFLOWS_SETTINGS_YML_FILE_NAME,
#         )
#
#     @staticmethod
#     def default_tesseract_data_path() -> str:
#         """Get the default path to tessdata files."""
#         return os.path.join(
#             StandardConfigFileLocator(
#                 config_directory_prefix=CONFIG_DIRECTORY_NAME
#             ).get_user_data_dir(),
#             "tessdata"
#         )
#
#     def run(self) -> None:
#         """Run task."""
#         yaml_file = self.get_config_file()
#
#         manager = WorkflowSettingsManager(
#             getter_strategy=WorkflowSettingsYAMLResolver(yaml_file),
#             setter_strategy=WorkflowSettingsYamlExporter(yaml_file)
#         )
#         workflow_settings: speedwagon.config.SettingsData = {}
#         ocr_workflow = OCRWorkflow()
#         ocr_existing_options = manager.get_workflow_settings(ocr_workflow)
#         if "Tesseract data file location" not in ocr_existing_options:
#             workflow_settings[
#                 "Tesseract data file location"
#             ] = self.default_tesseract_data_path()
#         if workflow_settings:
#             manager.save_workflow_settings(ocr_workflow, workflow_settings)
#
#     def description(self) -> str:
#         """Detailed message to user."""
#         return 'Setting up Tesseract data configuration settings.'
