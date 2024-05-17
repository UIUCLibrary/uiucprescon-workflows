"""Workflow to convert hathi limited packages to digital library format."""
from __future__ import annotations

import logging
import typing
from typing import List, Optional, Mapping

from uiucprescon import packager
import uiucprescon.packager.packages.collection

import speedwagon
import speedwagon.workflow
from speedwagon.job import Workflow
from speedwagon import reports, utils
from speedwagon import validators

if typing.TYPE_CHECKING:
    import sys
    if sys.version_info >= (3, 11):
        from typing import Never
    else:
        from typing_extensions import Never

__all__ = ['HathiLimitedToDLWorkflow']

PackageConverterReport = typing.TypedDict(
    "PackageConverterReport",
    {
        "destination": str
    }
)


UserOptions = typing.TypedDict(
    "UserOptions",
    {
        "Input": str,
        "Output": str,
    }
)

JobArgs = typing.TypedDict(
    "JobArgs",
    {
        "package": uiucprescon.packager.packages.collection.Package,
        "destination": str
    }
)


class HathiLimitedToDLWorkflow(Workflow[UserOptions]):
    """Converts Hathi Limited View file packages to Digital Library format."""

    name = "Convert HathiTrust limited view to Digital library"
    description = 'This tool converts HathiTrust limited view packages to ' \
                  'Digital library'

    active = True

    def discover_task_metadata(
        self,
        initial_results: List[  # pylint: disable=unused-argument
            speedwagon.tasks.Result[Never]
        ],
        additional_data: Mapping[  # pylint: disable=unused-argument
            str,
            Never
        ],
        user_args: UserOptions
    ) -> List[JobArgs]:
        """Find file packages."""
        hathi_limited_view_packager = packager.PackageFactory(
            packager.packages.HathiLimitedView())

        return [{
            "package": package,
            "destination": user_args['Output']
        } for package in hathi_limited_view_packager.locate_packages(
            user_args['Input'])]

    def create_new_task(
        self,
        task_builder: "speedwagon.tasks.TaskBuilder",
        job_args: JobArgs
    ) -> None:
        """Create a task for converting a package."""
        task_builder.add_subtask(
            PackageConverter(src=job_args['package'],
                             dst=job_args['destination'])
        )

    def job_options(
        self
    ) -> List[
        speedwagon.workflow.AbsOutputOptionDataType[
            speedwagon.workflow.UserDataType
        ]
    ]:
        """Get user options for input and output directories."""
        input_value = speedwagon.workflow.DirectorySelect("Input")

        input_value.add_validation(validators.ExistsOnFileSystem(
            message_template="Input does not exist"
        ))

        output_value = speedwagon.workflow.DirectorySelect("Output")
        output_value.add_validation(
            validators.CustomValidation[str](
                query=(
                    lambda candidate, job_args: candidate != job_args['Input']
                ),
                failure_message_function=(
                    lambda _: "Input cannot be the same as Output"
                )

            )
        )
        output_value.add_validation(
            validators.ExistsOnFileSystem(
                message_template="Output does not exist"
            )
        )

        return [input_value, output_value]

    @classmethod
    @reports.add_report_borders
    def generate_report(
        cls,
        results: List[speedwagon.tasks.Result[PackageConverterReport]],
        user_args: UserOptions
    ) -> Optional[str]:
        """Generate a report of packages converted."""
        total = len(results)

        return f"""All done. Converted {total} packages.
 Results located at {user_args['Output']}
"""


class PackageConverter(speedwagon.tasks.Subtask[PackageConverterReport]):
    name = "Convert Package"

    def __init__(
            self,
            src: uiucprescon.packager.packages.collection.Package,
            dst: str
    ) -> None:
        super().__init__()
        self.src = src
        self.dst = dst
        self.output_packager = packager.PackageFactory(
            packager.packages.DigitalLibraryCompound())

    def task_description(self) -> Optional[str]:
        return f"Converting package {self.src}"

    def work(self) -> bool:

        my_logger = logging.getLogger(packager.__name__)
        my_logger.setLevel(logging.INFO)

        with utils.log_config(my_logger, self.log):
            self.log(f"Converting package from {self.src}")
            self.output_packager.transform(self.src, self.dst)
            self.set_results({
                "destination": self.dst
            })

        return True
