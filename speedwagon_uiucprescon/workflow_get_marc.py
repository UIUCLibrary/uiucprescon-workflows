"""Generating MARC XML files by retrieving from a server."""
from __future__ import annotations
import abc
import functools
import os
import re
import typing
from copy import deepcopy

from typing import (
    List,
    Any,
    Optional,
    Union,
    Sequence,
    Dict,
    Tuple,
    Iterator,
    Mapping,
    TYPE_CHECKING,
    Callable,
    cast,
)


from xml.dom import minidom
import xml.etree.ElementTree as ET
import traceback
import sys
import requests

import speedwagon
from speedwagon.exceptions import (
    MissingConfiguration,
    SpeedwagonException,
    JobCancelled,
)
from speedwagon import reports, validators, workflow
from speedwagon_uiucprescon import conditions

if TYPE_CHECKING:
    if sys.version_info >= (3, 8):
        from typing import Final
    else:
        from typing_extensions import Final

    if sys.version_info >= (3, 11):
        from typing import Never
    else:
        from typing_extensions import Never

    from speedwagon.workflow import AbsOutputOptionDataType

__all__ = ["GenerateMarcXMLFilesWorkflow"]

MarcGeneratorTaskReport = typing.TypedDict(
    "MarcGeneratorTaskReport", {
        "success": bool,
        "identifier": str,
        "output": str,
    }
)


class BadNamingError(SpeedwagonException):
    """Bad file naming. Does not match expected value."""

    def __init__(self, msg: str, name: str, path: str, *args: Any) -> None:
        super().__init__(msg, *args)
        self.path = path
        self.name = name


# =========================== USER OPTIONS CONSTANTS ======================== #
OPTION_955_FIELD: Final[str] = "Add 955 field"
OPTION_035_FIELD: Final[str] = "Add 035 field"
OPTION_USER_INPUT: Final[str] = "Input"
IDENTIFIER_TYPE: Final[str] = "Identifier type"
# =========================================================================== #

MMSID_PATTERN = re.compile(
    r"^(?P<identifier>99[0-9]*(122)?05899)(_(?P<volume>[0-1]*))?"
)

BIBID_PATTERN = re.compile(r"^(?P<identifier>[0-9]*)")

MARC21_NAMESPACE = "http://www.loc.gov/MARC21/slim"


class RecordNotFound(SpeedwagonException):
    pass


DirectoryType = typing.TypedDict("DirectoryType", {"type": str, "value": str})

JobArgs = typing.TypedDict(
    "JobArgs", {
        "directory": DirectoryType,
        "api_server": str,
        "path": str,
        "enhancements": Dict[str, bool]
    }
)

UserArgs = typing.TypedDict(
    "UserArgs",
    {
        "Input": str,
        "Add 035 field": bool,
        "Add 955 field": bool,
        "Identifier type": str,
    },
)
GETMARC_SERVER_URL_CONFIG = "Getmarc server url"


