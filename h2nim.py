#!/usr/bin/env python
#!-*-coding:utf-8-*-
"""

Examples::

    python h2nim.py gr.h /usr/gr/lib/libGR.so
    python h2nim.py gr.h /usr/gr/lib/libGR.so gr_wrapper.nim
"""
import argparse, sys
from pyclibrary import CParser
import pyclibrary
from pprint import pprint
import os

# TODO: fnmacros
# TODO: structs
# TODO: unions
# TODO: functions
# TODO: values

KEYWORDS = ["addr", "and", "as", "asm", "bind", "block", "break", "case", "cast",
            "concept", "const", "continue", "converter", "defer", "discard",
            "distinct", "div", "do", "elif", "else", "end", "enum", "except", "export",
            "finally", "for", "from", "func", "if", "import", "in", "include",
            "interface", "is", "isnot", "iterator", "let", "macro", "method", "mixin",
            "mod", "nil", "not", "notin", "object", "of", "or", "out", "proc", "ptr",
            "raise", "ref", "return", "shl", "shr", "static", "template", "try", 
            "tuple", "type", "using", "var", "when", "while", "xor", "yield" ]


def add_header_and_libname(headerFileName, libFileName):
    tmp = os.path.split(headerFileName)[1]
    name = os.path.splitext(tmp)[0]
    # Macros
    tmp = []
    tmp.append( (f"header{name}", f"\"{headerFileName}\"", True,1, None) )
    tmp.append( (f"libName", f"\"{libFileName}\"", False,1, None) )

    return {"const": tmp}

def parse_macros( data, parser ):
    tmp = []
    for k,v in parser.defs["macros"].items():
        # Better if we have the actual values
        val = parser.defs["values"][k]
        if val != None:
            tmp.append( (k, val, False,1, None) )
        else:
            tmp.append( (k, '""', False,1, None) )
    _old = data.get("const", [])
    data["const"] = _old + tmp + [(None, None, False, 0, None)]  
    return data

