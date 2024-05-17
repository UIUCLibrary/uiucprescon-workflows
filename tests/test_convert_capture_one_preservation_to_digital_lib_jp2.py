from unittest.mock import Mock
import speedwagon
from speedwagon.utils import assign_values_to_job_options, validate_user_input
import pytest
import os.path
import os


from speedwagon_uiucprescon import \
    workflow_convert_capone_pres_to_digital_lib_jp2 as \
    capture_one_workflow


def test_package_image_task_success(monkeypatch):
    mock_processfile = Mock()
    with monkeypatch.context() as mp:
        mp.setattr(capture_one_workflow, "ProcessFile", mock_processfile)
        mp.setattr(os, "makedirs", lambda *x: None)
        task = capture_one_workflow.PackageImageConverterTask(
            source_file_path="spam",
            dest_path="eggs"
        )
        assert task.work() is True
    assert mock_processfile.called is True


def test_validate_user_options_valid(monkeypatch):
    workflow = capture_one_workflow.ConvertTiffPreservationToDLJp2Workflow()
    import os.path
    monkeypatch.setattr(os.path, "exists", lambda x: True)
    monkeypatch.setattr(os.path, "isdir", lambda x: True)
    user_args = {
        "Input": "./some/path/preservation"
    }
    findings = validate_user_input(
        {
            value.setting_name or value.label: value
            for value in assign_values_to_job_options(
                workflow.job_options(),
                **user_args
            )
        }
    )
    assert len(findings) == 0

def test_validate_user_options_input_not_exists(monkeypatch):
    workflow = capture_one_workflow.ConvertTiffPreservationToDLJp2Workflow()
    path_exists = Mock(return_value=False)
    monkeypatch.setattr(
        speedwagon.validators.ExistsOnFileSystem,
        "path_exists",
        path_exists
    )
    user_args = {
        "Input": "./some/path/that/does/not/exists/preservation"
    }
    findings = validate_user_input(
        {
            value.setting_name or value.label: value
            for value in assign_values_to_job_options(
                workflow.job_options(),
                **user_args
            )
        }
    )
    path_exists.assert_called_with(
        "./some/path/that/does/not/exists/preservation"
    )
    assert len(findings['Input']) > 0


def test_validate_user_options_input_is_file(monkeypatch):
    workflow = capture_one_workflow.ConvertTiffPreservationToDLJp2Workflow()
    monkeypatch.setattr(os.path, "exists", lambda x: True)
    monkeypatch.setattr(os.path, "isdir", lambda x: False)
    user_args = {
        "Input": "./some/path/a_file.tif"
    }
    findings = validate_user_input(
        {
            value.setting_name or value.label: value
            for value in assign_values_to_job_options(
                workflow.job_options(),
                **user_args
            )
        }
    )
    assert findings["Input"] == ['./some/path/a_file.tif is not a directory']


def test_validate_user_options_input_not_pres(monkeypatch):
    workflow = capture_one_workflow.ConvertTiffPreservationToDLJp2Workflow()
    monkeypatch.setattr(os.path, "exists", lambda x: True)
    monkeypatch.setattr(os.path, "isdir", lambda x: True)

    user_args = {
        "Input": "./some/path/that/does/not/exists"
    }
    findings = validate_user_input(
        {
            value.setting_name or value.label: value
            for value in assign_values_to_job_options(
                workflow.job_options(),
                **user_args
            )
        }
    )
    assert findings['Input'] == ['Invalid value in input: Not a preservation directory']


def test_package_image_task_failure(monkeypatch):
    import os
    mock_processfile = Mock()
    mock_processfile.process = Mock(
        side_effect=capture_one_workflow.ProcessingException("failure"))

    def get_mock_processfile(*args):
        return mock_processfile

    with monkeypatch.context() as mp:
        mp.setattr(os, "makedirs", lambda *x: None)
        mp.setattr(capture_one_workflow, "ProcessFile", get_mock_processfile)
        task = capture_one_workflow.PackageImageConverterTask(
            source_file_path="spam",
            dest_path="eggs"
        )
        assert task.work() is False


