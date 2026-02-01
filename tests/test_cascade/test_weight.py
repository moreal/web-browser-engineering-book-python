from browser.cascade.weight import SpecificityWeight


class TestSpecificityWeightCreation:
    def test_create(self):
        w = SpecificityWeight(0, 1, 0)
        assert w.id_column == 0
        assert w.class_column == 1
        assert w.type_column == 0

    def test_create_zero(self):
        w = SpecificityWeight(0, 0, 0)
        assert w == (0, 0, 0)


class TestSpecificityWeightAddition:
    def test_add(self):
        a = SpecificityWeight(1, 0, 0)
        b = SpecificityWeight(0, 1, 2)
        assert a + b == SpecificityWeight(1, 1, 2)

    def test_add_returns_specificity_weight(self):
        result = SpecificityWeight(0, 1, 0) + SpecificityWeight(0, 0, 1)
        assert type(result) is SpecificityWeight


class TestSpecificityWeightComparison:
    def test_id_column_takes_precedence(self):
        assert SpecificityWeight(1, 0, 0) > SpecificityWeight(0, 99, 99)

    def test_class_column_breaks_tie(self):
        assert SpecificityWeight(0, 2, 0) > SpecificityWeight(0, 1, 99)

    def test_type_column_breaks_tie(self):
        assert SpecificityWeight(0, 0, 2) > SpecificityWeight(0, 0, 1)

    def test_equal(self):
        assert SpecificityWeight(1, 2, 3) == SpecificityWeight(1, 2, 3)


class TestSpecificityWeightSorting:
    def test_sort(self):
        weights = [
            SpecificityWeight(0, 1, 0),
            SpecificityWeight(1, 0, 0),
            SpecificityWeight(0, 0, 1),
            SpecificityWeight(0, 1, 1),
        ]
        assert sorted(weights) == [
            SpecificityWeight(0, 0, 1),
            SpecificityWeight(0, 1, 0),
            SpecificityWeight(0, 1, 1),
            SpecificityWeight(1, 0, 0),
        ]
