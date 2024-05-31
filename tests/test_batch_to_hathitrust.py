import warnings
from unittest.mock import Mock

import pytest
import shutil

from speedwagon_uiucprescon import workflow_hathi_limited_to_dl_compound
from speedwagon_uiucprescon import tasks
import os


@pytest.mark.parametrize("index,label", [
    (0, "Input"),
    (1, "Output"),
])
def test_hathi_limited_to_dl_compound_has_options(index, label):
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        workflow = \
            workflow_hathi_limited_to_dl_compound.HathiLimitedToDLWorkflow()

    user_options = workflow.job_options()
    assert len(user_options) > 0
    assert user_options[index].label == label


def test_generate_checksum_calls_prep_checksum_task(monkeypatch):
    mmsid = "99423682912205899"
    dummy_file = '99423682912205899_0001.tif'
    working_dir = "./sample_path"
    task = tasks.GenerateChecksumTask(mmsid, dummy_file)
    task.log = Mock()
    task.subtask_working_dir = working_dir

    move_mock = Mock()
    mock_create_checksum_report = Mock()
    from pyhathiprep import package_creater
    with monkeypatch.context() as mp:

        mp.setattr(
            package_creater.InplacePackage,
            "create_checksum_report",
            mock_create_checksum_report

        )
        mp.setattr(os.path, "exists", lambda _: True)
        mp.setattr(shutil, "move", move_mock)
        task.work()
    assert mock_create_checksum_report.call_args[0][0] == working_dir


def test_yaml_task(monkeypatch):
    mmsid = "99423682912205899"
    title_page = '99423682912205899_0001.tif'
    source_directory = "./sample_path"
    working_dir = "./sample_working_path"

    task = \
        tasks.MakeMetaYamlTask(
            mmsid,
            source=source_directory,
            title_page=title_page
        )

    task.log = Mock()
    task.subtask_working_dir = working_dir
    from pyhathiprep import package_creater
    mock_make_yaml = Mock()
    with monkeypatch.context() as mp:
        mp.setattr(
            os.path,
            "exists",
            lambda path:
                path in [working_dir, source_directory] or
                path.endswith(".yml")
        )
        mp.setattr(package_creater.InplacePackage, "make_yaml",
                   mock_make_yaml)
        mp.setattr(shutil, "move", Mock())
        task.work()

    assert mock_make_yaml.called is True


