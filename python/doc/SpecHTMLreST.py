#!/usr/bin/env python3
#
#  %W%  %G% CSS
#
#  "pyspec" Release %R%

#%.src: rst/%.rst
#        rst2html.py --template=page.tpl $(RSTFLAGS) $< $@
#        ./postproc.py $@


"""
A minimal front end to the Docutils Publisher, producing HTML.
"""
TPL_HELPPAGE = "spec_help.tpl"

import sys
import re
import os

try:
   from docutils.core      import publish_cmdline, publish_file, Publisher
   from docutils.writers   import html4css1
   from docutils import nodes     
   from docutils.nodes     import reprunicode
   from docutils.writers.html4css1 import HTMLTranslator
except ImportError:
   print("Cannot import docutils")
   sys.exit(1)

if "-check" in sys.argv:
   sys.exit(0)

related_block = """
 <div class="related">
     <h3>%s</h3>
     <ul>
       %s
     </ul>
 </div>
"""

related_index_link = '      <li><a href="index.html">help index</a></li>\n'
related_link = '      <li><a href="%(url)s">%(name)s</a></li>\n'

content_link = '<li><a href="#%s">%s</a></li>\n'

class SpecHTMLTranslator(HTMLTranslator):

   def __init__(self,document):

       HTMLTranslator.__init__(self,document)

       self.in_related    = 0
       self.related       = ""
       self.related_links = ""

       #self.restro = re.compile(r"\*\*(?P<emph>[*()#+/a-zA-Z0-9\[\]\-_]+)\*\*")
       #self.remph  = re.compile(r"\*(?P<emph>[()#+/a-zA-Z0-9\-_]+)\*")

       # (?<!\\)*  means asterisk not preceded by a \
       self.restro = re.compile(r"\*\*(?!\ )(?P<emph>[\\@=\-()\:#+/a-zA-Z0-9_\ ]+)(?<!\ )\*\*")
       self.remph  = re.compile(r"\*(?!\ )(?P<emph>[\\@=\-()\:#+/a-zA-Z0-9_\ ]+)(?<!\ )\*")

       self.contentsbody = ""

   def visit_document(self,node):
       HTMLTranslator.visit_document(self,node)
       self.doctitle = node.get('title')

   def visit_subtitle(self,node):
       HTMLTranslator.visit_subtitle(self,node)
       self.docsubtitle = node.get('names')[0]

   def visit_section(self,node):

       try:
         nodename = reprunicode(node['names'][-1]).lower()

         try:
               idanchor = node.__dict__['attributes']['ids'][0]
               contentlink = content_link % (idanchor, nodename )
               self.contentsbody += contentlink 
         except:
               print("cannot get content info for node "+nodename)

         if nodename.find("related")  == 0 or \
            nodename.find("other")    == 0 :
               node['classes'].append('related-section')
               self.in_related = 1
               self.related_title = nodename
         elif nodename.find("see also") == 0:
               node['classes'].append('see-also')
               self.in_related = 1
               self.related_title = nodename
       except:
          pass 

       HTMLTranslator.visit_section(self,node)

   def depart_section(self,node):
      if self.in_related == 1:
         if self.related_title == "see also":
            self.related_links += related_index_link 
         self.related += related_block % (self.related_title.capitalize(), self.related_links)
         self.related_links = ""
         self.related_title = ""
         self.in_related = 0

      HTMLTranslator.depart_section(self,node)

   def depart_table(self, node):
       if len(self.context):
           self.compact_p = self.context.pop()
       self.body.append("</table>\n")

   def visit_reference(self,node):
       HTMLTranslator.visit_reference(self,node)
       if self.in_related:
          if 'name' in node.__dict__['attributes'].keys():
              vals = {'url': node.get('refuri'), 'name': node['name'] }
          else: 
              vals = {'url': node.get('refuri'), 'name': node.get('refuri') }
          self.related_links += related_link % vals


   def depart_document(self,node):
      if self.related_links != "":
         self.related += related_block % self.related_links

      self.contents = "<ul>\n%s</ul>\n" % self.contentsbody

      HTMLTranslator.depart_document(self,node)


   """
    Tables without borders
    - amazingly the border is set to 1 in the html4css1 writer, and not configurable 
      through css
   """
   def visit_table(self, node):
      classes = ' '.join(['docutils', self.settings.table_style]).strip()
      self.body.append(
           self.starttag(node, 'table', CLASS=classes, border="0"))

   """
    Rewrite the whole visit_literal from the original docutils 0.8.1
    html4css1 writer. 
    
    This solves two issues:
    - stop using tt that is a not supported tag in HTML-5 (span is used instead)
    - allow for emphasis inside literal blocks (necessary for spec and c-plot
      function parameters.  This functionality should actually be part of the parser
      but it would affect too many classes and compromise later compatibility
   """ 
   def visit_literal(self, node):
        """
        Inside literal will replace a string of letter, numbers and hyphens surrounded by * to be emphasized
        """ 

        """Process text to prevent tokens from wrapping."""
        self.body.append(
            self.starttag(node, 'span', '', CLASS='docutils literal'))
        text = node.astext()
        for token in self.words_and_spaces.findall(text):
            if token.strip():
                # Protect text like "--an-option" and the regular expression
                # ``[+]?(\d+(\.\d*)?|\.\d+)`` from bad line wrapping
		#if self.sollbruchstelle.search(token):
		#    toappend = '<span class="pre">%s</span>' % self.encode(token)
		#else:
                toappend = self.encode(token)
            elif token in ('\n', ' '):
                # Allow breaks at whitespace:
                toappend = token
            else:
                # Protect runs of multiple spaces; the last space can wrap:
                toappend = '&nbsp;' * (len(token) - 1) + ' '
            
            toappend = self.process_Text(toappend)
            self.body.append(toappend)
        self.body.append('</span>')
        # Content already processed:
        raise nodes.SkipNode

   def visit_literal_block(self, node):

        self.body.append(self.starttag(node, 'pre', CLASS='literal-block'))

        text = node.astext()
        text = self.process_Text(text)

        self.body.append( text )

        self.body.append('\n</pre>\n')

        # Content already processed:
        raise nodes.SkipNode

   def depart_literal_block(self, node):
        pass

   def process_Text(self, text):
       retstr = text

       # reserve escaped backlashes (in text as \\)
       retstr = re.sub("\\\\\\\\","&7&", retstr)

       # reserve escaped asterisks (in text as \*)
       retstr = re.sub("\\\\\*", "@=@", retstr)

       retstr = self.restro.sub("<b>\g<emph></b>",retstr )
       retstr = self.remph.sub("<i>\g<emph></i>",retstr )

       # restore escaped asterisks as normal asterisks
       retstr = re.sub("@=@", "*", retstr)

       # restore escaped backslashes as normal backslashes
       retstr = re.sub("&7&", "\\\\",  retstr)

       return retstr

