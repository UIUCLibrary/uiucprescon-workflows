"""Workflow for converting CaptureOne images to Digital Library format."""
from __future__ import annotations

import abc
import itertools
import os
import sys
import typing
from typing import List, Optional, Tuple, Mapping

import pykdu_compress

import speedwagon
import speedwagon.workflow
from speedwagon.workflow import AbsOutputOptionDataType, UserDataType
from speedwagon import reports
from speedwagon.job import Workflow
from speedwagon import validators

if typing.TYPE_CHECKING:
    if sys.version_info >= (3, 11):
        from typing import Never
    else:
        from typing_extensions import Never

__all__ = ['ConvertTiffPreservationToDLJp2Workflow']


PackageImageConverterTaskReport = typing.TypedDict(
    "PackageImageConverterTaskReport",
    {
        "output_filename": Optional[str],
        "source_filename": str,
        "success": bool,
    }

)


class AbsProcessStrategy(metaclass=abc.ABCMeta):

    def __init__(self) -> None:
        self.output: Optional[str] = None
        self.status: Optional[str] = None

    @abc.abstractmethod
    def process(self, source_file: str, destination_path: str) -> None:
        """Process."""


class ProcessFile:
    def __init__(self, process_strategy: AbsProcessStrategy) -> None:
        self._strategy = process_strategy

    def process(self, source_file: str, destination_path: str) -> None:
        self._strategy.process(source_file, destination_path)

    def status_message(self) -> typing.Optional[str]:
        return self._strategy.status

    @property
    def output(self) -> typing.Optional[str]:
        return self._strategy.output


class ProcessingException(Exception):
    """Processing Exception."""


class ConvertFile(AbsProcessStrategy):

    def process(self, source_file: str, destination_path: str) -> None:
        basename, _ = os.path.splitext(os.path.basename(source_file))

        output_file_path = os.path.join(destination_path,
                                        basename + ".jp2"
                                        )

        return_core = pykdu_compress.kdu_compress_cli2(
            infile=source_file, outfile=output_file_path)

        if return_core != 0:
            raise ProcessingException(
                "kdu_compress_cli returned nonzero value: {return_core}."
            )

        self.output = output_file_path
        self.status = f"Generated {output_file_path}"


UserOptions = typing.TypedDict("UserOptions", {"Input": str})
JobArgs = typing.TypedDict(
    "JobArgs",
    {
        "source_file": str,
        "output_path": str,
    }
)


