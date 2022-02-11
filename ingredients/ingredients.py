import re, markdown
from collections import defaultdict
from dataclasses import dataclass
from warnings import warn
from lxml import etree, html

DIRECTION_REGEX = '^\* \[ \] ' # matches GFM "* [ ] "
DIRECTIONS_FORMAT = '<label><input type="checkbox">%s</label><p>'

INGREDIENTS_TAG = 'ingredients' # appears as an HTML tag
INGREDIENTS_STYLE = 'margin-left: 3em' # style hardcoded to each ingredients table, currently set to indent it nicely
SCALE_TAG = 'scale' # appears as an HTML tag
DEFAULT_SCALE_NAME = 'batches'

DEFAULT_HEADER = ['<meta name="viewport" content="initial-scale=1">\
<style>\
input[type=checkbox] {\
    transform: scale(1.5);\
    margin-right: 0.5em;\
}\
input[type="text"] {\
    width: 4em;\
}\
input[type="number"] {\
    width: 4em;\
}\
</style>'] # think harder about where to put this

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

@dataclass
class IngredientsTable:
	ingredients: list
	total: float = 0

def parse_ingredients_table (text):
	ingredients = []
	has_consistent_unit = True # assume yes until proven no
	consistent_unit = None
	total = 0
	for line in text.split('\n'): 
		stripped_line = line.strip()
		if stripped_line != '':
			fields = re.split('\s*\|\s*', stripped_line)
			ingredient = fields[0]
			amount, unit = re.split('\s+', fields[1], 1)
			ingredients.append((ingredient, amount, unit))
			
			if has_consistent_unit:
				if consistent_unit is None:
					consistent_unit = unit
					total += float(amount)
				elif consistent_unit == unit:
					total += float(amount)
				else:
					has_consistent_unit = False
					total = None
	
	return(IngredientsTable(ingredients, total))


def generate_ingredient_table (element, form_name = None, scale_name = None, default_scale = None, checkbox = True):
	'''
	given an lxml.etree.Element of tag 'ingredients', return a new Element in the form of an HTML form containing the interactive table
	'''
	has_standalone_scale = 'scale' in element.keys()
	
	# get arguments from input (unless overridden by runtime arguments)
	if form_name is None:
		if 'form_name' in element.keys():
			form_name = element.get('form_name')
		else:
			form_name = 'ingredients'
	
	if scale_name is None:
		if 'scale_name' in element.keys():
			if has_standalone_scale: warn('"scale_name" is given for an ingredients table that already has a "scale" and is therefore ignored')
			scale_name = element.get('scale_name')
		else:
			scale_name = DEFAULT_SCALE_NAME
	
	if default_scale is None:
		if 'default_scale' in element.keys():
			if has_standalone_scale: warn('"default_scale" is given for an ingredients table that already has a "scale" and is therefore ignored')
			default_scale = element.get('default_scale')
		else:
			default_scale = '1'

	# parse the ingredients
	table = parse_ingredients_table(element.text)
	
	# create the new Element
	form_root = etree.Element('form', {
		'name': form_name,
		'style': INGREDIENTS_STYLE
	})
	if 'title' in element.keys():
		form_title = etree.SubElement(form_root, 'h4')
		form_title.text = element.get('title')
		if not has_standalone_scale: form_title.tail = scale_name + ': '
	else:
		if not has_standalone_scale: form_root.text = scale_name + ': '
	
	# hardcoded default values
	for i in range(len(table.ingredients)):
		form_root.append(etree.Element('input', {
			'type': 'hidden',
			'name': ('default%i' % i),
			'value': table.ingredients[i][1]
		}))
	if table.total is not None:
		form_root.append(etree.Element('input', {
			'type': 'hidden',
			'name': 'default_total',
			'value': str(table.total)
		}))
	
	# scale controls
	if not has_standalone_scale:
		scale_function = etree.SubElement(form_root, 'input', {
			'type': 'number',
			'name': 'scale',
			'value': default_scale,
			'onInput': ''
		})
		for i in range(len(table.ingredients)):
			scale_function.set('onInput', scale_function.get('onInput') + ('document.%s.amount%i.value = document.%s.scale.value * document.%s.default%i.value;' % (form_name, i, form_name, form_name, i)))
		if table.total is not None:
			scale_function.set('onInput', scale_function.get('onInput') + ('document.%s.total.value = document.%s.scale.value * document.%s.default_total.value;' % (form_name, form_name, form_name)))
		
		# reset button
		form_root.append(etree.Element('input', {'type': 'reset', 'value': 'Reset'}))
	
	# interactive table
	form_table = etree.SubElement(form_root, 'table')
	for i in range(len(table.ingredients)):
		ingredient, amount, unit = table.ingredients[i]
		row = etree.SubElement(form_table, 'tr')
		
		field1 = etree.SubElement(row, 'td')
		if checkbox:
			field1_checkbox = etree.SubElement(etree.SubElement(field1, 'label'), 'input', {'type': 'checkbox'}) # insert the checkbox input inside a label so the entire text is clickable
			field1_checkbox.tail = ingredient
		else:
			field1.text = ingredient
		
		field2 = etree.SubElement(row, 'td')
		field2_input = etree.SubElement(field2, 'input', {
			'type': 'text',
			'name': ('amount%i' % i),
			'value': str(float(default_scale) * float(amount)), # this is where the default scale is applied and errors may ensue
			'readonly': '' # don't see a way to add boolean attributes, only key + value, so empty value
		})
		field2_input.tail = ' ' + unit # tail will include the rest of the document too
	
	# automatic total
	if table.total is not None:
		form_table.tail = 'total: '
		total_box = etree.SubElement(form_root, 'input', {
			'type': 'text',
			'name': 'total',
			'value': str(float(default_scale) * table.total),
			'readonly': ''
		})
		total_box.tail = ' ' + table.ingredients[0][2] # unit, assuming all consistent because the total was given
	
	return form_root

