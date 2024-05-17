"""Validating technical metadata."""
from __future__ import annotations

import os
from typing import Optional, List, TypedDict, Mapping, TYPE_CHECKING


from uiucprescon import imagevalidate

import speedwagon
import speedwagon.workflow
from speedwagon.job import Workflow
from speedwagon_uiucprescon import tasks, conditions

if TYPE_CHECKING:
    import sys
    if sys.version_info >= (3, 11):
        from typing import Never
    else:
        from typing_extensions import Never

__all__ = ['ValidateMetadataWorkflow']


JobValues = TypedDict("JobValues", {
    "filename": str,
    "profile_name": str,
})

UserArgs = TypedDict(
    "UserArgs",
    {
        "Profile": str,
        "Input": str,
    }
)


class ValidateMetadataWorkflow(Workflow[UserArgs]):
    """Workflow for validating embedded image file metadata."""

    name = "Validate Metadata"
    description = "Validates the technical metadata for JP2000 files to " \
                  "include x and why resolution, bit depth and color space " \
                  "for images located inside a directory.  The tool also " \
                  "verifies values exist for address, city, state, zip " \
                  "code, country, phone number insuring the provenance of " \
                  "the file." \
                  "\n" \
                  "Input is path that contains subdirectory which " \
                  "containing a series of jp2 files."

    def discover_task_metadata(
        self,
        initial_results: List[  # pylint: disable=unused-argument
            speedwagon.tasks.Result[str]
        ],
        additional_data: Mapping[  # pylint: disable=unused-argument
            str,
            Never
        ],
        user_args: UserArgs,
    ) -> List[JobValues]:
        """Create task metadata based on the files located."""
        new_tasks: List[JobValues] = []

        for image_file in initial_results[0].data:
            new_tasks.append({
                "filename": image_file,
                "profile_name": user_args["Profile"]
            })
        return new_tasks

    def initial_task(
        self,
        task_builder: "speedwagon.tasks.TaskBuilder",
        user_args: UserArgs
    ) -> None:
        """Create task that locates files based on profile selected by user."""
        task_builder.add_subtask(
            LocateImagesTask(
                user_args["Input"],
                user_args["Profile"]
            )
        )

    def job_options(
        self
    ) -> List[
        speedwagon.workflow.AbsOutputOptionDataType[
            speedwagon.workflow.UserDataType
        ]
    ]:
        """Request user options.

        This includes an input folder and a validation profile.
        """
        input_option = \
            speedwagon.workflow.DirectorySelect("Input")
        input_option.add_validation(speedwagon.validators.ExistsOnFileSystem())

        input_option.add_validation(
            speedwagon.validators.IsDirectory(),
            condition=conditions.candidate_exists
        )

        profile_type = speedwagon.workflow.ChoiceSelection("Profile")
        profile_type.placeholder_text = "Select a Profile"

        for profile_name in sorted(imagevalidate.available_profiles()):
            profile_type.add_selection(profile_name)

        return [
            input_option,
            profile_type
        ]

    def create_new_task(
        self,
        task_builder: "speedwagon.tasks.TaskBuilder",
        job_args: JobValues
    ) -> None:
        """Create validation tasks."""
        filename = job_args["filename"]

        subtask = \
            tasks.ValidateImageMetadataTask(
                filename,
                job_args["profile_name"]
            )

        task_builder.add_subtask(subtask)

    @classmethod
    def generate_report(
        cls,
        results: List[
            speedwagon.tasks.Result[
                tasks.validation.ValidateImageMetadataResult
            ]
        ],
        user_args: UserArgs
    ) -> Optional[str]:
        """Generate validation report as a string."""

        def validation_result_filter(
            task_result: speedwagon.tasks.Result[
                tasks.validation.ValidateImageMetadataResult
            ]
        ) -> bool:
            return task_result.source == tasks.ValidateImageMetadataTask

        def filter_only_invalid(
            task_result: tasks.validation.ValidateImageMetadataResult
        ) -> bool:
            return not task_result["valid"]

        def invalid_messages(
            task_result: tasks.validation.ValidateImageMetadataResult
        ) -> str:
            source = task_result["filename"]

            messages = task_result["report"]

            message = "\n".join([
                f"{source}",
                messages
            ])
            return message

        data = list(
            map(lambda x: x.data, filter(validation_result_filter, results))
        )

        line_sep = "\n" + "-" * 60
        total_results = len(data)
        filtered_data = filter(filter_only_invalid, data)
        data_points = list(map(invalid_messages, filtered_data))

        report_data = "\n\n".join(data_points)

        summary = "\n".join([
            f"Validated files located in: {user_args['Input']}",
            f"Total files checked: {total_results}",

        ])

        report = f"\n{line_sep}\n".join(
            [
                "\nReport:",
                summary,
                report_data,
                "\n"
            ]
        )
        return report


class LocateImagesTask(speedwagon.tasks.Subtask[List[str]]):
    name = "Locate Image Files"

    def __init__(self,
                 root: str,
                 profile_name: str) -> None:
        super().__init__()
        self._root = root

        self._profile = imagevalidate.get_profile(profile_name)

    def task_description(self) -> Optional[str]:
        return f"Locating images in {self._root}"

    def work(self) -> bool:
        image_files = []
        for root, _, files in os.walk(self._root):
            for file_name in files:
                _, ext = os.path.splitext(file_name)
                if ext.lower() not in self._profile.valid_extensions:
                    continue
                image_file = os.path.join(root, file_name)
                self.log(f"Found {image_file}")
                image_files.append(image_file)
        self.set_results(image_files)
        return True
