"""Workflow for verifying checksums."""

from __future__ import annotations
import abc
import collections
import itertools
import os
from typing import (
    DefaultDict, Iterable, Optional, Dict, List, Union, TypedDict,
    TYPE_CHECKING, Mapping
)

import hathi_validate.process

import speedwagon
from speedwagon.job import Workflow
from speedwagon.reports import add_report_borders
from speedwagon import workflow, validators
from speedwagon_uiucprescon import conditions

if TYPE_CHECKING:
    import sys
    if sys.version_info >= (3, 11):
        from typing import Never, Unpack
    else:
        from typing_extensions import Never, Unpack

__all__ = ['ChecksumWorkflow', 'VerifyChecksumBatchSingleWorkflow']


TaskResult = Union[str, bool]


ReadChecksumTaskReport = TypedDict(
    "ReadChecksumTaskReport", {
        "expected_hash": str,
        "filename": str,
        "path": str,
        "source_report": str,
    }
)

ValidateChecksumTaskResult = TypedDict(
    "ValidateChecksumTaskResult", {
        "valid": bool,
        "filename": str,
        "path": str,
        "checksum_report_file": str,
    }
)

ChecksumWorkflowJobArgs = TypedDict("ChecksumWorkflowJobArgs", {
    "Input": str
})


