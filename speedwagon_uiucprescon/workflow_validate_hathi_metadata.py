"""Workflow for validating image metadata."""
from __future__ import annotations
from typing import List, Optional, TYPE_CHECKING, Mapping, TypedDict

from uiucprescon import imagevalidate

import speedwagon
from speedwagon import validators
from speedwagon.job import Workflow
from speedwagon import workflow

from speedwagon_uiucprescon import conditions

if TYPE_CHECKING:
    import sys
    if sys.version_info >= (3, 11):
        from typing import Never
    else:
        from typing_extensions import Never

__all__ = ['ValidateImageMetadataWorkflow']

UserArgs = TypedDict(
    "UserArgs",
    {
        "Input": str
    }
)

JobArgs = TypedDict(
    "JobArgs",
    {
        "source_file": str
    }
)


class ValidateImageMetadataWorkflow(Workflow[UserArgs]):
    """Validate tiff embedded metadata for HathiTrust."""

    name = "Validate Tiff Image Metadata for HathiTrust"
    description = "Validate the metadata located within a tiff file. " \
                  "Validates the technical metadata to include x and why " \
                  "resolution, bit depth and color space for images located " \
                  "inside a directory.  The tool also verifies values exist " \
                  "for address, city, state, zip code, country, phone " \
                  "number insuring the provenance of the file. " \
                  "\n" \
                  "Input is path that contains subdirectory which " \
                  "containing a series of tiff files."

    active = True

    def discover_task_metadata(
        self,
        initial_results: List[  # pylint: disable=unused-argument
            speedwagon.tasks.Result[Never]
        ],
        additional_data: Mapping[str, Never],  # pylint: disable=W0613
        user_args: UserArgs,
    ) -> List[JobArgs]:
        """Generate task metadata."""
        return [{"source_file": user_args["Input"]}]

    def job_options(self) -> List[
        workflow.AbsOutputOptionDataType[workflow.UserDataType]
    ]:
        """Request input setting from user."""
        input_path = workflow.FileSelectData("Input", required=True)
        input_path.add_validation(
            validators.ExistsOnFileSystem(),
        )
        input_path.add_validation(
            validators.IsFile(),
            condition=conditions.candidate_exists
        )

        return [input_path]

    def create_new_task(
        self,
        task_builder: "speedwagon.tasks.TaskBuilder",
        job_args: JobArgs
    ) -> None:
        """Create a validation task."""
        source_file = job_args["source_file"]
        new_task = MetadataValidatorTask(source_file)
        task_builder.add_subtask(new_task)


class MetadataValidatorTask(speedwagon.tasks.Subtask[imagevalidate.Report]):
    name = "Metadata Validation"

    def __init__(self, source_file: str) -> None:
        super().__init__()
        self._source_file = source_file

    def task_description(self) -> Optional[str]:
        return f"Validating Metadata for {self._source_file}"

    def work(self) -> bool:
        hathi_tiff_profile = imagevalidate.Profile(
            imagevalidate.get_profile('HathiTrust Tiff')
        )

        report = hathi_tiff_profile.validate(self._source_file)
        self.log(str(report))
        return True
