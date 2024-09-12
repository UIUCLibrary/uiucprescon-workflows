"""Hathi Prep Workflow."""
from __future__ import annotations

import itertools
import os
from typing import List, Sequence, Dict, Optional, Union, Mapping, TypedDict

import typing

from uiucprescon.packager.packages import collection, HathiJp2, HathiTiff
from uiucprescon.packager.common import Metadata
from uiucprescon.packager import PackageFactory


import speedwagon
import speedwagon.tasks.packaging
import speedwagon.workflow
from speedwagon.frontend.interaction import UserRequestFactory, DataItem
from speedwagon import validators

from speedwagon_uiucprescon import tasks

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
        "title_page": Optional[str],
        "source_path": str
    }
)


TitlePageResults = typing.TypedDict(
    'TitlePageResults',
    {
        'title_pages': Dict[str, Optional[str]]
    }
)


def data_gathering_callback(
    results: Mapping[str, object],  # pylint: disable=unused-argument
    pretask_results: List[speedwagon.tasks.Result[List[collection.Package]]]
) -> List[Sequence[DataItem]]:
    rows: List[Sequence[DataItem]] = []
    values = pretask_results[0]
    for package in values.data:
        title_page = DataItem(
            name="Title Page",
            value=typing.cast(str, package.metadata.get(Metadata.TITLE_PAGE))
        )
        title_page.editable = True
        files = []
        for i in package:
            for instance in i.instantiations.values():
                files += [os.path.basename(f) for f in instance.files]
        files.sort()
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

    def initial_task(
        self,
        task_builder: "speedwagon.tasks.tasks.TaskBuilder",
        user_args: UserArgs
    ) -> None:
        """Look for any packages located in the input argument directory.

        Args:
            task_builder: task builder object provided by speedwagon runtime
            user_args: User selected options

        """
        root = user_args['input']
        task_builder.add_subtask(
            FindHathiPackagesTask(root, user_args['Image File Type'])
        )

    def discover_task_metadata(
        self,
        initial_results: List[  # pylint: disable=unused-argument
            speedwagon.tasks.Result[collection.Package]
        ],
        additional_data: Mapping[str, Mapping[str, str]],
        user_args: UserArgs,  # pylint: disable=unused-argument
    ) -> List[JobArgs]:
        """Get enough information about the packages to create a new job.

        Args:
            initial_results: contains the packages discovered
            additional_data: title pages defined by user
            user_args: User arguments for the job

        Returns:
            Returns a dictionary containing the title page, package id, and
                the source path.

        """
        jobs: List[JobArgs] = []
        packages =\
            typing.cast(Sequence[collection.Package], initial_results[0].data)

        package_title_pages =\
            typing.cast(
                Mapping[str, str],
                additional_data.get('title_pages', {})
            )

        for package in packages:
            package_identifier =\
                typing.cast(str, package.metadata[Metadata.ID])

            job: JobArgs = {
                "package_id": package_identifier,
                "title_page": package_title_pages.get(package_identifier),
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
            task_builder: task builder object
            job_args: job arguments.

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
    ) -> Mapping[str, List[str]]:
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
            results: Results of Checksums and yaml file tasks
            user_args: User arguments

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


class FindHathiPackagesTask(speedwagon.tasks.Subtask[List[typing.Any]]):
    image_types = {
        "TIFF": HathiTiff(),
        "JPEG 2000": HathiJp2()
    }

    def __init__(self, search_path: str, image_type: str) -> None:
        super().__init__()
        self.image_type = image_type
        self.search_path = search_path

    def locate_packages(self) -> Sequence[collection.Package]:
        package_factory = PackageFactory(self.image_types[self.image_type])
        return list(package_factory.locate_packages(self.search_path))

    @staticmethod
    def _package_sortable_key(package: collection.Package) -> str:
        return typing.cast(str, package.metadata[Metadata.ID])

    def work(self) -> bool:
        self.set_results(
            sorted(self.locate_packages(), key=self._package_sortable_key)
        )
        return True
