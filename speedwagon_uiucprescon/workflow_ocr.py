"""Workflow for performing OCR on image files."""

from __future__ import annotations
import io
import logging
import os
import typing

from typing import List, Any, Optional, Iterator, Mapping, TypedDict
import contextlib
from uiucprescon import ocr

import speedwagon
import speedwagon.workflow
from speedwagon import validators

from speedwagon.exceptions import (
    MissingConfiguration,
    InvalidConfiguration,
    SpeedwagonException,
    JobCancelled,
)

TESSERACT_PATH_LABEL = "Tesseract data file location"

__all__ = ["OCRWorkflow"]


def locate_tessdata() -> Optional[str]:
    path = os.path.join(os.path.dirname(__file__), "tessdata")
    if path_contains_traineddata(path):
        return os.path.normpath(path)
    return None


def path_contains_traineddata(path: str) -> bool:
    for file in os.scandir(path):
        if not file.is_file():
            continue
        _, ext = os.path.splitext(file.name)
        if ext == ".traineddata":
            return True
    return False


ReportFormat = typing.TypedDict("ReportFormat", {"text": str, "source": str})
UserArgs = TypedDict(
    "UserArgs",
    {
        "Image File Type": str,
        "Language": str,
        "Path": str,
    },
)

JobArgs = TypedDict(
    "JobArgs",
    {
        "source_file_path": str,
        "destination_path": str,
        "output_file_name": str,
        "lang_code": str,
    },
)


