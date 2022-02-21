import asyncio
from collections import OrderedDict
import logging

from ruamel import yaml as yaml

from rasa.shared.importers.rasa import RasaFileImporter
import rasa.shared.data
import rasa.shared.utils.io
from rasa.shared.nlu.training_data.training_data import TrainingData

logger = logging.getLogger(__name__)

class SortableTrainingData(TrainingData):
    def get_intent_order(self):
        intent_order = list(
            dict.fromkeys([ex.data["intent"] for ex in self.training_examples])
        )
        return intent_order

    def sort_synonyms(self):
        self.entity_synonyms = OrderedDict(
            sorted(
                [(synonym, value) for synonym, value in self.entity_synonyms.items()],
                key=lambda x: (x[1], x[0]),
            )
        )
        self.sorted_synonym_names = sorted(list(set(self.entity_synonyms.values())))

    def sort_regex_names(self):
        self.sorted_regex_names = sorted(
            list(
                set(
                    [regex_feature.get("name") for regex_feature in self.regex_features]
                )
            )
        )

    def sort_lookup_values(self):
        self.lookup_tables = sorted(
            [
                {"name": lookup["name"], "elements": sorted(lookup["elements"])}
                for lookup in self.lookup_tables
            ],
            key=lambda x: x["name"],
        )
        self.sorted_lookup_names = sorted(
            list(set([lookup.get("name") for lookup in self.lookup_tables]))
        )

    def get_examples_per_intent(self, intent_list):
        examples_per_intent = {
            intent: [ex for ex in self.training_examples if ex.data["intent"] == intent]
            for intent in intent_list
        }
        return examples_per_intent

    def sort_intent_examples(self):
        self.sorted_intents = self.get_intent_order()
        examples_per_intent = self.get_examples_per_intent(self.sorted_intents)
        sorted_examples = [
            ex
            for intent in self.sorted_intents
            for ex in examples_per_intent.get(intent, [])
        ]
        self.training_examples = sorted_examples

    def sort_data(self):
        self.sort_synonyms()
        self.sort_regex_names()
        self.sort_lookup_values()
        self.sort_intent_examples()

    def get_all_keys_present(self):
        return {
            "intents": self.sorted_intents,
            "synonyms": self.sorted_synonym_names,
            "regexes": self.sorted_regex_names,
            "lookups": self.sorted_lookup_names,
        }


def load_sortable_nlu_data(nlu_data_path):
    nlu_files = rasa.shared.data.get_data_files(
        [nlu_data_path], rasa.shared.data.is_nlu_file
    )
    training_data_importer = RasaFileImporter(training_data_paths=nlu_files)
    loop = asyncio.get_event_loop()
    nlu_data = loop.run_until_complete(training_data_importer.get_nlu_data())
    nlu_data.__class__ = SortableTrainingData
    nlu_data.sort_data()
    return nlu_data


def get_training_data_for_keys(nlu_data, included_keys):
    training_data_for_keys = TrainingData()
    training_data_for_keys.training_examples = [
        ex
        for ex in nlu_data.training_examples
        if ex.data.get("intent") in included_keys["intents"]
    ]
    training_data_for_keys.entity_synonyms = OrderedDict(
        {
            syn_value: syn_name
            for syn_value, syn_name in nlu_data.entity_synonyms.items()
            if syn_name in included_keys["synonyms"]
        }
    )
    training_data_for_keys.regex_features = [
        reg
        for reg in nlu_data.regex_features
        if reg.get("name") in included_keys["regexes"]
    ]
    training_data_for_keys.lookup_tables = [
        lookup
        for lookup in nlu_data.lookup_tables
        if lookup.get("name") in included_keys["lookups"]
    ]
    return training_data_for_keys
