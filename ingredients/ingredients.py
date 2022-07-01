import re, markdown
from collections import defaultdict
from dataclasses import dataclass
from lxml import etree, html

# output formats
INGREDIENTS_STYLE = 'margin-left: 3em' # style hardcoded to each ingredients table, currently set to indent it nicely
DEFAULT_SCALE_LABEL = 'batches'
DEFAULT_HEADER = '''<meta name="viewport" content="initial-scale=1">
<style>
input[type=checkbox] {
	transform: scale(1.5);
	margin-right: 0.5em;
}
input[type="text"] {
	width: 4em;
}
input[type="number"] {
	width: 4em;
}
</style>''' # think harder about where to put this

# input formats
INGREDIENTS_REGEX = re.compile('```\{ingredients,?(.*?)\}(.*?)```', re.DOTALL) # returns the options and the table as groups
SCALE_REGEX = re.compile('<!scale,?(.*?)>', re.DOTALL)


def parse_opts (text):
	'''
	parse a simple batch of options in the form "option1 = value, option2 = value" with spaces optional
	return a dictionary; keys and values will all be strings
	simple hack: make it resemble a dummy HTML tag and use the HTML parser!
	'''
	return dict(html.fromstring('<dummy,' + text + '>').items())

@dataclass
class IngredientTable:
	ingredients: list
	total: float = 0

def parse_ingredient_table (text):
	ingredients = []
	has_consistent_unit = True # assume yes until proven no
	consistent_unit = None
	total = 0
	for line in text.split('\n'): 
		stripped_line = line.strip('\s\0')
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
	
	return(IngredientTable(ingredients, total))


def format_ingredient_table (
	table,
	title = None,
	name = None,
	scale = None,
	scale_label = DEFAULT_SCALE_LABEL,
	default_scale = 1,
	checkbox = True
):
	'''
	given an IngredientTable, return an HTML form containing the interactive table
	'''
	
	# create the new Element
	form_root = etree.Element('form', {
		'name': name,
		'style': INGREDIENTS_STYLE
	})
	if title is not None:
		form_title = etree.SubElement(form_root, 'h4')
		form_title.text = title
		if scale is None: form_title.tail = scale_label + ': '
	else:
		if scale is None: form_root.text = scale_label + ': '
	
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
	if scale is None:
		scale_function = etree.SubElement(form_root, 'input', {
			'type': 'number',
			'name': 'scale',
			'value': default_scale,
			'onInput': ''
		})
		for i in range(len(table.ingredients)):
			scale_function.set('onInput', scale_function.get('onInput') + ('document.%s.amount%i.value = document.%s.scale.value * document.%s.default%i.value;' % (name, i, name, name, i)))
		if table.total is not None:
			scale_function.set('onInput', scale_function.get('onInput') + ('document.%s.total.value = document.%s.scale.value * document.%s.default_total.value;' % (name, name, name)))
		
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
	
	return html.tostring(form_root).decode('utf-8')

def generate_scale(ingredients_tables, name, scale_label = DEFAULT_SCALE_LABEL, default_scale = 1):
	'''
	given a list of ingredient table names and lengths, return an HTML form containing the interactive scale adjuster
	'''
	
	form_root = etree.Element('form', {'name': name})
	form_root.text = scale_label + ': '
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
			scale_function.set('onInput', scale_function.get('onInput') + ('document.%s.amount%i.value = document.%s.scale.value * document.%s.default%i.value;' % (ingredients_name, i, name, ingredients_name, i)))
		if has_common_unit:
			scale_function.set('onInput', scale_function.get('onInput') + ('document.%s.total.value = document.%s.scale.value * document.%s.default_total.value;' % (ingredients_name, name, ingredients_name)))
	
	return html.tostring(form_root).decode('utf-8')


class Ingredients (markdown.preprocessors.Preprocessor):
	def __init__ (self):
		self.scale_tables = defaultdict(list) # each key is the name of a standalone scale and its value is a list of tuples: each tuple contains the name of an ingredients table, the number of ingredients in it, and whether it includes a total
		self.ingredients_counter = 0
	
	def generate_ingredient_tables (self, match):
		'''
		generate an ingredients table, but name it uniquely after the counter (then increment that) and note if there's a standalone scale that should point to it
		'''
		opts = parse_opts(match.groups()[0])
		parsed_table = parse_ingredient_table(match.groups()[1])
		table_name = 'ingredients%i' % self.ingredients_counter
		if 'scale' in opts:
			self.scale_tables[opts['scale']].append((
				table_name,
				len(parsed_table.ingredients), # table ingredients
				parsed_table.total is not None # whether table has a total
			))
		self.ingredients_counter += 1
		return format_ingredient_table(parsed_table, name = table_name, **opts)
	
	def generate_scales (self, match):
		opts = parse_opts(match.groups()[0])
		return generate_scale(self.scale_tables[opts['name']], **opts)
	
	def run (self, lines):
		textwall = '\n'.join(lines)
		
		# first pass: generate tables and enumerate the standalone scales
		textwall = INGREDIENTS_REGEX.sub(self.generate_ingredient_tables, textwall)
		
		# second pass: generate standalone scales
		textwall = SCALE_REGEX.sub(self.generate_scales, textwall)
		
		return (DEFAULT_HEADER + textwall).splitlines()

