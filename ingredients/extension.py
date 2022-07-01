import markdown
from .ingredients import Ingredients
from .directions import Directions

class IngredientExtension (markdown.extensions.Extension):
	def extendMarkdown (self, md):
		md.preprocessors.register(Ingredients(), 'ingredients', 175) # 175 is the suggested priority in the tutorial
		md.preprocessors.register(Directions(), 'directions', 174)

def makeExtension (**kwargs):
	'''
	the 'markdown' module looks for this function by name
	'''
	return IngredientExtension(**kwargs)

