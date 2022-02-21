import asyncio
from collections import OrderedDict, namedtuple
import logging
import os
from os.path import relpath
from typing import Text, Optional, Dict

from ruamel import yaml as yaml
from ruamel.yaml import RoundTripRepresenter

import rasa.shared.data
from rasa.shared.utils.io import write_yaml, read_yaml_file
from rasa.shared.nlu.training_data.formats.rasa_yaml import RasaYAMLWriter

from nlu_target_files.constants import DEFAULT_NLU_TARGET_FILE, NLU_DATA_PATH, TARGET_FILES_CONFIG_FILE
from nlu_target_files.training_data import load_sortable_nlu_data, get_training_data_for_keys

logger = logging.getLogger(__name__)

DEFAULT_ENCODING = "utf-8"

class OrderedDefaultDict(OrderedDict):
    """ A defaultdict with OrderedDict as its base class. """
    def __init__(self, default_factory=None, *args, **kwargs):
        if not (default_factory is None or callable(default_factory)):
            raise TypeError("first argument must be callable or None")
        super(OrderedDefaultDict, self).__init__(*args, **kwargs)
        self.default_factory = default_factory


    def __missing__(self, key):
        if self.default_factory is None:
            raise KeyError(
                key,
            )
        self[key] = value = self.default_factory()
        return value

    def __reduce__(self):
        args = (self.default_factory,) if self.default_factory else tuple()
        return self.__class__, args, None, None, iter(self.items())

    def __repr__(self):
        return "%s(%r, %r)" % (
            self.__class__.__name__,
            self.default_factory,
            self.items(),
        )

    @classmethod
    def add_yaml_representer(cls) -> None:
        yaml.add_representer(
            cls,
            RoundTripRepresenter.represent_dict,
            representer=RoundTripRepresenter,
        )

    def set_value_for_keys(self, keys=None, value=""):
        if not keys:
            keys = []
        for key in keys:
            self[key] = value

