"""Speedwagon Workflow for creating pdf files from scanned images."""

import dataclasses
import logging
import os
import time
import typing
from functools import lru_cache
from typing import (
    Any,
    Callable,
    List,
    Iterator,
    Mapping,
    Optional,
    Sequence,
    Tuple,
    TypedDict,
)

from speedwagon.exceptions import MissingConfiguration
from speedwagon.job import Workflow
from speedwagon.tasks import TaskBuilder, Result
import speedwagon.workflow
from uiucprescon import ocr

__all__ = ["MakePDFWorkflow"]


TESSERACT_PATH_LABEL = "Tesseract data file location"

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


@dataclasses.dataclass
class PDFGenerationResult:
    """Result of PDF generation."""

    success: bool
    total_time: float
    output: Optional[str] = None
    pages_added: list[str] = dataclasses.field(default_factory=list)


UserOptions = TypedDict(
    "UserOptions",
    {
        "Input directory": str,  # NOSONAR S1192
        "Output pdf": str,  # NOSONAR S1192
        "Language": str,
        "Image Format": str,
    }
)

TaskArgs = TypedDict(
    "TaskArgs",
    {
        "pages": list[str],
        "output": str,
    }
)


def get_available_languages(
    path: str,
    search_directory_strategy: Callable[
        [str], typing.Iterator[os.DirEntry[str]]
    ] = os.scandir
) -> typing.Iterator[str]:
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
            filter_only_trainingdata, search_directory_strategy(path.strip())
        ):
            yield os.path.splitext(file.name)[0]
    except FileNotFoundError as error:
        logging.warning("unable to locate language files. Reason: %s", error)
        yield from []


my_sentinel = speedwagon.tasks.tasks.Sentinel()


@speedwagon.tasks.workflow_task(
    description="Create PDF", logger=logger, sentinel=my_sentinel)
def make_pdf_task(
    output: str,
    pages: list[str],
    tessdata_path: str,
    tesseract_api_strategy=ocr.OCRApi,
    pdf_builder_strategy=ocr.PDFBuilder
) -> PDFGenerationResult:
    """Create a PDF from a list of pages.

    Args:
        output: The path to the output PDF file.
        pages: A list of paths to the image files to include in the PDF.
        tessdata_path: The path to the Tesseract data files.
        tesseract_api_strategy: The strategy to use for the OCR API.
        pdf_builder_strategy: The strategy to use for building the PDF.

    Returns:
        A dictionary containing the result of the PDF generation process.

    """
    if len(pages) == 0:
        logger.warning("No pages to add to %s", output)
        return PDFGenerationResult(
            success=False,
            output=output,
            total_time=0.0
        )
    ocr_api = tesseract_api_strategy(tessdata_path, "eng")
    task_start_time = time.perf_counter()
    pages_completed: List[str] = []
    success = False
    try:
        with pdf_builder_strategy(output, ocr_api) as builder:
            for i, page in enumerate(pages):
                if my_sentinel.job_aborted:
                    return PDFGenerationResult(
                        success=success,
                        output=output,
                        pages_added=pages_completed,
                        total_time=time.perf_counter() - task_start_time
                    )
                start_time_page = time.perf_counter()
                logger.info(
                    "Adding page %s to %s",
                    os.path.basename(page),
                    os.path.basename(output)
                )

                builder.add_page(page)
                pages_completed.append(page)
                percent_complete = (i + 1) / len(pages) * 100
                logger.info(
                    "%.2f%% of %s completed.",
                    percent_complete,
                    os.path.basename(output)
                )

                logger.debug(
                    "Processing \"%s\" took %.2f seconds",
                    os.path.basename(page),
                    time.perf_counter() - start_time_page
                )
        total_time = time.perf_counter() - task_start_time
        if total_time > 60:
            logger.debug("Task took %.2f minutes", total_time / 60)
        else:
            logger.debug("Task took %.2f seconds", total_time)
        logger.info("Finished adding pages to %s", output)
        success = True
        return PDFGenerationResult(
            success=success,
            output=output,
            pages_added=pages_completed,
            total_time=total_time
        )
    finally:
        if not success and os.path.exists(output):
            os.remove(output)


@lru_cache(maxsize=10)
def get_tesseract_path(backend_strategy) -> Optional[str]:
    """Get the path to the tesseract data files."""
    return typing.cast(
        Optional[str],
        backend_strategy(TESSERACT_PATH_LABEL),
    )


@dataclasses.dataclass
class PdfExtraInfo:
    time_taken: float


