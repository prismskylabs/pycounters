from exceptions import NotImplementedError


class CounterValueBase(object):
    """ a base class for counter values. Deals with defining merge semantics etc.
    """

    def __init__(self, value):
        self.value = value

    def merge_with(self, other_counter_value):
        """ updates this CounterValue with information of another. Used for multiprocess reporting
        """
        raise NotImplementedError("merge_with should be implemented in class inheriting from CounterValueBase")


class CounterValueCollection(dict):
    """ a dictionary of counter values, adding support for dictionary merges and getting a value only dict.
    """

    @property
    def values(self):
        r = {}
        for k, v in self.iteritems():
            r[k] = v.value if hasattr(v, "value") else v

        return r

    def merge_with(self, other_counter_value_collection):
        for k, v in other_counter_value_collection.iteritems():
            mv = self.get(k)
            if mv is None:
                # nothing local, just set it
                self[k] = v
            elif isinstance(mv, CounterValueBase):
                if not isinstance(v, CounterValueBase):
                    raise Exception("Can't merge with CounterValueCollection. Other Collection doesn't have a mergeable value for key %s" % (k, ))
                mv.merge_with(v)
            else:
                raise Exception("Can't merge with CounterValueCollection. Local key $s doesn't have a mergeable value." % (k, ))


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
