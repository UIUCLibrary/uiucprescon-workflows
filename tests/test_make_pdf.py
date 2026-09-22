import os
from unittest.mock import Mock, MagicMock

import pytest
import speedwagon

from speedwagon_uiucprescon import workflow_make_pdf
class TestMakePDFWorkflow:
    def test_has_job_options(self):
        workflow = workflow_make_pdf.MakePDFWorkflow()
        job_options = workflow.job_options()
        assert len(job_options) > 0

    def test_has_workflow_options(self):
        workflow = workflow_make_pdf.MakePDFWorkflow()
        workflow_options = workflow.workflow_options()
        assert len(workflow_options) > 0

    def test_generate_report(self):
        workflow = workflow_make_pdf.MakePDFWorkflow()
        workflow_make_pdf.MakePDFWorkflow.report_strategy = Mock()
        results = []
        user_args = {
            'Input directory': "/path/to/input/directory",
            'Output pdf': "/path/to/output.pdf",
        }
        workflow.generate_report(results, user_args)
        workflow_make_pdf.MakePDFWorkflow.report_strategy.assert_called_once_with(
            results,
            user_args
        )
    def test_discover_task_metadata(self):
        workflow_make_pdf.MakePDFWorkflow.task_metadata_creation_strategy = Mock()
        workflow = workflow_make_pdf.MakePDFWorkflow()
        user_args = {
            'Input directory': "/path/to/input/directory",
            'Output pdf': "/path/to/output.pdf"
        }
        workflow.discover_task_metadata([], {}, user_args)
        workflow.task_metadata_creation_strategy.assert_called_once()


    def test_discover_task_metadata_cancels_job_if_no_files_found(self):
        workflow_make_pdf.MakePDFWorkflow.task_metadata_creation_strategy = Mock(side_effect=FileNotFoundError())
        workflow = workflow_make_pdf.MakePDFWorkflow()
        user_args = {
            'Input directory': "/path/to/input/directory",
            'Output pdf': "/path/to/output.pdf"

        }
        with pytest.raises(speedwagon.JobCancelled):
            workflow.discover_task_metadata([], {}, user_args)
    def test_create_new_task(self) -> None:
        (workflow_make_pdf
         .MakePDFWorkflow).get_tesseract_path_from_backend_strategy = Mock(
            return_value="/path/to/tesseract"
        )
        workflow = workflow_make_pdf.MakePDFWorkflow()
        task_builder = Mock()
        task_args = {
            "output": "/path/to/output.pdf",
            "pages": []
        }
        workflow.create_new_task(task_builder, task_args)
        task_builder.add_subtask.assert_called_once()

    def test_create_new_task_fails_if_missing_tesseract_path(self) -> None:
        (workflow_make_pdf
         .MakePDFWorkflow).get_tesseract_path_from_backend_strategy = Mock(
            return_value=None
        )
        workflow = workflow_make_pdf.MakePDFWorkflow()
        task_builder = Mock()
        task_args = {
            "output": "/path/to/output.pdf",
            "pages": []
        }
        with pytest.raises(speedwagon.exceptions.MissingConfiguration):
            workflow.create_new_task(task_builder, task_args)



def test_include_all_jp2_files_in_directory_uses_find_files_strategy() -> None:
    first_file = Mock(spec_set=os.DirEntry)
    first_file.name = "somefile1.jp2"

    second_file = Mock(spec_set=os.DirEntry)
    second_file.name = "somefile2.jp2"

    find_files_strategy =\
        Mock(
            return_value=[first_file, second_file]
        )

    task_arg = workflow_make_pdf.include_all_jp2_files_in_directory(
        "/path/to/input/directory",
        "/path/to/output.pdf",
        find_files_strategy=find_files_strategy
    )
    task_arg['output'] = "/path/to/output.pdf"
    find_files_strategy.assert_called_once_with("/path/to/input/directory")

def test_include_all_jp2_files_in_directory():
    first_file = Mock(spec_set=os.DirEntry)
    first_file.name = "somefile1.jp2"

    second_file = Mock(spec_set=os.DirEntry)
    second_file.name = "somefile2.jp2"

    find_files_strategy = Mock(return_value=[first_file, second_file])

    task_arg = workflow_make_pdf.include_all_jp2_files_in_directory(
        "/path/to/input/directory",
        "/path/to/output.pdf",
        find_files_strategy=find_files_strategy,
    )
    assert task_arg['output'] == "/path/to/output.pdf"