# Enums
def parse_enums( data, parser ):
    _d = {"top" : []}    
    enumlist = []
    enum_define = []
    tmp = []
    _flag = True
    for k,v in parser.defs["enums"].items():
        enumlist.append(k)
        _d["top"].append((f"defineEnum({k})", None, False,0, None))
        _flag = False # Don't comment
        for k1,v1 in v.items():
            tmp.append( (f"{k1}", f"({v1}).{k}", False, 1, None) )
        tmp.append( (None, None, False,0, None))  # Add a space


    for k, v in parser.defs["types"].items():
        if v.type_spec.startswith("enum "):
            if not k in enumlist:
                _d["top"].append( (f"defineEnum({k})", None, False, 0, None) )
                _flag = False                
                # This is a corner case for VapourSynth where pyclibrary doesn't parse properly an enum
                _tmp = v.type_spec.split(f"enum {k}")[1].strip()
                
                _tmp = _tmp.split()
                for i in range(len(_tmp)//2):
                    tmp.append( (f"{_tmp[i*2]}", f"({_tmp[i*2+1]}).{k}", False, 1, None) ) 
                tmp.append( (None, None, False, 0, None))  # Add a space    

    _old = data.get("top", [])
    _tmp2 = [("import nimterop/types   # Provides \"defineEnum\"",None, _flag, 0, None), (None, None, False, 0, None)]
    data["top"] = _old + _tmp2 + _d["top"] + [(None, None, False, 0, None)]

    _old = data.get("const", [])
    data["const"] = _old + tmp        
    return data

def create_pragma( name ):
    """No longer necessary
    """
    return f"{{.pragma: imp{name}, importc, header: header{name}.}}\n\n"

#---------------
def get_field_name(data):
    return data[0]

def get_return(data):
    """Gets the relevant return values
    """
    _tmp = data[1]
    if type(_tmp) is pyclibrary.c_parser.Type:
        typename = _tmp.type_spec
        decl = []
        for i in _tmp.declarators:
            if type(i) is tuple:
                break
            decl.append(i)
        return {"type.name": typename, "type.decls": decl }

def get_parameters(data):
    _params = []
    _tmp = data[1]
    if type(_tmp) is pyclibrary.c_parser.Type:
        for i in _tmp.declarators:
            if type(i) is tuple:
                for item in i:
                    _name = item[0]
                    _type = item[1]
                    _typename = _type.type_spec
                    _params.append( {"name": _name, "type.name": _typename, "type.decls":list(_type.declarators)} ) 
    return _params

def get_parameters2(data):
    _params = []
    n = 0
    while not type(data[n]) is tuple and (len(data)-1) != n:
        n += 1
    _tmp = data[n]
    for name, t, _ in _tmp:
        _params.append( {"name": name, "type.name": t.type_spec, "type.decls":list(t.declarators)} ) 
    return _params


def is_typedef( name ):
    for k, _ in parser.defs["types"].items():
        if k == name:
            return True
    return False

def convert_type( d):
    tn = d["type.name"]
    decls = d["type.decls"]

    new_type = ""
    if tn == "int":
        new_type = "cint"
    elif tn == "double":
        new_type = "cdouble"
    elif tn == "int64_t":
        new_type = "int64"  # cint?
    elif tn == "uint8_t":
        new_type = "uint8"      # cuint?   
    elif tn == "unsigned char":    # TODO: ptr unsigned char  -> ptr cuchar
        new_type = "cuchar"
    elif tn == "unsigned int":    # TODO: unsigned int -> cuint
        new_type = "cuint"
    elif tn == "unsigned short":  # TODO: unsigned short -> cushort
        new_type = "cushort"
    elif tn == "short":           # TODO: short -> cshort
        new_type = "cshort"               
    elif tn == "char":
        new_type = "cchar"
    else:
        new_type = tn

    ispointer = False
    if len(decls) > 0:
        if decls[0] == "*":
            ispointer = True
    
    pointer = ""
    if ispointer:
        if tn == "void":
            pointer = "ptr "* (len(decls)-1) + "pointer"
            new_type = ""
        elif tn == "char":
            pointer = ""
            new_type = "cstring"
        else:
            pointer = "ptr "* (len(decls))
    else:
        if len(decls) > 0:
            if tn == "char":
                new_type = f"array[{decls[0][0]}, cchar]"
    return f"{pointer}{new_type}"


def get_return2(data):
    """Gets the relevant return values
    """
    _tmp = data#[0]
    #print("-->",_tmp, type(data))
    if type(_tmp) is pyclibrary.c_parser.Type:
        typename = _tmp.type_spec
        decl = []
        for i in _tmp.declarators:
            #print(i, type(i))
            if type(i) is tuple:
                break
            decl.append(i)
        return {"type.name": typename, "type.decls": decl }

def get_return3(data):
    """Gets the relevant return values
    """
    _tmp = data[0]
    if type(_tmp) is pyclibrary.c_parser.Type:
        typename = _tmp.type_spec
        decl = []
        for i in _tmp.declarators:
            if type(i) is tuple:
                break
            decl.append(i)
        return {"type.name": typename, "type.decls": decl }

#--------------

def look_in_typedef(parser, name):
    for k,v in parser.defs["types"].items():
        if v.type_spec == f"struct {name}":
            return k
    return None

def create_types(data, parser):
    _list = []
    for k,v in parser.defs["structs"].items():
        # Esto son structs (algunos structs se definen en typedefs)
        #if not is_typedef(k):
        #    types += f"  {k}*  = object \n" # {{.imp{name}.}} 
        #else:

        # The following is for typedef with annonimous structs
        _object_name = k
        if "anon_struct" in k:
            _new_name = look_in_typedef(parser, k)
            if _new_name != None:
                _object_name = _new_name

        _list.append((f"{_object_name}", "object", False, 1, {"bycopy":"{.bycopy.}"}) )  #importc: \"struct {k}\", header: header{name},



        for member in v.members:
            fname = get_field_name(member)
            ret = get_return(member)
            params = get_parameters(member)

            ret_type = convert_type(ret)
            # Some fields
            if len(params) == 0:
                _name = get_field_name(member)
                _type = get_return(member)
                _new_type = convert_type(_type)
                
                _list.append((f"{_name}",f"{_new_type}", False, 2, None) )

            # Function signatures declarations
            else:
                add_comma = False
                _parameters = ""
                for t in params:
                    if add_comma:
                        _parameters += ", "
                    add_comma = True
                    _t = convert_type(t)
                    if t["name"] in KEYWORDS:
                        _parameters += f'`{t["name"]}`:{_t}'
                    else:
                        _parameters += f'{t["name"]}:{_t}' 
                
                if ret_type == "void":
                    _list.append( (f"{fname}", f"proc({_parameters}) {{.cdecl.}}", False, 2, None) )
                else:
                    _list.append( (f"{fname}", f"proc({_parameters}):{ret_type} {{.cdecl.}}", False, 2, None) )


        _list.append((None, None, False, 0, None))
    _old = data.get("type", [])
    data["type"] = _old +_list
    return data

def gen_new_function(fname, params,ret_type,level = 1):
    new = "proc("
    add_comma = False
    _parameters = ""
    for t in params:
        if add_comma:
            _parameters += ", "
        add_comma = True
        _t = convert_type(t)
        if t["name"] in KEYWORDS:
            _parameters += f'`{t["name"]}`: {_t}'
        else:
            _parameters += f'{t["name"]}: {_t}'
    if ret_type == "void":
        new += f"{_parameters}) {{.cdecl.}}\n"
    else:
        new += f"{_parameters}):{ret_type} {{.cdecl.}}\n"    
    _tmp = (fname, new, False, level, None )
    return _tmp


def get_function_signatures_types(data, parser):
    """Creates types for function signatures::

        type
          VSGetVapourSynthAPI* = proc(version: cint):ptr VSAPI {.cdecl.}  

    """
    _tmp = []
    for k, v in parser.defs["types"].items():
        #if v.is_fund_type() and not k.startswith("struct ") and not v.type_spec.startswith("struct ") and not k.startswith("enum ") and not v.type_spec.startswith("enum "):
        if not k.startswith("struct ") and not v.type_spec.startswith("struct ") and not k.startswith("enum ") and not v.type_spec.startswith("enum "):
            #print(k,v)
            fname = k  
            ret = get_return2(v)
            params = get_parameters2(v)
            ret_type = convert_type(ret)
            #print(ret_type)
            new = gen_new_function( fname, params,ret_type)
            _tmp.append( new )

        #elif not k.startswith("struct ") and not v.type_spec.startswith("struct ") and not k.startswith("enum ") and not v.type_spec.startswith("enum "):
        #    fname = k
        #    ret = get_return2(v)
        #    params = get_parameters2(v)
        #    ret_type = convert_type(ret)
        #    new = gen_new_function(name, fname, params,ret_type)
        #    _tmp.append( new )
    _old = data.get("type", [])
    data["type"] = _old +_tmp
    return data

def create_functions(data, parser):
    _lista = []
    for k, v in parser.defs["functions"].items():
        ret = get_return3(v)
        params = get_parameters2(v)
        ret_type = convert_type(ret)    
        _tmp = f"proc {k}*("
        flag = False
        param_names = list(map(chr, range(97, 123))) 
        for param in params:
            if param["type.name"] != "void":
                if flag:
                    _tmp += ", "
                flag = True
                _tmp2 = ""
                if param["name"] != None:
                    _tmp2 = param["name"] + ":"
                    if param["name"] in KEYWORDS:
                        _tmp2 =f"`{param['name']}`:"
                else:
                    _inventedparam = param_names.pop(0) 
                    _tmp2 = _inventedparam + ":"
                    if _inventedparam in KEYWORDS:
                        _tmp2 =f"`{_inventedparam}`:"                
                
                #if _tmp2 != None:
                _tmp += _tmp2
                _t = convert_type( param)
                _tmp += f"{_t}"
        #_t = convert_type(ret_type)
        
        if ret_type == "void":
            _tmp += f")"
        else:
            _tmp += f"):{ret_type}" 
        #_tmp += f"    {{.importc,dynlib: libName.}}\n"
        #functions += _tmp
        _lista.append( (_tmp, "", False, 0, None) )
    
    _old = data.get("functions", [])
    data["functions"] = _old +_lista        
    return data
    

def create_text(data, tab = 2):
    # Top + defineEnums
    _txt = ""
    for txt1, txt2, comment, level, _ in data["top"]:
        if not comment:
            if level == 0 and txt1 == None and txt2 == None:
               _txt += "\n"
            else:
               _txt += " "*level*tab + txt1 + "\n" 
    
    # Consts
    _txt += "const\n"
    for txt1, txt2, comment, level,_ in data["const"]:
        spaces = level * tab * " "
        sep = "="
        if level > 1:
            sep = ":"
        if not comment:
            if level == 0 and txt1 == None and txt2 == None:
                _txt += "\n"
            else:
                _txt += spaces +  f"{txt1}* {sep} {txt2}\n"
    # Types
    _txt += "type\n"
    for txt1, txt2, comment, level, d in data["type"]:
        #print(txt1)
        spaces = level * tab * " "
        if not comment:
            if level == 0 and txt1 == None and txt2 == None:
                _txt += "\n"
            elif level == 1:
                # {.bycopy.} pass the structs by value
                _bycopy = ""
                if d != None:
                   _bycopy = d.get("bycopy", "")
                
                _txt += spaces +  f"{txt1}* {_bycopy} = {txt2}\n"
            elif level == 2:
                _txt += spaces +  f"{txt1}* : {txt2}\n"
    
    # Functions
    _txt += "{.push dynlib:libName,importc.}\n"
    for txt1, txt2, comment, level, _ in data["functions"]:
        if not comment:
            _txt += f"{txt1}\n"
    _txt += "{.pop.}\n"
    return _txt

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("header", nargs=1, type=argparse.FileType('r'), help="the header file")
    parser.add_argument("library", nargs=1, type=argparse.FileType('r'), help="the library file")
    parser.add_argument("output", nargs='?', type=argparse.FileType('w'), default=sys.stdout, help="the output file")
    args = parser.parse_args()

    headerFileName = args.header[0].name
    libFileName    = args.library[0].name

    #-----
    data = add_header_and_libname(headerFileName, libFileName)
    parser = CParser([headerFileName])
    data = parse_macros(data, parser) 
    data = parse_enums( data, parser )
    data = create_types(data, parser)
    data = get_function_signatures_types(data, parser) 
    data = create_functions(data, parser)
    #-----
    txt = create_text(data)
    args.output.write(txt)
    