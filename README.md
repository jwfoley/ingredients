readme goes here

# installation

1. install Python however appropriate
1. install the module 'markdown', which this is an extension for, e.g.

    $ sudo pip3 install markdown

1. install this module

    $ sudo ./setup.py install

# syntax

to create a list of ingredients, set off a section of your Markdown file with `<ingredients>` and `</ingredients>` tags, then between them, on each line, use this format:

    ingredient | amount unit

spacing is ignored except you must have whitespace between the amount, which must be a machine-readable numeral (e.g. `1.25` instead of `1 1/4`), and the unit, which can be any string of text (e.g. `fl. oz.`)

a complete example:

    <ingredients>
    	flour | 1.25 c
    	sugar or Splenda | 2 tbsp
    	baking powder | 2 tsp
    	salt | 0.5 tsp
    	water | 1.25 c
    	oil | 1 tbsp
    	vanilla extract or imitation vanilla | 1 tbsp
    </ingredients>



the result will be a simple HTML table of ingredients and amounts, except each amount is automatically scaled from an interactive text box that sets the number of batches, which can be reset to 1 with a neighboring button

anyone can view the HTML output in any modern web browser without installing this or any other software

more features to come

# simple command-line usage

    $ python3 -m markdown -x ingredients [input.md] > [output.html]

