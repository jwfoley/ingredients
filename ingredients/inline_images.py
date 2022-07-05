import re, markdown
from base64 import b64encode
from textwrap import wrap

WRAP_LENGTH = 80 # length of wrapped lines with raw image data
IMAGE_REGEX = re.compile('!\[(.*?)\]\((.*?)\)\{(.*?)\}', re.DOTALL)
TAG_REGEX = re.compile('\.inline\s*') # include trailing space to delete it when passing style
IMAGE_FORMAT = '%s<img%s src="data:image;base64,\n%s\n">%s'
SVG_REGEX = re.compile(b'<svg(.*?)>(.+)</svg>', re.DOTALL) # binary to identify raw data before decoding
TAG_SIZE_REGEX = re.compile('[^ ]*(width|height)=[^ ]+ *')
STYLE_SIZE_REGEX = re.compile('(width|height):')
SVG_FORMAT = '%s<svg%s>%s</svg>%s'

class InlineImages (markdown.preprocessors.Preprocessor):
	def run (self, lines):
		return self.insert_images(lines)
	
	def insert_images (self, lines):
		for line in lines:
			line_match = IMAGE_REGEX.search(line)
			if line_match is None:
				yield line
				continue
			
			style_sub = TAG_REGEX.subn('', line_match.group(3))
			if style_sub[1] != 1: # found tag once (and removed it)
				yield line
				continue
			
			raw_image = open(line_match.group(2), 'rb').read()
			line_before = line[:line_match.start()]
			line_after = line[line_match.end():]
			style = style_sub[0].strip()
			style_attrib = '' if style == '' else (' style="%s"' % style)
			title = line_match.group(1).strip()
			
			# SVG
			svg_match = SVG_REGEX.search(raw_image)
			if svg_match is not None:
				# remove previous height and width if (re)specified in style
				svg_tag = svg_match.group(1).decode()
				if (STYLE_SIZE_REGEX.search(style) is not None): svg_tag = TAG_SIZE_REGEX.sub('', svg_tag)
				
				yield SVG_FORMAT % (
					line_before,
					svg_tag + style_attrib,
					('' if title == '' else ('<title>%s</title>' % title)) + svg_match.group(2).decode(),
					line_after
				)
			
			# not SVG
			else:
				yield IMAGE_FORMAT % (
					line_before,
					style_attrib + ('' if title == '' else (' title="%s"' % title)),
					'\n'.join(wrap(b64encode(raw_image).decode(), WRAP_LENGTH)),
					line_after
				)

