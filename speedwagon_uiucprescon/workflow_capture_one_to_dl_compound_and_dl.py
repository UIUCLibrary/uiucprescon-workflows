"""Workflow for converting Capture One tiff file into two formats.

Notes:
    This module has a number of "type: ignore" statements because of the
    current version of the type-checker (mypy 0.902) at this writing has a
    problem with using module constants specified as Final for with typedict.
    If https://github.com/python/mypy/issues/4128 is resolved, please remove
    these type:ignore statements.
"""

from __future__ import annotations
import logging
import typing


from typing import List, Dict, Callable, Optional, Union, Mapping, TypedDict


from uiucprescon import packager
from uiucprescon.packager.packages.abs_package_builder import AbsPackageBuilder
from uiucprescon.packager.common import Metadata
from uiucprescon.packager.packages.collection import \
    Package

import speedwagon
import speedwagon.workflow
from speedwagon import utils
from speedwagon.job import Workflow
import speedwagon.exceptions

from speedwagon_uiucprescon import conditions

if typing.TYPE_CHECKING:
    import sys
    # pragma: no cover
    if sys.version_info >= (3, 11):
        from typing import Never
    else:
        from typing_extensions import Never
    from speedwagon.workflow import UserData

__all__ = ['CaptureOneToDlCompoundAndDLWorkflow']


UserArgs = TypedDict(
    'UserArgs',
    {
        "Input": str,
        "Package Type": str,
        "Output Digital Library": str,
        "Output HathiTrust": str
    },
)

JobArguments = TypedDict(
    "JobArguments",
    {
        "package": Package,
        "output_dl": Optional[str],
        "output_ht": Optional[str],
        "source_path": str,
    }
)

SUPPORTED_PACKAGE_SOURCES: \
    Dict[str,  packager.packages.abs_package_builder.AbsPackageBuilder] = {
        "Capture One": packager.packages.CaptureOnePackage(delimiter="-"),
        "Archival collections/Non EAS": packager.packages.ArchivalNonEAS(),
        "Cataloged collections/Non EAS": packager.packages.CatalogedNonEAS(),
        "EAS": packager.packages.Eas()
    }


def at_least_one_output_is_selected(
        candidate: Optional[str],
        job_args: UserData,
        *keys: str
) -> bool:
    if candidate is not None and candidate.strip() != '':
        return True

    # Check if any job arg with the given keys is set with a value. If the
    # value is a string,strip any whitespace before evaluating
    return any(
        filter(
            lambda val: (
                val.strip() != '' if isinstance(val, str)
                else val is not None
            ),
            [job_args.get(key) for key in keys]
        )
    )


def candidate_is_empty(candidate: Optional[str], _: UserData) -> bool:
    if candidate is None:
        return True
    return isinstance(candidate, str) and candidate.strip() == ""


def candidate_is_not_empty(candidate: Optional[str], _: UserData) -> bool:
    if candidate is None:
        return False
    return not isinstance(candidate, str) or candidate.strip() != ""