def generate_scale(element, ingredients_tables, form_name, scale_name = None, default_scale = None):
	'''
	given an lxml.etree.Element of tag 'scale' and a list of ingredient table names and lengths, return a new Element in the form of an HTML form containing the interactive scale adjuster
	'''
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
	
	form_root = etree.Element('form', {'name': form_name})
	form_root.text = scale_name + ': '
	scale_function = etree.SubElement(form_root, 'input', {
		'type': 'number',
		'name': 'scale',
		'value': default_scale,
		'onInput': ''
	})
	reset_button = etree.SubElement(form_root, 'input', {'type': 'reset', 'value': 'Reset', 'onClick': ''})
	for ingredients_name, ingredient_count, has_common_unit in ingredients_tables:
		reset_button.set('onClick', reset_button.get('onClick') + ('document.%s.reset();' % ingredients_name))
		for i in range(ingredient_count):
			scale_function.set('onInput', scale_function.get('onInput') + ('document.%s.amount%i.value = document.%s.scale.value * document.%s.default%i.value;' % (ingredients_name, i, form_name, ingredients_name, i)))
		if has_common_unit:
			scale_function.set('onInput', scale_function.get('onInput') + ('document.%s.total.value = document.%s.scale.value * document.%s.default_total.value;' % (ingredients_name, form_name, ingredients_name)))
	
	return form_root


class Ingredients (markdown.preprocessors.Preprocessor):
	def run (self, lines):
		parsed_html = html.fromstring('\n'.join(lines))
		
		# first pass: enumerate the standalone scales
		ingredients_counter_first_pass = 0
		scale_tables = defaultdict(list) # each key is the name of a standalone scale and its value is a list of tuples: each tuple contains the name of an ingredients table and the number of ingredients in it
		for i in range(len(parsed_html)):
			if parsed_html[i].tag == INGREDIENTS_TAG:
				if 'scale' in parsed_html[i].keys(): # ingredients table linked to standalone scale
					scale_name = parsed_html[i].get('scale')
					table = parse_ingredients_table(parsed_html[i].text)
					scale_tables[scale_name].append((
						'ingredients%i' % ingredients_counter_first_pass, # table name
						len(table.ingredients), # table length
						table.total is not None # whether table has a total
					))
					
				ingredients_counter_first_pass +=1 
		
		# second pass: create the forms
		ingredients_counter_second_pass = 0
		for i in range(len(parsed_html)):
			if parsed_html[i].tag == INGREDIENTS_TAG:
				new_element = generate_ingredient_table(parsed_html[i], ('ingredients%i' % ingredients_counter_second_pass))
				new_element.tail = parsed_html[i].tail
				parsed_html[i] = new_element
				ingredients_counter_second_pass += 1
			elif parsed_html[i].tag == SCALE_TAG:
				scale_name = parsed_html[i].get('name')
				new_element = generate_scale(parsed_html[i], scale_tables[scale_name], scale_name)
				new_element.tail = parsed_html[i].tail
				parsed_html[i] = new_element
		
		assert(ingredients_counter_second_pass == ingredients_counter_first_pass)
		
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


