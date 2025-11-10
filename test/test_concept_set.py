import unittest
from concept_set import Concept, ConceptSet


class TestConcept(unittest.TestCase):
    def test_creation(self):

        c1 = Concept("E11.22", "ICD10CM", "Type 2 diabetes mellitus with diabetic chronic kidney disease	")

        self.assertEqual(c1.key(), "E11.22|ICD10CM")  # add assertion here

class TestConceptSet(unittest.TestCase):
    def setUp(self):

       cst_1 = """G89.4	Chronic pain syndrome	ICD10CM
G89.29	Other chronic pain	ICD10CM
G89.21	Chronic pain due to trauma	ICD10CM
G89.28	Other chronic postprocedural pain	ICD10CM
G44.321	Chronic post-traumatic headache, intractable	ICD10CM
G44.201	Tension-type headache, unspecified, intractable	ICD10CM"""

       self.concept_list_1 = []
       for line in cst_1.split("\n"):
            code, description, vocabulary = line.split("\t")
            self.concept_list_1 += [Concept(code, vocabulary, description)]

       cst_2 = """G89.4	Chronic pain syndrome	ICD10CM
G89.29	Other chronic pain	ICD10CM
G89.21	Chronic pain due to trauma	ICD10CM
M10.059	Idiopathic gout, unspecified hip	ICD10CM
M25.562	Pain in left knee	ICD10CM
M25.532	Pain in left wrist	ICD10CM"""

       self.concept_list_2 = []
       for line in cst_2.split("\n"):
           code, description, vocabulary = line.split("\t")
           self.concept_list_2 += [Concept(code, vocabulary, description)]

    def test_creation(self):
        p1 = ConceptSet("Pain", self.concept_list_1)
        self.assertTrue(len(p1) == 6)

    def test_union(self):

        p1 = ConceptSet("Pain 1", self.concept_list_1)
        p2 = ConceptSet("Pain 2", self.concept_list_2)

        p3 = p1 | p2

        print(len(p3))

        self.assertTrue(len(p3) == 9)


if __name__ == '__main__':
    unittest.main()