class GenerateMarcXMLFilesWorkflow(speedwagon.Workflow[UserArgs]):
    """Generate Marc XML files.

    .. versionchanged:: 0.1.5
        No longer use http://quest.library.illinois.edu/GetMARC. Instead uses a
        getmarc api server that is configured with getmarc_server_url global
        setting.

        Identifier type is selected by the user

    .. versionadded:: 0.1.5
        Supports MMSID id type
        Supports adding 955 field
    """

    name = "Generate MARC.XML Files"
    description = (
        "For input, this tool takes a path to a directory of "
        "files, each of which is a digitized volume, and is named "
        "for that volume’s bibid. The program then retrieves "
        "MARC.XML files for these bibId's and writes them into "
        "the folder for each corresponding bibid or mmsid. It "
        "uses the GetMARC service to retrieve these MARC.XML "
        "files from the Library."
    )

    def job_options(self) -> List[
        AbsOutputOptionDataType[speedwagon.workflow.UserDataType]
    ]:
        """Request user options.

        User Options include:
            * Input - path directory containing files
            * Identifier type - ID type used in file name
            * Add 955 field - Add additional 955 field to metadata
            * Add 035 field - Add additional 035 field to metadata
        """
        user_input = workflow.DirectorySelect(OPTION_USER_INPUT)
        user_input.add_validation(validators.ExistsOnFileSystem())
        user_input.add_validation(
            validators.IsDirectory(),
            condition=conditions.candidate_exists
        )

        id_type_option = workflow.ChoiceSelection(IDENTIFIER_TYPE)
        id_type_option.placeholder_text = "Select an ID Type"
        for id_type in SUPPORTED_IDENTIFIERS:
            id_type_option.add_selection(id_type)

        id_type_option.add_validation(
            validators.CustomValidation[str](
                query=(
                    lambda candidate, job_options: (
                        candidate in SUPPORTED_IDENTIFIERS
                    )
                ),
                failure_message_function=(
                    lambda candidate: f"Unknown Identifier type, {candidate}"
                )
            ),
        )

        add_field_955 = workflow.BooleanSelect(OPTION_955_FIELD)
        add_field_955.value = True

        add_field_035 = workflow.BooleanSelect(OPTION_035_FIELD)

        add_field_035.add_validation(
            validators.CustomValidation[bool](
                query=(
                    lambda candidate, job_options: (
                        True if candidate is False else
                        job_options[OPTION_955_FIELD] is True
                    )
                ),
                failure_message_function=(
                    lambda *_: 'Add 035 field requires Add 955 field'
                )

            )
        )
        add_field_035.value = True

        return [user_input, id_type_option, add_field_955, add_field_035]

    @classmethod
    def filter_bib_id_folders(cls, item: os.DirEntry[str]) -> bool:
        """Filter only folders with bibids.

        Args:
            item: Directory path candidate

        Returns:
            True is the item is a folder with a bibid, else returns false

        """
        if not item.is_dir():
            return False

        if "v" not in item.name:
            if item.name.startswith("0"):
                raise BadNamingError(
                    f"Directory naming is an invalid format. "
                    f"Contains leading zero: {item.name}",
                    name=item.name,
                    path=item.path
                )
            try:
                if not isinstance(eval(item.name), int):
                    return False
            except NameError as error:
                raise BadNamingError(
                    f"Directory naming is an invalid format. {item.name}",
                    name=item.name,
                    path=item.path
                ) from error
        return True

    def get_marc_server(self) -> Optional[str]:
        """Get the server url from the configuration."""
        return typing.cast(
            Optional[str],
            self.get_workflow_configuration_value(GETMARC_SERVER_URL_CONFIG),
        )

    def discover_task_metadata(
        self,
        initial_results: Sequence[  # pylint: disable=unused-argument
            speedwagon.tasks.Result[Never]
        ],
        additional_data: Mapping[str, Never],  # pylint: disable=W0613
        user_args: UserArgs
    ) -> List[JobArgs]:
        """Create a list of metadata that the jobs will need in order to work.

        Args:
            initial_results: Not used here
            additional_data: Not used here
            **user_args:  User defined settings.

        Returns:
            list of dictionaries of job metadata

        """
        server_url = self.get_marc_server()
        if server_url is None:
            raise MissingConfiguration(
                workflow=self.name,
                key=GETMARC_SERVER_URL_CONFIG
            )

        search_path = user_args["Input"]
        try:
            jobs: List[JobArgs] = [
                {
                    "directory": {
                        "value": folder.name,
                        "type": user_args["Identifier type"],
                    },
                    "enhancements": {
                        "955": user_args.get("Add 955 field", False),
                        "035": user_args.get("Add 035 field", False),
                    },
                    "api_server": server_url,
                    "path": folder.path,
                }
                for folder in filter(
                    self.filter_bib_id_folders, os.scandir(search_path)
                )
            ]
        except BadNamingError as error:
            raise JobCancelled(
                f"Unable to locate marc record due to invalid naming "
                f"convention. {error.path}"
            ) from error
        if not jobs:
            raise JobCancelled(
                f"No directories containing packages located inside "
                f"of {search_path}"
            )
        return jobs

    def create_new_task(
        self,
        task_builder: "speedwagon.tasks.TaskBuilder",
        job_args: Union[str, Dict[str, Union[str, bool]]],
    ) -> None:
        """Create the task to be run.

        Args:
            task_builder: task builder
            **job_args: single item info determined by discover_task_metadata

        """
        _job_args = cast(JobArgs, job_args)
        if "directory" not in _job_args.keys():
            raise KeyError("Missing directory")
        directory = _job_args.get("directory", {})
        if not isinstance(directory, dict):
            raise TypeError()
        identifier_type = str(directory["type"])
        subdirectory = str(directory["value"])
        identifier, _ = self._get_identifier_volume(_job_args)

        folder = str(_job_args["path"])
        marc_file = os.path.join(folder, "MARC.XML")
        task_builder.add_subtask(
            MarcGeneratorTask(
                identifier=identifier,
                identifier_type=identifier_type,
                output_name=marc_file,
                server_url=str(_job_args["api_server"]),
            )
        )
        enhancements = _job_args.get("enhancements", {})
        if not isinstance(enhancements, dict):
            raise TypeError()

        add_955 = enhancements.get("955", False)
        if add_955:
            task_builder.add_subtask(
                MarcEnhancement955Task(
                    added_value=subdirectory, xml_file=marc_file
                )
            )
        add_035 = enhancements.get("035")
        if add_035:
            task_builder.add_subtask(
                MarcEnhancement035Task(xml_file=marc_file)
            )

    @classmethod
    @reports.add_report_borders
    def generate_report(
        cls,
        results: List[speedwagon.tasks.Result[MarcGeneratorTaskReport]],
        user_args: UserArgs  # pylint: disable=unused-argument
    ) -> Optional[str]:
        """Generate a simple home-readable report from the job results.

        Args:
            results: results of completed tasks
            **user_args: user defined settings

        Returns:
            str: optional report as a string

        """
        all_results = [i.data for i in results]
        failed = [
            result for result in all_results if result["success"] is not True
        ]

        if not failed:
            return (
                f"Success! [{len(all_results)}] MARC.XML files were "
                f"retrieved and written to their named folders"
            )

        status = (
            f"Warning! [{len(failed)}] packages experienced errors "
            f"retrieving MARC.XML files:"
        )

        failed_list = "\n".join(
            f"  * {i['identifier']}. Reason: {i['output']}" for i in failed
        )

        return f"{status}\n \n{failed_list}"

    @staticmethod
    def _get_identifier_volume(
        job_args: JobArgs,
    ) -> Tuple[str, Union[str, None]]:
        directory = job_args["directory"]
        subdirectory = directory["value"]
        regex_patterns: Dict[str, re.Pattern[str]] = {
            "MMS ID": MMSID_PATTERN,
            "Bibid": BIBID_PATTERN,
        }
        regex_pattern = regex_patterns.get(directory["type"])
        if regex_pattern is None:
            raise SpeedwagonException(
                f"No identifier pattern for {directory['type']}"
            )
        match = regex_pattern.match(subdirectory)
        if match is None:
            raise SpeedwagonException(
                f"Directory does not match expected format for "
                f"{directory['type']}: {subdirectory}"
            )
        results = match.groupdict()
        return results["identifier"], results.get("volume")

    def workflow_options(self) -> List[AbsOutputOptionDataType[str]]:
        """Set the settings for get marc workflow.

        This needs the getmarc server url.
        """
        return [
            speedwagon.workflow.TextLineEditData(
                "Getmarc server url", required=True
            ),
        ]


