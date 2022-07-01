import re, markdown
from base64 import b64encode
from textwrap import wrap

WRAP_LENGTH = 80 # length of wrapped lines with raw image data
IMAGE_REGEX = re.compile('!\[(.*?)\]\((.*?)\)\{(.*?)\}', re.DOTALL)
IMAGE_HEADER = '<img alt="%s" src="data:image;base64,'
IMAGE_FOOTER = '">'
SVG_REGEX = re.compile(b'<svg.*</svg>')

class InlineImages (markdown.preprocessors.Preprocessor):
	def run (self, lines):
		return self.insert_images(lines)
	
	def insert_images (self, lines):
		for line in lines:
			match = IMAGE_REGEX.search(line)
			if match is None:
				yield line
				continue
			
			attribs = match.group(3).split()
			try:
				inline_index = attribs.index('.inline')
			except ValueError:
				yield line
				continue
			
			raw_image = open(match.group(2), 'rb').read()
			line_before = line[:match.start()]
			line_after = line[match.end():]
			
			# SVG
			svg_match = SVG_REGEX.search(raw_image)
			if svg_match is not None:
				yield line_before + raw_image[svg_match.start():svg_match.end()].decode() + line_after
			
			# not SVG
			else:
				yield line_before + (IMAGE_HEADER % match.group(1))
				for wrap_line in wrap(b64encode(raw_image).decode(), WRAP_LENGTH): yield(wrap_line)
				yield IMAGE_FOOTER + line_after

