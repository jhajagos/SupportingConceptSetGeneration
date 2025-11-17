import io
import csv
import json
import datetime


def json_datetime_serializer(obj):
    if isinstance(obj, datetime.datetime):
        return obj.isoformat()
    raise TypeError(f"Object of type {obj.__class__.__name__} is not JSON serializable")



class CodedConceptMappings(object):
    def __init__(self, coded_concept_map_list):

        self.concept_coded_map_list = coded_concept_map_list
        self.map_dict = {}
        for coded_concept_map in coded_concept_map_list:
            self.map_dict[coded_concept_map.coded_conept.key()] = coded_concept_map.coded_concept_tuple

class CodedConceptTuple(object):
    def __init__(self, code_or_code_list):

        if type(code_or_code_list) in (list, tuple):
            self.multiple = True
        else:
            self.multiple = False

        if not self.multiple:
            self.tuple = (code_or_code_list,)
        elif type(code_or_code_list) == tuple:
            self.tuple = code_or_code_list
        elif type(code_or_code_list) == list:
            self.tuple = tuple(code_or_code_list)
        else:
            raise ValueError("Input must either be a single code a list or tuple")

    def get(self):
        if self.multiple:
            return self.tuple
        else:
            return self.tuple[0]


class CodedConceptMap(object):
    def __init__(self, coded_concept, coded_concept_tuple):
        self.coded_concept = coded_concept
        self.mapped_tuple = coded_concept_tuple


class CodedConcept(object):
    def __init__(self, code, vocabulary, description, metadata=None):
        self.code = code
        self.description = description
        self.vocabulary = vocabulary

        if metadata is None:
            self.metadata = {}
        else:
            self.metadata = metadata

    def key(self):
        return self.code + "|" + self.vocabulary

    def __repr__(self):
        return f"{self.code} - {self.description} ({self.vocabulary})"

    def to_struct(self):
        return {"code": self.code, "description": self.description, "vocabulary": self.vocabulary, "metadata": self.metadata}


class CodedConceptSetChange(object):
    def __init__(self, added_codes_list, removed_codes_list, change_name, change_type,  changed_by=None, change_type_dict=None):
        self.added_codes = added_codes_list
        self.removed_codes = removed_codes_list

        self.name = change_name
        self.previous_name = None

        self.change_type = change_type

        self.registration_utc_datetime = None
        self.changed_by = changed_by

        if change_type_dict is None: # Holds human or machine created labels why a specific change was made
            change_type_dict = {}
        self.change_type_dict = change_type_dict

    def __repr__(self):
        return str((self.added_codes, self.removed_codes, self.change_type, self.registration_utc_datetime))

    def to_struct(self):
        change_struct = {
            "added_code_list": [x.to_struct() for x in self.added_codes],
            "removed_code_list": [x.to_struct() for x in self.removed_codes],
            "name": self.name,
            "previous_name": self.previous_name,
            "change_type": self.change_type,
            "registration_utc_datetime": self.registration_utc_datetime,
            "changed_by": self.changed_by,
            "change_type_dict": self.change_type_dict
        }
        return change_struct


class CodedConceptSetHistory(object):
    """Concept set history contains links to all Concept Objects"""

    def __init__(self, concept_set):
        self.concept_set = concept_set
        self.concept_dict = {} # Need to store all concept objects that are in the history

        for concept in concept_set.concept_dict.values():
            self.concept_dict[concept.key()] = concept

        self.changes = []

    def register_change(self, change):
        change.registration_utc_datetime = datetime.datetime.utcnow()
        self.changes += [change]
        if change.added_codes is not None and len(change.added_codes) > 0: # Insure we have a Code Object for every change
            for code in change.added_codes:
                self.concept_dict[code.key()] = code



