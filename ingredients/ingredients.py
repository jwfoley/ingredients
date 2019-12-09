import re, markdown
from lxml import etree, html

DIRECTIONS_OPEN = '<directions>'
DIRECTIONS_CLOSE = '</directions>'
DIRECTIONS_HEADER = '<dl>'
DIRECTIONS_FOOTER = '</dl>'
DIRECTIONS_FORMAT = '<label><input type="checkbox">%s</label><p>'

INGREDIENTS_TAG = 'ingredients' # appears as an HTML tag

DEFAULT_HEADER = ['<meta name="viewport" content="initial-scale=1">'] # think harder about where to put this

class Directions (markdown.preprocessors.Preprocessor):
	def run (self, lines):
		new_lines = []
		in_section = False # track whether we are currently in the section
		
		for line in lines:
			if in_section: # currently in the section
				if DIRECTIONS_CLOSE in line: # find end of section
					lines.append(DIRECTIONS_FOOTER)
					in_section = False
					
				else: # parse a line of the section
					lines.append(DIRECTIONS_FORMAT % line)
				
			elif DIRECTIONS_OPEN in line: # find beginning of section
				lines.append(DIRECTIONS_HEADER)
				in_section = True
			
			else:
				new_lines.append(line)
		
		if in_section: raise RuntimeError('missing %s tag' % DIRECTIONS_CLOSE)
		return new_lines

def generate_ingredient_table (element, form_name = 'ingredients', scale_name = 'batches', checkbox = True):
	'''
	given an lxml.etree.Element of tag 'ingredients', return a new Element in the form of an HTML form containing the interactive table
	'''

	# parse the text contents
	ingredients = []
	for line in element.text.split('\n'):
		stripped_line = line.strip()
		if stripped_line != '':
			fields = re.split('\s*\|\s*', stripped_line)
			ingredients.append([fields[0]] + re.split('\s+', fields[1], 1))
		
	# create the new Element
		
	form_root = etree.Element('form', {'name': form_name})
	form_root.text = scale_name + ': '
	
	# hardcoded default values
	for i in range(len(ingredients)):
		form_root.append(etree.Element('input', {
			'type': 'hidden',
			'name': ('default%i' % i),
			'value': ingredients[i][1]
		}))
	
	# scale controls
	scale_function = etree.SubElement(form_root, 'input', {
		'name': 'scale',
		'value': '1',
		'onInput': ''
	})
	for i in range(len(ingredients)):
		scale_function.set('onInput', scale_function.get('onInput') + ('document.%s.amount%i.value = document.%s.scale.value * document.%s.default%i.value;' % (form_name, i, form_name, form_name, i)))
	
	# reset button
	form_root.append(etree.Element('input', {'type': 'reset', 'value': 'Reset'}))
	
	# interactive table
	form_table = etree.SubElement(form_root, 'table')
	for i in range(len(ingredients)):
		row = etree.SubElement(form_table, 'tr')
		
		field1 = etree.SubElement(row, 'td')
		if checkbox:
			field1_checkbox = etree.SubElement(etree.SubElement(field1, 'label'), 'input', {'type': 'checkbox'}) # insert the checkbox input inside a label so the entire text is clickable
			field1_checkbox.tail = ingredients[i][0]
		else:
			field1.text = ingredients[i][0]
		
		field2 = etree.SubElement(row, 'td')
		field2_input = etree.SubElement(field2, 'input', {
			'name': ('amount%i' % i),
			'value': ingredients[i][1],
			'readonly': '' # don't see a way to add boolean attributes, only key + value, so empty value
		})
		field2_input.tail = ' ' + ingredients[i][2] # tail will include the rest of the document too
	
	return form_root


class Ingredients (markdown.preprocessors.Preprocessor):
	def __init__ (self, default_scale_name = 'batches'):
		self.default_scale_name = default_scale_name
	
	def run (self, lines):
		parsed_html = html.fromstring('\n'.join(lines))
		ingredients_counter = 0
		for i in range(len(parsed_html)):
			if parsed_html[i].tag == INGREDIENTS_TAG:
				new_element = generate_ingredient_table(parsed_html[i], ('ingredients%i' % ingredients_counter))
				new_element.tail = parsed_html[i].tail
				parsed_html[i] = new_element
				ingredients_counter += 1
		
		return DEFAULT_HEADER + html.tostring(parsed_html)[3:-4].decode('utf-8').split('\n') # the [3:-4] is a workaround to remove the unwanted <p> tags added for the root tree


class IngredientExtension (markdown.extensions.Extension):
	def extendMarkdown (self, md):
		md.preprocessors.register(Ingredients(), 'ingredients', 175) # 175 is the suggested priority in the tutorial

def makeExtension (**kwargs):
	'''
	the 'markdown' module looks for this function by name
	'''
	return IngredientExtension(**kwargs)


