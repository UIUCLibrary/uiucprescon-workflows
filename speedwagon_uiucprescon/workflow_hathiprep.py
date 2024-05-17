"""Hathi Prep Workflow."""
from __future__ import annotations
import itertools
import os
from typing import List, Sequence, Dict, Optional, Union, Mapping, TypedDict
import sys

import typing

from uiucprescon.packager.packages import collection
from uiucprescon.packager.common import Metadata

import speedwagon
import speedwagon.tasks.packaging
import speedwagon.workflow
from speedwagon.frontend.interaction import UserRequestFactory, DataItem
from speedwagon import validators

from speedwagon_uiucprescon import tasks

if typing.TYPE_CHECKING:
    if sys.version_info >= (3, 11):
        from typing import Never
    else:
        from typing_extensions import Never

__all__ = ['HathiPrepWorkflow']

UserArgs = TypedDict(
    "UserArgs",
    {
        "input": str,
        "Image File Type": str
    }
)

JobArgs = TypedDict(
    "JobArgs",
    {
        "package_id": str,
        "title_page": str,
        "source_path": str
    }
)


class TitlePageResults(typing.TypedDict):
    title_pages: Dict[str, Optional[str]]


def data_gathering_callback(
    results,  # pylint: disable=unused-argument
    pretask_results: List[speedwagon.tasks.Result[List[collection.Package]]]
) -> List[Sequence[DataItem]]:
    rows: List[Sequence[DataItem]] = []
    values = pretask_results[0]
    for package in values.data:
        title_page = DataItem(
            name="Title Page",
            value=typing.cast(str, package.metadata[Metadata.TITLE_PAGE])
        )
        title_page.editable = True
        files = []
        for i in package:
            for instance in i.instantiations.values():
                files += [os.path.basename(f) for f in instance.files]
        title_page.possible_values = files

        rows.append(
            (
                DataItem(
                    name="Object",
                    value=typing.cast(str, package.metadata[Metadata.ID])
                ),
                title_page,
                DataItem(
                    name="Location",
                    value=typing.cast(str, package.metadata[Metadata.PATH])
                )
            )
        )

    return rows


