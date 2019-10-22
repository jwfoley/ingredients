import re, markdown

DIRECTIONS_OPEN = '<directions>'
DIRECTIONS_CLOSE = '</directions>'
DIRECTIONS_HEADER = '<dl>'
DIRECTIONS_FOOTER = '</dl>'
DIRECTIONS_FORMAT = '<label><input type="checkbox">%s</label><p>'

INGREDIENTS_OPEN = '<ingredients>'
INGREDIENTS_CLOSE = '</ingredients>'

DEFAULT_HEADER = ['<dl><meta name="viewport" content="initial-scale=1"></dl>']

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



class Ingredients (markdown.preprocessors.Preprocessor):
	def __init__ (self, scale_name = 'batches'):
		self.scale_name = scale_name
	
	def generate_table (self, ingredients):
		table_lines = ['<dl>', '\t<form name="ingredients">']
		
		# hardcoded default values
		table_lines.extend(['\t\t', '\t\t<!--hardcoded default values-->'])
		for i in range(len(ingredients)):
			table_lines.append('\t\t<input type="hidden" name="default%i" value="%s">' % (i, ingredients[i][1]))
		
		# scale control
		table_lines.extend(['\t\t', '\t\t<!--scale controls-->', ('\t\t%s: <input name="scale" value=1 onInput="' % self.scale_name)])
		for i in range(len(ingredients)):
			table_lines.append('\t\t\tdocument.ingredients.amount%i.value = document.ingredients.scale.value * document.ingredients.default%i.value;' % (i, i))
		
		table_lines.extend(['\t\t">', '\t\t<input type="reset" value="Reset">'])
		
		# table with automatic fields
		table_lines.extend(['\t\t', '\t\t<!--automatically calculated fields-->', '\t\t<table>'])
		for i in range(len(ingredients)):
			table_lines.extend([
				'\t\t\t<tr>',
				'\t\t\t\t<td>%s</td>' % ingredients[i][0],
				'\t\t\t\t<td><input name="amount%i" value="%s" readonly> %s</td>' % (i, ingredients[i][1], ingredients[i][2]),
				'\t\t\t</tr>'
			])
			
		table_lines.append('\t\t</table>')
		
		table_lines.extend(['\t\t', '\t</form>', '</dl>'])
		return table_lines
	
	def run (self, lines):
		new_lines = DEFAULT_HEADER
		in_section = False # track whether we are currently in the section
		ingredients = []
		
		for line in lines:
			line = line.rstrip()
			if in_section: # currently in the section
				if INGREDIENTS_CLOSE in line: # find end of section
					new_lines.extend(self.generate_table(ingredients))
					in_section = False
					ingredients = []
					
				else: # parse a line of the section
					fields = re.split('\s*\|\s*', line.lstrip())
					ingredients.append([fields[0]] + re.split('\s+', fields[1], 1))
				
			elif INGREDIENTS_OPEN in line: # find beginning of section
				in_section = True
			
			else:
				new_lines.append(line)
		
		if in_section: raise RuntimeError('missing %s tag' % INGREDIENTS_CLOSE)
		return new_lines


class IngredientExtension (markdown.extensions.Extension):
	def extendMarkdown (self, md):
		md.preprocessors.register(Ingredients(), 'ingredients', 175) # 175 is the suggested priority in the tutorial

def makeExtension (**kwargs):
	'''
	the 'markdown' module looks for this function by name
	'''
	return IngredientExtension(**kwargs)


