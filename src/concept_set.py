class Concept(object):
    def __init__(self, code, vocabulary, description):
        self.code = code
        self.description = description
        self.vocabulary = vocabulary

    def key(self):
        return self.code + "|" + self.vocabulary


class ConceptSet(object):

    def __init__(self, name, concepts=None, version=0):
        self.name = name
        self.concept_dict = {}
        self.version = version

        if concepts is not None:
            for concept in concepts:
                concept_key = concept.key()
                self.concept_dict[concept_key] = concept

    def __and__(self, other):
        """Intersection of two concept sets"""
        set_intersection = self._keys() & other._keys()
        new_concept_list = []
        for key in set_intersection:
            new_concept_list += [self.concept_dict[key]]
        return ConceptSet(name=self.name + " & " + other.name, concepts=new_concept_list)

    def __or__(self, other):
        """Union of two concept sets"""
        set_union = self._keys() | other._keys()

        new_concept_list = []
        for key in set_union:
            if key in self.concept_dict:
                new_concept_list += [self.concept_dict[key]]
            else:
                new_concept_list += [other.concept_dict[key]]

        return ConceptSet(name=self.name + " | " + other.name, concepts=new_concept_list)

    def __len__(self):
        return len(self.concept_dict)

    def __sub__(self, other):
        set_difference = self._keys() - other._keys()

        new_concept_list = []
        for key in set_difference:
            new_concept_list += [self.concept_dict[key]]
        return ConceptSet(name=self.name + " - " + other.name, concepts=new_concept_list)

    def _keys(self):
        return set(self.concept_dict.keys())


class ConceptSetChange(object):

    def __init__(self, added_codes, removed_codes, change_type):
        self.added_codes = added_codes
        self.removed_codes = removed_codes
        self.change_type = change_type

class ConceptSetHistory(object):

    def __init__(self, concept_set):
        self.version = 0
        self.concept_set = concept_set

    def register_change(self, change):
        pass

    def get_version(self, version):
        pass

    def get_latest_version(self):
        pass


