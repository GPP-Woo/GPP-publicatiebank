import re
from typing import IO

# This regex pattern checks if a string matches a closed info group.
# The pattern does the following:
# - `{` checks if the start is an open-bracket, which is the start
#   symbol of a group.
# - `\n*` checks if there MIGHT be any linebreaks, rtf allows
#   for none or X amount of linebreaks after the opening symbol.
# - `\\?` checks if there is a backslash (optionally 2 in case of escaping).
# - `info\b` simply checks if the next letters are "info".
# - `(?:[^{}]|\{[^{}]*\})*` is a non-capturing group.
#   This checks if the set of information matches either everything but brackets,
#   or everything between brackets except nested brackets.
#   this means that between the start and end of the info group you can define data as:
#   "some string" or "{some string between brackets}"
# - `\}` check if the data ends with a closing-bracket, which is the end symbol
#   of a group
RTF_INFO_GROUP_PATTERN = r"{\n*\\?info\b(?:[^{}]|\{[^{}]*\})*\}"


class StripRtf:
    """
    A custom parser to strip all metadata of an RTF file.
    This custom parser requires an input and output file to
    process all the data on disc. This means we can prevent high memory usage,
    which all-purpose libraries fall victim to.
    """

    def __init__(self, input_file: IO[bytes], output_file: IO[bytes]):
        self.input_file = input_file
        self.output_file = output_file
        # TODO: add real encoding detection
        self.encoding = "cp1252"

    def _detect_start_of_group(self, data: bytes) -> bytes | None:
        """
        Call when the start of a group has been found in the file.
        This code will slowly construct in memory the start of the group
        so we can figure out if it is the info group (which is where the
        metadata is stored).

        When the info group is detected call the internal method to strip
        the metadata from the group, and write the data to the file. If there
        is excess data make sure to pass it back so we can evaluate said data.
        """

        element: bytes = data
        excess_data: bytes | None = None

        while True:
            data = self.input_file.read(2)
            if not data:
                self.output_file.write(element)
                break

            element += data

            # Checks if the start of a group is properly constructed
            # so we can identify the name of the group.
            # The regex checks 3 things:
            # - the data starts with open-bracket (`{`)
            # - after the open-bracket there may be linebreaks (`[\n]*`)
            # - after the open-bracket or linebreaks there must be
            #   one escaped backslashes (\)
            #
            # this regex also put the linebreak and backslash detection into
            # 2 different groups.
            start = re.search(
                pattern=r"{([\n]*)(\\?)",
                string=element.decode(self.encoding),
                flags=re.DOTALL,
            )

            if not start:
                self.output_file.write(element)
                break

            # Check if the last group (the backslash) is present.
            # If this is the case we can read the next 6 bytes (in case of
            # the double escaped backslashes) which allows us to check if
            # this group is the info group (which is where all the metadata is stored)
            if start.groups()[1]:
                element += self.input_file.read(6)

                if b"info" in element:
                    excess_data = self._strip_info_group(element)
                    break

                self.output_file.write(element)
                break

            # if the escaped backslash isn't present check if we detect
            # any linebreaks in group 2, if not then abort and start over
            elif not start.groups()[0]:
                self.output_file.write(element)
                break

        return excess_data

    def _strip_info_group(self, data: bytes) -> bytes | None:
        """
        Construct the full info group so we can replace it with an empty one.
        """
        element: bytes = data
        tail: bytes = b""

        # loop through the file until we constructed and thus strip the info group.
        while True:
            data = self.input_file.read(2)
            if not data:
                self.output_file.write(element)
                break

            element += data

            # check's if the info group is fully constructed.
            # when it is, make sure to get the text before and after.
            # This allows us to write it before and after empty info group.
            if info := re.search(
                pattern=RTF_INFO_GROUP_PATTERN,
                string=element.decode(self.encoding),
                flags=re.DOTALL,
            ):
                # try and get the text before the info group,
                # if there is any write it to the file.
                if head := element[: info.start()]:
                    self.output_file.write(head)

                # write an empty info group which will replace the
                # original info group.
                self.output_file.write(b"{\\info}")

                # set the tail so we can return it and process it
                # incase it's the start of a new group
                tail = element[info.end() :]
                break

        # if the tail isn't an empty return it so we can process it.
        if tail:
            return tail

    def _process_data(self, data: bytes) -> None:
        # checks for the start tag of a group.
        # if it is detected make sure to process it,
        # otherwise just write the data to disk.
        if b"{" in data:
            if data := self._detect_start_of_group(data):
                self._process_data(data)

            return

        self.output_file.write(data)

    def strip_file(self):
        """
        Parses the input full's data and crawls through it till it detects the
        """
        while True:
            data = self.input_file.read(2)
            if not data:
                break

            self._process_data(data)

        self.output_file.flush()
