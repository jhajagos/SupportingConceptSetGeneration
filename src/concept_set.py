import datetime

class CodedConcept(object):
    def __init__(self, code, vocabulary, description):
        self.code = code
        self.description = description
        self.vocabulary = vocabulary

    def key(self):
        return self.code + "|" + self.vocabulary

    def __repr__(self):
        return f"{self.code} - {self.description} ({self.vocabulary})"


class CodedConceptSetChange(object):
    def __init__(self, added_codes_list, removed_codes_list, change_type, changed_by=None, change_type_dict=None,
                 derived_from=None, derived_from_version=None):
        self.added_codes = added_codes_list
        self.removed_codes = removed_codes_list

        self.change_type = change_type
        self.derived_from = derived_from
        self.derived_from_version = derived_from_version

        self.registration_utc_datetime = None
        self.changed_by = changed_by

        if change_type_dict is None: # Holds human or machine created labels why a specific change was made
            change_type_dict = {}
        self.change_type_dict = change_type_dict

    def __repr__(self):
        return str((self.added_codes, self.removed_codes, self.change_type, self.registration_utc_datetime))


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

        self.created_utc_datetime = datetime.datetime.utcnow()

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
