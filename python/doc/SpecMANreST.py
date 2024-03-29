#!/usr/bin/env python3 
# -*- coding: utf-8 -*-
#
#  %W%  %G% CSS
#
#  "pyspec" Release %R%

"""
A minimal front end to the Docutils Publisher, producing HTML.
"""

import sys, re

DEBUG = 0

try:
    from docutils.core      import publish_cmdline, publish_file, Publisher
    from docutils.writers   import manpage
    from docutils           import nodes
    from docutils.nodes     import reprunicode
    from docutils.writers.manpage import Writer, Translator, Table
    from docutils.core import publish_string
except ImportError:
    print("Cannot import docutils")
    sys.exit(1)

if "-check" in sys.argv:
    sys.exit(0)

DEFINITION_LIST_INDENT = 5
FIELD_LIST_INDENT = 7
OPTION_LIST_INDENT = 7
BLOCKQUOTE_INDENT = 4
LITERALBLOCK_INDENT = 3


def debug(fn):
    if DEBUG:
       def wrapped(self, node):
          self.body.append('.\" <ENTER : %s >\n' % fn.__name__)
          return fn(self, node)
    else:
       def wrapped(self, node):
          return fn(self, node)
    return wrapped

class SpecMANTranslator(Translator):

   document_start = "spec reStructuredText documentation"

   def __init__(self,document):

       Translator.__init__(self,document)

       self.restro = re.compile(r"\*\*(?!\ )(?P<emph>[\\@=\-()\:#+/a-zA-Z0-9_\ ]+)(?<!\ )\*\*")
       self.remph  = re.compile(r"\*(?!\ )(?P<emph>[\\@=\-()\:#+/a-zA-Z0-9_\ ]+)(?<!\ )\*")
       self.keyw   = re.compile(r"(?P<keyw>[a-zA-Z0-9_]+)\s?\:\s?(?P<value>.*?)$")
 
       self.deflist_level = 0

       self.hanging    = 0
       self.inlistitem = 0

       self.intitle    = 0
       self.insection  = 0
       self.insubsect  = 0
       self.section_visited = 0

       self.prevent_nestfont = 0
       self.literalblock = 0

       self.doctitle = ""
       self.docsubtitle = ""
 
       self.defs = {
                'indent' : ('.RS %dm\n', '.RE\n'),

                'definition_list' : ('', ''),
                'definition_list_item' : ('.HP %dm\n', ''),
                'field_name' : ('.HP 5m\n', '\n'),
                'literal' : ('\\fB', '\\fP'),
                'literal_block' : ('.sp\n.nf\n.ft CB\n', '\n.ft P\n.fi\n'),

                'option_list_item' : ('.HP 5m\n', ''),

                'reference' : (r'\fI\%', r'\fP'),
                'emphasis': ('\\fB', '\\fP'),
                'strong' : ('\\fB', '\\fP'),
                'term' : ('\n', '\n'),
                'title_reference' : ('\\fI', '\\fP'),

                'topic-title' : ('.SH ',),
                'sidebar-title' : ('.SH ',),

                'problematic' : ('\n.nf\n', '\n.fi\n'),
                    }

       self._docinfo = {
                "title" : "", "title_upper": "",
                "subtitle" : "",
                "manual_section" : "", "manual_group" : "",
                "author" : [],
                "date" : "",
                "copyright" : "",
                "version" : "",
                "versioninfo" : "",
            }


   @debug
   def visit_versioninfo(self,node):
       self._docinfo["versioninfo"] =  " ".join( node.content )

   @debug
   def depart_versioninfo(self,node):
       pass

   @debug
   def visit_document(self,node):
       Translator.visit_document(self,node)
       self.doctitle = node.get('title')

   @debug
   def depart_document(self,node):
       pass

   @debug
   def visit_title(self, node):

       self.deflist_level = 0
       self.hanging       = 0

       if isinstance(node.parent, nodes.topic):
           self.body.append(self.defs['topic-title'][0])
       elif isinstance(node.parent, nodes.sidebar):
           self.body.append(self.defs['sidebar-title'][0])
       elif isinstance(node.parent, nodes.admonition):
           self.body.append('.IP "')

       elif self.section_level == 0:
           self._docinfo['title_upper'] = node.astext().upper()
           self.intitle = 1
       elif self.section_level == 1:
           self.insection = 1
       else:
           self.insubsect = 1

       self._keepbody = self.body
       self.body = []


   def depart_title(self, node):

        title = ''.join(self.body)
        self.body = self._keepbody

        if isinstance(node.parent, nodes.admonition):
            self.body.append('"')

        if self.insection:
            self.insection = 0
            title = re.sub(r'"',r'\\(dq',title)
            self.body.append('.SH \"%s\"\n.rs\n' % title )
           
        if self.insubsect:
            self.insubsect = 0
            title = re.sub(r'"',r'\\(dq',title)
            self.body.append('.SH \"%s\"\n' % title )

        if self.intitle:
            self.intitle = 0
            self._docinfo["title"] = title

        # if we miss level 0. there is a problem
        if not self.doctitle and self.section_level == 1 :
           self.doctitle = "NO TITLE"
           self._docinfo["title"] = title

        if not self.docsubtitle and self.section_level == 2 :
           self.docsubtitle = "Document with no title. Please provide one"
           self._docinfo["subtitle"] = title


   @debug
   def visit_subtitle(self, node):
        if isinstance(node.parent, nodes.sidebar):
            self.body.append(self.defs['strong'][0])
        elif isinstance(node.parent, nodes.document):
            # self.visit_docinfo_item(node, 'subtitle')
            # to catch and process subtitle we need to skip docinfo call
            self.subtitle_raw = node.astext()
            self.insubtitle = 1
            self._keepbody = self.body
            self.body = []

            self._docinfo_keys.append('subtitle')
        elif isinstance(node.parent, nodes.section):
            self.body.append(self.defs['strong'][0])

   def depart_subtitle(self, node):
        # document subtitle calls SkipNode
        self.subtitle = ''.join( self.body )
        self._docinfo['subtitle'] = self.subtitle
        self.docsubtitle = self.subtitle
        self.body = self._keepbody
        self.body.append(self.defs['strong'][1]+'\n.PP\n')

   def visit_comment(self, node, sub=re.compile('-(?=-)').sub):
       ## search for keywords in comments only if we have not visited
       # a section yet
       if self.section_visited == 0:
            mat = self.keyw.search( node.astext() )
            if mat:
                 keyw  = mat.group("keyw")
                 value = mat.group("value")
                 self._docinfo[keyw] = value

       self.body.append(self.comment(node.astext()))
       raise nodes.SkipNode

   def header(self):
       if self._docinfo['title']:
           self._docinfo['title_upper'] = self._docinfo['title']

       # Allow for basic formatting in versioninfo

       self.prevent_nestfont = 1
       self._docinfo['versioninfo'] = self.process_Text( self._docinfo['versioninfo'] )
       self.prevent_nestfont = 0

       tmpl  = (".TH %(versioninfo)s\n"
                ".ds HF R\n"
                ".na\n"      #  no justification
                ".hy 0\n"    #  do not hyphenate words
                ".SH NAME\n"
               "%(title)s \- %(subtitle)s\n")

       return tmpl % self._docinfo

   def visit_paragraph(self, node):
       self.ensure_eol()
       if not self.first_child(node):
           self.body.append('.sp\n')

   def first_child(self, node):
       first = isinstance(node.parent[0], nodes.label) # skip label
       for child in node.parent.children[first:]:
           if isinstance(child, nodes.Invisible):
               continue
           if child is node:
               return 1
           break
       return 0

   @debug
   def visit_section(self,node):
       self.section_visited += 1
       Translator.visit_section(self,node)

   def myindent(self, by=5):
        # if we are in a section ".SH" there already is a .RS
        self.body.append(self.defs['indent'][0] % by)

   def indent(self,by=0):
       pass

   def mydedent(self, by=5):
        self.body.append(self.defs['indent'][1])
   def dedent(self,by=0):
       pass


   """
    Change from original docutils manpage Writer 
    is that here we use our own Table class
   """
   def visit_table(self, node):
      self._active_table = SpecTable()

   def depart_table(self, node):
      self.ensure_eol()
      self.body.extend(self._active_table.as_list())
      self._active_table = None

   """
    This solves the issues:
    - allow for emphasis inside literal blocks (necessary for spec and c-plot
      function parameters.  This functionality should actually be part of the parser
      but it would affect too many classes and compromise later compatibility
   """ 
   @debug
   def visit_literal(self, node):
        """
        Inside literal will replace a string of letter, numbers and hyphens surrounded by * to be emphasized
        """ 

        """Process text to get away extra formatting in literals (extra formatting is used in HTML, but not supported here)"""

        self.prevent_nestfont = 1
        text = self.process_Text( node.astext() )

        self.body.append(self.defs['literal'][0])
        self.body.append(text)
        self.body.append(self.defs['literal'][1])

        # Content already processed:
        raise nodes.SkipNode

   @debug
   def depart_literal(self, node):
        self.prevent_nestfont = 0

   def visit_Text(self, node):
        text = self.process_Text( node.astext() )
        self.body.append(text)

   def process_Text(self, text):
        # reserve escaped backlashes (in text as \\)
        text = re.sub("\\\\\\\\","&7&",text)

        # reserve escaped asterisks (in text as \*)
        text = re.sub("\\\\\*", "@=@",text)

        text = text.replace('\\','\\e')

        replace_pairs = [
	    (u'-', r'\-'),
	    (u'\'', r'\(aq'),
	    (u'`', r'\(ga'),
            ]
        for (in_char, out_markup) in replace_pairs:
            text = text.replace(in_char, out_markup)

        # unicode
        text = self.deunicode(text)
        if self._in_literal:
            # prevent interpretation of "." at line start
            if text[0] == '.':
                text = '\\&' + text
            text = text.replace('\n.', '\n\\&.')


        if self.prevent_nestfont:
           text = self.restro.sub(r"\g<emph>",text )
           text = self.remph.sub(r"\g<emph>",text )
        else:
           text = self.restro.sub(r"\\fB\g<emph>\\fP",text )
           text = self.remph.sub(r"\\fI\g<emph>\\fP",text )

        # restore escaped asterisks as normal asterisks
        text = re.sub("@=@", "*", text)
        # restore escaped backlashes as normal backslashes
        text = re.sub("&7&", "\\\\e",  text)


        return text
        
   def depart_Text(self, node):
       pass

   @debug
   def visit_bullet_list(self, node):
        self.list_start(node)

   @debug
   def depart_bullet_list(self, node):
        self.list_end()

   @debug
   def visit_literal_block0(self, node):

        """Process text to get away extra formatting in literals (extra formatting is used in HTML, but not supported here)"""
        """
          Indent the whole literal block by two spaces to avoid characters in first column 
          to be interpreted by nroff
        """
        #text = re.sub("\n","\n  ",text )
        #text = "  "+text

        self.body.append(self.defs['literal_block'][0])
        self.body.append( text )
        self.body.append(self.defs['literal_block'][1])

        # Content already processed:
        raise nodes.SkipNode

   @debug
   def depart_literal_block0(self, node):
        pass

   def visit_literal_block(self, node):
        if self.inlistitem and self.hanging == self.deflist_level: 
           self.hanging += 1
           self.myindent(DEFINITION_LIST_INDENT)
        self.myindent(LITERALBLOCK_INDENT)
        self.body.append(self.defs['literal_block'][0])
        self._in_literal = True
        self.prevent_nestfont = 1
        self.literalblock = 1

   def depart_literal_block(self, node):
        self._in_literal = False
        self.prevent_nestfont = 0
        self.literalblock = 0
        self.body.append(self.defs['literal_block'][1])
        self.mydedent()

   @debug
   def visit_block_quote(self, node):
        self.body.append(".sp\n")
        self.prevent_nestfont = 1
        if self.inlistitem and self.hanging == self.deflist_level: 
           self.hanging += 1
           self.myindent(DEFINITION_LIST_INDENT)
        self.myindent(BLOCKQUOTE_INDENT)

   @debug
   def depart_block_quote(self, node):
        self.prevent_nestfont = 0
        self.mydedent()

   @debug
   def visit_definition_list_item(self, node):
        self.inlistitem = 1
        self.body.append(self.defs['definition_list_item'][0] % DEFINITION_LIST_INDENT)
        self.body.append('."')

   @debug
   def depart_definition_list_item(self, node):
        if self.hanging > self.deflist_level: 
            self.mydedent()
            self.hanging -= 1
        self.inlistitem = 0
        self.body.append(self.defs['definition_list_item'][1])

   @debug
   def visit_definition_list(self, node):
       self.deflist_level += 1
       self.hanging       += 1
       if self.deflist_level > 1:
          self.myindent(DEFINITION_LIST_INDENT)
          self.body.append('.sp\n.PD 0.2v\n')
       # set a reference with no indent to return to
       self.myindent(0)

   @debug
   def depart_definition_list(self, node):

       if self.deflist_level == 2:
          self.body.append('.PD\n')

       self.mydedent()
       self.deflist_level -=1

   @debug
   def visit_definition(self,node):
       self.body.append('\- \n')

   @debug
   def visit_enumerated_list(self, node):
        self.list_start(node)

   @debug
   def depart_enumerated_list(self, node):
        self.list_end()

   @debug
   def visit_field(self, node):
        pass

   @debug
   def depart_field(self, node):
        pass

   @debug
   def visit_field_body(self, node):
        if self._in_docinfo:
            name_normalized = self._field_name.lower().replace(" ","_")
            self._docinfo_names[name_normalized] = self._field_name
            self.visit_docinfo_item(node, name_normalized)
            raise nodes.SkipNode

   @debug
   def depart_field_body(self, node):
        pass

   @debug
   def visit_field_list(self, node):
        self.myindent(FIELD_LIST_INDENT)

   @debug
   def depart_field_list(self, node):
        self.mydedent()

   @debug
   def visit_field_name(self, node):
        if self._in_docinfo:
            self._field_name = node.astext()
            raise nodes.SkipNode
        else:
            self.body.append(self.defs['field_name'][0])

   @debug
   def depart_field_name(self, node):
        self.body.append(self.defs['field_name'][1])

   @debug
   def visit_figure(self, node):
        self.myindent(2.5)
        self.myindent(0)

   @debug
   def depart_figure(self, node):
        self.mydedent()
        self.mydedent()


    # WHAT should we use .INDENT, .UNINDENT ?
   @debug
   def visit_line_block(self, node):
        self._line_block += 1
        if self._line_block == 1:
            # TODO: separate inline blocks from previous paragraphs
            # see http://hg.intevation.org/mercurial/crew/rev/9c142ed9c405
            # self.body.append('.sp\n')
            # but it does not work for me.
            self.body.append('.nf\n')
        else:
            self.body.append('.in +2\n')

   @debug
   def depart_line_block(self, node):
        self._line_block -= 1
        if self._line_block == 0:
            self.body.append('.fi\n')
            self.body.append('.sp\n')
        else:
            self.body.append('.in -2\n')

   @debug
   def visit_option_list(self, node):
        self.myindent(OPTION_LIST_INDENT)

   @debug
   def depart_option_list(self, node):
        self.mydedent()

   def depart_paragraph(self, node):
        self.body.append('\n')

   @debug
   def visit_system_message(self,node,name=None):
       raise nodes.SkipNode