class ChecksumWorkflow(Workflow[ChecksumWorkflowJobArgs]):
    """Checksum validation workflow for Speedwagon."""

    name = "Verify Checksum Batch [Multiple]"
    description = "Verify checksum values in checksum batch file, report " \
                  "errors. Verifies every entry in the checksum.md5 files " \
                  "matches expected hash value for the actual file.  Tool " \
                  "reports discrepancies in console of Speedwagon." \
                  "\n" \
                  "Input is path that contains subdirectory which a text " \
                  "file containing a list of multiple files and their md5 " \
                  "values. The listed files are expected to be siblings to " \
                  "the checksum file."

    TaskArgs = TypedDict(
        "TaskArgs", {
            "expected_hash": str,
            "filename": str,
            "path": str,
            "source_report": str,
        }

    )

    @staticmethod
    def locate_checksum_files(root: str) -> Iterable[str]:
        """Locate any checksum.md5 files located inside a directory.

        Notes:
            This searches a path recursively.
        """
        for search_root, _, files in os.walk(root):
            for file_ in files:
                if file_ != "checksum.md5":
                    continue
                yield os.path.join(search_root, file_)

    def discover_task_metadata(
        self,
        initial_results: List[
            speedwagon.tasks.Result[List[ReadChecksumTaskReport]]
        ],
        additional_data: Mapping[  # pylint: disable=unused-argument
            str,
            None
        ],
        user_args: ChecksumWorkflowJobArgs  # pylint: disable=unused-argument
    ) -> List[TaskArgs]:
        """Read the values inside the checksum report."""
        jobs: List[ChecksumWorkflow.TaskArgs] = []
        for result in initial_results:
            for file_to_check in result.data:
                new_job: ChecksumWorkflow.TaskArgs = {
                    "expected_hash": file_to_check["expected_hash"],
                    "filename": file_to_check["filename"],
                    "path": file_to_check["path"],
                    "source_report": file_to_check["source_report"],
                }
                jobs.append(new_job)
        return jobs

    def job_options(
        self
    ) -> List[workflow.AbsOutputOptionDataType[workflow.UserDataType]]:
        """Request user options.

        User Options include:
            * Input - path directory containing checksum files
        """
        input_folder = \
            speedwagon.workflow.DirectorySelect(
                "Input",
                required=True
            )

        input_folder.add_validation(validators.ExistsOnFileSystem())

        input_folder.add_validation(
            validators.IsDirectory(),
            condition=conditions.candidate_exists
        )

        return [input_folder]

    def initial_task(
        self,
        task_builder: "speedwagon.tasks.TaskBuilder",
        user_args: ChecksumWorkflowJobArgs
    ) -> None:
        """Add a task to read the checksum report files."""
        root = user_args['Input']
        for checksum_report_file in self.locate_checksum_files(root):
            task_builder.add_subtask(
                ReadChecksumReportTask(checksum_file=checksum_report_file))

    def create_new_task(
        self,
        task_builder: "speedwagon.tasks.TaskBuilder",
        job_args: TaskArgs
    ) -> None:
        """Create a checksum validation task."""
        filename = job_args['filename']
        file_path = job_args['path']
        expected_hash = job_args['expected_hash']
        source_report = job_args['source_report']
        task_builder.add_subtask(
            ValidateChecksumTask(file_name=filename,
                                 file_path=file_path,
                                 expected_hash=expected_hash,
                                 source_report=source_report))

    @classmethod
    def generate_report(
        cls,
        results: List[speedwagon.tasks.Result[ValidateChecksumTaskResult]],
        user_args: ChecksumWorkflowJobArgs  # pylint: disable=unused-argument
    ) -> Optional[str]:
        """Generate a report for files failed checksum test."""
        def validation_result_filter(
            task_result: speedwagon.tasks.Result[ValidateChecksumTaskResult]
        ) -> bool:
            if task_result.source != ValidateChecksumTask:
                return False
            return True

        line_sep = "\n" + "-" * 60
        results_with_failures = cls.find_failed(
            cls._sort_results(
                map(lambda x: x.data,
                    filter(validation_result_filter, results))
            )
        )

        if len(results_with_failures) > 0:
            messages = []
            for checksum_file, failed_files in results_with_failures.items():
                status = f"{len(failed_files)} files " \
                         f"failed checksum validation."
                failed_files_bullets = [f"* {failure['filename']}"
                                        for failure in failed_files]
                failure_list = "\n".join(failed_files_bullets)
                single_message = f"{checksum_file}" \
                                 f"\n\n{status}" \
                                 f"\n{failure_list}"
                messages.append(single_message)
            report = f"\n{line_sep}\n".join(messages)

        else:
            stats_message = f"All {len(results)} passed checksum validation."
            failure_list = ""
            report = f"Success" \
                     f"\n{stats_message}" \
                     f"\n{failure_list}"
        return report

    @classmethod
    def find_failed(
        cls,
        new_results: Dict[str, List[ValidateChecksumTaskResult]]
    ) -> dict[str, List[ValidateChecksumTaskResult]]:
        """Locate failed results."""
        failed: DefaultDict[
            str,
            List[ValidateChecksumTaskResult]
        ] = collections.defaultdict(list)

        for checksum_file, results in new_results.items():

            for failed_item in filter(lambda it: not it["valid"],
                                      results):
                failed[checksum_file].append(failed_item)
        return dict(failed)

    @classmethod
    def _sort_results(
            cls,
            results: Iterable[ValidateChecksumTaskResult]
    ) -> Dict[str, List[ValidateChecksumTaskResult]]:
        """Sort the data & put it into a dict with the source for the key.

        Args:
            results:

        Returns: Dictionary of organized data where the source is the key and
                 the value contains all the files updated

        """
        new_results: \
            DefaultDict[str, List[ValidateChecksumTaskResult]] = \
            collections.defaultdict(list)

        sorted_results = sorted(results,
                                key=lambda it:
                                it["checksum_report_file"])
        for key, value in itertools.groupby(
                sorted_results,
                key=lambda it: it["checksum_report_file"]):

            for result_data in value:
                new_results[key].append(result_data)
        return dict(new_results)


class ReadChecksumReportTask(
    speedwagon.tasks.Subtask[List[ReadChecksumTaskReport]]
):

    def __init__(self, checksum_file: str) -> None:
        super().__init__()
        self._checksum_file = checksum_file

    def task_description(self) -> Optional[str]:
        return f"Reading {self._checksum_file}"

    def work(self) -> bool:
        results = []

        checksums = hathi_validate.process.extracts_checksums(
            self._checksum_file)

        for report_md5_hash, filename in checksums:
            new_job_to_do: ReadChecksumTaskReport = {
                "expected_hash": report_md5_hash,
                "filename": filename,
                "path": os.path.dirname(self._checksum_file),
                "source_report": self._checksum_file
            }
            results.append(new_job_to_do)
        self.set_results(results)
        return True


