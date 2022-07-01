import re, markdown

DIRECTIONS_FORMAT = '<label><input type="checkbox">%s</label>\n' # add another newline to make sure the downstream processor turns these into separate HTML paragraphs (if we add the <p> now, downstream processors won't parse any Markdown inside)

DIRECTION_REGEX = re.compile('^\* \[ \]\s*(.*)\s*') # matches GFM "* [ ] " and ignores leading and trailing whitespace

class Directions (markdown.preprocessors.Preprocessor):
	def run (self, lines):
		return map(lambda line: DIRECTION_REGEX.sub(lambda match: DIRECTIONS_FORMAT % match.groups()[0], line), lines)

