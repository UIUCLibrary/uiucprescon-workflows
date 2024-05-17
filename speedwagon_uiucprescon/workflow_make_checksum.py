"""Workflows for generating checksums."""
from __future__ import annotations
import collections
import typing

import os

import itertools
import warnings
from abc import ABC
from typing import (
    List, DefaultDict, Optional, TypedDict, Iterable, Any, Mapping, TypeVar,
    Generic, TYPE_CHECKING
)

import speedwagon
from speedwagon.job import Workflow
import speedwagon.workflow
from speedwagon.reports import add_report_borders
from speedwagon import validators

from speedwagon_uiucprescon import tasks

if TYPE_CHECKING:
    import sys
    if sys.version_info >= (3, 11):
        from typing import Never
    else:
        from typing_extensions import Never

__all__ = [
    'MakeChecksumBatchSingleWorkflow',
    'MakeChecksumBatchMultipleWorkflow',
    'RegenerateChecksumBatchSingleWorkflow',
    'RegenerateChecksumBatchMultipleWorkflow'
]

DEFAULT_CHECKSUM_FILE_NAME = "checksum.md5"

UserArgs = TypedDict("UserArgs", {
    "Input": str
})

_T = TypeVar("_T", bound=Mapping[str, object])
_RT = TypeVar("_RT", bound=Mapping[str, object])


class CreateChecksumWorkflow(Generic[_T, _RT], Workflow[_T], ABC):
    @staticmethod
    def locate_files(package_root: str) -> Iterable[str]:
        for root, _, files in os.walk(package_root):
            for file_ in files:
                yield os.path.join(root, file_)

    @classmethod
    def sort_results(
        cls,
        results: typing.List[tasks.MakeChecksumResult]
    ) -> typing.Dict[str, typing.List[tasks.MakeChecksumResult]]:
        new_results: DefaultDict[
            str,
            List[tasks.MakeChecksumResult]
        ] = collections.defaultdict(list)

        def sort_func(value: tasks.MakeChecksumResult) -> str:
            return value['checksum_file']

        sorted_results = sorted(results, key=sort_func)

        for key, value in itertools.groupby(sorted_results, key=sort_func):

            for result_data in value:
                new_results[key].append(result_data)
        return dict(new_results)

    def completion_task(
        self,
        task_builder: "speedwagon.tasks.TaskBuilder",
        results: List[
            speedwagon.tasks.Result[
                tasks.MakeChecksumResult
            ]
        ],
        user_args: _T  # pylint: disable=unused-argument
    ) -> None:
        """Create checksum report at very end."""
        sorted_results = self.sort_results([i.data for i in results])

        for checksum_report, checksums in sorted_results.items():

            process = tasks.MakeCheckSumReportTask(
                checksum_report, checksums)

            task_builder.add_subtask(process)

    def create_new_task(
        self,
        task_builder: speedwagon.tasks.TaskBuilder,
        job_args: MakeChecksumBatchMultipleTaskArgs
    ) -> None:

        filename = job_args['filename']
        source_path = job_args['source_path']
        report_name = job_args['save_to_filename']

        new_task = \
            tasks.MakeChecksumTask(source_path, filename, report_name)

        task_builder.add_subtask(new_task)


MakeChecksumTaskArgs = TypedDict("MakeChecksumTaskArgs", {
    "source_path": str,
    "filename": str,
    "save_to_filename": str
})


class MakeChecksumBatchSingleWorkflow(
    CreateChecksumWorkflow[UserArgs, MakeChecksumTaskArgs]
):
    """Workflow for generating a checksum report for single batch of files."""

    name = "Make Checksum Batch [Single]"
    description = "The checksum is a signature of a file.  If any data is " \
                  "changed, the checksum will provide a different " \
                  f"signature.  The {DEFAULT_CHECKSUM_FILE_NAME} contains a " \
                  f"record of each file in a single item along with " \
                  f"respective checksum values " \
                  "\n" \
                  f"Creates a single {DEFAULT_CHECKSUM_FILE_NAME} for every " \
                  f"file inside a given folder" \
                  "\n" \
                  "Input: Path to a root folder"

    def discover_task_metadata(
        self,
        initial_results: List[  # pylint: disable=unused-argument
            speedwagon.tasks.Result[Never]
        ],
        additional_data: Mapping[str, Never],  # pylint: disable=W0613
        user_args: UserArgs,
    ) -> List[MakeChecksumTaskArgs]:
        """Generate metadata for task."""
        jobs = []
        package_root = user_args["Input"]
        report_to_save_to = os.path.normpath(
            os.path.join(package_root, DEFAULT_CHECKSUM_FILE_NAME)
        )
        for file_path in self.locate_files(package_root):
            relpath = os.path.relpath(file_path, package_root)
            job: MakeChecksumTaskArgs = {
                "source_path": package_root,
                "filename": relpath,
                "save_to_filename": report_to_save_to
            }
            jobs.append(job)
        return jobs

    @classmethod
    @add_report_borders
    def generate_report(
        cls,
        results: List[
            speedwagon.tasks.Result[tasks.MakeChecksumResult]
        ],
        user_args: UserArgs  # pylint: disable=unused-argument
    ) -> Optional[str]:
        """Generate report based on number of files hash calculated in file."""
        report_lines = [
            f"Checksum values for {len(items_written)} "
            f"files written to {checksum_report}"
            for checksum_report, items_written in cls.sort_results(
                [i.data for i in results]
            ).items()
        ]

        return "\n".join(report_lines)

    def job_options(
        self
    ) -> List[
            speedwagon.workflow.AbsOutputOptionDataType[
                speedwagon.workflow.UserDataType
            ]
    ]:
        """Request directory input setting from user."""
        input_path = speedwagon.workflow.DirectorySelect("Input")
        input_path.add_validation(validators.ExistsOnFileSystem())

        return [
            input_path
        ]


