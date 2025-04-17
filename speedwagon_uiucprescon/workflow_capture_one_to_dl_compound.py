"""Workflow for converting Capture One tiff file into DL compound format."""
from __future__ import annotations
import logging
import typing
import warnings

from typing import Any, List, Optional, Mapping, TypedDict

from uiucprescon import packager
from uiucprescon.packager.packages.collection import Package
from uiucprescon.packager.common import Metadata

import speedwagon
from speedwagon import validators, utils
from speedwagon.job import Workflow


CaptureOneToDlCompoundWorkflowTaskArgs = TypedDict(
    'CaptureOneToDlCompoundWorkflowTaskArgs',
    {
        "package": Package,
        "output": str,
        "source_path": str,
    }
)

UserArgs = TypedDict(
    'UserArgs', {
        "Input": str,
        "Output": str
    }
)


class PackageConverter(speedwagon.tasks.Subtask[None]):
    """Convert packages formats."""

    name = "Package Conversion"

    def __init__(self,
                 source_path: str,
                 packaging_id: str,
                 existing_package: Package,
                 new_package_root: str) -> None:
        """Create a new PackageConverter object.

        Args:
            source_path:
            packaging_id:
            existing_package:
            new_package_root:
        """
        super().__init__()
        self.packaging_id = packaging_id
        self.existing_package = existing_package
        self.new_package_root = new_package_root
        self.source_path = source_path
        self.package_factory = None

    def task_description(self) -> Optional[str]:
        return \
            f"Creating a new Digital Library package from {self.source_path}"

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
                f"to a Hathi Trust Tiff package at {self.new_package_root}")

            package_factory = self.package_factory or packager.PackageFactory(
                packager.packages.DigitalLibraryCompound()
            )

            package_factory.transform(
                self.existing_package, dest=self.new_package_root
            )

        return True
