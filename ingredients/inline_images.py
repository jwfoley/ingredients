import re, markdown
from base64 import b64encode
from textwrap import wrap

WRAP_LENGTH = 80 # length of wrapped lines with raw image data
IMAGE_REGEX = re.compile('!\[(.*?)\]\((.*?)\)\{(.*?)\}', re.DOTALL)
TAG_REGEX = re.compile('\.inline\s*') # include trailing space to delete it when passing style
IMAGE_FORMAT = '<img%s src="data:image;base64,\n%s\n">'
SVG_REGEX = re.compile(b'<svg(.*?)>(.+)</svg>', re.DOTALL) # binary to identify raw data before decoding
TAG_SIZE_REGEX = re.compile('[^ ]*(width|height)=[^ ]+ *')
STYLE_SIZE_REGEX = re.compile('(width|height):')
SVG_FORMAT = '<svg%s>%s</svg>'

class InlineImages (markdown.preprocessors.Preprocessor):
	def run (self, lines):
		return self.insert_images(lines)
	
	def insert_images (self, lines):
		for line in lines:
			for image_match in list(IMAGE_REGEX.finditer(line))[::-1]: # iterate in reverse so coordinates from left will still be correct after each replacement
				style_sub = TAG_REGEX.subn('', image_match.group(3))
				if style_sub[1] != 1: # found tag once (and removed it)
					yield line
					continue
				
				raw_image = open(image_match.group(2), 'rb').read()
				line_before = line[:image_match.start()]
				line_after = line[image_match.end():]
				style = style_sub[0].strip()
				style_attrib = '' if style == '' else (' style="%s"' % style)
				title = image_match.group(1).strip()
				
				# SVG
				svg_match = SVG_REGEX.search(raw_image)
				if svg_match is not None:
					# remove previous height and width if (re)specified in style
					svg_tag = svg_match.group(1).decode()
					if (STYLE_SIZE_REGEX.search(style) is not None): svg_tag = TAG_SIZE_REGEX.sub('', svg_tag)
					
					replacement = SVG_FORMAT % (
						svg_tag + style_attrib,
						('' if title == '' else ('<title>%s</title>' % title)) + svg_match.group(2).decode()
					)
				
				# not SVG
				else:
					replacement = IMAGE_FORMAT % (
						style_attrib + ('' if title == '' else (' title="%s"' % title)),
						'\n'.join(wrap(b64encode(raw_image).decode(), WRAP_LENGTH))
					)
				
				line = line[:image_match.start()] + replacement + line[image_match.end():]
			
			yield line

