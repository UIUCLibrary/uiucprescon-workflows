import itertools
from unittest.mock import MagicMock, Mock, ANY, mock_open, patch

import pytest
import os.path

import speedwagon
from speedwagon.utils import assign_values_to_job_options, validate_user_input

from speedwagon_uiucprescon import workflow_ocr
from speedwagon.exceptions import MissingConfiguration, SpeedwagonException
from uiucprescon.ocr import reader, tesseractwrap



def test_discover_task_metadata_raises_with_no_tessdata(monkeypatch):
    user_options = {"tessdata": "/some/path"}
    monkeypatch.setattr(os.path, "exists", lambda args: True)
    workflow = workflow_ocr.OCRWorkflow(global_settings=user_options)

    monkeypatch.setattr(os.path, "exists", lambda args: False)
    with pytest.raises(SpeedwagonException):
        user_options = {"tessdata": None}
        workflow.discover_task_metadata([], None, user_options)


def test_discover_task_metadata(monkeypatch, tmpdir):
    # user_options = {"tessdata": "/some/path"}
    # monkeypatch.setattr(os.path, "exists", lambda args: True)
    workflow = workflow_ocr.OCRWorkflow()
    tessdata_dir = tmpdir / "tessdata"
    image_dir = tmpdir / "images"
    tessdata_dir.ensure_dir()
    user_options = {
        "tessdata": tessdata_dir.strpath,
        'Image File Type': 'JPEG 2000',
        'Language': 'English',
        'Path':  image_dir.strpath
    }
    initial_results = [
        speedwagon.tasks.Result(
            source=workflow_ocr.FindImagesTask,
            data=[(image_dir / "dummy.jp2").strpath]
        )
    ]
    options_backend = Mock(get=lambda key: {"Tesseract data file location": "/some/file/path"}.get(key))
    workflow.set_options_backend(options_backend)
    with monkeypatch.context() as ctx:
        ctx.setattr(os.path, "exists", lambda path: path == "/some/file/path")
        new_tasks = workflow.discover_task_metadata(
            initial_results, None, user_options
        )

    assert len(new_tasks) == 1
    new_task = new_tasks[0]
    assert new_task == {
        'source_file_path': (image_dir / "dummy.jp2").strpath,
        'destination_path': image_dir.strpath,
        'output_file_name': 'dummy.txt',
        'lang_code': 'eng',
    }


def test_generate_task_creates_a_file(monkeypatch, tmpdir):
    source_image = tmpdir / "dummy.jp2"
    out_text = tmpdir / "dummy.txt"
    tessdata_dir = tmpdir / "tessdata"
    tessdata_dir.ensure_dir()
    (tessdata_dir / "eng.traineddata").ensure()
    (tessdata_dir / "osd.traineddata").ensure()

    def mock_read(*args, **kwargs):
        return "Spam bacon eggs"
    mock_reader = Mock()

    with monkeypatch.context() as patcher:
        patcher.setattr(reader.Reader, "read", mock_read)
        patcher.setattr(tesseractwrap, "Reader", mock_reader)
        task = workflow_ocr.GenerateOCRFileTask(
            source_image=source_image.strpath,
            out_text_file=out_text.strpath,
            tesseract_path=tessdata_dir.strpath
        )
        task.log = MagicMock()

        task.work()

    assert os.path.exists(out_text.strpath)
    with open(out_text.strpath, "r") as f:
        assert f.read() == "Spam bacon eggs"


class MockGenerateOCRFileTask(workflow_ocr.GenerateOCRFileTask):
    def mock_reader(self, *args, **kwargs):
        return Mock(read=Mock(return_value="Spam bacon eggs"))

    engine = Mock(get_reader=mock_reader)