class HathiPrepWorkflow(speedwagon.Workflow[UserArgs]):
    """Workflow for Hathi prep."""

    name = "Hathi Prep"
    description = "Enables user to select, from a dropdown list of image " \
                  "file names, the title page to be displayed on the " \
                  "HathiTrust website for the item. This updates the .yml " \
                  "file.\n" \
                  "\n" \
                  "NB: It is useful to first identify the desired " \
                  "title page and associated filename in a separate image " \
                  "viewer." \


    def job_options(
            self
    ) -> List[
            speedwagon.workflow.AbsOutputOptionDataType[
                speedwagon.workflow.UserDataType
            ]
    ]:
        """Get user options.

        User Settings:
            * input - folder used as a source path
            * Image File Type - select the type of file to use

        """
        package_type = speedwagon.workflow.ChoiceSelection("Image File Type")
        package_type.placeholder_text = "Select an Image Format"
        package_type.add_selection("JPEG 2000")
        package_type.add_selection("TIFF")

        input_option = speedwagon.workflow.DirectorySelect("input")
        input_option.add_validation(validators.ExistsOnFileSystem())

        return [
            input_option,
            package_type,
        ]

    def initial_task(self,
                     task_builder: "speedwagon.tasks.tasks.TaskBuilder",
                     user_args: UserArgs
                     ) -> None:
        """Look for any packages located in the input argument directory.

        Args:
            task_builder:
            **user_args:

        """
        root = user_args['input']
        task_builder.add_subtask(FindHathiPackagesTask(root))

    def discover_task_metadata(
        self,
        initial_results: List[  # pylint: disable=unused-argument
            speedwagon.tasks.Result[Never]
        ],
        additional_data: Mapping[str, Sequence[collection.Package]],
        user_args: UserArgs,  # pylint: disable=unused-argument
    ) -> List[JobArgs]:
        """Get enough information about the packages to create a new job.

        Args:
            initial_results:
            additional_data:
            **user_args:

        Returns:
            Returns a dictionary containing the title page, package id, and
                the source path.

        """
        jobs: List[JobArgs] = []
        packages: Sequence[collection.Package] = additional_data["packages"]
        for package in packages:
            job: JobArgs = {
                "package_id":
                    typing.cast(str, package.metadata[Metadata.ID]),
                "title_page":
                    typing.cast(
                        str,
                        package.metadata[Metadata.TITLE_PAGE]
                    ),
                "source_path":
                    typing.cast(
                        str,
                        package.metadata[Metadata.PATH]
                    )
            }
            jobs.append(job)

        return jobs

    def create_new_task(
        self,
        task_builder: "speedwagon.tasks.TaskBuilder",
        job_args: JobArgs
    ) -> None:
        """Add yaml and checksum tasks.

        Args:
            task_builder:
            **job_args:

        """
        title_page = job_args['title_page']
        source = job_args['source_path']
        package_id = job_args['package_id']

        task_builder.add_subtask(
            subtask=tasks.MakeMetaYamlTask(
                package_id,
                source,
                title_page
            )
        )

        task_builder.add_subtask(
            subtask=tasks.GenerateChecksumTask(
                package_id,
                source
            )
        )

    def get_additional_info(
        self,
        user_request_factory: UserRequestFactory,
        options: UserArgs,
        pretask_results: List[speedwagon.tasks.Result[List[str]]]
    ) -> Dict[str, List[str]]:
        """Request title pages information for the packages from the user."""
        if len(pretask_results) != 1:
            return {}

        def process_data(
                data: List[Sequence[DataItem]]
        ) -> TitlePageResults:
            return {
                "title_pages": {
                    typing.cast(str, row[0].value): row[1].value
                    for row in data
                }
            }

        selection_editor = user_request_factory.table_data_editor(
            enter_data=data_gathering_callback,
            process_data=process_data
        )
        selection_editor.title = "Title Page Selection"
        selection_editor.column_names = ["Object", "Title Page", "Location"]
        return selection_editor.get_user_response(options, pretask_results)

    @classmethod
    def generate_report(
        cls,
        results: List[
            speedwagon.tasks.tasks.Result[
                Union[
                    tasks.GenerateChecksumTaskResults,
                    tasks.MakeMetaYamlReport
                ],
            ]
        ],
        user_args: UserArgs  # pylint: disable=unused-argument
    ) -> Optional[str]:
        """Generate a report about prepping work.

        Args:
            results:
            **user_args:

        Returns:
            Returns a string explaining the prepped objects.

        """
        results_sorted = sorted(results, key=lambda x: x.source.__name__)
        _result_grouped = itertools.groupby(results_sorted, lambda x: x.source)
        results_grouped = {k: [i.data for i in v] for k, v in _result_grouped}

        num_checksum_files = len(
            results_grouped[tasks.GenerateChecksumTask]
        )

        num_yaml_files = len(
            results_grouped[tasks.MakeMetaYamlTask]
        )

        objects = {
            result['package_id']
            for result in results_grouped[
                tasks.GenerateChecksumTask
            ]
        }

        for result in results_grouped[tasks.MakeMetaYamlTask]:
            objects.add(result['package_id'])

        objects_prepped_list = "\n  ".join(objects)

        return f"HathiPrep Report:" \
               f"\n" \
               f"\nPrepped the following objects:" \
               f"\n  {objects_prepped_list}" \
               f"\n" \
               f"\nTotal files generated: " \
               f"\n  {num_checksum_files} checksum.md5 files" \
               f"\n  {num_yaml_files} meta.yml files"


class FindHathiPackagesTask(tasks.AbsFindPackageTask):

    def find_packages(self, search_path: str) -> List[str]:
        def find_dirs(item: os.DirEntry[str]) -> bool:

            return bool(item.is_dir())

        directories = []

        for directory in filter(find_dirs, os.scandir(search_path)):
            directories.append(directory.path)
            self.log(f"Located {directory.name}")

        return directories