class AbsMarcFileStrategy(abc.ABC):
    """Base class for retrieving MARC records from a server."""

    def __init__(self, server_url: str) -> None:
        """Use as the base class for retrieving MARC records from a server.

        Args:
            server_url: url to server

        """
        self.url = server_url

    @abc.abstractmethod
    def get_record(self, ident: str) -> str:
        """Retrieve a record type.

        Args:
            ident: Identifier uses for the record

        Returns:
            str: Record requested as a string

        """

    @staticmethod
    def download_record(url: str) -> str:
        """Download a marc record from the url."""
        record = requests.get(url)
        record.raise_for_status()
        return record.text


class GetMarcBibId(AbsMarcFileStrategy):
    """Retrieve an record based on bibid."""

    def get_record(self, ident: str) -> str:
        """Retrieve an record based on bibid.

        Args:
            ident: bibid

        Returns:
            str: Record requested as a string

        """
        try:
            return self.download_record(
                f"{self.url}/api/record?bib_id={ident}"
            )
        except requests.exceptions.HTTPError as error:
            raise RecordNotFound(
                f"Unable to retrieve record with bib_id: {ident}"
            ) from error


class GetMarcMMSID(AbsMarcFileStrategy):
    """Retrieve a record based on MMSID."""

    def get_record(self, ident: str) -> str:
        """Retrieve a record based on MMSID.

        Args:
            ident: MMSID

        Returns:
            str: Record requested as a string

        """
        try:
            return self.download_record(
                f"{self.url}/api/record?mms_id={ident}"
            )
        except requests.exceptions.HTTPError as error:
            raise RecordNotFound(
                f"Unable to retrieve record with mms_id: {ident}"
            ) from error


