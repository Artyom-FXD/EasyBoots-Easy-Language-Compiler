import sys, os
from typing import List, Optional, Any, Dict, Tuple

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from parser import *

class CodeGenUtils:
    def __init__(self, debug=False, is_module=False):
        self.debug = debug 
        self.is_module = is_module
        self.code: List[str] = []
        self.method_code: List[str] = []
        self.specializations: List[str] = []
        self.indent: int = 0
        self.var_types: Dict[str, str] = {}
        self.global_types: Dict[str, str] = {}
        self.scopes: List[Dict[str, str]] = []
        self.scope_roots: List[List[str]] = []
        self.temp_counter: int = 0
        self.type_aliases: Dict[str, str] = {}
        self.used_modules: List[str] = []
        self.global_vars_to_init: List[Tuple[str, str, Expression]] = []
        self.original_functions: Dict[str, MethodDeclaration] = {}
        self.builtin_signatures: Dict[str, Tuple[str, str, List[str]]] = {}
        self.current_class_name: Optional[str] = None
        self.current_namespace: Optional[str] = None
        self.classes_ast: Dict[str, ClassDeclaration] = {}
        self.structs: set = set()
        self.namespaces: Dict[str, Dict[str, str]] = {}
        self.imported_namespaces: Dict[str, str] = {}

    # --- scopes ---
    def push_scope(self):
        """new scope"""
        self.scopes.append(self.var_types)
        self.var_types = {}
        self.scope_roots.append([])

    def pop_scope(self):
        """closes scope"""
        if self.scopes:
            self.var_types = self.scopes.pop()
        if self.scope_roots:
            for name in reversed(self.scope_roots.pop()):
                if name not in ('None', 'NULL'):
                    self.emit_to_method(f"gc_remove_root((void**)&{name});")

    def ensure_identifier(self, name: str, line=0, col=0):
        if name in self.var_types: return
        for s in reversed(self.scopes):
            if name in s: return
        if name in self.global_types: return
        if '_' in name and not name.startswith('__'):
            parts = name.split('_', 1)
            if parts[0] in self.classes_ast:
                return
        self.emit_to_method(f"ely_value* {name} = ely_value_new_null();")
        self.emit_to_method(f"gc_add_root((void**)&{name});")
        self.var_types[name] = 'any'
        if self.scope_roots:
            self.scope_roots[-1].append(name)

    # --- types ---
    def get_expression_type(self, expr: Expression) -> str:
        if isinstance(expr, Literal):
            v = expr.value
            if isinstance(v, bool): return 'bool'
            if isinstance(v, int): return 'int'
            if isinstance(v, float): return 'flt'
            if isinstance(v, str): return 'str'
            return 'any'
        if isinstance(expr, Identifier):
            name = expr.name
            if name == 'self' and self.current_class_name:
                return self.current_class_name
            if name in self.classes_ast:
                return name
            if name in self.interfaces_ast:
                return name
            if name in self.imported_namespaces:
                return self.imported_namespaces[name]
            if name in self.var_types:
                return self.resolve_type_alias(self.var_types[name])
            if name in self.global_types:
                return self.resolve_type_alias(self.global_types[name])
            for s in reversed(self.scopes):
                if name in s:
                    return self.resolve_type_alias(s[name])
            return 'any'
        if isinstance(expr, BinaryOp):
            return self.get_expression_type(expr.left)
        if isinstance(expr, UnaryOp):
            return self.get_expression_type(expr.operand)
        if isinstance(expr, ArrayLiteral): return 'arr<any>'
        if isinstance(expr, DictLiteral): return 'dict<any, any>'
        if isinstance(expr, IndexExpression): return 'any'
        if isinstance(expr, MemberAccess):
            obj_type = self.get_expression_type(expr.object)
            if obj_type in self.classes_ast:
                cls = self.classes_ast[obj_type]
                def find_field(c):
                    for f in c.fields:
                        if f.name == expr.member: return f.type
                    if c.extends and c.extends in self.classes_ast:
                        return find_field(self.classes_ast[c.extends])
                    return None
                ft = find_field(cls)
                if ft: return self.resolve_type_alias(ft)
            if obj_type in self.interfaces_ast:
                return 'any'  # интерфейсы не имеют полей
            return 'any'
        if isinstance(expr, Call):
            if isinstance(expr.callee, Identifier):
                if expr.callee.name.endswith('_constructor'):
                    cn = expr.callee.name[:-len('_constructor')]
                    if cn in self.classes_ast: return cn
                if expr.callee.name in self.original_functions:
                    ret = self.original_functions[expr.callee.name].return_type
                    if ret: return self.resolve_type_alias(ret)
            return 'any'
        return 'any'

    def type_to_cpp(self, ely_type: str, for_signature=False, is_param=False,
                    is_self=False, is_field=False) -> str:
        ely_type = self.resolve_type_alias(ely_type)
        if ely_type in self.classes_ast:
            if is_param or is_self or is_field:
                return f"{ely_type}*"
            return 'ely_value*'
        mapping = {
            'void':'void','bool':'int','byte':'signed char','ubyte':'unsigned char',
            'int':'int','uint':'unsigned int','more':'long long','umore':'unsigned long long',
            'flt':'float','double':'double','str':'char*','any':'ely_value*','char':'char',
        }
        if ely_type.startswith('arr<') or ely_type.startswith('dict<'):
            return 'ely_value*'
        if ely_type in mapping:
            if for_signature and not is_param and ely_type != 'void':
                return 'ely_value*'
            return mapping[ely_type]
        if ely_type in self.structs:
            return f"struct {ely_type}"
        if ely_type.endswith('*'):
            inner = ely_type[:-1].strip()
            return self.type_to_cpp(inner, for_signature, is_param, is_self, is_field) + '*'
        return 'ely_value*'

    def resolve_type_alias(self, t: str) -> str:
        while t in self.type_aliases:
            t = self.type_aliases[t]
        return t

    def is_numeric(self, t: str) -> bool:
        return t in ('int','uint','more','umore','flt','double','byte','ubyte')

    # --- emitters ---
    def emit(self, line: str):
        self.code.append("    " * self.indent + line)

    def emit_to_method(self, line: str):
        self.method_code.append("    " * self.indent + line)

    # --- names ---
    def method_full_name(self, name: str) -> str:
        ns = self.ns_prefix()
        if self.current_class_name:
            return f"{ns}{self.current_class_name}_{name}"
        return f"{ns}{name}"

    def ns_prefix(self) -> str:
        return self.current_namespace + "_" if self.current_namespace else ""

    # --- helpers ---
    def gen_expr_rooted(self, expr: Expression) -> str:
        code = self.gen_expression(expr)  # определён в FuncCodeGen
        if isinstance(expr, Identifier):
            return code
        tmp = f"__tmp_{self.temp_counter}"
        self.temp_counter += 1
        self.emit_to_method(f"ely_value* {tmp} = {code};")
        self.emit_to_method(f"gc_add_root((void**)&{tmp});")
        return tmp

    def error(self, msg: str, node: Optional[Expression] = None):
        if node:
            print(f"Code generation error: {msg} at line {node.line}, col {node.col}")
        else:
            print(f"Code generation error: {msg}")

    def set_builtins(self, builtins: Dict[str, Tuple[str, str, List[str]]]):
        self.builtin_signatures = builtins