import re, markdown
from lxml import etree, html

DIRECTION_REGEX = '^\* \[ \] ' # matches GFM "* [ ] "
DIRECTIONS_FORMAT = '<label><input type="checkbox">%s</label><p>'

INGREDIENTS_TAG = 'ingredients' # appears as an HTML tag
INGREDIENTS_STYLE = 'margin-left: 3em' # style hardcoded to each ingredients table, currently set to indent it nicely
DEFAULT_SCALE_NAME = 'batches'

DEFAULT_HEADER = ['<meta name="viewport" content="initial-scale=1">'] # think harder about where to put this

class Directions (markdown.preprocessors.Preprocessor):
	def run (self, lines):
		new_lines = []
		in_section = False # track whether we are currently in a direction list (currently not used but might be nice if I use an HTML list)
		
		for line in lines:
			match = re.match(DIRECTION_REGEX, line)
			
			if in_section: # currently in a direction list
				if match: # still in the direction list
					new_lines.append(DIRECTIONS_FORMAT % line[match.end():])
				else: # end of the direction list
					new_lines.append(line)
			
			else: # not currently in a direction list
				if match: # start of a new direction list
					new_lines.append(DIRECTIONS_FORMAT % line[match.end():])
				else: # still not in a direction list
					new_lines.append(line)
		
		if in_section: raise RuntimeError('missing %s tag' % DIRECTIONS_CLOSE)
		return new_lines


def generate_ingredient_table (element, form_name = None, scale_name = None, default_scale = None, checkbox = True):
	'''
	given an lxml.etree.Element of tag 'ingredients', return a new Element in the form of an HTML form containing the interactive table
	'''
	
	# get arguments from input (unless overridden by runtime arguments)
	if form_name is None:
		if 'form_name' in element.keys():
			form_name = element.get('form_name')
		else:
			form_name = 'ingredients'
	
	if scale_name is None:
		if 'scale_name' in element.keys():
			scale_name = element.get('scale_name')
		else:
			scale_name = DEFAULT_SCALE_NAME
	
	if default_scale is None:
		if 'default_scale' in element.keys():
			default_scale = element.get('default_scale')
		else:
			default_scale = '1'

	# parse the text contents
	ingredients = []
	for line in element.text.split('\n'):
		stripped_line = line.strip()
		if stripped_line != '':
			fields = re.split('\s*\|\s*', stripped_line)
			ingredients.append([fields[0]] + re.split('\s+', fields[1], 1))
		
	# create the new Element
		
	form_root = etree.Element('form', {
		'name': form_name,
		'style': INGREDIENTS_STYLE
	})
	if 'title' in element.keys():
		form_title = etree.SubElement(form_root, 'h4')
		form_title.text = element.get('title')
		form_title.tail = scale_name + ': '
	else:
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
		'value': default_scale,
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
			'value': str(float(default_scale) * float(ingredients[i][1])), # this is where the default scale is applied and errors may ensue
			'readonly': '' # don't see a way to add boolean attributes, only key + value, so empty value
		})
		field2_input.tail = ' ' + ingredients[i][2] # tail will include the rest of the document too
	
	return form_root


class Ingredients (markdown.preprocessors.Preprocessor):
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
		md.preprocessors.register(Directions(), 'directions', 174)

def makeExtension (**kwargs):
	'''
	the 'markdown' module looks for this function by name
	'''
	return IngredientExtension(**kwargs)