class SpecHTMLWriter(html4css1.Writer):

    def __init__(self, template=None):
      html4css1.Writer.__init__(self)
      self.translator_class = SpecHTMLTranslator
      self.template_str = ""
      self.extraclass   = None

      if template:
          self.setTemplate(template)

    def setTemplate(self, templ_file):
      self.template_file = templ_file
      if os.path.exists(self.template_file):
          self.template_str = open(self.template_file).read()
      else:
          self.template_str = ""

    def process(self, filename, outfilename="/dev/null", template=None, extraclass=None):

       if template:
           self.setTemplate(template)

       self.extraclass = extraclass
       convbuf = publish_file( source_path=filename, destination_path=outfilename, writer_name='html',  writer=self) 
       return(self.doctitle, self.docsubtitle, convbuf)

    def apply_template(self):

      if not self.template_str:
         print("NO TEMPLATE")
         raise BaseException("NoTemplate")

      subs = self.interpolation_dict()

      subs['related']     = self.visitor.related
      subs['description'] = self.visitor.doctitle
      subs['contents']    = self.visitor.contents 

      return self.template_str % subs

    def translate(self):
        html4css1.Writer.translate(self)
        self.doctitle    = self.visitor.doctitle
      
        try:
            self.docsubtitle = self.visitor.docsubtitle
        except:
            self.docsubtitle = "NO SUBTITLE"

def dOneFile(filename, template=None):

    from os.path import dirname, abspath

    if template is None:
        template = os.path.join(dirname(abspath(__file__)), "spec_help.tpl")

    writer = SpecHTMLWriter(template=template)
    return writer.process( filename )

def process(filename, outfile=None, template=None):
    buf = open(filename).read()
    title, subtitle, converted = dOneFile(filename , template)

    if not outfile:
       fd = sys.stdout
    else:
       fd = open(outfile,"w")

    fd.write(converted)

if __name__ == '__main__':

    import sys

    if "-d" in sys.argv:
        idx = sys.argv.index("-d")
        sys.argv.pop(idx)
        DEBUG = 1

    if len(sys.argv) < 2:
        print("Usage: %s filename [outfile]", sys.argv[0])
        sys.exit(0)

    filename = sys.argv[1]

    if len(sys.argv) >= 3:
        outfile = sys.argv[2]
    else:
        outfile = None

    process(filename, outfile)