class TargetFilesConfig:
    def __init__(
        self,
        nlu_data_path: Text = NLU_DATA_PATH,
        default_intent_target_file: Text = DEFAULT_NLU_TARGET_FILE,
        default_synonym_target_file: Text = DEFAULT_NLU_TARGET_FILE,
        default_regex_target_file: Text = DEFAULT_NLU_TARGET_FILE,
        default_lookup_target_file: Text = DEFAULT_NLU_TARGET_FILE,
        intent_target_files: Optional[Dict[Text, Text]] = None,
        synonym_target_files: Optional[Dict[Text, Text]] = None,
        regex_target_files: Optional[Dict[Text, Text]] = None,
        lookup_target_files: Optional[Dict[Text, Text]] = None,
        config_filepath: Optional[Text] = TARGET_FILES_CONFIG_FILE
    ):
        self.config_filepath = config_filepath
        self.nlu_data_path = nlu_data_path
        self.default_intent_target_file = default_intent_target_file
        self.default_synonym_target_file = default_synonym_target_file
        self.default_regex_target_file = default_regex_target_file
        self.default_lookup_target_file = default_lookup_target_file

        self.intent_target_files = OrderedDefaultDict(lambda: self.default_intent_target_file)
        self.synonym_target_files = OrderedDefaultDict(lambda: self.default_synonym_target_file)
        self.regex_target_files = OrderedDefaultDict(lambda: self.default_regex_target_file)
        self.lookup_target_files = OrderedDefaultDict(lambda: self.default_lookup_target_file)

        self.intent_target_files.update(intent_target_files or {})
        self.synonym_target_files.update(synonym_target_files or {})
        self.regex_target_files.update(regex_target_files or {})
        self.lookup_target_files.update(lookup_target_files or {})

        self.ensure_relative_paths()
        self.sort()

    def ensure_relative_paths(self):
        """Ensure all target paths are relative so that enforcement makes sense across machines.
        """
        self.nlu_data_path = relpath(self.nlu_data_path)
        self.default_intent_target_file = relpath(self.default_intent_target_file)
        self.default_synonym_target_file = relpath(self.default_synonym_target_file)
        self.default_regex_target_file = relpath(self.default_regex_target_file)
        self.default_lookup_target_file = relpath(self.default_lookup_target_file)
        self.intent_target_files = {item: relpath(target) for item, target in self.intent_target_files.items()}
        self.synonym_target_files = {item: relpath(target) for item, target in self.synonym_target_files.items()}
        self.regex_target_files = {item: relpath(target) for item, target in self.regex_target_files.items()}
        self.lookup_target_files = {item: relpath(target) for item, target in self.lookup_target_files.items()}

    def sort(self):
        for section in [
            "intent_target_files",
            "synonym_target_files",
            "regex_target_files",
            "lookup_target_files",
        ]:
            section_to_update = getattr(self, section)
            current_order = {ix: item for item, ix in enumerate(section_to_update)}
            file_order = {
                ix: filename
                for filename, ix in enumerate(
                    list(dict.fromkeys([nlu_file for nlu_file in section_to_update.values()]))
                )
            }
            ordered = OrderedDefaultDict(str)
            ordered.update(sorted(
                    section_to_update.items(),
                    key=lambda x: (file_order.get(x[1]), current_order.get(x[0])),
                )
            )

            setattr(self, section, ordered)

    def as_dict(self):
        return {
                "nlu_data_path": self.nlu_data_path,
                "default_target_files": {
                    "intents": self.default_intent_target_file,
                    "synonyms": self.default_synonym_target_file,
                    "regexes": self.default_regex_target_file,
                    "lookups": self.default_lookup_target_file,
                },
                "target_files": {
                    "intents": OrderedDict(self.intent_target_files),
                    "synonyms": OrderedDict(self.synonym_target_files),
                    "regexes": OrderedDict(self.regex_target_files),
                    "lookups": OrderedDict(self.lookup_target_files),
                },
            }

    def as_inverted_dict(self):
        target_files = self.as_dict()["target_files"]
        filenames = set(
            [fname for section in target_files.values() for fname in section.values()]
        )
        keys_per_file = OrderedDefaultDict(lambda: OrderedDefaultDict(list))
        for filename in filenames:
            for section in target_files.keys():
                keys_per_file[filename][section] = [
                    key
                    for key, value in target_files[section].items()
                    if value == filename
                ]

        return keys_per_file

    def get_handled_keys(self):
        return {
            section: set(values.keys())
            for section, values in self.as_dict()["target_files"].items()
        }

    def write_target_config_to_file(self):
        write_yaml(self.as_dict(), self.config_filepath, True)

    def enforce_on_files(self, update_config_file=False):
        nlu_data = load_sortable_nlu_data(self.nlu_data_path)
        all_keys_in_data = nlu_data.get_all_keys_present()
        all_keys_in_nlu_target_files = self.get_handled_keys()
        new_keys = {
            key: set(all_keys_in_data[key]) - set(all_keys_in_nlu_target_files[key])
            for key in all_keys_in_data.keys()
        }

        target_keys_per_file = self.as_inverted_dict()

        for section, filename in self.as_dict()["default_target_files"].items():
            target_keys_per_file[filename][section].extend(new_keys[section])

        existing_nlu_files = set(
            rasa.shared.data.get_data_files(
                self.nlu_data_path, rasa.shared.data.is_nlu_file
            )
        )
        existing_and_new_nlu_files = existing_nlu_files.union(
            set(target_keys_per_file.keys())
        )

        writer = RasaYAMLWriter()
        for filename in existing_and_new_nlu_files:
            target_keys = target_keys_per_file.get(filename, [])
            if not target_keys and filename in existing_nlu_files:
                logger.warning(
                    f"No data found for file {filename}; deleting {filename}"
                )
                os.remove(filename)
                continue
            contents_per_file = get_training_data_for_keys(nlu_data, target_keys)
            logger.warning(f"Writing data to file {filename}")
            writer.dump(filename, contents_per_file)
        
        if update_config_file:
            self.write_target_config_to_file()

    @classmethod
    def from_dict(cls, nlu_target_files_dict):
        target_files = cls(
            nlu_target_files_dict.get("nlu_data_path"),
            nlu_target_files_dict.get("default_target_files",{}).get("intents"),
            nlu_target_files_dict.get("default_target_files",{}).get("synonyms"),
            nlu_target_files_dict.get("default_target_files",{}).get("regexes"),
            nlu_target_files_dict.get("default_target_files",{}).get("lookups"),
            nlu_target_files_dict.get("target_files",{}).get("intents",{}),
            nlu_target_files_dict.get("target_files",{}).get("synonyms",{}),
            nlu_target_files_dict.get("target_files",{}).get("regexes",{}),
            nlu_target_files_dict.get("target_files",{}).get("lookups",{}),
        )
        return target_files

    @classmethod
    def load_structure_from_file(cls, input_file):
        loaded_structure = read_yaml_file(input_file)
        target_files = cls.from_dict(loaded_structure)
        target_files.config_filepath = input_file
        return target_files

    @classmethod
    def infer_structure_from_files(
        cls,
        nlu_data_path: Text = NLU_DATA_PATH,
        default_intent_target_file: Text = DEFAULT_NLU_TARGET_FILE,
        default_synonym_target_file: Text = DEFAULT_NLU_TARGET_FILE,
        default_regex_target_file: Text = DEFAULT_NLU_TARGET_FILE,
        default_lookup_target_file: Text = DEFAULT_NLU_TARGET_FILE,
    ):
        intent_target_files = OrderedDefaultDict(lambda: default_intent_target_file)
        synonym_target_files = OrderedDefaultDict(lambda: default_synonym_target_file)
        regex_target_files = OrderedDefaultDict(lambda: default_regex_target_file)
        lookup_target_files = OrderedDefaultDict(lambda: default_lookup_target_file)

        nlu_files = rasa.shared.data.get_data_files(
            nlu_data_path, rasa.shared.data.is_nlu_file
        )

        for filepath in nlu_files:
            nlu_data = load_sortable_nlu_data(filepath)
            intent_target_files.set_value_for_keys(
                nlu_data.sorted_intents, filepath
            )
            synonym_target_files.set_value_for_keys(
                nlu_data.sorted_synonym_names, filepath
            )
            regex_target_files.set_value_for_keys(
                nlu_data.sorted_regex_names, filepath
            )
            lookup_target_files.set_value_for_keys(
                nlu_data.sorted_lookup_names, filepath
            )
        target_files = cls(
            nlu_data_path,
            default_intent_target_file,
            default_synonym_target_file,
            default_regex_target_file,
            default_lookup_target_file,
            intent_target_files,
            synonym_target_files,
            regex_target_files,
            lookup_target_files,

        )
        return target_files