class TestOCRWorkflow:
    @pytest.fixture
    def workflow(self, monkeypatch):
        global_settings = {
            "tessdata": os.path.join("some", "path")
        }
        monkeypatch.setattr(
            workflow_ocr.os.path,
            "exists",
            lambda path: path == global_settings["tessdata"]
        )
        return \
            workflow_ocr.OCRWorkflow(global_settings)

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
        import os
        user_options = default_options.copy()
        user_options["Path"] = os.path.join("some", "path")
        monkeypatch.setattr(
            workflow_ocr.os.path,
            "isdir",
            lambda path: path == user_options["Path"]
        )
        assert workflow.validate_user_options(**user_options) is True

    @pytest.mark.parametrize("check_function", ["isdir", "exists"])
    def test_validate_user_options_invalid(
            self,
            monkeypatch,
            workflow,
            default_options,
            check_function
    ):
        import os
        user_args = default_options.copy()
        user_args["Path"] = os.path.join("some", "path")
        user_args["Language"] = "eng"
        findings = validate_user_input(
            {
                value.setting_name or value.label: value
                for value in assign_values_to_job_options(
                    workflow.job_options(),
                    **user_args
                )
            }
        )
        assert len(findings) > 0

    def test_discover_task_metadata(self, workflow, default_options, monkeypatch):
        user_options = default_options.copy()
        user_options["Language"] = "English"
        user_options["Path"] = os.path.join("some", "path")

        initial_results = [
            speedwagon.tasks.Result(workflow_ocr.FindImagesTask, [
                "spam.jp2"
            ])
        ]
        additional_data = {}
        options_backend = Mock(get=lambda key: {"Tesseract data file location": "/some/file/path"}.get(key))
        workflow.set_options_backend(options_backend)
        with monkeypatch.context() as ctx:
            def exists(path):
                result = path == "/some/file/path"
                return result
            ctx.setattr(os.path, "exists", exists)
            # ctx.setattr(os.path, "exists", lambda path: path == "/some/file/path")
            tasks_generated = workflow.discover_task_metadata(
                initial_results=initial_results,
                additional_data=additional_data,
                user_args=user_options
            )
        assert len(tasks_generated) == 1
        task = tasks_generated[0]
        assert task['lang_code'] == "eng" and \
               task['source_file_path'] == "spam.jp2" and \
               task["output_file_name"] == "spam.txt"

    def test_create_new_task(self, workflow, monkeypatch):
        import os
        job_args = {
            "source_file_path": os.path.join("some", "path", "bacon.jp2"),
            "output_file_name": "bacon.txt",
            "lang_code": "eng",
            'destination_path':
                os.path.join(
                    "some",
                    "path",
                ),
        }
        task_builder = Mock()
        GenerateOCRFileTask = Mock()
        GenerateOCRFileTask.name = "GenerateOCRFileTask"
        monkeypatch.setattr(workflow_ocr, "GenerateOCRFileTask",
                            GenerateOCRFileTask)
        #
        options_backend = Mock(get=lambda key: {"Tesseract data file location": "/some/file/path"}.get(key))
        workflow.set_options_backend(options_backend)
        workflow.create_new_task(task_builder, job_args)
        assert task_builder.add_subtask.called is True
        GenerateOCRFileTask.assert_called_with(
            source_image=job_args['source_file_path'],
            out_text_file=os.path.join("some", "path", "bacon.txt"),
            lang="eng",
            tesseract_path=ANY
        )

    def test_generate_report(self, workflow, default_options):
        user_args = default_options.copy()
        results = [
            speedwagon.tasks.Result(workflow_ocr.GenerateOCRFileTask, {}),
            speedwagon.tasks.Result(workflow_ocr.GenerateOCRFileTask, {}),
        ]
        report = workflow.generate_report(results=results, user_args=user_args)
        assert "Completed generating OCR 2 files" in report

    @pytest.mark.parametrize("image_file_type,expected_file_extension", [
        ('JPEG 2000', '.jp2'),
        ('TIFF', '.tif'),
    ])
    def test_initial_task(self, monkeypatch, workflow, default_options,
                          image_file_type, expected_file_extension):

        user_args = default_options.copy()
        user_args['Image File Type'] = image_file_type
        task_builder = Mock()
        FindImagesTask = Mock()

        monkeypatch.setattr(
            workflow_ocr,
            "FindImagesTask",
            FindImagesTask
        )

        workflow.initial_task(task_builder, user_args)
        assert task_builder.add_subtask.called is True

        FindImagesTask.assert_called_with(
            ANY,
            file_extension=expected_file_extension
        )

    def test_get_available_languages(self, workflow, monkeypatch):
        path = "tessdir"

        def scandir(path):
            results = []
            m = Mock()
            m.name = "eng.traineddata"
            m.path = os.path.join(path, m.name)
            results.append(m)
            return results

        monkeypatch.setattr(workflow_ocr.os, "scandir", scandir)
        languages = list(workflow.get_available_languages(path))
        assert len(languages) == 1

    def test_get_available_languages_ignores_osd(self, workflow, monkeypatch):
        path = "tessdir"

        def scandir(path):
            results = []
            osd = Mock()
            osd.name = "osd.traineddata"
            osd.path = os.path.join(path, osd.name)
            results.append(osd)

            eng = Mock()
            eng.name = "eng.traineddata"
            eng.path = os.path.join(path, eng.name)
            results.append(eng)
            return results

        monkeypatch.setattr(workflow_ocr.os, "scandir", scandir)
        languages = list(workflow.get_available_languages(path))
        assert len(languages) == 1