class ValidateChecksumTask(
    speedwagon.tasks.Subtask[ValidateChecksumTaskResult]
):
    name = "Validating File Checksum"

    def __init__(self,
                 file_name: str,
                 file_path: str,
                 expected_hash: str,
                 source_report: str) -> None:
        super().__init__()
        self._file_name = file_name
        self._file_path = file_path
        self._expected_hash = expected_hash
        self._source_report = source_report

    def task_description(self) -> Optional[str]:
        return f"Validating checksum for {self._file_name}"

    def work(self) -> bool:
        self.log(f"Validating {self._file_name}")

        actual_md5 = hathi_validate.process.calculate_md5(
            os.path.join(self._file_path, self._file_name))

        standard_comparison = CaseSensitiveComparison()
        valid_but_warnable_strategy = CaseInsensitiveComparison()

        if standard_comparison.compare(actual_md5, self._expected_hash):
            is_valid = True

        elif valid_but_warnable_strategy.compare(actual_md5,
                                                 self._expected_hash):
            is_valid = True
            self.log(f"Hash for {self._file_name} is valid but is presented"
                     f"in a different format than expected."
                     f"Expected: {self._expected_hash}. Actual: {actual_md5}")
        else:
            self.log(f"Hash mismatch for {self._file_name}. "
                     f"Expected: {self._expected_hash}. Actual: {actual_md5}")
            is_valid = False
        result: ValidateChecksumTaskResult = {
            "filename": self._file_name,
            "path": self._file_path,
            "checksum_report_file": self._source_report,
            "valid": is_valid
        }
        self.set_results(result)

        return True


class AbsComparisonMethod(metaclass=abc.ABCMeta):

    @abc.abstractmethod
    def compare(self, a: str, b: str) -> bool:
        pass


class CaseSensitiveComparison(AbsComparisonMethod):

    def compare(self, a: str, b: str) -> bool:
        return a == b


class CaseInsensitiveComparison(AbsComparisonMethod):

    def compare(self, a: str, b: str) -> bool:
        return a.lower() == b.lower()


VerifyChecksumBatchSingleJobArgs = TypedDict(
    "VerifyChecksumBatchSingleJobArgs",
    {
        "Input": str
    }
)