MakeChecksumBatchMultipleTaskArgs = TypedDict(
    "MakeChecksumBatchMultipleTaskArgs",
    {
        "source_path": str,
        "filename": str,
        "save_to_filename": str
    }
)


class MakeChecksumBatchMultipleWorkflow(
    CreateChecksumWorkflow[
        UserArgs,
        MakeChecksumBatchMultipleTaskArgs
    ]
):
    """Make checksum batch workflow for Speedwagon."""

    name = "Make Checksum Batch [Multiple]"
    description = "The checksum is a signature of a file.  If any data " \
                  "is changed, the checksum will provide a different " \
                  f"signature.  The {DEFAULT_CHECKSUM_FILE_NAME} contains a " \
                  f"record of the files for a given package." \
                  "\n" \
                  f"The tool creates a {DEFAULT_CHECKSUM_FILE_NAME} for " \
                  f"every subdirectory found inside a given path." \
                  "\n" \
                  "Input: Path to a root directory that contains " \
                  f"subdirectories to generate {DEFAULT_CHECKSUM_FILE_NAME} " \
                  f"files"

    def discover_task_metadata(
        self,
        initial_results: List[  # pylint: disable=unused-argument
            speedwagon.tasks.Result[Never]
        ],
        additional_data: Mapping[str, Never],  # pylint: disable=W0613
        user_args: UserArgs,
    ) -> List[MakeChecksumBatchMultipleTaskArgs]:
        """Generate metadata for task."""
        jobs = []

        for sub_dir in filter(lambda it: it.is_dir(),
                              os.scandir(user_args["Input"])):

            package_root = sub_dir.path
            report_to_save_to = os.path.normpath(
                os.path.join(package_root, DEFAULT_CHECKSUM_FILE_NAME)
            )

            for root, _, files in os.walk(package_root):
                for file_ in files:
                    full_path = os.path.join(root, file_)
                    relpath = os.path.relpath(full_path, package_root)
                    job: MakeChecksumBatchMultipleTaskArgs = {
                        "source_path": package_root,
                        "filename": relpath,
                        "save_to_filename": report_to_save_to
                    }
                    jobs.append(job)
        return jobs

    def job_options(
            self
    ) -> List[
        speedwagon.workflow.AbsOutputOptionDataType[
            speedwagon.workflow.UserDataType
        ]
    ]:
        """Request input directory value from the user."""
        input_path = speedwagon.workflow.DirectorySelect("Input")
        input_path.add_validation(validators.ExistsOnFileSystem())
        return [input_path]

    def create_new_task(
        self,
        task_builder: "speedwagon.tasks.TaskBuilder",
        job_args: MakeChecksumBatchMultipleTaskArgs
    ) -> None:
        """Create a checksum generation task."""
        filename = job_args['filename']
        report_name = job_args['save_to_filename']
        source_path = job_args['source_path']

        task_builder.add_subtask(
            tasks.MakeChecksumTask(
                source_path,
                filename,
                report_name
            )
        )

    @classmethod
    @add_report_borders
    def generate_report(
        cls,
        results: List[
            speedwagon.tasks.Result[tasks.validation.MakeChecksumResult]
        ],
        user_args: UserArgs  # pylint: disable=unused-argument
    ) -> Optional[str]:
        """Generate report based on number of files hash calculated in file."""
        report_lines = [
            f"Checksum values for {len(items_written)} "
            f"files written to {checksum_report}"
            for checksum_report, items_written in cls.sort_results(
                [i.data for i in results]
            ).items()
        ]

        return "\n".join(report_lines)