def test_include_all_jp2_files_in_directory_raises_if_no_files_found():
    find_files_strategy = Mock(return_value=[])
    with pytest.raises(FileNotFoundError):
        workflow_make_pdf.include_all_jp2_files_in_directory(
            "/path/to/input/directory",
            "/path/to/output.pdf",
            find_files_strategy=find_files_strategy,
        )

class TestPDFGenerationReportCreator:
    def test_create_report_includes_header(self):
        generator = workflow_make_pdf.PDFGenerationReportCreator()
        report = generator.create()
        assert generator.header in report

    def test_add_pdf_created_section(self):
        generator = workflow_make_pdf.PDFGenerationReportCreator()
        generator.add_pdf_created_section(
            input_directory="/path/to/input/directory",
            output_pdf="/path/to/output.pdf",
            pages=[
                "/path/to/input/directory/file1.jp2",
                "/path/to/input/directory/file2.jp2"
            ],
            extra_info=workflow_make_pdf.PdfExtraInfo(time_taken=10.0)
        )
        report = generator.create()
        assert "/path/to/output.pdf" in report

    @pytest.mark.parametrize(
        "time_taken, expected_string",
        [
            (10.0, "10.00 seconds"),
            (120.0, "2.00 minutes"),
        ]
    )
    def test_add_pdf_created_section_time_taken(self, time_taken, expected_string):
        generator = workflow_make_pdf.PDFGenerationReportCreator()
        generator.add_pdf_created_section(
            input_directory="/path/to/input/directory",
            output_pdf="/path/to/output.pdf",
            pages=[
                "/path/to/input/directory/file1.jp2",
                "/path/to/input/directory/file2.jp2"
            ],
            extra_info=workflow_make_pdf.PdfExtraInfo(time_taken=time_taken)
        )
        report = generator.create()
        assert expected_string in report

@pytest.mark.parametrize(
    "language_files, expected_languages",
    [
        (["eng.traineddata"], ["eng"]),
        (["eng.traineddata", "fre.traineddata"], ["eng", "fre"]),
        (["eng.traineddata", "osd.traineddata"], ["eng"]),
        (["eng.traineddata", "someotherfile.txt"], ["eng"]),
    ]
)
def test_get_available_languages(language_files, expected_languages):
    files = []
    for file in language_files:
        file_found = Mock(name=file)
        file_found.name = file
        files.append(file_found)
    search_strategy = Mock(return_value=files)
    languages = workflow_make_pdf.get_available_languages(
        "/path/to/input/directory",
        search_strategy
    )
    assert all(language in expected_languages for language in languages)

def test_make_pdf_task():
    pdf_builder_strategy = MagicMock()
    task = workflow_make_pdf.make_pdf_task(
        output="somefile.pdf",
        pages=["somefile.jp2"],
        tessdata_path="/path/to/tessdata",
        tesseract_api_strategy=Mock(),
        pdf_builder_strategy=pdf_builder_strategy
    )
    task.work()
    pdf_builder_strategy.assert_called_once()

def test_make_pdf_task_sentinel_stops_if_aborts(monkeypatch):
    pdf_builder_strategy = MagicMock()
    task_sentinel = Mock(job_aborted=True)
    monkeypatch.setattr(workflow_make_pdf, "my_sentinel", task_sentinel)
    task = workflow_make_pdf.make_pdf_task(
        output="somefile.pdf",
        pages=["somefile.jp2"],
        tessdata_path="/path/to/tessdata",
        tesseract_api_strategy=Mock(),
        pdf_builder_strategy=pdf_builder_strategy
    )
    task.work()
    assert task.task_result.data.success is False


def test_make_pdf_task_no_pages():
    pdf_builder_strategy = MagicMock()
    task = workflow_make_pdf.make_pdf_task(
        output="somefile.pdf",
        pages=[],
        tessdata_path="/path/to/tessdata",
        tesseract_api_strategy=Mock(),
        pdf_builder_strategy=pdf_builder_strategy
    )
    task.work()
    assert task.task_result.data.success is False
