import unittest

import concept_set
from concept_set.base import (CodedConcept, CodedConceptSet, CodedConceptSetChange, CompareCodedConceptSets,
                              CodedConceptTuple, CodedConceptMap, CodedConceptMappings, build_icd10cm_snomed_code_mapper)
import json
import pandas as pd

def helper_concept_list(concept_set_string):
    concept_list = []
    for line in concept_set_string.split("\n"):
        code, description, vocabulary = line.split("\t")
        concept_list += [CodedConcept(code, vocabulary, description)]

    return concept_list


class TestConcept(unittest.TestCase):
    def test_creation(self):

        c1 = CodedConcept("E11.22", "ICD10CM", "Type 2 diabetes mellitus with diabetic chronic kidney disease	")

        self.assertEqual(c1.key(), "E11.22|ICD10CM")  # add assertion here

class TestConceptSet(unittest.TestCase):
    def setUp(self):

       cst_1 = """G89.4	Chronic pain syndrome	ICD10CM
G89.29	Other chronic pain	ICD10CM
G89.21	Chronic pain due to trauma	ICD10CM
G89.28	Other chronic postprocedural pain	ICD10CM
G44.321	Chronic post-traumatic headache, intractable	ICD10CM
G44.201	Tension-type headache, unspecified, intractable	ICD10CM"""

       self.concept_list_1 =  helper_concept_list(cst_1)

       cst_2 = """G89.4	Chronic pain syndrome	ICD10CM
G89.29	Other chronic pain	ICD10CM
G89.21	Chronic pain due to trauma	ICD10CM
M10.059	Idiopathic gout, unspecified hip	ICD10CM
M25.562	Pain in left knee	ICD10CM
M25.532	Pain in left wrist	ICD10CM"""
       self.concept_list_2 = helper_concept_list(cst_2)

       cst3 = """G44.209	Tension-type headache, unspecified, not intractable	ICD10CM
G44.029	Chronic cluster headache, not intractable	ICD10CM"""

       self.concept_list_3 = helper_concept_list(cst3)

       cst4 = """G44.321	Chronic post-traumatic headache, intractable	ICD10CM
G44.201	Tension-type headache, unspecified, intractable	ICD10CM"""

       self.concept_list_4 = helper_concept_list(cst4)

    def test_creation(self):
        p1 = CodedConceptSet("Pain", self.concept_list_1)
        self.assertTrue(len(p1) == 6)

    def test_union(self):

        p1 = CodedConceptSet("Pain 1", self.concept_list_1)
        p2 = CodedConceptSet("Pain 2", self.concept_list_2)

        p3 = p1 | p2
        self.assertTrue(len(p3) == 9)

    def test_intersection(self):
        p1 = CodedConceptSet("Pain 1", self.concept_list_1)
        p2 = CodedConceptSet("Pain 2", self.concept_list_2)
        p3 = p1 & p2

        self.assertTrue(len(p3) == 3)

    def test_difference(self):
        p1 = CodedConceptSet("Pain 1", self.concept_list_1)
        p2 = CodedConceptSet("Pain 2", self.concept_list_2)
        p3 = p1 - p2

        self.assertTrue(len(p3) == 3)

    def test_concept_set_change(self):

        p1 = CodedConceptSet("Pain 1", self.concept_list_1)

        pl3 = self.concept_list_3

        dx1 = pl3[0].key()
        dx2 = pl3[1].key()

        change_description_1 = {dx1: "Missed codes", dx2: "Missed codes"}
        change_obj_1 = CodedConceptSetChange(added_codes_list=pl3, removed_codes_list=[], change_name="Pain 1 with added codes", change_type="addition", change_type_dict=change_description_1)

        self.assertIsNotNone(change_obj_1)

        p1.register_change(change_obj_1)

        self.assertEqual(8, len(p1))
        self.assertEqual(1, p1.version)

        pl4 = self.concept_list_4
        dx4 = pl4[0].key()
        dx5 = pl4[1].key()

        change_description_2 = {dx4: "Codes are incorrect", dx5: "Codes are incorrect"}
        change_obj_2 = CodedConceptSetChange(added_codes_list=[], removed_codes_list=pl4, change_name="Pain 1 with codes added and removed",
                                             change_type="removal",
                                             change_type_dict=change_description_2)

        p1.register_change(change_obj_2)

        self.assertEqual(6, len(p1))
        self.assertEqual(2, p1.version)

        p1_v1 = p1.get_version(1)
        self.assertEqual(8, len(p1_v1))

        p1_v0 = p1.get_version(0)
        self.assertEqual(6, len(p1_v0))

        p1_recreated = CodedConceptSet("Pain 1 Recreated", self.concept_list_1)

        self.assertEqual(p1_v0, p1_recreated)

        p1.history_summary()

        cs_struct = p1.to_struct()

        self.assertIsNotNone(cs_struct)

        p1_json_dump = p1.to_json()

        with open("./output/p1.json", "w") as f:
            f.write(p1_json_dump)

        p1_recreated_struct = json.loads(p1_json_dump)

        self.assertIsNotNone(p1_recreated_struct)

        p1_with_versions_recreated = concept_set.base.recreate_concept_set_from_struct(p1_recreated_struct)

        p1_with_versions_recreated.summary()
        p1_with_versions_recreated.history_summary()


    def test_iteration(self):
        p1 = CodedConceptSet("Pain 1", self.concept_list_1)
        i = 0
        for concept in p1:
            self.assertIsNotNone(concept)
            i += 1

        self.assertEqual(6, i)

    def test_summary(self):
        concept_set_1 = CodedConceptSet("Pain 1", self.concept_list_1)
        concept_set_2 = CodedConceptSet("Pain 2", self.concept_list_2)

        CompareCodedConceptSets(concept_set_1, concept_set_2).summary()

        self.assertTrue(True)

    def test_concept_map(self):
        concept_set_1 = CodedConceptSet("Pain 1", self.concept_list_1)

    def test_concept_map_creation(self):

        coded_concept_1 = CodedConcept("M84.60XK", "ICD10CM", "Pathological fracture in other disease, unspecified site, subsequent encounter for fracture with nonunion")

        coded_concept_2 = CodedConcept("E11.3511", "ICD10CM", "Type 2 diabetes mellitus with proliferative diabetic retinopathy with macular edema, right eye")

        concept_struct_map = []
        with open("./sample_icd10cm_snomed_ohdsi_map.jsonl") as f:
            for line in f:
                concept_struct_map += [json.loads(line)]

        self.assertTrue(len(concept_struct_map) > 0)

        concept_mapper_obj = build_icd10cm_snomed_code_mapper(concept_struct_map)
        self.assertIsNotNone(concept_mapper_obj)

        mapped_concept_obj = concept_mapper_obj.map(coded_concept_1)

        mapped_concept_str_1 = str(mapped_concept_obj)

        print(str(coded_concept_1) + " -> " + mapped_concept_str_1)
        print(concept_mapper_obj.map(coded_concept_2))


if __name__ == '__main__':
    unittest.main()