class VerifyChecksumBatchSingleWorkflow(
    Workflow[VerifyChecksumBatchSingleJobArgs]
):
    """Verify Checksum Batch."""

    name = "Verify Checksum Batch [Single]"
    description = "Verify checksum values in checksum batch file, report " \
                  "errors. Verifies every entry in the checksum.md5 files " \
                  "matches expected hash value for the actual file.  Tool " \
                  "reports discrepancies in console of Speedwagon." \
                  "\n" \
                  "Input is a text file containing a list of multiple files " \
                  "and their md5 values. The listed files are expected to " \
                  "be siblings to the checksum file."
    TaskArgs = TypedDict(
        "TaskArgs",
        {
            "source_report": str,
            "expected_hash": str,
            "filename": str,
            "path": str,
        }
    )

    def discover_task_metadata(
        self,
        initial_results: List[  # pylint: disable=unused-argument
            speedwagon.tasks.Result[Never]
        ],
        additional_data: Mapping[  # pylint: disable=unused-argument
            str,
            None
        ],
        user_args: VerifyChecksumBatchSingleJobArgs,
    ) -> List[TaskArgs]:
        """Discover metadata needed for generating a task."""
        jobs: List[VerifyChecksumBatchSingleWorkflow.TaskArgs] = []
        relative_path = os.path.dirname(user_args["Input"])
        checksum_report_file = os.path.abspath(user_args["Input"])

        for report_md5_hash, filename in \
                sorted(hathi_validate.process.extracts_checksums(
                    checksum_report_file),
                    key=lambda x: x[1]
                ):

            new_job: VerifyChecksumBatchSingleWorkflow.TaskArgs = {
                "expected_hash": report_md5_hash,
                "filename": filename,
                "path": relative_path,
                "source_report": checksum_report_file
            }
            jobs.append(new_job)
        return jobs

    def job_options(
        self
    ) -> List[workflow.AbsOutputOptionDataType[workflow.UserDataType]]:
        """Request user options.

        User Options include:
            * Input - path checksum file
        """
        input_file =\
            workflow.FileSelectData("Input", required=True)

        input_file.filter = "Checksum files (*.md5)"
        input_file.add_validation(validators.ExistsOnFileSystem())
        input_file.add_validation(
            validators.IsFile(),
            condition=lambda candidate, _: os.path.exists(candidate)
        )
        return [input_file]

    def create_new_task(
        self,
        task_builder: "speedwagon.tasks.TaskBuilder",
        job_args: TaskArgs
    ) -> None:
        """Generate a new checksum task."""
        new_task = ChecksumTask(**job_args)
        task_builder.add_subtask(new_task)

    @classmethod
    @add_report_borders
    def generate_report(
        cls,
        results: List[speedwagon.tasks.Result[ValidateChecksumTaskResult]],
        user_args: VerifyChecksumBatchSingleJobArgs  # pylint: disable=W0613
    ) -> Optional[str]:
        """Generate a report for files failed checksum test."""
        results_data: List[ValidateChecksumTaskResult] = [
            res.data for res in results
        ]

        line_sep = "\n" + "-" * 60
        sorted_results = cls.sort_results(results_data)
        results_with_failures = cls.find_failed(sorted_results)

        if len(results_with_failures) > 0:
            messages = []
            for checksum_file, failed_files in results_with_failures.items():
                status = \
                    f"{len(failed_files)} files failed checksum validation."

                failed_files_bullets = [
                    f"* {failure['filename']}"
                    for failure in failed_files
                ]

                failure_list = "\n".join(failed_files_bullets)
                single_message = f"{checksum_file}" \
                                 f"\n\n{status}" \
                                 f"\n{failure_list}"
                messages.append(single_message)

            report = f"\n{line_sep}\n".join(messages)

        else:
            stats_message =\
                f"All {len(results_data)} passed checksum validation."

            failure_list = ""
            report = f"Success" \
                     f"\n{stats_message}" \
                     f"\n{failure_list}"
        return report

    @classmethod
    def sort_results(
        cls,
        results: List[ValidateChecksumTaskResult]
    ) -> Dict[str, List[ValidateChecksumTaskResult]]:
        """Sort the data and put it into a dictionary using source as the key.

        Args:
            results:

        Returns: Dictionary of organized data where the source is the key and
                 the value contains all the files updated

        """
        new_results: DefaultDict[str, List[ValidateChecksumTaskResult]] = \
            collections.defaultdict(list)

        sorted_results = sorted(
            results, key=lambda it: it["checksum_report_file"]
        )

        for key, value in itertools.groupby(
                sorted_results,
                key=lambda it: it["checksum_report_file"]
        ):
            for result_data in value:
                new_results[key].append(result_data)
        return dict(new_results)

    @classmethod
    def find_failed(
        cls,
        new_results: Dict[str, List[ValidateChecksumTaskResult]]
    ) -> Dict[str, List[ValidateChecksumTaskResult]]:
        """Locate failed results."""
        failed: DefaultDict[str, List[ValidateChecksumTaskResult]] = \
            collections.defaultdict(list)

        for checksum_file, results in new_results.items():

            for failed_item in \
                    filter(lambda it: not it["valid"], results):

                failed[checksum_file].append(failed_item)
        return dict(failed)


class ChecksumTask(speedwagon.tasks.Subtask[ValidateChecksumTaskResult]):
    name = "Verifying file checksum"

    def __init__(
        self,
        *_: None,
        **kwargs: Unpack[VerifyChecksumBatchSingleWorkflow.TaskArgs]
    ) -> None:
        super().__init__()
        self._kwarg: ChecksumWorkflow.TaskArgs = kwargs

    def task_description(self) -> Optional[str]:
        return f"Calculating file checksum for {self._kwarg['filename']}"

    def work(self) -> bool:
        filename = self._kwarg["filename"]

        source_report = self._kwarg["source_report"]

        expected = self._kwarg["expected_hash"]

        checksum_path = self._kwarg["path"]

        full_path = os.path.join(checksum_path, filename)
        actual_md5: str = hathi_validate.process.calculate_md5(full_path)

        standard_comparison = CaseSensitiveComparison()

        valid_but_warnable_strategy = CaseInsensitiveComparison()

        if standard_comparison.compare(actual_md5, expected):
            is_valid = True
        elif valid_but_warnable_strategy.compare(actual_md5, expected):
            is_valid = True
            self.log(f"Hash for {filename} is valid but is presented"
                     f"in a different format than expected."
                     f"Expected: {expected}. Actual: {actual_md5}")
        else:
            self.log(f"Hash mismatch for {filename}. "
                     f"Expected: {expected}. Actual: {actual_md5}")
            is_valid = False
        result: ValidateChecksumTaskResult = {
            "filename": filename,
            "path": checksum_path,
            "checksum_report_file": source_report,
            "valid": is_valid
        }

        self.set_results(result)
        return True
