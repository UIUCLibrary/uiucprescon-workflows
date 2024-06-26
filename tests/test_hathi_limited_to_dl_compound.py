import os
from unittest.mock import Mock
from zipfile import ZipFile
from speedwagon.utils import assign_values_to_job_options, validate_user_input
from speedwagon import validators
import pytest
from uiucprescon import packager
from uiucprescon.packager.packages.collection import Package
from speedwagon_uiucprescon.workflow_hathi_limited_to_dl_compound import \
    HathiLimitedToDLWorkflow, PackageConverter


@pytest.fixture(scope="module")
def hathi_limited_view_package_dirs(tmpdir_factory):
    test_dir = tmpdir_factory.mktemp("hathi_limited", numbered=True)
    sample_package_names = {
        "uiuc.40": [
            (
                "40.mets.xml",
                (
                    "40",
                    [
                        "40.mets.xml"
                    ] +
                    [f"{str(a).zfill(7)}.txt" for a in range(282)] +
                    [f"{str(a).zfill(7)}.jp2" for a in range(282)] +
                    [f"{str(a).zfill(7)}.xml" for a in range(282)]
                )
            )
        ],
        "uiuc.40834v1": [
            (
                "40834v1.mets.xml",
                (
                    "40834v1",
                    [
                        "40834v1.mets.xml"
                    ] +
                    [f"{str(a).zfill(7)}.txt" for a in range(256)] +
                    [f"{str(a).zfill(7)}.tif" for a in range(256)] +
                    [f"{str(a).zfill(7)}.xml" for a in range(256)]
                )
            )
        ],
        "uiuc.5285248v1924": [
            (
                "5285248v1924.mets.xml",
                (
                    "5285248v1924",
                    [
                        "5285248v1924.mets.xml"
                    ] +
                    [f"{str(a).zfill(7)}.txt" for a in range(282)] +
                    [f"{str(a).zfill(7)}.jp2" for a in range(282)] +
                    [f"{str(a).zfill(7)}.xml" for a in range(282)]
                )
            )
        ]
    }

    # eg: 5285248v1924/
    for pkg_name, pkg_data in sample_package_names.items():
        pkg_dir = test_dir.mkdir(pkg_name)

        tmp_dir = test_dir.mkdir(f"build_dir-{pkg_name}")
        for mets_file_filename, archive_data in pkg_data:
            # Add any files to the package
            pkg_dir.join(mets_file_filename).write("")
            bib_id, zip_content = archive_data

            # eg: 5285248v1924/5285248v1924.zip
            with ZipFile(pkg_dir.join(f"{bib_id}.zip"), 'w') as myzip:
                build_package_dir = tmp_dir.mkdir(bib_id)
                for zipped_file in zip_content:
                    generated_file = build_package_dir.join(zipped_file)
                    generated_file.write("")

                    arcname = os.path.join(bib_id, zipped_file)
                    myzip.write(generated_file, arcname=arcname)

    return test_dir


def test_output_input_same_is_invalid(monkeypatch):
    workflow = HathiLimitedToDLWorkflow()
    user_args = {
        "Input": "/some/path",
        "Output": "/some/path"
    }
    path_exists = Mock(return_value=True)
    monkeypatch.setattr(
        validators.ExistsOnFileSystem,
        "path_exists",
        path_exists
    )
    findings = validate_user_input(
        {
            value.setting_name or value.label: value
            for value in assign_values_to_job_options(
                workflow.job_options(),
                **user_args
            )
        }
    )
    path_exists.assert_called_with("/some/path")
    assert findings["Output"] == ["Input cannot be the same as Output"]


def test_finding_if_output_not_exist(monkeypatch):
    user_args = {
        "Input": "some/other/folder",
        "Output": "./invalid_folder/"
    }
    monkeypatch.setattr(
        validators.ExistsOnFileSystem,
        "path_exists",
        lambda *_: False
    )
    workflow = HathiLimitedToDLWorkflow()
    findings = validate_user_input(
        {
            value.setting_name or value.label: value
            for value in assign_values_to_job_options(
                workflow.job_options(),
                **user_args
            )
        }
    )
    assert findings["Output"] == ["Output does not exist"]


def test_finding_if_input_not_exist(monkeypatch):
    path_exists = Mock(return_value=False)
    user_args = {
        "Input": "some/other/folder",
        "Output": "./invalid_folder/"
    }
    monkeypatch.setattr(
        validators.ExistsOnFileSystem,
        "path_exists",
        path_exists
    )
    workflow = HathiLimitedToDLWorkflow()
    findings = validate_user_input(
        {
            value.setting_name or value.label: value
            for value in assign_values_to_job_options(
                workflow.job_options(),
                **user_args
            )
        }
    )
    assert findings["Input"] == ["Input does not exist"]

class TestPackageConverter:
    def test_transform_is_called(self):
        source = Package("some_source")
        task = PackageConverter(source, "out")
        task.output_packager.transform = Mock()
        task.work()
        task.output_packager.transform.assert_called_with(source, "out")


options = [
    (0, "Input"),
    (1, "Output")
]


@pytest.mark.parametrize("index,label", options)
def test_hathi_limited_to_dl_compound_has_options(index, label):
    workflow = HathiLimitedToDLWorkflow()
    user_options = workflow.job_options()
    assert len(user_options) > 0
    assert user_options[index].label == label


class TestHathiLimitedToDLWorkflow:
    def test_report(self):
        results = [
            Mock(),
            Mock(),
        ]
        report = HathiLimitedToDLWorkflow.generate_report(
            results=results,
            user_args={"Output": "dummy"}
        )
        assert "All done. Converted 2 packages." in report

    def test_create_new_task(self):
        workflow = HathiLimitedToDLWorkflow()
        task_builder = Mock()
        args = {
            "package": Mock(),
            "destination": Mock()
        }
        workflow.create_new_task(task_builder, args)
        assert task_builder.add_subtask.called is True

    def test_discover_task_metadata(self, monkeypatch):
        workflow = HathiLimitedToDLWorkflow()
        user_args = {
            "Input": "source",
            "Output": "dest"
        }

        def locate_packages(_, path):
            return [
                Mock()
            ]
        monkeypatch.setattr(
            packager.packages.HathiLimitedView,
            "locate_packages", locate_packages
        )
        task_metadata = workflow.discover_task_metadata(
            initial_results=[],
            additional_data=[],
            user_args=user_args
        )
        assert task_metadata[0]["destination"] == user_args['Output'] and \
               'package' in task_metadata[0]
