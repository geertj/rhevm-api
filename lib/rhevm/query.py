#
# This file is part of RHEVM-API. RHEVM-API is free software that is made
# available under the MIT license. Consult the file "LICENSE" that is
# distributed together with this file for the exact licensing terms.
#
# RHEVM-API is copyright (c) 2010 by the RHEVM-API authors. See the file
# "AUTHORS" for a complete overview.

from argproc.plyparse import Parser


class Query(object):

    def __init__(self, expr_list, sort_spec):
        self.expr_list = expr_list
        self.sort_spec = sort_spec

    def tostring(self):
        s = self.expr_list.tostring()
        if self.sort_spec:
            s += ' '
            s += self.sort_spec.tostring()
        return s


class ResultSpec(object):

    def __init__(self, field):
        self.field = field

    def tostring(self):
        if not self.field:
            return ''
        s = '%s:' % self.field.tostring()
        return s


class SortSpec(object):

    def __init__(self, field, sense):
        self.field = field
        self.sense = sense

    def tostring(self):
        if not self.field:
            return ''
        s = 'sortby '
        s += self.field.tostring()
        if self.sense:
            s += ' '
            s += self.sense
        return s


class BinOp(object):

    sign = None

    def __init__(self, left, right):
        self.left = left
        self.right = right

    def tostring(self):
        s = '%s %s %s' % (self.left.tostring(), self.sign,
                          self.right.tostring())
        return s


class AND(BinOp):

    sign = 'AND'


class OR(BinOp):

    sign = 'OR'


class EQ(BinOp):

    sign = '='


class LT(BinOp):

    sign = '<'


class LTE(BinOp):

    sign = '<='


class GT(BinOp):

    sign = '>'


class GTE(BinOp):

    sign = '>='


class Name(object):

    def __init__(self, name):
        self.name = name

    def tostring(self):
        return self.name


class Value(object):

    def __init__(self, value):
        self.value = value

    def tostring(self):
        return '"%s"' % self.value


class QueryParser(Parser):

    keywords = \
    {
        'and': 'AND',
        'or': 'OR',
        'sortby': 'SORTBY',
        'asc': 'ASC',
        'desc': 'DESC'
    }

    tokens = ('ID', 'STRING', 'EQ', 'LT', 'LTE', 'GT', 'GTE', 'DOT') \
                + tuple(keywords.values())

    t_EQ = '='
    t_LT = '<'
    t_LTE = '<='
    t_GT = '>'
    t_GTE = '>='
    t_DOT = r'\.'
    t_ignore = ' \t\r\n'

    def t_ID(self, t):
        """[a-zA-Z_][a-zA-Z0-9_]*"""
        t.type = self.keywords.get(t.value.lower(), 'ID')
        return t

    def t_STRING(self, t):
        '''"(?P<value>[^"])*"'''
        t.value = t.value[1:-1]
        return t

    def p_main(self, p):
        """main : expr_list sort_spec"""
        p[0] = Query(p[1], p[2])

    def p_expr_list(self, p):
        """expr_list : expr
                     | expr_list expr 
                     | expr_list AND expr 
                     | expr_list OR expr 
        """
        if len(p) == 2:
            p[0] = p[1]
        elif len(p) == 3:
            p[0] = OR(p[1], p[2])
        elif p[2].upper() == 'AND':
            p[0] = AND(p[1], p[3])
        elif p[2].upper() == 'OR':
            p[0] = OR(p[1], p[3])

    def p_sort_spec(self, p):
        """sort_spec : SORTBY name ASC
                     | SORTBY name DESC
                     | SORTBY name
                     | empty"""
        if len(p) == 4:
            p[0] = SortSpec(p[2], p[3])
        elif len(p) == 3:
            p[0] = SortSpec(p[2])
        else:
            p[0] = None

    def p_expr(self, p):
        """expr : qname EQ value
                | qname LT value
                | qname LTE value
                | qname GT value
                | qname GTE value
        """
        if p[2] == '=':
            p[0] = EQ(p[1], p[3])
        elif p[2] == '<':
            p[0] = LT(p[1], p[3])
        elif p[2] == '<=':
            p[0] = LTE(p[1], p[3])
        elif p[2] == '>':
            p[0] = GT(p[1], p[3])
        elif p[2] == '>=':
            p[0] = GTE(p[1], p[3])

    def p_qname(self, p):
        """qname : name
                 | qname DOT name
        """
        if len(p) == 2:
            p[0] = p[1]
        else:
            p[0] = Name('%s.%s' % (p[1].name, p[3].name))

    def p_name(self, p):
        """name : ID"""
        p[0] = Name(p[1])

    def p_value(self, p):
        """value : STRING"""
        p[0] = Value(p[1])

    def p_empty(self, p):
        """empty : """
        p[0] = None