class SpecTable(Table):
     """
     Redefines the way a table is drawn from the original 
     doctutils manpage writer.

     Changes:  set no border
     """

     def __init__(self):
        self._rows = []
        self._options = ['']
        self._tab_char = '\t'
        self._coldefs = []

     def as_list(self):
        text = ['.TS\n']
        text.append(' '.join(self._options) + ';\n')
        text.append('%s .\n' % (' '.join(self._coldefs)))
        for row in self._rows:
            # row = array of cells. cell = array of lines.
            #text.append('_\n')       # line above
            #text.append('T{\n')
            for i in range(len(row)):
                cell = row[i]
                self._minimize_cell(cell)
                text.extend(cell)
                #if not text[-1].endswith('\n'):
                #    text[-1] += '\n'
                if i < len(row)-1:
                    text.append(self._tab_char)
                else:
                    text.append('\n')
                #if i < len(row)-1:
                #    text.append('T}'+self._tab_char+'T{\n')
                #else:
                #    text.append('T}\n')
        #text.append('_\n')
        text.append('.TE\n')
        return text


class SpecMANWriter(Writer):


   def __init__(self):
      Writer.__init__(self)
      self.translator_class = SpecMANTranslator
      self.template_str = ""
      self.extraclass   = None

   def setTemplate(self, templ_file):
      self.template_file = templ_file
      self.template_str = open(self.template_file).read()

   def apply_template(self):

      if not self.template_str:
         print("NO TEMPLATE")
         raise "NoTemplate"

      subs = self.interpolation_dict()

      subs['description'] = self.visitor.doctitle

      return self.template_str % subs

   def translate(self):
      self.visitor = self.translator_class(self.document)
      self.document.walkabout(self.visitor)

      self.doctitle    = self.visitor.doctitle

      try:
         self.docsubtitle = self.visitor.docsubtitle
      except:
         self.docsubtitle = "NO SUBTITLE"

      self.output = self.visitor.astext()


def process(filename, outfile=None):
    buf = open(filename).read()
    pub_str = publish_string(buf, writer=SpecMANWriter(), settings_overrides={'output_encoding': 'unicode'})

    if not outfile:
       fd = sys.stdout
    else:
       fd = open(outfile,"w")

    fd.write(pub_str)

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