class CaptureOneToDlCompoundAndDLWorkflow(Workflow[UserArgs]):
    """Settings for convert capture one tiff files.

    .. versionchanged:: 0.1.5
        workflow only requires a single output to be set. Any empty output
            parameters will result in that output format not being made.

        Add EAS package format support for input

    .. versionchanged:: 0.3.0
        No packages located will raise a JobCancelled error.

    """

    name = "Convert CaptureOne TIFF to Digital Library Compound Object and " \
           "HathiTrust"
    description = "Input is a path to a folder of TIFF files all named with " \
                  "an object identifier sequence, a final delimiting" \
                  "dash, and a sequence consisting of " \
                  "padded zeroes and a number." \
                  "\n" \
                  "Output Hathi is a directory to put the new packages for " \
                  "HathiTrust."
    active = True

    def job_options(self) -> List[
        speedwagon.workflow.AbsOutputOptionDataType[
            speedwagon.workflow.UserDataType
        ]
    ]:
        """Request user options.

        User Options include:
            * Input - path directory containing tiff files
            * Package Type - File package type in the input directory
            * Output Digital Library - Output path to save new DL packages
            * Output HathiTrust - Output path to save new HT packages
        """
        input_path =\
            speedwagon.workflow.DirectorySelect("Input", required=True)

        input_path.add_validation(speedwagon.validators.ExistsOnFileSystem())

        input_path.add_validation(
            speedwagon.validators.IsDirectory(),
            condition=conditions.candidate_exists
        )

        package_type_selection = \
            speedwagon.workflow.ChoiceSelection("Package Type")

        package_type_selection.placeholder_text = "Select a Package Type"
        for package_type_name in SUPPORTED_PACKAGE_SOURCES:
            package_type_selection.add_selection(package_type_name)

        output_digital_library =\
            speedwagon.workflow.DirectorySelect(
                "Output Digital Library",
                required=False
            )

        output_digital_library.add_validation(
            speedwagon.validators.CustomValidation[Union[str, None]](
                query=(
                    lambda candidate, job_args: (
                        at_least_one_output_is_selected(
                            candidate,
                            job_args,
                            "Output HathiTrust"
                        )
                    )
                ),
                failure_message_function=(
                    lambda value: "At least one output is required"
                ),
            ),
            condition=candidate_is_empty
        )

        output_digital_library.add_validation(
            speedwagon.validators.ExistsOnFileSystem(),
            condition=candidate_is_not_empty
        )

        output_hathi_trust =\
            speedwagon.workflow.DirectorySelect(
                "Output HathiTrust",
                required=False
            )

        output_hathi_trust.add_validation(
            speedwagon.validators.CustomValidation[str](
                query=(
                    lambda candidate, job_args: (
                        at_least_one_output_is_selected(
                            candidate,
                            job_args,
                            "Output Digital Library"
                        )
                    )
                ),
                failure_message_function=(
                    lambda value: "At least one output is required"
                )
            ),
            condition=candidate_is_empty
        )
        output_digital_library.add_validation(
            speedwagon.validators.IsDirectory(
                message_template="{} is not a path to a valid directory"
            ),
            condition=candidate_is_not_empty
        )
        return [
            input_path,
            package_type_selection,
            output_digital_library,
            output_hathi_trust
        ]

    def discover_task_metadata(
        self,
        initial_results: List[  # pylint: disable=unused-argument
            speedwagon.tasks.Result[Never]
        ],
        additional_data: Mapping[  # pylint: disable=unused-argument
            str,
            Never
        ],
        user_args: UserArgs,
    ) -> List[JobArguments]:
        """Loot at user settings and discover any data needed to build a task.

        Args:
            initial_results:
            additional_data:
            **user_args:

        Returns:
            Returns a list of data to create a job with

        """
        source_input = user_args["Input"]
        dest_dl = user_args["Output Digital Library"]
        dest_ht = user_args["Output HathiTrust"]
        package_type = SUPPORTED_PACKAGE_SOURCES.get(
            user_args["Package Type"]
        )
        if package_type is None:
            raise ValueError(
                f"Unknown package type "
                f"{user_args['Package Type']}"
            )
        package_factory = packager.PackageFactory(package_type)

        jobs: List[JobArguments] = []
        try:
            for package in package_factory.locate_packages(source_input):
                jobs.append(
                    {
                        "package": package,
                        "output_dl": dest_dl,
                        "output_ht": dest_ht,
                        "source_path": source_input
                    }
                )
        except Exception as error:
            raise speedwagon.exceptions.SpeedwagonException(
                f"Failed to locate packages at {source_input}. Reason: {error}"
            ) from error

        if not jobs:
            raise speedwagon.JobCancelled(
                f"No packages located at {source_input}. Check location "
                f"and/or the structure of the files and folders match the "
                f"Package Type."
            )
        return jobs

    def create_new_task(
        self,
        task_builder: speedwagon.tasks.TaskBuilder,
        job_args: JobArguments
    ) -> None:
        """Generate a new task.

        Args:
            task_builder:
            **job_args:

        """

        existing_package = job_args['package']
        source_path = job_args["source_path"]

        package_id: str = typing.cast(
            str,
            existing_package.metadata[Metadata.ID]
        )

        new_dl_package_root = job_args.get("output_dl")
        if new_dl_package_root is not None:
            dl_packaging_task = PackageConverter(
                source_path=source_path,
                existing_package=existing_package,
                new_package_root=new_dl_package_root,
                packaging_id=package_id,
                package_format="Digital Library Compound",
            )
            task_builder.add_subtask(dl_packaging_task)

        new_ht_package_root = job_args.get("output_ht")
        if new_ht_package_root is not None:
            ht_packaging_task = PackageConverter(
                source_path=source_path,
                existing_package=existing_package,
                new_package_root=new_ht_package_root,
                packaging_id=package_id,
                package_format="HathiTrust jp2",

            )
            task_builder.add_subtask(ht_packaging_task)


class PackageConverter(speedwagon.tasks.Subtask[None]):
    """Convert packages formats."""

    name = "Package Conversion"
    package_formats: Dict[str, AbsPackageBuilder] = {
        "Digital Library Compound": packager.packages.DigitalLibraryCompound(),
        "HathiTrust jp2": packager.packages.HathiJp2()
    }

    def __init__(self,
                 source_path: str,
                 packaging_id: str,
                 existing_package: Package,
                 new_package_root: str,
                 package_format: str) -> None:
        """Create PackageConverter object.

        Args:
            source_path:
            packaging_id:
            existing_package:
            new_package_root:
            package_format:
        """
        super().__init__()
        self.package_factory: \
            Callable[[AbsPackageBuilder], packager.PackageFactory] \
            = packager.PackageFactory

        self.packaging_id = packaging_id
        self.existing_package = existing_package
        self.new_package_root = new_package_root
        if package_format not in PackageConverter.package_formats.keys():
            raise ValueError(f"{package_format} is not a known value")
        self.package_format = package_format
        self.source_path = source_path

    def task_description(self) -> Optional[str]:
        return f"Converting {self.source_path}"

    def work(self) -> bool:
        """Convert source package to the new type.

        Returns:
            True on success, False on failure

        """
        my_logger = logging.getLogger(packager.__name__)
        my_logger.setLevel(logging.INFO)
        with utils.log_config(my_logger, self.log):
            self.log(
                f"Converting {self.packaging_id} from {self.source_path} "
                f"to a {self.package_format} package at "
                f"{self.new_package_root}")
            self.log('Please note: This could take a while if the data is '
                     'located on slow storage.')
            self.log('Please note: Converting to some package formats do not '
                     'provided very detailed information to the progress bar')

            package_factory = self.package_factory(
                PackageConverter.package_formats[self.package_format]
            )

            package_factory.transform(
                self.existing_package, dest=self.new_package_root)
        return True