class CodedConceptSet(object):
    """A container for concepts"""

    def __init__(self, name, concepts=None, version=0):
        self.name = name
        self.concept_dict = {}
        self.version = version

        if concepts is not None:
            for concept in concepts:
                concept_key = concept.key()
                self.concept_dict[concept_key] = concept

        self.history = CodedConceptSetHistory(self)

        self.created_utc_datetime = datetime.datetime.now(datetime.timezone.utc)


    def to_struct(self):
        cs_struct = {"name": self.name,
                     "version": self.version,
                     "concept_list": [x.to_struct() for x in self],
                     "created_utc_datetime": self.created_utc_datetime,
                     "history": []
                     }

        for change in self.history.changes:
            cs_struct["history"] += [change.to_struct()]

        return cs_struct


    def to_json(self):

        cs_struct = self.to_struct()

        return json.dumps(cs_struct, default=json_datetime_serializer)



    def __item__(self, key):
        return self.concept_dict[key]

    def __repr__(self):
        return f"{self.name} ({len(self)} concepts)"


    def summary(self):

        print(f"Concept set `{self.name}` contains {len(self)} concepts:")
        for concept in sorted(self, key=lambda x: x.code):
            print(f"\t{concept}")
        print("")


    def __and__(self, other):
        """Intersection of two concept sets"""
        set_intersection = self._keys() & other._keys()
        new_concept_list = []
        for key in set_intersection:
            new_concept_list += [self.concept_dict[key]]
        return CodedConceptSet(name= "(" + self.name + " & " + other.name + ")", concepts=new_concept_list)

    def __or__(self, other):
        """Union of two concept sets"""
        set_union = self._keys() | other._keys()

        new_concept_list = []
        for key in set_union:
            if key in self.concept_dict:
                new_concept_list += [self.concept_dict[key]]
            else:
                new_concept_list += [other.concept_dict[key]]

        return CodedConceptSet(name=self.name + " | " + other.name, concepts=new_concept_list)

    def __len__(self):
        return len(self.concept_dict)

    def __sub__(self, other):
        set_difference = self._keys() - other._keys()

        new_concept_list = []
        for key in set_difference:
            new_concept_list += [self.concept_dict[key]]
        return CodedConceptSet(name=self.name + " - " + other.name, concepts=new_concept_list)

    def __iter__(self):
        return iter(self.concept_dict.values())

    def __eq__(self, other):
        return set(self.concept_dict.keys()) == set(other.concept_dict.keys())

    def _keys(self):
        return set(self.concept_dict.keys())

    def register_change(self, change):
        self.history.register_change(change)
        self.version += 1

        if change.added_codes is not None and len(change.added_codes) > 0:
            for code in change.added_codes:
                self.concept_dict[code.key()] = code

        if change.removed_codes is not None and len(change.removed_codes) > 0:
            for code in change.removed_codes:
                self.concept_dict.pop(code.key())

        if change.name is not None:
            change.previous_name = self.name
            self.name = change.name

    def get_version(self, version):
        """Takes the current version and back steps to older versions. New version loses past history"""

        local_concept_dict = dict.copy(self.concept_dict)
        reversed_history = list(reversed(self.history.changes))

        for i in range(self.version - version):
            change_to_reverse = reversed_history[i]
            for code in change_to_reverse.added_codes:
                local_concept_dict.pop(code.key())

            for code in change_to_reverse.removed_codes:
                local_concept_dict[code.key()] = code

        version_concept_set_name = self.name + f"(Copy: v{version})"

        local_concepts = [local_concept_dict[c] for c in local_concept_dict]
        return CodedConceptSet(name=version_concept_set_name, concepts=local_concepts)

    def history_summary(self):

        print(f"There are a total of {self.version + 1} versions of the concept set `{self.name}`:")

        local_changes_reversed = list(reversed(self.history.changes))

        for i in range(self.version):
            historical_version = self.version - i
            get_historical_version = self.get_version(historical_version)
            if i == 0:
                latest_version = " (LATEST)"
            else:
                latest_version = ""

            print(f"\tVersion {historical_version} contains {len(get_historical_version)} concepts{latest_version}")
            change = local_changes_reversed[i]

            if change.name is not None:
                print(f"\t\tName changed:\n\t\t\tFrom `{change.previous_name}` to `{change.name}`")

            if len(change.added_codes) > 0:
                print(f"\t\tAdded {len(change.added_codes)} concepts:")
                for concept in sorted(change.added_codes, key=lambda x: x.code):
                    print(f"\t\t\t{concept}")

            if len(change.removed_codes) > 0:
                print(f"\t\tRemoved {len(change.removed_codes)} concepts:")
                for concept in sorted(change.removed_codes, key=lambda x: x.code):
                    print(f"\t\t\t{concept}")

        get_historical_version = self.get_version(0)
        print(f"\tVersion 0 started with {len(get_historical_version)} concepts:")
        for concept in sorted(get_historical_version, key=lambda x: x.code):
            print(f"\t\t\t{concept}")
        print("")

    def to_csv_string(self, start_i=None, end_i=None):

        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["code", "description", "vocabulary"])

        full_concept_list = list(self)
        if start_i is not None and end_i is not None:
            concept_list = full_concept_list[start_i:end_i]
        elif start_i is not None:
            concept_list = full_concept_list[start_i:]
        elif end_i is not None:
            concept_list = full_concept_list[:end_i]

        for concept in concept_list:
            writer.writerow([concept.code, concept.description, concept.vocabulary])
        return output.getvalue()

    def to_csv(self, file_path):
        with open(file_path, "w", newline="") as csv_file:
            writer = csv.writer(csv_file)
            writer.writerow(["code", "description", "vocabulary"])
            for concept in self:
                writer.writerow([concept.code, concept.description, concept.vocabulary])