class TestConvertTiffPreservationToDLJp2Workflow:
    @pytest.fixture
    def workflow(self):
        return \
            capture_one_workflow.ConvertTiffPreservationToDLJp2Workflow()

    @pytest.fixture
    def default_options(self, workflow):
        return {
            data.label: data.value for data in workflow.job_options()
        }

    def test_validate_user_options_valid(
            self,
            monkeypatch,
            workflow,
            default_options
    ):
        user_args = default_options.copy()
        import os

        user_args["Input"] = os.path.join(
            "some", "valid", "path", "preservation")

        monkeypatch.setattr(
            capture_one_workflow.os.path,
            "exists",
            lambda path: path == user_args["Input"]
        )

        monkeypatch.setattr(
            capture_one_workflow.os.path,
            "isdir",
            lambda path: path == user_args["Input"]
        )

        assert workflow.validate_user_options(**user_args) is True

    def test_discover_task_metadata(
            self,
            monkeypatch,
            workflow,
            default_options
    ):
        import os
        user_args = default_options.copy()
        user_args["Input"] = os.path.join(
            "some", "valid", "path", "preservation")

        initial_results = []
        additional_data = {}

        def scandir(path):
            path_file = Mock(
                path=os.path.join(path, "123.tif"),
            )
            path_file.name = "123.tif"
            return [path_file]

        monkeypatch.setattr(
            capture_one_workflow.os,
            "scandir",
            scandir
        )

        task_metadata = \
            workflow.discover_task_metadata(
                initial_results=initial_results,
                additional_data=additional_data,
                user_args=user_args
            )
        assert len(task_metadata) == 1 and \
               task_metadata[0]['source_file'] == \
               os.path.join(user_args["Input"], "123.tif")

    def test_create_new_task(self, workflow, monkeypatch):
        import os
        job_args = {
            "source_file": os.path.join("some", "source", "preservation"),
            "output_path": os.path.join("some", "source", "access"),
        }
        task_builder = Mock()
        PackageImageConverterTask = Mock()
        PackageImageConverterTask.name = "PackageImageConverterTask"
        monkeypatch.setattr(
            capture_one_workflow,
            "PackageImageConverterTask",
            PackageImageConverterTask
        )

        workflow.create_new_task(task_builder, job_args)

        assert task_builder.add_subtask.called is True
        PackageImageConverterTask.assert_called_with(
            source_file_path=job_args['source_file'],
            dest_path=job_args['output_path'],
        )

    def test_generate_report_success(self, workflow, default_options):
        user_args = default_options.copy()
        results = [
            speedwagon.tasks.Result(
                capture_one_workflow.PackageImageConverterTask,
                {
                    "success": True,
                    "output_filename": "somefile"
                }
            )
        ]
        report = workflow.generate_report(results, user_args)
        assert isinstance(report, str)
        assert "Success" in report

    def test_generate_report_failure(self, workflow, default_options):
        user_args = default_options.copy()
        results = [
            speedwagon.tasks.Result(
                capture_one_workflow.PackageImageConverterTask,
                {
                    "success": False,
                    "output_filename": "somefile",
                    "source_filename": "some_source"
                }
            )
        ]
        report = workflow.generate_report(results, user_args)
        assert isinstance(report, str)
        assert "Failed" in report


class TestPackageImageConverterTask:
    def test_work(self, monkeypatch):
        source_file_path = "source_file"
        dest_path = "output_path"
        tasks = capture_one_workflow.PackageImageConverterTask(
            source_file_path=source_file_path,
            dest_path=dest_path
        )
        makedirs = Mock()
        monkeypatch.setattr(capture_one_workflow.os, "makedirs", makedirs)
        process = Mock()

        monkeypatch.setattr(
            capture_one_workflow.ProcessFile,
            "process",
            process
        )

        assert tasks.work() is True
        assert process.called is True


def test_kdu_non_zero_throws_exception(monkeypatch):
    with pytest.raises(capture_one_workflow.ProcessingException):
        process = capture_one_workflow.ConvertFile()
        monkeypatch.setattr(
            capture_one_workflow.pykdu_compress,
            'kdu_compress_cli2',
            Mock(return_value=2)
        )
        process.process("dummy", "out")


def test_kdu_success(monkeypatch):
    process = capture_one_workflow.ConvertFile()
    monkeypatch.setattr(
        capture_one_workflow.pykdu_compress,
        'kdu_compress_cli2',
        Mock(return_value=0)
    )
    process.process("dummy", "out.jp2")
    assert "Generated out.jp2" in process.status


def test_tasks_have_description():
    task = capture_one_workflow.PackageImageConverterTask(
        source_file_path="some_source_path",
        dest_path="some_dest_path"
    )

    assert task.task_description() is not None