def strip_volume(full_bib_id: str) -> int:
    # Only pull the base bib id
    volume_regex = re.compile("^[0-9]{7}(?=((v[0-9]*)((i[0-9])?)?)?$)")
    result = volume_regex.match(full_bib_id)
    if not result:
        raise ValueError(f"{full_bib_id} is not a valid bib_id")
    return int(result.group(0))


SUPPORTED_IDENTIFIERS = {"MMS ID": GetMarcMMSID, "Bibid": GetMarcBibId}


class MarcGeneratorTask(speedwagon.tasks.Subtask[MarcGeneratorTaskReport]):
    """Task for generating the MARC xml file."""

    name = "Generate MARC File"

    def __init__(
        self,
        identifier: str,
        identifier_type: str,
        output_name: str,
        server_url: str,
    ) -> None:
        """Task for retrieving the data from the server and saving as a file.

        Args:
            identifier: id of the record
            identifier_type: type of identifier used
            output_name: file name to save the data to
            server_url: getmarc server url
        """
        super().__init__()
        self._identifier = identifier
        self._identifier_type = identifier_type
        self._output_name = output_name
        self._server_url = server_url

    def task_description(self) -> Optional[str]:
        return f"Retrieving MARC record for {self._identifier}"

    @property
    def identifier_type(self) -> str:
        """Type of identifier.

        Such as MMS ID or BIBID
        """
        return self._identifier_type

    @property
    def identifier(self) -> str:
        """Record id."""
        return self._identifier

    @staticmethod
    def reflow_xml(data: str) -> str:
        """Redraw the xml data to make it more human readable.

        This includes adding newline characters

        Args:
            data: xml data as a string

        Returns:
            str: Reformatted xml data.

        """
        return minidom.parseString(data).toprettyxml()

    def work(self) -> bool:
        """Run the task.

        Returns:
            bool: True on success, False otherwise.

        Notes:
            Connection errors to the getmarc server will throw a
                SpeedwagonException.
        """
        strategy = SUPPORTED_IDENTIFIERS[self._identifier_type](
            self._server_url
        )
        try:
            self.log(f"Accessing MARC record for {self._identifier}")
            record = strategy.get_record(self._identifier)
            pretty_xml = self.reflow_xml(record)
            self.write_file(data=pretty_xml)

            self.log(f"Wrote file {self._output_name}")
            self.set_results(
                {
                    "success": True,
                    "identifier": self._identifier,
                    "output": self._output_name,
                }
            )
            return True
        except UnicodeError as error:
            raise SpeedwagonException(
                f"Error with {self._identifier}"
            ) from error
        except RecordNotFound as record_error:
            raise JobCancelled(
                f"Unable to locate record with identifier: {self._identifier}."
                " Make the identifier is valid and the identifier type is "
                "correct.",
            ) from record_error
        except (requests.ConnectionError, requests.HTTPError) as exception:
            self.set_results(
                {
                    "success": False,
                    "identifier": self._identifier,
                    "output": str(exception),
                }
            )
            raise SpeedwagonException(
                "Trouble connecting to server getmarc"
            ) from exception

    def write_file(self, data: str) -> None:
        """Write the data to a file.

        Args:
            data: Raw string data to save

        """
        try:
            with open(self._output_name, "w", encoding="utf-8") as write_file:
                write_file.write(data)
        except UnicodeError as error:
            traceback.print_exc(file=sys.stderr)
            raise SpeedwagonException from error