class OCRWorkflow(speedwagon.Workflow[UserArgs]):
    """Optical Character Recognition workflow for Speedwagon."""

    name = "Generate OCR Files"

    SUPPORTED_IMAGE_TYPES = {"JPEG 2000": ".jp2", "TIFF": ".tif"}

    def __init__(self, *args, **kwargs) -> None:
        """Create a OCR Workflow."""
        super().__init__(*args, **kwargs)
        self.global_settings = kwargs.get("global_settings", {})
        self._update_description()

    def set_options_backend(
        self, options_backend: speedwagon.workflow.OptionsBackend
    ) -> None:
        super().set_options_backend(options_backend)
        self._update_description()

    def _update_description(self):
        try:
            tessdata_path = self.get_tesseract_path()

        except AttributeError:
            tessdata_path = ""

        description_header = "Create OCR text files for images."
        if tessdata_path:
            description_body = (
                "Settings: \n"
                "    Path: Path containing tiff or jp2 files. \n"
                "    Image File Type: The type of Image file to use.\n"
                "\n"
                "\n"
                "Adding Additional Languages:\n"
                "    To modify the available languages, place "
                "Tesseract traineddata files"
                "into the following directory:\n"
                "\n"
                f"{tessdata_path}.\n"
            )
        else:
            description_body = (
                "TESSERACT DATA FILE LOCATION NOT SET!\n"
                "\n"
                "To fix this, open Settings/Preferences for Speedwagon and "
                'go to the "Workflow Settings" Tab. Locate the '
                '"Generate OCR Files" sections and set the value for '
                '"Tesseract data file location"'
            )
        description_footer = (
            "Note:\n"
            "    It's important to use the correct version of the "
            "traineddata files. Using incorrect versions won't crash the "
            "program but they may produce unexpected results.\n"
            "\n"
            "For more information about these files, go to "
            "https://github.com/tesseract-ocr/tesseract/wiki/Data-Files\n"
        )

        description = [
            description_header,
            "\n",
            description_body,
            "\n",
            description_footer,
        ]
        self.set_description("\n".join(description))

    @classmethod
    def set_description(cls, text: str) -> None:
        """Change the workflow's description seen by the user."""
        cls.description = text

    def discover_task_metadata(
        self,
        initial_results: List[speedwagon.tasks.Result[List[str]]],
        additional_data: Mapping[str, Any],  # pylint: disable=unused-argument
        user_args: UserArgs,
    ) -> List[JobArgs]:
        """Create OCR task metadata for each file located."""
        tessdata_path = self.get_tesseract_path()
        if tessdata_path is None:
            raise InvalidConfiguration("Tesseract data file location not set")

        if os.path.exists(tessdata_path) is False:
            raise InvalidConfiguration(
                f'Tesseract data file location "{tessdata_path}" '
                f"does not exist"
            )

        new_tasks: List[JobArgs] = []

        for result in initial_results:
            for image_file in result.data:
                for key, value in ocr.LANGUAGE_CODES.items():
                    if value == user_args["Language"]:
                        language_code = key
                        break
                else:
                    language = user_args["Language"]
                    raise ValueError(
                        f"Unable to look up language code for {language}"
                    )

                base_name = os.path.splitext(os.path.basename(image_file))[0]
                new_task: JobArgs = {
                    "source_file_path": image_file,
                    "destination_path": os.path.dirname(image_file),
                    "output_file_name": f"{base_name}.txt",
                    "lang_code": language_code,
                }
                new_tasks.append(new_task)
        return new_tasks

    def create_new_task(
        self, task_builder: "speedwagon.tasks.TaskBuilder", job_args: JobArgs
    ) -> None:
        """Add ocr task for each file."""
        image_file = job_args["source_file_path"]
        destination_path = job_args["destination_path"]
        ocr_file_name = job_args["output_file_name"]
        lang_code = job_args["lang_code"]
        tessdata_path = self.get_tesseract_path()
        if tessdata_path is None:
            raise MissingConfiguration(
                "Tesseract data file location is not set"
            )

        ocr_generation_task = GenerateOCRFileTask(
            source_image=image_file,
            out_text_file=os.path.join(destination_path, ocr_file_name),
            lang=lang_code,
            tesseract_path=tessdata_path,
        )
        task_builder.add_subtask(ocr_generation_task)

    def initial_task(
        self, task_builder: "speedwagon.tasks.TaskBuilder", user_args: UserArgs
    ) -> None:
        """Create a task to locate appropriate files."""
        root = user_args["Path"]
        file_type = user_args["Image File Type"]
        try:
            file_extension = self.get_file_extension(file_type)
        except KeyError as exc:
            raise JobCancelled(f"Invalid Image Type: {exc}") from exc

        task_builder.add_subtask(
            FindImagesTask(root, file_extension=file_extension)
        )

    @classmethod
    def get_file_extension(cls, file_type: str) -> str:
        """Identify file type extension."""
        return cls.SUPPORTED_IMAGE_TYPES[file_type]

    def job_options(
        self,
    ) -> List[
        speedwagon.workflow.AbsOutputOptionDataType[
            speedwagon.workflow.UserDataType
        ]
    ]:
        """Request use settings for OCR job."""
        package_type = speedwagon.workflow.ChoiceSelection("Image File Type")
        package_type.required = True
        package_type.placeholder_text = "Select Image Format"
        for file_type in OCRWorkflow.SUPPORTED_IMAGE_TYPES:
            package_type.add_selection(file_type)

        language_type = speedwagon.workflow.ChoiceSelection("Language")
        language_type.placeholder_text = "Select Language"
        tessdata_path = self.get_tesseract_path()

        def full_name(code: str) -> str:
            language_name = ocr.LANGUAGE_CODES.get(code)
            return "" if language_name is None else language_name

        if tessdata_path:
            for lang in sorted(
                self.get_available_languages(
                    path=typing.cast(str, tessdata_path)
                ),
                key=full_name,
            ):
                fullname = ocr.LANGUAGE_CODES.get(lang)
                if fullname is None:
                    continue
                language_type.add_selection(fullname)

        package_root_option = speedwagon.workflow.DirectorySelect(
            "Path", required=True
        )

        package_root_option.add_validation(validators.ExistsOnFileSystem())
        package_root_option.add_validation(
            validators.IsDirectory(),
            condition=lambda candidate, _: candidate is not None,
        )

        return [package_type, language_type, package_root_option]

    def get_tesseract_path(self) -> Optional[str]:
        """Get the path to the tesseract data files."""
        return typing.cast(
            Optional[str],
            self.get_workflow_configuration_value(TESSERACT_PATH_LABEL),
        )

    @staticmethod
    def get_available_languages(path: str) -> Iterator[str]:
        """Get languages accessible based on the available data files."""

        def filter_only_trainingdata(item: os.DirEntry[str]) -> bool:
            if not item.is_file():
                return False

            base, ext = os.path.splitext(item.name)

            if ext != ".traineddata":
                return False

            if base == "osd":
                return False

            return True

        try:
            for file in filter(
                filter_only_trainingdata, os.scandir(path.strip())
            ):
                yield os.path.splitext(file.name)[0]
        except FileNotFoundError as error:
            logging.warning(
                "unable to locate language files. Reason: %s",
                error
            )
            yield from []

    @classmethod
    def generate_report(
        cls,
        results: List[speedwagon.tasks.Result[ReportFormat]],
        user_args: UserArgs,  # pylint: disable=unused-argument
    ) -> Optional[str]:
        """Generate report for OCR files generated."""
        amount = len(cls._get_ocr_tasks(results))

        return (
            "*************************************\n"
            "Report\n"
            "*************************************\n"
            f"Completed generating OCR {amount} files.\n"
            "\n"
            "*************************************\n"
            "Done\n"
        )

    @staticmethod
    def _get_ocr_tasks(
        results: List[speedwagon.tasks.Result[ReportFormat]],
    ) -> List[speedwagon.tasks.Result[ReportFormat]]:
        def filter_ocr_gen_tasks(
            result: speedwagon.tasks.Result[ReportFormat],
        ) -> bool:
            if result.source != GenerateOCRFileTask:
                return False
            return True

        return list(filter(filter_ocr_gen_tasks, results))

    def workflow_options(
        self,
    ) -> List[
        speedwagon.workflow.AbsOutputOptionDataType[
            speedwagon.workflow.UserDataType
        ]
    ]:
        """Set the settings for get marc workflow.

        This needs the path to the tesseract data.
        """
        tesseract_path = speedwagon.workflow.DirectorySelect(
            label=TESSERACT_PATH_LABEL
        )

        tesseract_path.required = True
        return [tesseract_path]