class ConvertTiffPreservationToDLJp2Workflow(Workflow[UserOptions]):
    """Package conversion workflow for Speedwagon."""

    name = "Convert CaptureOne Preservation TIFF to Digital Library Access JP2"
    description = 'This tool takes as its input a "preservation" folder of ' \
                  'TIFF files and as its output creates a sibling folder ' \
                  'called "access" containing digital-library compliant JP2 ' \
                  'files named the same as the TIFFs.'
    active = True

    def discover_task_metadata(
        self,
        initial_results: List[  # pylint: disable=unused-argument
            speedwagon.tasks.Result[Never]
        ],
        additional_data: Mapping[str, str],  # pylint: disable=unused-argument
        user_args: UserOptions
    ) -> List[JobArgs]:
        """Generate task metadata for converting file packages."""
        jobs: List[JobArgs] = []
        source_input = user_args["Input"]

        dest = os.path.abspath(
            os.path.join(source_input,
                         "..",
                         "access")
        )

        def filter_only_tif_files(item: os.DirEntry[str]) -> bool:
            if not item.is_file():
                return False

            _, ext = os.path.splitext(item.name)
            if ext.lower() != ".tif":
                return False

            return True

        for tiff_file in \
                filter(filter_only_tif_files, os.scandir(source_input)):

            jobs.append({
                "source_file": tiff_file.path,
                "output_path": dest,
            })

        return jobs

    def job_options(self) -> List[AbsOutputOptionDataType[UserDataType]]:
        """Request use settings for source path."""
        input_directory = speedwagon.workflow.DirectorySelect("Input")
        input_directory.add_validation(validators.ExistsOnFileSystem())

        input_directory.add_validation(validators.IsDirectory())

        input_directory.add_validation(
            validators.CustomValidation[str](
                query=lambda candidate, job_args: (
                    typing.cast(str, candidate).endswith("preservation")
                ),
                failure_message_function=(
                    lambda _: "Invalid value in input: Not a preservation "
                              "directory"
                )
            ),
            condition=lambda candidate, _: all(
                [
                    os.path.exists(candidate),
                    os.path.isdir(candidate)
                ]
            )
        )

        return [input_directory]

    def create_new_task(
        self,
        task_builder: speedwagon.tasks.TaskBuilder,
        job_args: JobArgs
    ) -> None:
        """Create task to convert file package."""
        source_file = job_args['source_file']
        dest_path = job_args['output_path']
        new_task = PackageImageConverterTask(
            source_file_path=source_file,
            dest_path=dest_path
        )
        task_builder.add_subtask(new_task)

    @classmethod
    @reports.add_report_borders
    def generate_report(
        cls,
        results: List[
            speedwagon.tasks.Result[PackageImageConverterTaskReport]
        ],
        user_args: UserOptions  # pylint: disable=unused-argument
    ) -> str:
        """Generate a report for number of successful files created."""
        failure = False
        dest = None

        failed_results, successful_results = cls._partition_results(results)

        dest_paths = set()
        for result in successful_results:
            new_file = result.data["output_filename"]
            if new_file is None:
                raise KeyError("missing output_filename from results")
            dest_paths.add(os.path.dirname(new_file))

        if len(dest_paths) == 1:
            dest = dest_paths.pop()
        else:
            failure = True

        if not failure:
            report = \
                f"Success! [{results}] JP2 files written to \"{dest}\" folder"
        else:
            failed_list = "* \n".join(
                [result.data["source_filename"]
                 for result in failed_results]
            )

            report = "Failed!\n" \
                     "The following files failed to convert: \n" \
                     f"{failed_list}"
        return report

    @classmethod
    def _partition_results(
        cls,
        results: List[speedwagon.tasks.Result[PackageImageConverterTaskReport]]
    ) -> Tuple[
         typing.Iterator[
             speedwagon.tasks.Result[PackageImageConverterTaskReport]
         ],
         typing.Iterator[
             speedwagon.tasks.Result[PackageImageConverterTaskReport]
         ]
    ]:

        def successful(
            res: speedwagon.tasks.Result[PackageImageConverterTaskReport]
        ) -> bool:
            if not res.data["success"]:
                return False
            return True

        iterator_1, iterator_2 = itertools.tee(results)
        return \
            itertools.filterfalse(successful, iterator_1), \
            filter(successful, iterator_2)


class PackageImageConverterTask(
    speedwagon.tasks.Subtask[PackageImageConverterTaskReport]
):
    name = "Package Image Convert"

    def __init__(self, source_file_path: str, dest_path: str) -> None:
        super().__init__()
        self._dest_path = dest_path
        self._source_file_path = source_file_path

    def task_description(self) -> Optional[str]:
        return f"Converting package from {self._source_file_path}"

    def work(self) -> bool:
        des_path = self._dest_path

        process_task = ProcessFile(ConvertFile())

        try:
            os.makedirs(des_path)
            self.log(f"Created {des_path}")
        except FileExistsError:
            pass

        try:
            process_task.process(self._source_file_path, des_path)
            success = True
        except ProcessingException as error:
            print(error, file=sys.stderr)
            success = False
        self.set_results(
            {
                "output_filename": process_task.output,
                "source_filename": self._source_file_path,
                "success": success
            }
        )
        status_message = process_task.status_message()
        if status_message is not None:
            self.log(status_message)

        return success