class EnhancementTask(speedwagon.tasks.Subtask[None]):
    """Base class for enhancing xml file."""

    def __init__(self, xml_file: str) -> None:
        """Create a new Enchancement object for processing the xml file.

        Args:
            xml_file: Path to an XML file to process.

        """
        super().__init__()
        self.xml_file = xml_file

    def work(self) -> bool:
        raise NotImplementedError()

    def task_description(self) -> Optional[str]:
        return f"Enhancing {self.xml_file}"

    @staticmethod
    def to_pretty_string(root: ET.Element) -> str:
        """Convert lxml Element into a pretty formatted string."""
        ET.register_namespace("", MARC21_NAMESPACE)
        flat_xml_string = "\n".join(
            line.strip()
            for line in ET.tostring(root, encoding="unicode").split("\n")
        ).replace("\n", "")
        return str(minidom.parseString(flat_xml_string).toprettyxml())

    @staticmethod
    def redraw_tree(
        tree: ET.ElementTree, *new_datafields: ET.Element
    ) -> ET.Element:
        """Redraw the tree so that everything is in order."""
        root = tree.getroot()
        namespaces = {"marc": MARC21_NAMESPACE}
        fields = list(new_datafields)
        for datafield in tree.findall(".//marc:datafield", namespaces):
            fields.append(datafield)
            root.remove(datafield)
        for field in sorted(fields, key=lambda x: int(x.attrib["tag"])):
            root.append(field)
        return root


_T = typing.TypeVar("_T")
# pylint: disable=typevar-name-incorrect-variance
# pylint: disable=invalid-name
_T_EnhancementTask = typing.TypeVar(
    "_T_EnhancementTask", contravariant=True, bound=EnhancementTask
)
# pylint: enable=typevar-name-incorrect-variance
# pylint: enable=invalid-name


def provide_info(
    func: Callable[[_T_EnhancementTask], _T]
) -> Callable[[_T_EnhancementTask], _T]:
    @functools.wraps(func)
    def wrapped(task: _T_EnhancementTask) -> _T:
        try:
            return func(task)
        except Exception as error:
            raise SpeedwagonException(
                f"Problem enhancing {task.xml_file}"
            ) from error

    return wrapped