class CompareCodedConceptSets(object):
    """Compares two concept sets and returns a list of differences"""

    def __init__(self, concept_set_1, concept_set_2):
        self.concept_set_1 = concept_set_1
        self.concept_set_2 = concept_set_2

        self.intersection = self.concept_set_1 & self.concept_set_2
        self.union = self.concept_set_1 | self.concept_set_2

        self.left_difference = self.concept_set_1 - self.concept_set_2
        self.right_difference = self.concept_set_2 - self.concept_set_1

    def summary(self):

        print(f"Summarizing differences between concept sets:")
        print(f'\tConcept set `{self.concept_set_1.name}` contains {len(self.concept_set_1)} concepts')
        print(f''
              f'\tConcept set `{self.concept_set_2.name}` contains {len(self.concept_set_2)} concepts')
        print("")
        print(f"The intersection between the two concept sets contains {len(self.intersection)} concepts:")
        for concept in sorted(self.intersection, key=lambda x: x.code):
            print(f"\t{concept}")

        print("")
        print(f"The union contains {len(self.union)} concepts:")
        for concept in sorted(self.union, key=lambda x: x.code):
            print(f"\t{concept}")
        print("")
        print(f"The fractional overlap between the two concept sets is: {len(self.intersection)/len(self.union)}")
        print("")
        print(f"The left set difference `{self.concept_set_1.name}` contains {len(self.left_difference)} unique concepts:")
        for concept in sorted(self.left_difference, key=lambda x: x.code):
            print(f"\t{concept}")
        print("")

        print(f'The right set difference `{self.concept_set_2.name}` contains {len(self.right_difference)} unique concepts:')
        for concept in sorted(self.right_difference, key=lambda x: x.code):
            print(f"\t{concept}")
        print("")


def concepts_df_to_concept_set(df, concept_set_name):
    concept_list = []
    for row in df.to_dict("records"):
        concept_list += [CodedConcept(row["code"], row["vocabulary"], row["description"])]

    return CodedConceptSet(concept_set_name, concept_list)


def concept_dict_to_concept(concept_dict):
    return CodedConcept(concept_dict["code"], concept_dict["vocabulary"], concept_dict["description"], concept_dict["metadata"])


def recreate_concept_set_from_struct(concept_set_struct):
    concept_set_name = concept_set_struct["name"]
    concept_list = []
    for concept_struct in concept_set_struct["concept_list"]:
        concept_list += [concept_dict_to_concept(concept_struct)]

    created_utc_datetime = datetime.datetime.fromisoformat(concept_set_struct["created_utc_datetime"])
    concept_set = CodedConceptSet(concept_set_name, concept_list, version=concept_set_struct["version"])
    concept_set.created_utc_datetime = created_utc_datetime

    history_changes = []
    for change_struct in concept_set_struct["history"]:
        changes = CodedConceptSetChange(

                                       [concept_dict_to_concept(x) for x in change_struct["added_code_list"]],
                                       [concept_dict_to_concept(x) for x in change_struct["removed_code_list"]],
                                       change_struct["name"],
                                       change_struct["change_type"],
                                       change_struct["changed_by"],
                                       change_struct["change_type_dict"])

        changes.previous_name = change_struct["previous_name"]
        changes.registration_utc_datetime = datetime.datetime.fromisoformat(change_struct["registration_utc_datetime"])
        history_changes += [changes]

    concept_set.history.changes = history_changes

    return concept_set

def build_icd10cm_snomed_code_mapper(code_mapping_struct_list):

    code_mapping_list = []

    for code_mapping_struct in code_mapping_struct_list:

        description = code_mapping_struct["concept_name"]
        code = code_mapping_struct["concept_code"]
        vocabulary = code_mapping_struct["vocabulary_id"]
        metadata = {"concept_id": code_mapping_struct["concept_id"]}

        code_mapped_from_obj  = CodedConcept(code, vocabulary, description, metadata)

        mapped_concept_struct_list = code_mapping_struct["mapped_concept_list"]

        mapped_coding_obj_list = []
        for mapped_concept_struct in mapped_concept_struct_list:
            mapped_description = mapped_concept_struct["mapped_concept_name"]
            mapped_code = mapped_concept_struct["mapped_concept_code"]
            mapped_vocabulary = mapped_concept_struct["mapped_vocabulary_id"]
            mapped_metadata = {"concept_id": mapped_concept_struct["mapped_concept_id"]}

            mapped_coded_list_obj = CodedConcept(mapped_code, mapped_vocabulary, mapped_description, mapped_metadata)
            mapped_coding_obj_list += [mapped_coded_list_obj]

        mapped_tuple_obj = CodedConceptTuple(mapped_coding_obj_list)

        code_mapping_list += [CodedConceptMap(code_mapped_from_obj, mapped_tuple_obj)]

    code_mapper_obj = CodedConceptMappings(code_mapping_list)

    return code_mapper_obj