"""Workflow for Medusa Preingest.

Added on 3/30/2022

.. versionadded:: 0.3.0 added option for removing Thumbs.db files.
"""
from __future__ import annotations
import abc
import os
import pathlib
import typing
from typing import List, Dict, Optional, Iterator, Union, TypedDict, Mapping
from pathlib import Path

import speedwagon
from speedwagon import workflow, tasks, validators
from speedwagon.frontend import interaction
from speedwagon.tasks import filesystem as filesystem_tasks
from speedwagon_uiucprescon import conditions

if typing.TYPE_CHECKING:
    import sys
    if sys.version_info >= (3, 11):
        from typing import Unpack, Never
    else:
        from typing_extensions import Unpack, Never

__all__ = ['MedusaPreingestCuration']


UserArgs = TypedDict(
    "UserArgs", {
        "Path": str,
        "Include Subdirectories": bool,
        "Locate and delete Capture One files": bool,
        "Locate and delete dot underscore files": bool,
        "Locate and delete .DS_Store files": bool,
        "Locate and delete Thumbs.db files": bool,
    }
)

TaskArgs = TypedDict(
    "TaskArgs", {
        "type": str,
        "path": str
    }
)


class MedusaPreingestCuration(speedwagon.Workflow[UserArgs]):
    """Medusa Preingest curation Workflow."""

    name = "Medusa Preingest Curation"
    description = \
        """
-  Locates and deletes file that start with ._ (dot underscore)
-  Locates and deletes .DS_Store files
-  Locates and deletes Thumbs.db files
-  Locates and deletes Capture One files
    """.strip()

    def initial_task(self, task_builder: tasks.TaskBuilder,
                     user_args: UserArgs) -> None:
        """Add task to search for files to be removed."""
        task_builder.add_subtask(FindOffendingFiles(**user_args))
        super().initial_task(task_builder, user_args)

    @staticmethod
    def _build_task(item: pathlib.Path) -> TaskArgs:
        if item.is_dir():
            return {
                "type": "directory",
                "path": str(item)
            }
        if item.is_file():
            return {
                "type": "file",
                "path": str(item),
            }
        raise RuntimeError(
            f'not sure what to do. "{item}" is not '
            f'considered a file or a directory.'
        )

    def discover_task_metadata(
        self,
        initial_results: List[  # pylint: disable=unused-argument
            speedwagon.tasks.Result[Never]
        ],
        additional_data: Mapping[str, List[str]],
        user_args: UserArgs,  # pylint: disable=unused-argument
    ) -> List[TaskArgs]:
        """Organize the order the files & directories should be removed."""
        new_tasks: List[TaskArgs] = []
        to_remove: typing.Set[str] = set()

        for item in additional_data.get('to remove', []):
            if str(item) in to_remove:
                continue
            if os.path.isdir(item):
                for child_item in get_contents_of_folder_for_removal(item):
                    if str(child_item) in to_remove:
                        continue
                    new_tasks.append(self._build_task(child_item))
                    to_remove.add(str(child_item))
            elif os.path.isfile(item):
                new_tasks.append({
                    "type": "file",
                    "path": item,
                })
            to_remove.add(item)
        return new_tasks

    AdditionalInfo = TypedDict("AdditionalInfo", {"to remove": List[str]})

    def get_additional_info(
        self,
        user_request_factory: interaction.UserRequestFactory,
        options: UserArgs,
        pretask_results: List[speedwagon.tasks.Result[List[str]]]
    ) -> AdditionalInfo:
        """Confirm which files should be deleted or removed."""
        confirm = \
            user_request_factory.confirm_removal()

        return {
            "to remove": [
                os.path.join(str(options['Path']), item)
                for item in
                confirm.get_user_response(options, pretask_results)['items']
            ]
        }

    @staticmethod
    def sort_item_data(data: List[str]) -> Dict[str, List[str]]:
        """Sort list of file contents into a dictionary based on type."""
        dirs: List[str] = []
        files: List[str] = []

        for item in data:
            if os.path.isdir(item):
                dirs.append(item)
            elif os.path.isfile(item):
                files.append(item)
            else:
                raise ValueError(
                    f"Unable to determine if file or directory: {item}."
                )
        return {
            "files": files,
            "directories": dirs,
        }

    def job_options(self) -> List[
        workflow.AbsOutputOptionDataType[workflow.UserDataType]
    ]:
        """Get which types of files to search for."""
        root_directory = speedwagon.workflow.DirectorySelect("Path", True)
        root_directory.add_validation(validators.ExistsOnFileSystem())
        root_directory.add_validation(
            validators.IsDirectory(),
            condition=conditions.candidate_exists
        )

        include_subdirectories = \
            speedwagon.workflow.BooleanSelect("Include Subdirectories")
        include_subdirectories.value = True

        delete_dot_underscore = \
            speedwagon.workflow.BooleanSelect(
                "Locate and delete dot underscore files"
            )
        delete_dot_underscore.value = True

        delete_ds_store = \
            speedwagon.workflow.BooleanSelect(
                "Locate and delete .DS_Store files"
            )
        delete_ds_store.value = True

        delete_thumbs_db = \
            speedwagon.workflow.BooleanSelect(
                "Locate and delete Thumbs.db files"
            )
        delete_thumbs_db.value = True

        delete_capture_one = \
            speedwagon.workflow.BooleanSelect(
                "Locate and delete Capture One files"
            )
        delete_capture_one.value = True

        return [
            root_directory,
            include_subdirectories,
            delete_dot_underscore,
            delete_ds_store,
            delete_thumbs_db,
            delete_capture_one
        ]

    @classmethod
    def generate_report(
        cls,
        results: List[tasks.Result[List[str]]],  # pylint: disable=W0613
        user_args: UserArgs  # pylint: disable=unused-argument
    ) -> Optional[str]:
        """Generate a report about what files and directories were removed.

        Args:
            results:
            **user_args:
        """
        items_deleted = [
            result.data for result in results if result.source in [
                filesystem_tasks.delete_file,
                filesystem_tasks.delete_directory
            ]
        ]

        report_lines = [
            "*" * 80,
            "Deleted the following files and/or folders",
            "------------------------------------------",
            "\n",
            "\n".join([f"* {item}" for item in items_deleted]),
            "*" * 80,
        ]
        return "\n".join(report_lines)

    def create_new_task(
        self,
        task_builder: tasks.TaskBuilder,
        job_args: TaskArgs
    ) -> None:
        """Add a delete file or delete directory task to the task list.

        Args:
            task_builder:
            **job_args:
        """
        if job_args['type'] == "file":
            task_builder.add_subtask(
                filesystem_tasks.delete_file(job_args["path"])
            )
        elif job_args['type'] == "directory":
            task_builder.add_subtask(
                filesystem_tasks.delete_directory(job_args["path"])
            )