class MarcEnhancement035Task(EnhancementTask):
    """Enhancement for Marc xml by adding a 035 field."""

    namespaces = {"marc": MARC21_NAMESPACE}

    @classmethod
    def find_959_field_with_uiudb(
        cls, tree: ET.ElementTree
    ) -> Iterator[ET.Element]:
        """Locate any 959 fields containing the text UIUdb.

        Args:
            tree: Root element of record

        Yields:
            Yields subelements if found.

        """
        for datafield in tree.findall(
            ".//marc:datafield/[@tag='959']", cls.namespaces
        ):
            for subfield in datafield:
                if subfield.text is not None and "UIUdb" in subfield.text:
                    yield subfield

    @classmethod
    def has_959_field_with_uiudb(cls, tree: ET.ElementTree) -> bool:
        """Check if tree contains an 955 element with UIUdb.

        Args:
            tree: Root element of record

        Returns:
            Returns True is found one, False if none have been found.

        """
        try:
            next(cls.find_959_field_with_uiudb(tree))
        except StopIteration:
            return False
        return True

    @staticmethod
    def new_035_field(data: ET.Element) -> ET.Element:
        """Create a new 035 Element based on the data element.

        Args:
            data: subfield of a 959 element

        Returns:
            Returns a New 035 Element.

        """
        new_datafield = ET.Element(
            "{http://www.loc.gov/MARC21/slim}datafield",
            attrib={"tag": "035", "ind1": " ", "ind2": " "},
        )
        new_subfield = deepcopy(data)
        if new_subfield.text is not None:
            new_subfield.text = new_subfield.text.replace(
                "(UIUdb)", "(UIU)Voyager"
            )

        new_datafield.append(new_subfield)
        return new_datafield

    @provide_info
    def work(self) -> bool:
        """Add 035 field to the file.

        if there is a 959 field, check if there is a subfield that contains
            "UIUdb".
        if not, ignore and move on.
        If there is, add a new 035 field with the same value as that 959 field
            but replace  (UIUdb) with "(UIU)Voyager"

        Returns:
            Returns True on success else returns False

        """
        tree = ET.parse(self.xml_file)
        uiudb_subfields = list(self.find_959_field_with_uiudb(tree))

        if uiudb_subfields:
            root = self.redraw_tree(
                tree, self.new_035_field(uiudb_subfields[0])
            )

            with open(self.xml_file, "w", encoding="utf-8") as write_file:
                write_file.write(self.to_pretty_string(root))

        return True


class MarcEnhancement955Task(EnhancementTask):
    """Enhancement for Marc xml by adding a 955 field."""

    def __init__(self, added_value: str, xml_file: str) -> None:
        """Create a new EnhancementTask object.

        Args:
            added_value: The value added to the 955 field
            xml_file: File applied to.
        """
        super().__init__(xml_file)
        self.added_value = added_value

    @provide_info
    def work(self) -> bool:
        """Perform the enhancement.

        Returns:
            Returns True on success, False on failure

        """
        tree = ET.parse(self.xml_file)
        root = self.enhance_tree_with_955(tree)
        with open(self.xml_file, "w", encoding="utf-8") as write_file:
            write_file.write(self.to_pretty_string(root))

        return True

    def enhance_tree_with_955(self, tree: ET.ElementTree) -> ET.Element:
        """Enhance the current tree by adding a new 955 field,.

        Args:
            tree:
                XML tree

        Returns:
            Returns a new Element with the 955 field added.

        """
        new_datafield = self.create_new_955_element(self.added_value)

        return self.redraw_tree(tree, new_datafield)

    @staticmethod
    def create_new_955_element(added_value: str) -> ET.Element:
        """Create aa new 955 element.

        Args:
            added_value:
                Text to be added to the 955 subfield

        Returns:
            Returns a new 955 Elements

        """
        new_datafield = ET.Element(
            "{http://www.loc.gov/MARC21/slim}datafield",
            attrib={"tag": "955", "ind1": " ", "ind2": " "},
        )
        new_subfield = ET.Element(
            "{http://www.loc.gov/MARC21/slim}subfield",
            attrib={"code": "b"},
        )
        new_subfield.text = added_value
        new_datafield.append(new_subfield)
        return new_datafield