class FindImagesTask(speedwagon.tasks.Subtask[List[str]]):
    name = "Finding Images"

    def __init__(self, root: str, file_extension: str) -> None:
        super().__init__()
        self._root = root
        self._extension = file_extension

    def task_description(self) -> Optional[str]:
        return (
            f"Finding files in {self._root} with {self._extension} extension"
        )

    def work(self) -> bool:
        self.log(f"Locating {self._extension} files in {self._root}")

        def find_images(file_located: str) -> bool:
            if os.path.isdir(file_located):
                return False

            _, ext = os.path.splitext(file_located)
            if ext.lower() != self._extension:
                return False

            return True

        directories = []

        for root, _, files in os.walk(self._root):
            for file_name in filter(find_images, files):
                file_path = os.path.join(root, file_name)
                self.log(f"Located {file_path}")
                directories.append(file_path)
        self.set_results(directories)

        return True


class GenerateOCRFileTask(speedwagon.tasks.Subtask[ReportFormat]):
    engine: Optional[ocr.Engine] = None
    name = "Optical character recognition"

    def __init__(
        self,
        source_image: str,
        out_text_file: str,
        lang: str = "eng",
        tesseract_path: Optional[str] = None,
    ) -> None:
        super().__init__()

        self._source = source_image
        self._output_text_file = out_text_file
        self._lang = lang
        self._tesseract_path = tesseract_path
        GenerateOCRFileTask.set_tess_path(tesseract_path or locate_tessdata())
        assert self.engine is not None

    def task_description(self) -> Optional[str]:
        return f"Scanning for text in {self._source}"

    @classmethod
    def set_tess_path(cls, path: Optional[str] = None) -> None:
        if path is None:
            path = locate_tessdata()
        assert path is not None
        cls.engine = ocr.Engine(path)
        assert cls.engine is not None

    def write_data(self, data: str, file_handle: io.TextIOWrapper) -> None:
        file_handle.write(data)

    def work(self) -> bool:
        resulting_text = self.read_image(self._source, self._lang)

        # Generate a text file from the text data extracted from the image
        self.log(f"Writing to {self._output_text_file}")
        with open(self._output_text_file, "w", encoding="utf8") as write_file:
            self.write_data(resulting_text, write_file)
            # write_file.write(resulting_text)

        result: ReportFormat = {"text": resulting_text, "source": self._source}
        self.set_results(result)
        return True

    def read_image(self, file: str, lang: str) -> str:
        if self.engine is None:
            raise RuntimeError("OCR Engine not set")

        if self.engine.data_set_path is None:
            self.engine.data_set_path = self._tesseract_path

        # Get the ocr text reader for the proper language
        reader = self.engine.get_reader(lang)
        self.log(f"Reading {os.path.normcase(file)}")

        file_handle = io.StringIO()

        with contextlib.redirect_stderr(file_handle):
            # Capture the warning messages
            try:
                resulting_text = reader.read(file)
            except ocr.tesseractwrap.TesseractGlueException as error:
                raise SpeedwagonException(f"Unable to read {file}") from error

        stderr_messages = file_handle.getvalue()
        if stderr_messages:
            # Log any error messages
            self.log(stderr_messages.strip())
        return resulting_text