class AbsChecker(abc.ABC):  # pylint: disable=R0903

    @abc.abstractmethod
    def is_valid(self, path: Path) -> bool:
        """Is path valid."""


class AbsPathItemDecision(abc.ABC):  # pylint: disable=R0903
    @abc.abstractmethod
    def is_offending(self, path: Path) -> bool:
        """Get if file is offending or not."""


class DsStoreChecker(AbsChecker):  # pylint: disable=R0903
    def is_valid(self, path: Path) -> bool:
        return path.name != ".DS_Store"


class ThumbsDbChecker(AbsChecker):  # pylint: disable=R0903
    def is_valid(self, path: Path) -> bool:
        return path.name != "Thumbs.db"


class DotUnderScoreChecker(AbsChecker):  # pylint: disable=R0903
    def is_valid(self, path: Path) -> bool:
        return not path.name.startswith("._")


class CaptureOneChecker(AbsChecker):

    def is_valid(self, path: Path) -> bool:
        if not path.is_dir():
            return True
        return path.name != "CaptureOne"


class OffendingPathDecider(AbsPathItemDecision):

    def __init__(self) -> None:
        self._checkers: List[AbsChecker] = []

    def add_checker(self, value: AbsChecker) -> None:
        self._checkers.append(value)

    def is_offending(self, path: Path) -> bool:
        return any(not checker.is_valid(path) for checker in self._checkers)


class FindOffendingFiles(tasks.Subtask[List[str]]):

    def __init__(self, **user_args: Unpack[UserArgs]) -> None:
        super().__init__()
        self.filesystem_locator_strategy = FilesystemItemLocator()

        self.root: str = user_args['Path']
        self._include_subdirectory = user_args['Include Subdirectories']

        self.file_deciding_strategy = OffendingPathDecider()

        if user_args['Locate and delete Capture One files']:
            self.file_deciding_strategy.add_checker(CaptureOneChecker())

        if user_args['Locate and delete dot underscore files']:
            self.file_deciding_strategy.add_checker(DotUnderScoreChecker())

        if user_args['Locate and delete .DS_Store files']:
            self.file_deciding_strategy.add_checker(DsStoreChecker())

        if user_args['Locate and delete Thumbs.db files']:
            self.file_deciding_strategy.add_checker(ThumbsDbChecker())

    def task_description(self) -> Optional[str]:
        return f"Searching {self.root}"

    def work(self) -> bool:
        self.set_results(self.locate_results())
        return True

    def locate_results(self) -> List[str]:
        return [
            item
            for item in self.filesystem_locator_strategy.locate(self.root)
            if self.file_deciding_strategy.is_offending(
                Path(self.root) / Path(item)
            )
        ]


class FilesystemItemLocator:

    def locate(self, path: str) -> Iterator[str]:
        if not os.path.exists(path):
            raise FileNotFoundError(f"Could not find {path}")
        for item in get_contents_of_folder_for_removal(path):
            yield os.path.relpath(item, start=path)


def find_capture_one_data(directory: str) -> Iterator[str]:
    potential_capture_one_dir_name = \
        os.path.join(directory, "CaptureOne")

    if os.path.exists(potential_capture_one_dir_name):
        for root, dirs, files in os.walk(potential_capture_one_dir_name):
            for file_name in files:
                yield os.path.join(root, file_name)
            for dir_name in dirs:
                yield os.path.join(root, dir_name)
        yield potential_capture_one_dir_name


def get_contents_of_folder_for_removal(
    root: Union[Path, str]
) -> Iterator[Path]:
    """Locate files and folders in the path.

    This function guarantees that the content of a folder is listed before
    the folder itself. This is to help delete items in the right order.
    """
    root = Path(root)
    files = []

    for item in root.iterdir():
        if item.is_dir():
            yield from get_contents_of_folder_for_removal(item)
        else:
            files.append(item)
    yield from files
    yield root
