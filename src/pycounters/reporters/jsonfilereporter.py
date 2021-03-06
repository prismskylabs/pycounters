import fcntl
import json
import os

from . import BaseReporter


class JSONFileReporter(BaseReporter):
    """
        Reports to a file in a JSON format.

    """

    def __init__(self, output_file=None):
        """
            :param output_file: a file name to which the reports will be written.
        """
        super(JSONFileReporter, self).__init__()
        self.output_file = output_file

    def output_values(self, counter_values):
        JSONFileReporter.safe_write(counter_values, self.output_file)

    @staticmethod
    def _lockfile(file):
        try:
            fcntl.flock(file, fcntl.LOCK_EX)
            return True
        except IOError, exc_value:
        #  IOError: [Errno 11] Resource temporarily unavailable
            if exc_value[0] == 11 or exc_value[0] == 35:
                return False
            else:
                raise

    @staticmethod
    def _unlockfile(file):
        fcntl.flock(file, fcntl.LOCK_UN)

    @staticmethod
    def safe_write(value, filename):
        """ safely writes value in a JSON format to file
        """
        fd = os.open(filename, os.O_CREAT | os.O_WRONLY)
        JSONFileReporter._lockfile(fd)
        try:

            file = os.fdopen(fd, "w")
            file.truncate()
            json.dump(value, file)
        finally:
            JSONFileReporter._unlockfile(fd)
            file.close()
        # fd is now close by the with clause

    @staticmethod
    def safe_read(filename):
        """ safely reads a value in a JSON format frome file
        """
        fd = os.open(filename, os.O_RDONLY)
        JSONFileReporter._lockfile(fd)
        try:
            file = os.fdopen(fd, "r")
            return json.load(file)
        finally:
            JSONFileReporter._unlockfile(fd)
            file.close()

        # fd is now close by the with clause
