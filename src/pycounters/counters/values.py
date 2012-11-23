from pycounters.base import CounterValueBase


class AccumulativeCounterValue(CounterValueBase):
    """ Counter values that are added upon merges
    """

    def merge_with(self, other_counter_value):
        """ updates this CounterValue with information of another. Used for multiprocess reporting
        """
        if self.value:
            if other_counter_value.value:
                self.value += other_counter_value.value
        else:
            self.value = other_counter_value.value


class AverageCounterValue(CounterValueBase):
    """ Counter values that are averaged upon merges
    """

    @property
    def value(self):
        if not self._values:
            return None
        sum_of_counts = sum([c for v, c in self._values], 0)
        return sum([v * c for v, c in self._values], 0.0) / sum_of_counts

    def __init__(self, value, agg_count):
        """
            value - the average counter to store
            agg_count - the number of elements that was averaged in value. Important for proper merging.
        """
        self._values = [(value, agg_count)] if value is not None else []

    def merge_with(self, other_counter_value):
        """ updates this CounterValue with information of another. Used for multiprocess reporting
        """
        self._values.extend(other_counter_value._values)


class MaxCounterValue(CounterValueBase):
    """ Counter values that are merged by selecting the maximal value. None values are ignored.
        """

    def merge_with(self, other_counter_value):
        """ updates this CounterValue with information of another. Used for multiprocess reporting
        """
        if self.value is None:
            self.value = other_counter_value.value
            return
        if other_counter_value.value is not None and self.value < other_counter_value.value:
            self.value = other_counter_value.value


class MinCounterValue(CounterValueBase):
    """ Counter values that are merged by selecting the minimal value. None values are ignored.
        """

    def merge_with(self, other_counter_value):
        """ updates this CounterValue with information of another. Used for multiprocess reporting
        """
        if self.value is None:
            self.value = other_counter_value.value
            return
        if other_counter_value.value is not None and self.value > other_counter_value.value:
            self.value = other_counter_value.value
