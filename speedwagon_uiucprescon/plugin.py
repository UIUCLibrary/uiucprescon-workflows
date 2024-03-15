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
from .workflow_convertCapOnePresToDigitalLibJP2 import (
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
from .workflow_batch_to_HathiTrust_TIFF import (
    CaptureOneBatchToHathiComplete,
)
from .workflow_capture_one_to_dl_compound import (
    CaptureOneToDlCompoundWorkflow,
)
from .workflow_capture_one_to_hathi import (
    CaptureOneToHathiTiffPackageWorkflow,
)
from .workflow_convertTifftoHathiTrustJP2 import (
    ConvertTiffToHathiJp2Workflow,
)
from .workflow_make_checksum import (
    RegenerateChecksumBatchSingleWorkflow,
    RegenerateChecksumBatchMultipleWorkflow,
)


active_workflows: typing.List[typing.Type[speedwagon.Workflow]] = [
    GenerateMarcXMLFilesWorkflow,
    CaptureOneToDlCompoundAndDLWorkflow,
    CompletenessWorkflow,
    ConvertTiffPreservationToDLJp2Workflow,
    HathiLimitedToDLWorkflow,
    HathiPrepWorkflow,
    MakeChecksumBatchSingleWorkflow,
    MakeChecksumBatchMultipleWorkflow,
    MakeJp2Workflow,
    MedusaPreingestCuration,
    OCRWorkflow,
    ValidateImageMetadataWorkflow,
    ChecksumWorkflow,
    VerifyChecksumBatchSingleWorkflow,
    ZipPackagesWorkflow,
]

deprecated_workflows: typing.List[typing.Type[speedwagon.Workflow]] = [
    CaptureOneBatchToHathiComplete,
    CaptureOneToDlCompoundWorkflow,
    CaptureOneToHathiTiffPackageWorkflow,
    ConvertTiffToHathiJp2Workflow,
    RegenerateChecksumBatchSingleWorkflow,
    RegenerateChecksumBatchMultipleWorkflow,
]


class TesseractConfigSetupTask(AbsSystemTask):
    def __init__(self) -> None:
        super().__init__()
        self.config_file_location_strategy = StandardConfigFileLocator()

    def get_config_file(self) -> str:
        """Get config file path."""
        return os.path.join(
            self.config_file_location_strategy.get_app_data_dir(),
            WORKFLOWS_SETTINGS_YML_FILE_NAME,
        )

    @staticmethod
    def default_tesseract_data_path() -> str:
        """Get the default path to tessdata files."""
        return os.path.join(
            StandardConfigFileLocator().get_user_data_dir(),
            "tessdata"
        )

    def run(self) -> None:
        yaml_file = self.get_config_file()

        manager = WorkflowSettingsManager(
            getter_strategy=WorkflowSettingsYAMLResolver(yaml_file),
            setter_strategy=WorkflowSettingsYamlExporter(yaml_file)
        )
        workflow_settings: speedwagon.config.SettingsData = {}
        ocr_workflow = OCRWorkflow()
        ocr_existing_options = manager.get_workflow_settings(ocr_workflow)
        if "Tesseract data file location" not in ocr_existing_options:
            workflow_settings[
                "Tesseract data file location"
            ] = self.default_tesseract_data_path()
        if workflow_settings:
            manager.save_workflow_settings(ocr_workflow, workflow_settings)

    def description(self) -> str:
        return 'Setting up Tesseract data configuration settings.'


# def register_active_plugin() -> Plugin:
#     new_plugin = Plugin()
#     for workflow in active_workflows:
#         new_plugin.register_workflow(workflow)
#     new_plugin.register_plugin_startup_task(TesseractConfigSetupTask())
#     return new_plugin
#
#
# def register_deprecated_plugin() -> Plugin:
#     new_plugin = Plugin()
#     for workflow in deprecated_workflows:
#         new_plugin.register_workflow(workflow)
#     return new_plugin