def log_inference_warning(
    nlu_data_path,
    nlu_target_files_config,
):
    logger.warning(
        f"""
        Bootstrapping NLU target files config based on files in {nlu_data_path}.

        N.B. Manually review the the output in {nlu_target_files_config} before enforcing it!

        If an intent/synonym/etc. is found in multiple files, the last file it appears in will be taken as the target file.
        Because of how training data is loaded by Rasa, inference of target files can have unexpected results.
        E.g. synonyms in both the short (inline) and long formats have equal status in loaded training data. 
        This means a file can be found to contain a synonym even when it has no explicit "synonym:" section.
        """
    )


def log_enforcement_info(nlu_target_files_config, nlu_data_path):
    logger.warning(
        f"""
        Redistributing data in directory {nlu_data_path} into target files
        according to config in {nlu_target_files_config}
        """
    )

    logger.warning(
        "\n"
        f"Note that synonyms, regexes & lookups will be sorted alphabetically."
        "\nTherefore you may see a large diff the first time you run this command.\n"
    )


def infer_nlu_target_files(
    nlu_data_path, nlu_target_files_config, default_nlu_target_file
):
    log_inference_warning(nlu_data_path, nlu_target_files_config)
    target_files = TargetFilesConfig.infer_structure_from_files(
        nlu_data_path,
        default_nlu_target_file,
        default_nlu_target_file,
        default_nlu_target_file,
        default_nlu_target_file,
        config_filepath=nlu_target_files_config
    )
    target_files.write_target_config_to_file()


def enforce_nlu_target_files(nlu_target_files_config, update_config_file):
    nlu_target_files = TargetFilesConfig.load_structure_from_file(
        nlu_target_files_config
    )
    log_enforcement_info(nlu_target_files_config, nlu_target_files.nlu_data_path)
    nlu_target_files.enforce_on_files(update_config_file)