class RegenerateChecksumBatchSingleWorkflow(CreateChecksumWorkflow):
    name = "Regenerate Checksum Batch [Single]"
    description = "Regenerates hash values for every file inside for a " \
                  f"given {DEFAULT_CHECKSUM_FILE_NAME} file" \
                  "\n" \
                  "Input: Path to a root folder"
    active = False

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

        warnings.warn(
            "Pending removal of Regenerate Checksum Batch [Single]",
            DeprecationWarning,
            stacklevel=2
        )

    def discover_task_metadata(
        self,
        initial_results: List[  # pylint: disable=unused-argument
            speedwagon.tasks.Result[Never]
        ],
        additional_data,  # pylint: disable=unused-argument
        user_args: UserArgs
    ) -> List[MakeChecksumTaskArgs]:
        jobs: List[MakeChecksumTaskArgs] = []

        report_to_save_to = user_args["Input"]
        package_root = os.path.dirname(report_to_save_to)

        for file_path in self.locate_files(package_root):
            relpath = os.path.relpath(file_path, package_root)
            jobs.append(
                {
                    "source_path": package_root,
                    "filename": relpath,
                    "save_to_filename": report_to_save_to
                }
            )
        return jobs

    def create_new_task(
        self,
        task_builder: "speedwagon.tasks.TaskBuilder",
        job_args: MakeChecksumTaskArgs
    ) -> None:

        source_path = job_args['source_path']
        filename = job_args['filename']
        report_name = job_args['save_to_filename']

        new_task = tasks.MakeChecksumTask(
            source_path, filename, report_name)

        task_builder.add_subtask(new_task)

    def completion_task(
        self,
        task_builder: "speedwagon.tasks.TaskBuilder",
        results: List[speedwagon.tasks.Result],
        user_args: UserArgs
    ) -> None:

        sorted_results = self.sort_results([i.data for i in results])

        for checksum_report, checksums in sorted_results.items():

            process = tasks.MakeCheckSumReportTask(
                checksum_report, checksums)

            task_builder.add_subtask(process)

    @classmethod
    @add_report_borders
    def generate_report(
        cls,
        results: List[
            speedwagon.tasks.Result[tasks.validation.MakeChecksumResult]
        ],

        user_args: UserArgs  # pylint: disable=unused-argument
    ) -> Optional[str]:

        report_lines = [
            f"Checksum values for {len(items_written)} "
            f"files written to {checksum_report}"
            for checksum_report, items_written in cls.sort_results(
                [i.data for i in results]
            ).items()
        ]

        return "\n".join(report_lines)


class RegenerateChecksumBatchMultipleWorkflow(CreateChecksumWorkflow):
    name = "Regenerate Checksum Batch [Multiple]"
    description = f"Regenerates the hash values for every " \
                  f"{DEFAULT_CHECKSUM_FILE_NAME} located inside a " \
                  f"given path\n" \
                  "\n" \
                  "Input: Path to a root directory that contains " \
                  f"subdirectories to generate {DEFAULT_CHECKSUM_FILE_NAME} " \
                  f"files"
    active = False

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

        warnings.warn(
            "Pending removal of Regenerate Checksum Batch [Multiple]",
            DeprecationWarning,
            stacklevel=2
        )

    def discover_task_metadata(
        self,
        initial_results: List[  # pylint: disable=unused-argument
            speedwagon.tasks.Result[Never]
        ],
        additional_data,  # pylint: disable=unused-argument
        user_args: Mapping[str, Any],
    ) -> List[MakeChecksumTaskArgs]:

        jobs: List[MakeChecksumTaskArgs] = []

        for sub_dir in filter(lambda it: it.is_dir(),
                              os.scandir(user_args["Input"])):

            package_root = sub_dir.path

            report_to_save_to = os.path.normpath(
                os.path.join(package_root, DEFAULT_CHECKSUM_FILE_NAME)
            )

            for root, _, files in os.walk(package_root):
                for file_ in files:
                    full_path = os.path.join(root, file_)
                    if os.path.samefile(report_to_save_to, full_path):
                        continue
                    relpath = os.path.relpath(full_path, package_root)
                    job: MakeChecksumTaskArgs = {
                        "source_path": package_root,
                        "filename": relpath,
                        "save_to_filename": report_to_save_to
                    }
                    jobs.append(job)
        return jobs

    def completion_task(
        self,
        task_builder: "speedwagon.tasks.TaskBuilder",
        results: List[
            speedwagon.tasks.Result[tasks.validation.MakeChecksumResult]
        ],
        user_args: UserArgs
    ) -> None:

        sorted_results = self.sort_results([i.data for i in results])

        for checksum_report, checksums in sorted_results.items():
            task_builder.add_subtask(
                tasks.MakeCheckSumReportTask(
                    checksum_report,
                    checksums
                )
            )

    @classmethod
    @add_report_borders
    def generate_report(
        cls,
        results: List[speedwagon.tasks.Result[tasks.MakeChecksumResult]],
        user_args: UserArgs  # pylint: disable=unused-argument
    ) -> Optional[str]:
        report_lines = [
            f"Checksum values for {len(items_written)} "
            f"files written to {checksum_report}"
            for checksum_report, items_written in cls.sort_results(
                [i.data for i in results]
            ).items()
        ]

        return "\n".join(report_lines)
