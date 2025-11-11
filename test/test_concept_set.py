import unittest
from concept_set import CodedConcept, CodedConceptSet, CodedConceptSetChange, CompareCodedConceptSets

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
        change_obj_1 = CodedConceptSetChange(added_codes_list=pl3, removed_codes_list=[], change_type="addition", change_type_dict=change_description_1)

        self.assertIsNotNone(change_obj_1)

        p1.register_change(change_obj_1)

        self.assertEqual(8, len(p1))
        self.assertEqual(1, p1.version)

        pl4 = self.concept_list_4
        dx4 = pl4[0].key()
        dx5 = pl4[1].key()

        change_description_2 = {dx4: "Codes are incorrect", dx5: "Codes are incorrect"}
        change_obj_2 = CodedConceptSetChange(added_codes_list=[], removed_codes_list=pl4, change_type="removal",
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


if __name__ == '__main__':
    unittest.main()
