import pytest
from speedwagon_uiucprescon import active_workflows


@pytest.mark.parametrize(
    "expected_workflow",
    [
        "Generate MARC.XML Files",
        "Convert CaptureOne TIFF to Digital Library Compound Object and "
        "HathiTrust",
        "Verify HathiTrust Package Completeness",
        "Convert CaptureOne Preservation TIFF to Digital Library Access JP2",
        "Convert HathiTrust limited view to Digital library",
        "Hathi Prep",
        "Make Checksum Batch [Single]",
        "Make Checksum Batch [Multiple]",
        "Make JP2",
        "Medusa Preingest Curation",
        "Generate OCR Files",
        "Validate Tiff Image Metadata for HathiTrust",
        "Verify Checksum Batch [Multiple]",
        "Verify Checksum Batch [Single]",
        "Zip Packages"
    ]
)
def test_registered_workflows(expected_workflow):
    assert expected_workflow in active_workflows.registered_workflows()