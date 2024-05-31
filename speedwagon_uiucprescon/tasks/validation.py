"""Shared checksum tasks."""
import os
import typing
from typing import Optional, TypedDict

from pyhathiprep import checksum
from uiucprescon import imagevalidate

import speedwagon


MakeChecksumResult = typing.TypedDict("MakeChecksumResult", {
    "source_filename": str,
    "checksum_hash": str,
    "checksum_file": str,
})


class MakeChecksumTask(speedwagon.tasks.Subtask[MakeChecksumResult]):
    """Create a make checksum task."""

    name = "Create Checksum"

    def __init__(
        self, source_path: str, filename: str, checksum_report: str
    ) -> None:
        """Create a make checksum task."""
        super().__init__()
        self._source_path = source_path
        self._filename = filename
        self._checksum_report = checksum_report

    def task_description(self) -> Optional[str]:
        """Get user readable information about what the subtask is doing."""
        return f"Calculating checksum for {self._filename}"

    def work(self) -> bool:
        """Calculate file checksum."""
        item_path = self._source_path
        item_file_name = self._filename
        report_path_to_save_to = self._checksum_report
        self.log(f"Calculated the checksum for {item_file_name}")

        file_to_calculate = os.path.join(item_path, item_file_name)
        result: MakeChecksumResult = {
            "source_filename": item_file_name,
            "checksum_hash": checksum.calculate_md5_hash(
                file_to_calculate
            ),
            "checksum_file": report_path_to_save_to,
        }
        self.set_results(result)

        return True


class MakeCheckSumReportTask(speedwagon.tasks.Subtask[None]):
    """Generate a checksum report.

    This normally an .md5 file.
    """

    name = "Checksum Report Creation"

    def __init__(
        self,
        output_filename: str,
        checksum_calculations: typing.Iterable[MakeChecksumResult],
    ) -> None:
        """Create a checksum report task."""
        super().__init__()
        self._output_filename = output_filename
        self._checksum_calculations = checksum_calculations

    def task_description(self) -> Optional[str]:
        """Get user readable information about what the subtask is doing."""
        return f"Writing checksum report: {self._output_filename}"

    def work(self) -> bool:
        """Generate the report file."""
        report_builder = checksum.HathiChecksumReport()
        for item in self._checksum_calculations:
            filename = item['source_filename']
            hash_value = item['checksum_hash']
            report_builder.add_entry(filename, hash_value)
        report: str = report_builder.build()

        with open(self._output_filename, "w", encoding="utf-8") as write_file:
            write_file.write(report)
        self.log(f"Wrote {self._output_filename}")

        return True


ValidateImageMetadataResult = TypedDict(
    "ValidateImageMetadataResult", {
        "valid": bool,
        "filename": str,
        "report": str,
    }
)


class ValidateImageMetadataTask(
    speedwagon.tasks.Subtask[ValidateImageMetadataResult]
):
    """Validate the metadata of a image file."""

    name = "Validate Image Metadata"

    def __init__(self, filename: str, profile_name: str) -> None:
        """Create an image validation subtask.

        Args:
            filename: path to file
            profile_name: Name of the validation profile to use.
        """
        super().__init__()
        self._filename = filename
        self._profile = imagevalidate.get_profile(profile_name)

    def task_description(self) -> Optional[str]:
        """Get user readable information about what the subtask is doing."""
        return f"Validating image metadata for {self._filename}"

    def work(self) -> bool:
        """Validate file."""
        self.log(f"Validating {self._filename}")

        profile_validator = imagevalidate.Profile(self._profile)

        try:
            report = profile_validator.validate(self._filename)
            is_valid = report.valid
            report_text = "\n* ".join(report.issues())
        except RuntimeError as error:
            is_valid = False
            report_text = str(error)
        self.log(f"Validating {self._filename} -- {is_valid}")

        self.set_results(
            {
                "filename": self._filename,
                "valid": is_valid,
                "report": f"* {report_text}",
            }
        )

        return True