class PDFGenerationReportCreator:

    def __init__(self) -> None:
        super().__init__()
        self.header = "Report of Make PDF Book"
        self._pdf_creation_info: List[
            Tuple[
                str,
                str,
                List[str],
                Optional[PdfExtraInfo]
            ]
        ] = []

    def add_pdf_created_section(
        self,
        input_directory: str,
        output_pdf: str,
        pages: List[str],
        extra_info: Optional[PdfExtraInfo] = None
    ) -> None:
        self._pdf_creation_info.append(
            (input_directory, output_pdf, pages, extra_info)
        )

    def create(self) -> str:
        report_lines = [self.header]
        for input_directory, output_pdf, pages, extra_info in (
            self._pdf_creation_info
        ):
            report_lines.append(
                f"Added the following pages to {output_pdf} "
                f"from {input_directory}."
            )

            for page in pages:
                relative_filename = os.path.relpath(
                    page, start=input_directory
                )
                report_lines.append(f"  * {relative_filename}")

            if extra_info:
                if extra_info.time_taken > 60:
                    minutes = extra_info.time_taken / 60
                    time_taken = f"{minutes:.2f} minutes"
                else:
                    time_taken = f"{extra_info.time_taken:.2f} seconds"
                report_lines.append(
                    f"Creating {os.path.basename(output_pdf)} took "
                    f"{time_taken}."
                )

        return "\n".join(report_lines)


def generate_pdf_report(results, user_args) -> str:
    if any(not result.data.success for result in results):
        return "PDF creation failed."
    generator = PDFGenerationReportCreator()
    for result in results:
        generator.add_pdf_created_section(
            input_directory=user_args["Input directory"],
            output_pdf=result.data.output,
            pages=result.data.pages_added,
            extra_info=PdfExtraInfo(
                time_taken=result.data.total_time
            )
        )
    return generator.create()


def include_all_jp2_files_in_directory(
    input_directory: str,
    output_pdf: str,
    find_files_strategy: Callable[
        [str], Iterator[os.DirEntry[str]]
    ] = os.scandir
) -> TaskArgs:
    """Create a task for each file in the input directory."""
    pages = [
        a.path
        for a in sorted(
            filter(
                lambda f: f.name.endswith(".jp2"),
                find_files_strategy(input_directory),
            ),
            key=lambda f: f.name,
        )
    ]
    if len(pages) == 0:
        raise FileNotFoundError("No .jp2 files found in the input directory.")
    return TaskArgs(pages=pages, output=output_pdf)


class MakePDFWorkflow(Workflow[UserOptions]):
    """Speedwagon Workflow for creating a PDF book."""

    name = "Make PDF Book"

    report_strategy = generate_pdf_report
    task_metadata_creation_strategy = include_all_jp2_files_in_directory
    get_tesseract_path_from_backend_strategy = get_tesseract_path

    def job_options(self) -> List[speedwagon.workflow.AbsOutputOptionDataType]:
        """Return the options for the PDF creation job."""
        job_options: List[speedwagon.workflow.AbsOutputOptionDataType] = [
            speedwagon.workflow.DirectorySelect(
                "Input directory",
                required=True
            )
        ]

        image_format = speedwagon.workflow.ChoiceSelection("Image Format")
        image_format.add_selection(".jp2")
        image_format.add_selection(".tif")
        image_format.default_value = ".jp2"
        job_options.append(image_format)

        lang_selection = speedwagon.workflow.ChoiceSelection("Language")
        tessdata_path = self.get_tesseract_path()
        if tessdata_path:
            for lang_code in get_available_languages(tessdata_path):
                lang_selection.add_selection(lang_code)
        job_options.append(lang_selection)

        output_pdf_option =\
            speedwagon.workflow.FileSave(
                "Output pdf",
                required=True
            )
        output_pdf_option.filter = "PDF files (*.pdf)"
        job_options.append(output_pdf_option)

        return job_options

    def get_tesseract_path(self) -> Optional[str]:
        """Get the path to the tesseract data files."""
        return MakePDFWorkflow.get_tesseract_path_from_backend_strategy(
            self.get_workflow_configuration_value
        )

    @classmethod
    def generate_report(
        cls,
        results: List[Result[Any, PDFGenerationResult]],
        user_args: UserOptions
    ) -> Optional[str]:
        """Generate a report of the PDF creation process.

        Args:
            results: A list of results from the PDF generation tasks.
                        This should really only contain one result.
            user_args: The user-provided arguments for the workflow.

        Returns:
            String report of the PDF creation process.

        """
        return cls.report_strategy(results, user_args)

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

    def discover_task_metadata(
        self,
        initial_results: List[Result],
        additional_data: Mapping[str, Any],
        user_args: UserOptions
    ) -> Sequence[TaskArgs]:
        """Discover the metadata for the PDF creation tasks.

        Looks for jp2 files in the user provide folder and sort file names
        alpha-numerically.
        """
        try:
            return [
                MakePDFWorkflow.task_metadata_creation_strategy(
                    user_args["Input directory"],
                    user_args["Output pdf"]
                )
            ]
        except FileNotFoundError as e:
            raise speedwagon.exceptions.JobCancelled(
                "Problem with finding files"
            ) from e

    def create_new_task(self, task_builder: TaskBuilder, job_args) -> None:
        """Create a new task for creating a PDF."""
        tessdata_path = self.get_tesseract_path()
        if tessdata_path is None:
            raise MissingConfiguration(
                "Tesseract data file location is not set"
            )
        task_builder.add_subtask(
            make_pdf_task(
                output=job_args["output"],
                pages=job_args["pages"],
                tessdata_path=tessdata_path
            )
        )