class TestFindImagesTask:
    def test_work(self, monkeypatch):
        root = os.path.join("some", "directory")
        file_extension = ".jp2"
        task = workflow_ocr.FindImagesTask(
            root=root,
            file_extension=file_extension
        )

        def walk(path):
            return [
                ("12345", ('access'), ('sample.jp2', "sample.txt"))
            ]

        monkeypatch.setattr(workflow_ocr.os, "walk", walk)
        assert task.work() is True
        assert os.path.join("12345", "sample.jp2") in task.results and \
               os.path.join("12345", "sample.txt") not in task.results


class TestGenerateOCRFileTask:
    def test_work(self, monkeypatch):
        source_image = os.path.join("12345", "sample.jp2")
        out_text_file = os.path.join("12345", "sample.txt")
        lang = "eng"
        tesseract_path = "tesspath"
        workflow_ocr.GenerateOCRFileTask.set_tess_path = Mock()
        workflow_ocr.GenerateOCRFileTask.engine = Mock()
        task = workflow_ocr.GenerateOCRFileTask(
            source_image=source_image,
            out_text_file=out_text_file,
            lang=lang,
            tesseract_path=tesseract_path
        )
        m = mock_open()
        with patch('speedwagon_uiucprescon.workflow_ocr.open', m):
            assert task.work() is True
        assert m.called is True

    def test_read_image(self, monkeypatch):
        source_image = os.path.join("12345", "sample.jp2")
        out_text_file = os.path.join("12345", "sample.txt")
        lang = "eng"
        tesseract_path = "tesspath"
        workflow_ocr.GenerateOCRFileTask.set_tess_path = Mock()
        workflow_ocr.GenerateOCRFileTask.engine = Mock()

        reader = Mock()
        workflow_ocr.GenerateOCRFileTask.engine.get_reader = \
            lambda args: reader

        task = workflow_ocr.GenerateOCRFileTask(
            source_image=source_image,
            out_text_file=out_text_file,
            lang=lang,
            tesseract_path=tesseract_path
        )
        task.read_image(source_image, "eng")
        assert reader.read.called is True


@pytest.mark.parametrize(
    "task",
    [
        workflow_ocr.GenerateOCRFileTask(
            source_image="source_image",
            out_text_file="out_text_file",
            lang="lang",
            tesseract_path="tesseract_path"
        ),
        workflow_ocr.FindImagesTask(
            root="root",
            file_extension=".tif"
        )
    ]
)
def test_tasks_have_description(task):
    assert task.task_description() is not None
