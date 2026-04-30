import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from parser import *
from typing import List, Optional


from collections import namedtuple
CallSignature = namedtuple('CallSignature', ['name', 'return_type', 'param_types', 'is_method'])
class CCodeGen:
    def __init__(self, debug=False, is_module=False):
        self.debug = debug
        self.is_module = is_module
        self.code = []
        self.specializations = []
        self.main_code = []
        self.indent = 0
        self.var_types = {}
        self.global_types = {}
        self.scopes = []
        self.scope_roots = []
        self.func_name = None
        self.inside_func = False
        self.used_modules = []
        self.global_vars_to_init = []
        self.temp_counter = 0
        self.type_aliases = {}
        self.generic_instances = {}
        self.original_functions = {}
        self.structs = set()
        self.struct_fields = {}
        self.in_asafe = False
        self.hoisted_functions = []
        self.extern_functions = {}
        self.builtin_signatures = {}
        self._init_builtins()
        self.classes = {}
        self.current_class_name = None
        self.current_function = None
        self.classes_ast = {}
        self.current_class_name = None

    def _init_builtins(self):
        builtins = {
            # Console
            'print':     ('ely_println', 'void', ['str']),
            'println':   ('ely_println', 'void', ['str']),
            'printOld':  ('ely_print',   'void', ['str']),

            # Time module
            'timeNow':     ('ely_time_now',      'more', []),
            'timeNowMs':   ('ely_time_now_ms',   'more', []),
            'timeDiff':    ('ely_time_diff',     'double', ['more', 'more']),
            'formatTime':  ('ely_format_time',   'str',   ['more', 'str']),
            'parseTime':   ('ely_parse_time',    'more',  ['str', 'str']),
            'sleep':       ('ely_sleep',         'void',  ['more']),

            # Random module
            'randInt':       ('ely_rand_int',        'int',  []),
            'randIntRange':  ('ely_rand_int_range',  'int',  ['int', 'int']),
            'randBool':      ('ely_rand_bool',       'bool', []),
            'srand':         ('ely_srand',           'void', ['uint']),
            'rand':          ('ely_rand',            'int',  []),
            'randDouble':    ('ely_rand_double',     'double', []),

            # File module
            'fileWrite':    ('ely_file_write',    'int',  ['str', 'str']),
            'fileRead':     ('ely_file_read',     'str',  ['str']),
            'fileExists':   ('ely_file_exists',   'bool', ['str']),
            'fileReadAll':  ('ely_file_read_all', 'str',  ['str']),
            'fileClose':    ('ely_file_close',    'void', ['int']),
            'fileRemove':   ('ely_file_remove',   'int',  ['str']),
            'fileRename':   ('ely_file_rename',   'int',  ['str', 'str']),

            # Path module
            'pathJoin':        ('ely_path_join',        'str', ['str', 'str']),
            'pathBasename':    ('ely_path_basename',    'str', ['str']),
            'pathDirname':     ('ely_path_dirname',     'str', ['str']),
            'pathIsAbsolute':  ('ely_path_is_absolute', 'bool', ['str']),

            # DinLibs module
            'loadLibrary':      ('ely_load_library',      'any',  ['str']),
            'getFunction':      ('ely_get_function',      'any',  ['any', 'str']),
            'callIntInt':       ('ely_call_int_int',      'int',  ['any', 'int']),
            'callDoubleDouble': ('ely_call_double_double','double',['any', 'double']),
            'callDoubleDoubleDouble': ('ely_call_double_double_double', 'double', ['any', 'double', 'double']),
            'callStrVoid':      ('ely_call_str_void',     'str',  ['any', 'str']),
            'closeLibrary':     ('ely_close_library',     'void', ['any']),

            # JSON
            'jsonify':  ('ely_dict_to_json', 'str', ['dict']),
            'dictify':  ('ely_dictify',      'dict', ['str']),

            # Dicts
            'keys': ('ely_dict_keys', 'arr<str>', ['dict']),
            'has':  ('ely_dict_has',  'bool',     ['dict', 'any']),
            'del':  ('ely_dict_del',  'void',     ['dict', 'any']),

            # Strs
            'len':      ('ely_str_len',       'int',   ['str']),
            'concat':   ('ely_str_concat',    'str',   ['str', 'str']),
            'dup':      ('ely_str_dup',       'str',   ['str']),
            'cmp':      ('ely_str_cmp',       'int',   ['str', 'str']),
            'substr':   ('ely_str_substr',    'str',   ['str', 'int', 'int']),
            'trim':     ('ely_str_trim',      'str',   ['str']),
            'replace':  ('ely_str_replace',   'str',   ['str', 'str', 'str']),
            'intToStr': ('ely_int_to_str',    'str',   ['int']),
            'strToInt': ('ely_str_to_int',    'int',   ['str']),

            # Nums
            'abs':      ('ely_abs_int',       'int',   ['int']),
            'absMore':  ('ely_abs_more',      'more',  ['more']),
            'fabs':     ('ely_fabs',          'double',['double']),
            'min':      ('ely_min_int',       'int',   ['int', 'int']),
            'max':      ('ely_max_int',       'int',   ['int', 'int']),
            'pow':      ('ely_pow',           'double',['double', 'double']),
            'sqrt':     ('ely_sqrt',          'double',['double']),
            'sin':      ('ely_sin',           'double',['double']),
            'cos':      ('ely_cos',           'double',['double']),
            'tan':      ('ely_tan',           'double',['double']),

            # Reflection
            'typeof':  ('ely_typeof',         'str',   ['any']),
            'fields':  ('ely_value_get_fields', 'arr<str>', ['any']),
            'methods': ('ely_value_get_methods','arr<str>', ['any']),
        }
        for name, (c_name, ret, params) in builtins.items():
            self.builtin_signatures[name] = (c_name, ret, params)

    # SCOPES
    def _push_scope(self):
        self.scopes.append(self.var_types)
        self.var_types = {}
        self.scope_roots.append([])

    def _ensure_identifier(self, name: str, line: int, col: int):
        if name in self.var_types:
            return
        for scope in reversed(self.scopes):
            if name in scope:
                return
        if name in self.global_types:
            return

        self.emit_to_main(f"ely_value* {name} = ely_value_new_null();")
        self.emit_to_main(f"gc_add_root((void**)&{name});")
        self.var_types[name] = 'any'
        if self.scope_roots:
            self.scope_roots[-1].append(name)

    def _pop_scope(self):
        if self.scopes:
            self.var_types = self.scopes.pop()
        if self.scope_roots:
            roots = self.scope_roots.pop()
            for name in reversed(roots):
                if name not in ('None', 'NULL'):
                    self.emit_to_main(f"gc_remove_root((void**)&{name});")

    # TYPES
    def _get_expression_type(self, expr: Expression) -> str:
        if isinstance(expr, Literal):
            val = expr.value
            if isinstance(val, bool):
                return 'bool'
            if isinstance(val, int):
                return 'int'
            if isinstance(val, float):
                return 'flt'
            if isinstance(val, str):
                return 'str'
            return 'any'
        elif isinstance(expr, Identifier):
            if expr.name in self.var_types:
                return self._resolve_type_alias(self.var_types[expr.name])
            if expr.name in self.global_types:
                return self._resolve_type_alias(self.global_types[expr.name])
            for scope in reversed(self.scopes):
                if expr.name in scope:
                    return self._resolve_type_alias(scope[expr.name])
            return 'any'
        elif isinstance(expr, BinaryOp):
            return self._get_expression_type(expr.left)
        elif isinstance(expr, UnaryOp):
            return self._get_expression_type(expr.operand)
        elif isinstance(expr, ArrayLiteral):
            return 'arr<any>'
        elif isinstance(expr, DictLiteral):
            return 'dict<any, any>'
        elif isinstance(expr, IndexExpression):
            return 'any'
        elif isinstance(expr, MemberAccess):
            return 'any'
        elif isinstance(expr, TypeOfExpression):
            arg_code = self.gen_expression(expr.argument)
            return f"ely_value_new_string(ely_typeof({arg_code}))"
        elif isinstance(expr, FieldsExpression):
            arg_code = self.gen_expression(expr.argument)
            return f"ely_value_get_fields({arg_code})"
        elif isinstance(expr, MethodsExpression):
            arg_code = self.gen_expression(expr.argument)
            return f"ely_value_get_methods({arg_code})"
        elif isinstance(expr, Call):
            if isinstance(expr.callee, MemberAccess):
                obj = expr.callee.object
                method = expr.callee.member
                obj_type = self._get_expression_type(obj)
                if obj_type.startswith('arr<'):
                    if method == 'len':
                        return 'int'
                    elif method == 'pop':
                        return 'any'
                    elif method == 'push':
                        return 'void'
                elif obj_type.startswith('dict<'):
                    if method == 'keys':
                        return 'arr<str>'
            elif isinstance(expr.callee, Identifier):
                func_name = expr.callee.name
                if func_name in self.original_functions:
                    ret = self.original_functions[func_name].return_type
                    if ret:
                        return self._resolve_type_alias(ret)
                if func_name == 'time_now':
                    return 'more'
                if func_name == 'time_diff':
                    return 'double'
                if func_name in ('print', 'println', 'sleep'):
                    return 'void'
            return 'any'
        return 'any'

    def _type_to_c(self, ely_type: str, for_signature: bool = False) -> str:
        ely_type = self._resolve_type_alias(ely_type)
        
        if for_signature and ely_type != 'void':
            return 'ely_value*'
        
        mapping = {
            'void': 'void',
            'bool': 'int',
            'byte': 'signed char',
            'ubyte': 'unsigned char',
            'int': 'int',
            'uint': 'unsigned int',
            'more': 'long long',
            'umore': 'unsigned long long',
            'flt': 'float',
            'double': 'double',
            'str': 'char*',
            'any': 'ely_value*',
            'char': 'char',
        }
        if ely_type.startswith('arr<') or ely_type.startswith('dict<'):
            return 'ely_value*'
        if ely_type in mapping:
            return mapping[ely_type]
        if ely_type in self.structs:
            return f"struct {ely_type}"
        if ely_type.endswith('*'):
            inner = ely_type[:-1].strip()
            return f"{self._type_to_c(inner)}*"
        return ely_type

    def _type_to_tag(self, ely_type: str) -> int:
        tags = {
            'int': 1, 'uint': 2, 'more': 3, 'umore': 4,
            'flt': 5, 'double': 6, 'bool': 7, 'str': 8,
            'byte': 9, 'ubyte': 10
        }
        return tags.get(ely_type, 1)

    # ------------------- Генерация кода -------------------
    def emit(self, line: str):
        self.code.append("    " * self.indent + line)

    def emit_to_main(self, line: str):
        self.main_code.append("    " * self.indent + line)

    def generate(self, program: Program) -> str:
        self.code = []
        self.specializations = []
        self.main_code = []
        self.used_modules = []
        self.global_vars_to_init = []
        self.type_aliases = {}
        self.generic_instances = {}
        self.original_functions = {}
        self.structs = set()
        self.struct_fields = {}
        self.classes_ast.clear()
        self.current_class_name = None

        self.code.append('#include "ely_runtime.h"\n')
        self.code.append('#include "ely_gc.h"\n')
        self.code.append('#include <stdio.h>\n')
        self.code.append('#include <stdlib.h>\n')
        self.code.append('#include <setjmp.h>\n')
        for mod in self.used_modules:
            self.code.append(f'#include "{mod}.h"\n')
        self.code.append('\n')
        self.code.append('static jmp_buf __ex_buf;\n')
        self.code.append('static ely_value* __ex_value = NULL;\n')

        for stmt in program.statements:
            if isinstance(stmt, GlobalCBlock):
                self.code.append(stmt.code)
        self.code.append('')

        for stmt in program.statements:
            if isinstance(stmt, TypeAlias):
                self.type_aliases[stmt.name] = stmt.target_type
            elif isinstance(stmt, MethodDeclaration):
                self.original_functions[stmt.name] = stmt
            elif isinstance(stmt, StructDeclaration):
                self.structs.add(stmt.name)
                fields = {}
                for field in stmt.fields:
                    fields[field.name] = field.type
                self.struct_fields[stmt.name] = fields
            elif isinstance(stmt, ClassDeclaration):
                self.classes_ast[stmt.name] = stmt
                # Зарегистрируем методы как функции: имя = ClassName_methodName
                for method in stmt.methods:
                    full_name = f"{stmt.name}_{method.name}"
                    self.original_functions[full_name] = method
            elif isinstance(stmt, ExternFunction):
                self.extern_functions[stmt.name] = stmt

        for stmt in program.statements:
            if isinstance(stmt, UsingDirective):
                self.used_modules.append(stmt.module)

        for stmt in program.statements:
            if isinstance(stmt, ExternFunction):
                ret_type = self._type_to_c(stmt.return_type or 'void')
                params = []
                for p in stmt.parameters:
                    if p.type == '...':
                        params.append("...")
                    else:
                        param_type = self._type_to_c(p.type)
                        params.append(f"{param_type} {p.name}")
                param_str = ", ".join(params)
                self.emit(f"extern {ret_type} {stmt.name}({param_str});")
        self.code.append('\n')

        for stmt in program.statements:
            if isinstance(stmt, StructDeclaration):
                self._gen_struct(stmt)

        if not self.is_module:
            has_main = any(isinstance(s, MethodDeclaration) and s.name == 'main' for s in program.statements)
            if not has_main:
                self.main_code.append("int main() {")
                self.main_code.append("    gc_init();")
                self.main_code.append("    if (_global_init) _global_init();")
                self.main_code.append("    return 0;")
                self.main_code.append("}")

        global_methods = []
        class_methods = {}

        for stmt in program.statements:
            if isinstance(stmt, MethodDeclaration):
                global_methods.append(stmt)

        for name, cls in self.classes_ast.items():
            class_methods[name] = cls.methods

        for stmt in program.statements:
            if isinstance(stmt, VariableDeclaration):
                self._gen_global_variable(stmt)

        for method in global_methods:
            self.current_class_name = None
            self._forward_declare(method)
        for class_name, methods in class_methods.items():
            self.current_class_name = class_name
            for method in methods:
                self._forward_declare(method)

        for cls in self.classes_ast.values():
            self._gen_class_constructor_forward(cls)
        for cls in self.classes_ast.values():
            self._gen_class_constructor(cls)

        for method in global_methods:
            self.current_class_name = None
            self._gen_function(method)

        for class_name, methods in class_methods.items():
            self.current_class_name = class_name
            for method in methods:
                self._gen_function(method)
        self.current_class_name = None

        if self.global_vars_to_init:
            self._create_global_init()

        final_code = self.code + self.specializations + self.main_code
        return "\n".join(final_code)

    def _method_full_name(self, method_name: str) -> str:
        if self.current_class_name:
            return f"{self.current_class_name}_{method_name}"
        return method_name

    def _resolve_type_alias(self, type_name: str) -> str:
        while type_name in self.type_aliases:
            type_name = self.type_aliases[type_name]
        return type_name

    def _declare_function(self, node: MethodDeclaration):
        pass

    def _gen_global_variable(self, node: VariableDeclaration):
        resolved_type = self._resolve_type_alias(node.type)
        ctype = self._type_to_c(resolved_type)
        self.emit(f"{ctype} {node.name};")
        self.global_types[node.name] = node.type
        if node.initializer:
            self.global_vars_to_init.append((node.name, node.type, node.initializer))
        self.global_types[node.name] = resolved_type

    def _create_global_init(self):
        self.emit("static void _global_init(void) {")
        self.indent += 1
        for name, typ, init_node in self.global_vars_to_init:
            if isinstance(init_node, ArrayLiteral):
                self._gen_global_array_init(name, typ, init_node)
            elif isinstance(init_node, DictLiteral):
                self._gen_global_dict_init(name, typ, init_node)
            else:
                init_code = self.gen_expression(init_node)
                self.emit(f"{name} = {init_code};")
        self.indent -= 1
        self.emit("}")

    def _gen_global_array_init(self, name: str, typ: str, node: ArrayLiteral):
        self.emit(f"arr* __tmp_arr = arr_new();")
        self.emit(f"{name} = ely_value_new_array(__tmp_arr);")
        for elem in node.elements:
            elem_code = self.gen_expression(elem)
            tmp_var = f"__tmp_global_{self.temp_counter}"
            self.temp_counter += 1
            self.emit(f"ely_value* {tmp_var} = {elem_code};")
            self.emit(f"arr_push({name}->u.array_val, {tmp_var});")

    def _gen_global_dict_init(self, name: str, typ: str, node: DictLiteral):
        self.emit(f"dict* __tmp_dict = dict_new_str();")
        self.emit(f"{name} = ely_value_new_object(__tmp_dict);")
        for pair in node.pairs:
            key_code = self.gen_expression(pair.key)
            val_code = self.gen_expression(pair.value)
            key_tmp = f"__tmp_key_{self.temp_counter}"
            self.temp_counter += 1
            val_tmp = f"__tmp_val_{self.temp_counter}"
            self.temp_counter += 1
            self.emit(f"ely_value* {key_tmp} = {key_code};")
            self.emit(f"ely_value* {val_tmp} = {val_code};")
            self.emit(f"dict_set({name}->u.object_val, {key_tmp}, {val_tmp});")

    def _gen_struct(self, node: StructDeclaration):
        self.emit(f"struct {node.name} {{")
        self.indent += 1
        for field in node.fields:
            ctype = self._type_to_c(field.type)
            self.emit(f"{ctype} {field.name};")
        self.indent -= 1
        self.emit("};")

    # STATEMENTS GENERATION
    def gen_statement(self, stmt: Statement):
        if isinstance(stmt, GlobalCBlock):
            return
        if isinstance(stmt, ExpressionStatement):
            expr = self.gen_expression(stmt.expression)
            if expr:
                self.emit_to_main(f"{expr};")
        elif isinstance(stmt, VariableDeclaration):
            self._gen_local_variable(stmt)
        elif isinstance(stmt, MethodDeclaration):
            self._gen_function(stmt)
        elif isinstance(stmt, IfStatement):
            self._gen_if(stmt)
        elif isinstance(stmt, WhileLoop):
            self._gen_while(stmt)
        elif isinstance(stmt, ForLoop):
            self._gen_for(stmt)
        elif isinstance(stmt, ForEachLoop):
            self._gen_foreach(stmt)
        elif isinstance(stmt, ThrowStatement):
            self._gen_throw(stmt)
        elif isinstance(stmt, MatchStatement):
            self._gen_match(stmt)
        elif isinstance(stmt, AsafeBlock):
            self._gen_asafe(stmt)
        elif isinstance(stmt, GivebackStatement):
            self._gen_giveback(stmt)
        elif isinstance(stmt, ReturnStatement):
            self._gen_return(stmt)
        elif isinstance(stmt, CollapseStatement):
            self._gen_collapse(stmt)
        elif isinstance(stmt, BreakStatement):
            self._gen_break(stmt)
        elif isinstance(stmt, Assignment):
            expr = self.gen_expression(stmt)
            if expr:
                self.emit_to_main(f"{expr};")

    def _is_primitive_type(self, ely_type: str) -> bool:
        return ely_type == 'void'

    def _gen_local_variable(self, node: VariableDeclaration):
        resolved_type = self._resolve_type_alias(node.type)
        if resolved_type == 'void':
            self.error("Cannot declare variable of type void", node)
            return

        ctype = 'ely_value*'
        if node.initializer:
            init_code = self.gen_expression(node.initializer)
            if resolved_type not in ('any', 'void', 'arr', 'dict', '*'):
                source_type = self._get_expression_type(node.initializer)
                if source_type != resolved_type:
                    init_code = self._convert_value(init_code, source_type, resolved_type)
            self.emit_to_main(f"{ctype} {node.name} = {init_code};")
        else:
            if resolved_type in self.classes_ast:
                need_args = any(f.initializer is None for f in self.classes_ast[resolved_type].wait_fields)
                if need_args:
                    self.error(f"Class '{resolved_type}' requires constructor arguments (no defaults for all wait fields)", node)
                    return
                self.emit_to_main(f"{ctype} {node.name} = {resolved_type}_constructor();")
            elif resolved_type == 'int':
                self.emit_to_main(f"{ctype} {node.name} = ely_value_new_int(0);")
            elif resolved_type == 'bool':
                self.emit_to_main(f"{ctype} {node.name} = ely_value_new_bool(0);")
            elif resolved_type in ('flt', 'double'):
                self.emit_to_main(f"{ctype} {node.name} = ely_value_new_double(0.0);")
            else:
                self.emit_to_main(f"{ctype} {node.name} = ely_value_new_null();")

        self.var_types[node.name] = resolved_type
        self.emit_to_main(f"gc_add_root((void**)&{node.name});")
        if self.scope_roots:
            if node.name and node.name != 'None' and node.name != 'NULL':
                self.scope_roots[-1].append(node.name)

    def _gen_primitive_expression(self, expr: Expression) -> str:
        if isinstance(expr, Literal):
            val = expr.value
            if isinstance(val, bool):
                return '1' if val else '0'
            elif isinstance(val, int):
                return str(val)
            elif isinstance(val, float):
                return str(val)
            elif isinstance(val, str):
                return '""'
            else:
                return '0'
        elif isinstance(expr, Identifier):
            return expr.name
        elif isinstance(expr, BinaryOp):
            left = self._gen_primitive_expression(expr.left)
            right = self._gen_primitive_expression(expr.right)
            op = expr.operator
            if op in ('+', '-', '*', '/', '%', '<', '>', '<=', '>=', '==', '!=', '&&', '||'):
                return f"({left} {op} {right})"
            else:
                self.error(f"Unsupported primitive binary operator: {op}", expr)
                return "0"
        elif isinstance(expr, UnaryOp):
            operand = self._gen_primitive_expression(expr.operand)
            if expr.operator == '-':
                return f"(-{operand})"
            elif expr.operator == '!':
                return f"(!{operand})"
            else:
                return operand
        elif isinstance(expr, Call):
            self.error("Call in primitive expression not yet supported", expr)
            return "0"
        else:
            self.error(f"Cannot generate primitive expression for {type(expr).__name__}", expr)
            return "0"

    def _is_field_in_class_hierarchy(self, cls: ClassDeclaration, field_name: str) -> bool:
        if field_name in [f.name for f in cls.fields]:
            return True
        if cls.extends and cls.extends in self.classes_ast:
            parent = self.classes_ast[cls.extends]
            return self._is_field_in_class_hierarchy(parent, field_name)
        return False

    def _wrap_primitive_to_value(self, expr_code: str, ely_type: str) -> str:
        resolved = self._resolve_type_alias(ely_type)
        if resolved == 'int':
            return f"ely_value_new_int({expr_code})"
        elif resolved == 'bool':
            return f"ely_value_new_bool({expr_code})"
        elif resolved == 'flt' or resolved == 'double':
            return f"ely_value_new_double({expr_code})"
        elif resolved == 'str':
            return f"ely_value_new_string({expr_code})"
        else:
            return expr_code

    def _convert_to_ctype(self, expr_node: Expression, expr_code: str, target_type: str) -> str:
        if target_type == 'any' or target_type == 'ely_value*':
            source_type = self._get_expression_type(expr_node)
            if source_type in ('int', 'uint', 'more', 'umore', 'byte', 'ubyte'):
                return f"ely_value_new_int({expr_code})"
            if source_type in ('double', 'flt'):
                return f"ely_value_new_double({expr_code})"
            if source_type == 'bool':
                return f"ely_value_new_bool({expr_code})"
            if source_type == 'str':
                return f"ely_value_new_string({expr_code})"
            return expr_code
        if target_type in ('int', 'uint', 'more', 'umore', 'byte', 'ubyte'):
            return f"ely_value_as_int({expr_code})"
        if target_type in ('double', 'flt'):
            return f"ely_value_as_double({expr_code})"
        if target_type == 'bool':
            return f"ely_value_as_bool({expr_code})"
        if target_type == 'str':
            return f"ely_value_to_string({expr_code})"
        if target_type == 'char':
            return f"ely_value_as_char({expr_code})"
        return expr_code

    def _wrap_result(self, call_expr: str, return_type: str) -> str:
        if return_type == 'void':
            return f"({call_expr}, ely_value_new_null())"
        if return_type in ('int', 'uint', 'more', 'umore', 'byte', 'ubyte'):
            return f"ely_value_new_int({call_expr})"
        if return_type in ('double', 'flt'):
            return f"ely_value_new_double({call_expr})"
        if return_type == 'bool':
            return f"ely_value_new_bool({call_expr})"
        if return_type == 'str':
            return f"ely_value_new_string({call_expr})"
        if return_type == 'char':
            return f"ely_value_new_char({call_expr})"
        return call_expr

    def _get_call_signature_for_func(self, node: Call, func_name: str):
        if func_name in self.extern_functions:
            ext = self.extern_functions[func_name]
            param_types = [p.type for p in ext.parameters]
            return_type = ext.return_type or 'void'
            return (func_name, return_type, param_types)
        if func_name in self.original_functions:
            func = self.original_functions[func_name]
            param_types = [p.type for p in func.parameters]
            return_type = func.return_type or 'void'
            return (func_name, return_type, param_types)
        if func_name in self.builtin_signatures:
            c_name, ret, params = self.builtin_signatures[func_name]
            return (c_name, ret, params)
        self.error(f"Unknown function '{func_name}'", node)
        return None

    def _convert_value(self, value_code: str, from_type: str, to_type: str) -> str:
        if from_type == to_type or not to_type or to_type == 'any':
            return value_code

        if from_type in ('any', None):
            if to_type == 'int':
                return f'ely_value_new_int(ely_value_as_int({value_code}))'
            elif to_type in ('flt', 'double'):
                return f'ely_value_new_double(ely_value_as_double({value_code}))'
            elif to_type == 'bool':
                return f'ely_value_new_bool(ely_value_as_bool({value_code}))'
            elif to_type == 'str':
                return f'ely_value_new_string(ely_value_to_string({value_code}))'

        if self.is_numeric(from_type) and self.is_numeric(to_type):
            if to_type == 'int':
                return f'ely_value_new_int(ely_value_as_int({value_code}))'
            elif to_type in ('flt', 'double'):
                return f'ely_value_new_double(ely_value_as_double({value_code}))'

        return f'ely_value_new_string(ely_value_to_string({value_code}))'

    def is_numeric(self, ely_type: str) -> bool:
        return ely_type in ('int', 'uint', 'more', 'umore', 'flt', 'double', 'byte', 'ubyte')

    def _gen_if(self, node: IfStatement):
        cond = self.gen_expression(node.condition)
        self.emit_to_main(f"if (ely_value_as_bool({cond})) {{")
        self.indent += 1
        self._push_scope()
        for stmt in node.then_body:
            self.gen_statement(stmt)
        self._pop_scope()
        self.indent -= 1
        if node.else_body:
            self.emit_to_main("} else {")
            self.indent += 1
            self._push_scope()
            for stmt in node.else_body:
                self.gen_statement(stmt)
            self._pop_scope()
            self.indent -= 1
            self.emit_to_main("}")
        else:
            self.emit_to_main("}")

    def _gen_while(self, node: WhileLoop):
        cond = self.gen_expression(node.condition)
        self.emit_to_main(f"while (ely_value_as_bool({cond})) {{")
        self.indent += 1
        self._push_scope()
        for stmt in node.body:
            self.gen_statement(stmt)
        self._pop_scope()
        self.indent -= 1
        self.emit_to_main("}")

    def _gen_for(self, node: ForLoop):
        self._push_scope()
        
        init_part = ";"
        if node.init:
            if isinstance(node.init, VariableDeclaration):
                self._gen_local_variable(node.init)
                init_part = ";"
            elif isinstance(node.init, ExpressionStatement):
                expr_code = self.gen_expression(node.init.expression)
                init_part = expr_code + ";" if expr_code else ";"
            else:
                init_part = ";"

        cond_part = "1"
        if node.condition:
            cond_expr = self.gen_expression(node.condition)
            cond_part = f"ely_value_as_bool({cond_expr})"

        update_part = ""
        if node.update:
            update_expr = self.gen_expression(node.update)
            update_part = update_expr

        self.emit_to_main(f"for ({init_part} {cond_part}; {update_part}) {{")
        self.indent += 1

        for stmt in node.body:
            self.gen_statement(stmt)

        self.indent -= 1
        self.emit_to_main("}")
        self._pop_scope()

    def _gen_foreach(self, node: ForEachLoop):
        iterable_type = self._get_expression_type(node.iterable)
        iterable_code = self.gen_expression(node.iterable)

        if iterable_type.startswith('arr<'):
            self.emit_to_main(f"for (size_t __i = 0; __i < ely_array_len({iterable_code}); __i++) {{")
            self.indent += 1
            elem_code = f"ely_array_get({iterable_code}, __i)"
            if isinstance(node.item_decl, VariableDeclaration):
                decl_type = node.item_decl.type or 'any'
                c_decl_type = self._type_to_c(decl_type)
                self.emit_to_main(f"{c_decl_type} {node.item_decl.name} = {elem_code};")
                self.var_types[node.item_decl.name] = decl_type
                if c_decl_type == 'ely_value*' or c_decl_type.startswith('ely_value*'):
                    self.emit_to_main(f"gc_add_root((void**)&{node.item_decl.name});")
                    if self.scope_roots and node.item_decl.name and node.item_decl.name not in ['None', 'NULL']:
                        self.scope_roots[-1].append(node.item_decl.name)
                self.var_types[node.item_decl.name] = decl_type
            else:
                self.emit_to_main(f"ely_value* {node.item_decl.name} = {elem_code};")
                self.var_types[node.item_decl.name] = 'any'
            for stmt in node.body:
                self.gen_statement(stmt)
            self.indent -= 1
            self.emit_to_main("}")

        elif iterable_type.startswith('dict<'):
            keys_var = f"__keys_{self.temp_counter}"
            self.temp_counter += 1
            self.emit_to_main(f"ely_value* {keys_var} = ely_dict_keys({iterable_code});")
            self.emit_to_main(f"for (size_t __i = 0; __i < ely_array_len({keys_var}); __i++) {{")
            self.indent += 1
            self.emit_to_main(f"ely_value* __key = ely_array_get({keys_var}, __i);")
            self.emit_to_main(f"ely_value* __value = ely_dict_get({iterable_code}, __key);")
            if isinstance(node.item_decl, VariableDeclaration):
                decl_type = node.item_decl.type or 'any'
                c_decl_type = self._type_to_c(decl_type)
                self.emit_to_main(f"{c_decl_type} {node.item_decl.name} = __value;")
                self.var_types[node.item_decl.name] = decl_type
            else:
                self.emit_to_main(f"ely_value* {node.item_decl.name} = __value;")
                self.var_types[node.item_decl.name] = 'any'
            for stmt in node.body:
                self.gen_statement(stmt)
            self.indent -= 1
            self.emit_to_main("}")
            self.emit_to_main(f"ely_value_free({keys_var});")
        else:
            self.error(f"foreach not supported for type {iterable_type}", node.iterable)

    def _gen_match(self, node: MatchStatement):
        expr = self.gen_expression(node.expression)
        self.emit_to_main(f"switch ({expr}) {{")
        self.indent += 1
        for case in node.cases:
            case_val = self.gen_expression(case.value)
            self.emit_to_main(f"case {case_val}: {{")
            self.indent += 1
            for stmt in case.body:
                self.gen_statement(stmt)
            self.emit_to_main("break;")
            self.indent -= 1
            self.emit_to_main("}")
        if node.default_body:
            self.emit_to_main("default: {")
            self.indent += 1
            for stmt in node.default_body:
                self.gen_statement(stmt)
            self.indent -= 1
            self.emit_to_main("}")
        self.indent -= 1
        self.emit_to_main("}")

    def _gen_asafe(self, node: AsafeBlock):
        param = node.except_handler.parameter if node.except_handler else None
        if not param or param == 'None':
            param = '__ex'
        
        self.emit_to_main(f"ely_value* {param} = NULL;")
        self.var_types[param] = 'any'
        self.emit_to_main(f"gc_add_root((void**)&{param});")
        if self.scope_roots:
            self.scope_roots[-1].append(param)
        
        self.emit_to_main("int __ex_result = setjmp(__ex_buf);")
        self.emit_to_main("if (__ex_result == 0) {")
        self.indent += 1
        self._push_scope()
        for stmt in node.body:
            self.gen_statement(stmt)
        self._pop_scope()
        self.indent -= 1
        self.emit_to_main("} else {")
        self.indent += 1
        if node.except_handler:
            self.emit_to_main(f"{param} = __ex_value;")
            for stmt in node.except_handler.body:
                self.gen_statement(stmt)
            self.emit_to_main("__ex_value = NULL;")
        self.indent -= 1
        self.emit_to_main("}")

    def _gen_throw(self, node: ThrowStatement):
        val_code = self.gen_expression(node.value)
        self.emit_to_main(f"__ex_value = {val_code};")
        self.emit_to_main("longjmp(__ex_buf, 1);")

    def _gen_giveback(self, node: GivebackStatement):
        if node.value:
            val = self.gen_expression(node.value)
            self.emit_to_main(f"return {val};")
        else:
            self.emit_to_main("return;")

    def _gen_return(self, node: ReturnStatement):
        if not self.current_function and not self.current_method:
            self.error("return outside function/method", node)
            return
        if node.value:
            val = self.gen_expression(node.value)
            expected_type = self.func_return_type if self.current_function else 'void'
            if expected_type and expected_type != 'void':
                source_type = self._get_expression_type(node.value)
                val = self._convert_value(val, source_type, expected_type)
            if self.current_function == 'main':
                self.emit_to_main(f"return ely_value_as_int({val});")
            else:
                self.emit_to_main(f"return {val};")
        else:
            if self.current_function == 'main':
                self.emit_to_main("return 0;")
            else:
                self.emit_to_main("return;")

    def _gen_collapse(self, node: CollapseStatement):
        if node.name in self.var_types:
            del self.var_types[node.name]

    def _gen_break(self, node: BreakStatement):
        self.emit_to_main("break;")

    def gen_expression(self, expr: Expression) -> Optional[str]:
        if isinstance(expr, Literal):
            return self._gen_literal(expr)
        elif isinstance(expr, Identifier):
            return self._gen_identifier(expr)
        elif isinstance(expr, BinaryOp):
            return self._gen_binary_op(expr)
        elif isinstance(expr, UnaryOp):
            return self._gen_unary_op(expr)
        elif isinstance(expr, Assignment):
            return self._gen_assignment(expr)
        elif isinstance(expr, Call):
            return self._gen_call(expr)
        elif isinstance(expr, MemberAccess):
            return self._gen_member_access(expr)
        elif isinstance(expr, Conditional):
            return self._gen_conditional(expr)
        elif isinstance(expr, FString):
            return self._gen_fstring(expr)
        elif isinstance(expr, ArrayLiteral):
            return self._gen_array_literal(expr)
        elif isinstance(expr, DictLiteral):
            return self._gen_dict_literal(expr)
        elif isinstance(expr, IndexExpression):
            return self._gen_index_expression(expr)
        else:
            self.error(f"Unknown expression type: {type(expr).__name__}", expr)
            return None

    def _gen_literal(self, node: Literal) -> str:
        if isinstance(node.value, bool):
            return f"ely_value_new_bool({1 if node.value else 0})"
        elif isinstance(node.value, int):
            return f"ely_value_new_int({node.value})"
        elif isinstance(node.value, float):
            return f"ely_value_new_double({node.value})"
        elif isinstance(node.value, str):
            escaped = node.value.replace('\\', '\\\\').replace('"', '\\"')
            escaped = escaped.replace('\n', '\\n').replace('\r', '\\r').replace('\t', '\\t')
            return f'ely_value_new_string("{escaped}")'
        elif node.value is None:
            return "ely_value_new_null()"
        return "ely_value_new_null()"

    def _gen_identifier(self, node: Identifier) -> str:
        if node.name == 'self' and self.current_class_name:
            return "self"

        if self.current_class_name:
            cls = self.classes_ast.get(self.current_class_name)
            if cls and node.name in [f.name for f in cls.fields]:
                return f"ely_value_get_key(self, \"{node.name}\")"

        self._ensure_identifier(node.name, node.line, node.col)
        return node.name

    def _gen_binary_op(self, node: BinaryOp) -> str:
        left = self.gen_expression(node.left)
        right = self.gen_expression(node.right)
        op = node.operator
        op_map = {
            '+': 'add',
            '-': 'sub',
            '*': 'mul',
            '/': 'div',
            '%': 'mod',
            '==': 'eq',
            '!=': 'ne',
            '<': 'lt',
            '<=': 'le',
            '>': 'gt',
            '>=': 'ge',
            '&&': 'and',
            '||': 'or',
        }
        func = f"ely_value_{op_map.get(op, op)}"
        return f"{func}({left}, {right})"

    def _gen_unary_op(self, node: UnaryOp) -> str:
        operand = self.gen_expression(node.operand)
        op = node.operator
        if op == '!':
            return f"ely_value_not({operand})"
        elif op == '-':
            return f"ely_value_neg({operand})"
        elif op == '&':
            return f"(&{operand})"
        else:
            return f"{op}{operand}"

    def _is_lvalue(self, expr: Expression) -> bool:
        if isinstance(expr, Identifier):
            return True
        if isinstance(expr, IndexExpression):
            return True
        if isinstance(expr, MemberAccess):
            return True
        return False

    def _gen_identifier(self, node: Identifier) -> str:
        if node.name == 'self' and self.current_class_name:
            return "self"

        if self.current_class_name:
            cls = self.classes_ast.get(self.current_class_name)
            if cls and self._is_field_in_class_hierarchy(cls, node.name):
                return f"ely_value_get_key(self, \"{node.name}\")"

        self._ensure_identifier(node.name, node.line, node.col)
        return node.name

    def _is_field_in_class_hierarchy(self, cls: ClassDeclaration, field_name: str) -> bool:
        if field_name in [f.name for f in cls.fields]:
            return True
        if cls.extends and cls.extends in self.classes_ast:
            return self._is_field_in_class_hierarchy(self.classes_ast[cls.extends], field_name)
        return False

    def _gen_assignment(self, node: Assignment) -> str:
        target_code = self.gen_expression(node.target)
        raw_value_code = self.gen_expression(node.value)
        op = node.operator

        if op != '=':
            binary_op = BinaryOp(
                line=node.line, col=node.col,
                left=node.target,
                operator=op[:-1],
                right=node.value
            )
            value_code = self.gen_expression(binary_op)
        else:
            value_code = raw_value_code

        target_ely_type = None
        if isinstance(node.target, Identifier):
            name = node.target.name
            if name in self.var_types:
                target_ely_type = self._resolve_type_alias(self.var_types[name])
            else:
                for scope in reversed(self.scopes):
                    if name in scope:
                        target_ely_type = self._resolve_type_alias(scope[name])
                        break
            if target_ely_type is None and name in self.global_types:
                target_ely_type = self._resolve_type_alias(self.global_types[name])

        if isinstance(node.target, Identifier):
            name = node.target.name
            found = (name in self.var_types)
            if not found:
                for scope in reversed(self.scopes):
                    if name in scope:
                        found = True
                        break
            if name in self.global_types:
                found = True
            if not found:
                self.var_types[name] = 'any'
                self.emit_to_main(f"ely_value* {name};")
                self.emit_to_main(f"gc_add_root((void**)&{name});")
                if self.scope_roots and name and name not in ['None', 'NULL']:
                    self.scope_roots[-1].append(name)

        if target_ely_type and target_ely_type not in ('any', 'void', 'arr', 'dict', '*'):
            source_type = self._get_expression_type(node.value)
            if source_type != target_ely_type:
                value_code = self._convert_value(value_code, source_type, target_ely_type)

        if isinstance(node.target, MemberAccess):
            obj = self.gen_expression(node.target.object)
            self.emit_to_main(f"gc_write_barrier({obj}, (void**)&({obj}->{node.target.member}), {value_code});")
            return f"{obj}->{node.target.member} = {value_code}"
        if isinstance(node.target, IndexExpression):
            target = self.gen_expression(node.target.target)
            index = self.gen_expression(node.target.index)
            return f"ely_value_set_index({target}, {index}, {value_code})"

        if isinstance(node.target, Identifier) and self.current_class_name:
            cls = self.classes_ast.get(self.current_class_name)
            if cls and self._is_field_in_class_hierarchy(cls, node.target.name):
                return f"ely_value_set_key(self, \"{node.target.name}\", {value_code})"

        return f"{target_code} = {value_code}"

    def _gen_conditional(self, node: Conditional) -> str:
        cond = self.gen_expression(node.condition)
        then_expr = self.gen_expression(node.then_expr)
        else_expr = self.gen_expression(node.else_expr)
        return f"((ely_value_as_bool({cond})) ? {then_expr} : {else_expr})"

    def _gen_class_constructor_forward(self, cls: ClassDeclaration):
        all_wait = self._collect_wait_fields(cls)
        params = ', '.join([f"ely_value* {f.name}" for f in all_wait])
        self.code.append(f"ely_value* {cls.name}_constructor({params});")

    def _gen_class_constructor(self, cls: ClassDeclaration):
        name = cls.name
        parent = cls.extends
        wait_fields = self._collect_wait_fields(cls)
        param_list = ', '.join([f"ely_value* {f.name}" for f in wait_fields])

        self.emit_to_main(f"ely_value* {name}_constructor({param_list}) {{")
        self.indent += 1

        for f in wait_fields:
            self.var_types[f.name] = f.type

        self.emit_to_main("ely_value* obj = ely_value_new_object(dict_new_str());")
        self.emit_to_main("gc_add_root((void**)&obj);")

        if parent and cls.super_args:
            parent_cls = self.classes_ast.get(parent)
            if parent_cls:
                for pf in self._collect_wait_fields(parent_cls):
                    if pf.name not in self.var_types:
                        self.var_types[pf.name] = pf.type
            super_actuals = ', '.join([self.gen_expression(arg) for arg in cls.super_args])
            self.emit_to_main(f"{parent}_constructor({super_actuals});")
            if parent_cls:
                for pf in self._collect_wait_fields(parent_cls):
                    self.emit_to_main(f"ely_value_set_key(obj, \"{pf.name}\", {pf.name});")

        for f in cls.wait_fields:
            self.emit_to_main(f"ely_value_set_key(obj, \"{f.name}\", {f.name});")

        self.emit_to_main("gc_remove_root((void**)&obj);")
        self.emit_to_main("return obj;")
        self.indent -= 1
        self.emit_to_main("}")

        for f in wait_fields:
            if f.name in self.var_types:
                del self.var_types[f.name]
        if parent and cls.super_args:
            parent_cls = self.classes_ast.get(parent)
            if parent_cls:
                for pf in self._collect_wait_fields(parent_cls):
                    if pf.name in self.var_types:
                        del self.var_types[pf.name]

    def _collect_wait_fields(self, cls: ClassDeclaration) -> List[VariableDeclaration]:
        fields = []
        if cls.extends and cls.extends in self.classes_ast:
            parent = self.classes_ast[cls.extends]
            fields.extend(self._collect_wait_fields(parent))
        fields.extend(cls.wait_fields)
        return fields

    def _gen_fstring(self, node: FString) -> str:
        if not node.parts:
            return 'ely_value_new_string("")'
        
        result = None
        for part in node.parts:
            if isinstance(part, str):
                escaped = part.replace('"', '\\"').replace('\n', '\\n')
                part_expr = f'ely_value_new_string("{escaped}")'
            else:
                part_expr = self.gen_expression(part)
            
            if result is None:
                result = part_expr
            else:
                result = f'ely_value_add({result}, {part_expr})'
        return result

    def _gen_array_literal(self, node: ArrayLiteral) -> str:
        if not node.elements:
            return "ely_value_new_array(arr_new())"
        elems = []
        for elem in node.elements:
            elem_code = self.gen_expression(elem)
            tmp = f"__tmp_ary_{self.temp_counter}"
            self.temp_counter += 1
            self.emit_to_main(f"ely_value* {tmp} = {elem_code};")
            elems.append(tmp)
        arr_var = f"__arr_{self.temp_counter}"
        self.temp_counter += 1
        self.emit_to_main(f"arr* {arr_var} = arr_new();")
        for e in elems:
            self.emit_to_main(f"arr_push({arr_var}, {e});")
        return f"ely_value_new_array({arr_var})"

    def _gen_dict_literal(self, node: DictLiteral) -> str:
        if not node.pairs:
            return "ely_value_new_object(dict_new_str())"
        pairs = []
        for pair in node.pairs:
            key_code = self.gen_expression(pair.key)
            val_code = self.gen_expression(pair.value)
            key_tmp = f"__tmp_key_{self.temp_counter}"
            self.temp_counter += 1
            val_tmp = f"__tmp_val_{self.temp_counter}"
            self.temp_counter += 1
            self.emit_to_main(f"ely_value* {key_tmp} = {key_code};")
            self.emit_to_main(f"ely_value* {val_tmp} = {val_code};")
            pairs.append((key_tmp, val_tmp))
        dict_var = f"__dict_{self.temp_counter}"
        self.temp_counter += 1
        self.emit_to_main(f"dict* {dict_var} = dict_new_str();")
        for key, val in pairs:
            self.emit_to_main(f"dict_set_str({dict_var}, {key}->u.string_val, {val});")
        return f"ely_value_new_object({dict_var})"

    def _gen_index_expression(self, node: IndexExpression) -> str:
        target = self.gen_expression(node.target)
        index = self.gen_expression(node.index)
        return f"ely_value_index({target}, {index})"

    def _gen_member_access(self, node: MemberAccess) -> str:
        obj = self.gen_expression(node.object)
        return f"ely_value_get_key({obj}, \"{node.member}\")"

    def _gen_call(self, node: Call) -> str:
        if isinstance(node.callee, MemberAccess):
            obj = node.callee.object
            method = node.callee.member
            obj_type = self._get_expression_type(obj)
            obj_code = self.gen_expression(obj)
            if obj_code is None:
                return "ely_value_new_null()"

            if obj_type.startswith('arr<'):
                args = [self.gen_expression(a) for a in node.arguments]
                if method == 'push':
                    if len(args) != 1:
                        self.error("push expects 1 argument", node)
                        return ""
                    val = self._convert_to_ctype(node.arguments[0], args[0], 'any')
                    return f"ely_array_push({obj_code}, {val})"
                elif method == 'pop':
                    return f"ely_array_pop({obj_code})"
                elif method == 'len':
                    return self._wrap_result(f"ely_array_len({obj_code})", 'int')
                elif method == 'insert':
                    if len(args) != 2:
                        self.error("insert expects 2 arguments", node)
                        return ""
                    idx = self._convert_to_ctype(node.arguments[0], args[0], 'int')
                    val = self._convert_to_ctype(node.arguments[1], args[1], 'any')
                    return f"ely_array_insert({obj_code}, {idx}, {val})"
                elif method == 'remove':
                    if len(args) != 1:
                        self.error("remove expects 1 argument", node)
                        return ""
                    val = self._convert_to_ctype(node.arguments[0], args[0], 'any')
                    return f"ely_array_remove_value({obj_code}, {val})"
                elif method == 'index':
                    if len(args) != 1:
                        self.error("index expects 1 argument", node)
                        return ""
                    val = self._convert_to_ctype(node.arguments[0], args[0], 'any')
                    return self._wrap_result(f"ely_array_index({obj_code}, {val})", 'int')
                else:
                    self.error(f"Unknown array method '{method}'", node)
                    return ""

            if obj_type.startswith('dict<'):
                args = [self.gen_expression(a) for a in node.arguments]
                if method == 'keys':
                    return self._wrap_result(f"ely_dict_keys({obj_code})", 'arr<str>')
                elif method == 'del':
                    if len(args) != 1:
                        self.error("del expects 1 argument", node)
                        return ""
                    key = self._convert_to_ctype(node.arguments[0], args[0], 'any')
                    return f"ely_dict_del({obj_code}, {key})"
                elif method == 'has':
                    if len(args) != 1:
                        self.error("has expects 1 argument", node)
                        return ""
                    key = self._convert_to_ctype(node.arguments[0], args[0], 'any')
                    return self._wrap_result(f"ely_dict_has({obj_code}, {key})", 'bool')
                elif method == 'toJson':
                    return self._wrap_result(f"ely_dict_to_json({obj_code})", 'str')
                else:
                    self.error(f"Unknown dict method '{method}'", node)
                    return ""

            if obj_type == 'str':
                args = [self.gen_expression(a) for a in node.arguments]
                if method == 'len':
                    return self._wrap_result(f"ely_str_len(({obj_code})->u.string_val)", 'int')
                elif method == 'concat':
                    if len(args) != 1:
                        self.error("concat expects 1 argument", node)
                        return ""
                    other = self._convert_to_ctype(node.arguments[0], args[0], 'str')
                    return self._wrap_result(f"ely_str_concat(({obj_code})->u.string_val, {other})", 'str')
                elif method == 'substr':
                    if len(args) != 2:
                        self.error("substr expects 2 arguments", node)
                        return ""
                    start = self._convert_to_ctype(node.arguments[0], args[0], 'int')
                    length = self._convert_to_ctype(node.arguments[1], args[1], 'int')
                    return self._wrap_result(f"ely_str_substr(({obj_code})->u.string_val, {start}, {length})", 'str')
                elif method == 'trim':
                    return self._wrap_result(f"ely_str_trim(({obj_code})->u.string_val)", 'str')
                elif method == 'replace':
                    if len(args) != 2:
                        self.error("replace expects 2 arguments", node)
                        return ""
                    old = self._convert_to_ctype(node.arguments[0], args[0], 'str')
                    new = self._convert_to_ctype(node.arguments[1], args[1], 'str')
                    return self._wrap_result(f"ely_str_replace(({obj_code})->u.string_val, {old}, {new})", 'str')
                else:
                    self.error(f"Unknown string method '{method}'", node)
                    return ""

            if obj_type in ('int', 'uint', 'more', 'umore', 'flt', 'double'):
                if method == 'toStr':
                    return self._wrap_result(f"ely_value_to_string({obj_code})", 'str')
                elif method == 'abs':
                    return self._wrap_result(f"ely_value_abs({obj_code})", obj_type)
                else:
                    self.error(f"Unknown number method '{method}'", node)
                    return ""

            if obj_type in self.classes_ast:
                c_func = f"{obj_type}_{method}"
                args_code = [obj_code]  # self первый аргумент
                for arg in node.arguments:
                    arg_code = self.gen_expression(arg)
                    if arg_code is None:
                        return "ely_value_new_null()"
                    args_code.append(arg_code)
                return f"{c_func}({', '.join(args_code)})"

            self.error(f"Method calls not supported for type {obj_type}", node)
            return ""

        if not isinstance(node.callee, Identifier):
            self.error("Call expression must be a function or method", node)
            return "ely_value_new_null()"

        func_name = node.callee.name

        if func_name in self.original_functions:
            func_node = self.original_functions[func_name]
            if func_node.type_params:
                bindings = {}
                for arg, param in zip(node.arguments, func_node.parameters):
                    arg_type = self._get_expression_type(arg)
                    if param.type in func_node.type_params:
                        bindings[param.type] = arg_type
                missing = [tp for tp in func_node.type_params if tp not in bindings]
                if missing:
                    self.error(f"Could not infer type parameters: {missing}", node)
                    return "ely_value_new_null()"
                key = (func_name, tuple(bindings.values()))
                if key not in self.generic_instances:
                    spec_name = self._generate_specialization(func_node, bindings)
                    self.generic_instances[key] = spec_name
                else:
                    spec_name = self.generic_instances[key]
                args_code = [self.gen_expression(arg) for arg in node.arguments]
                call_expr = f"{spec_name}({', '.join(args_code)})"
                return call_expr
            else:
                args_code = [self.gen_expression(arg) for arg in node.arguments]
                call_expr = f"{func_name}({', '.join(args_code)})"
                return call_expr

        if func_name in self.builtin_signatures:
            c_func_name, return_type, param_types = self.builtin_signatures[func_name]
            args_code = []
            for i, arg in enumerate(node.arguments):
                arg_code = self.gen_expression(arg)
                if arg_code is None:
                    return "ely_value_new_null()"
                if i < len(param_types):
                    expected = param_types[i]
                    arg_code = self._convert_to_ctype(arg, arg_code, expected)
                args_code.append(arg_code)
            call_expr = f"{c_func_name}({', '.join(args_code)})"
            return self._wrap_result(call_expr, return_type)

        if func_name in self.extern_functions:
            ext = self.extern_functions[func_name]
            return_type = ext.return_type or 'void'
            param_types = [p.type for p in ext.parameters]
            args_code = []
            for i, arg in enumerate(node.arguments):
                arg_code = self.gen_expression(arg)
                if arg_code is None:
                    return "ely_value_new_null()"
                if i < len(param_types):
                    expected = param_types[i]
                    arg_code = self._convert_to_ctype(arg, arg_code, expected)
                args_code.append(arg_code)
            call_expr = f"{func_name}({', '.join(args_code)})"
            return self._wrap_result(call_expr, return_type)

        self.error(f"Unknown function '{func_name}'", node)
        return "ely_value_new_null()"

    def _generate_specialization(self, func_node: MethodDeclaration, mapping: dict) -> str:
        def substitute(s: str) -> str:
            if s is None:
                return s
            for tp, ct in mapping.items():
                s = s.replace(tp, ct)
            return s

        new_params = []
        for p in func_node.parameters:
            new_type = substitute(p.type)
            new_params.append(Parameter(type=new_type, name=p.name))
        new_return_type = substitute(func_node.return_type)
        new_body = []
        for stmt in func_node.body:
            if isinstance(stmt, VariableDeclaration):
                new_type = substitute(stmt.type)
                new_body.append(VariableDeclaration(
                    line=stmt.line, col=stmt.col,
                    modifier=stmt.modifier, type=new_type, name=stmt.name,
                    initializer=stmt.initializer, tag=stmt.tag
                ))
            else:
                new_body.append(stmt)
        suffix = '_'.join(str(ct) for ct in mapping.values())
        spec_name = f"{func_node.name}_{suffix}"
        new_func = MethodDeclaration(
            line=func_node.line, col=func_node.col,
            return_type=new_return_type,
            name=spec_name,
            parameters=new_params,
            body=new_body,
            modifier=func_node.modifier,
            type_params=[]
        )
        old_main = self.main_code
        self.main_code = []
        self.indent = 0
        self._gen_function(new_func)
        spec_code = "\n".join(self.main_code)
        self.main_code = old_main
        self.specializations.append(spec_code)
        return spec_name

    def _gen_gc_roots(self):
        roots = []
        for name, typ in self.var_types.items():
            resolved = self._resolve_type_alias(typ)
            ctype = self._type_to_c(resolved)
            if ctype == 'ely_value*' or ctype.startswith('ely_value*'):
                roots.append(name)
        self.current_roots = roots
        for name in roots:
            self.emit_to_main(f"gc_add_root((void**)&{name});")

    def error(self, message: str, node: Expression):
        print(f"Code generation error: {message} at line {node.line}, col {node.col}")

    def _hoist_nested_functions(self, stmts: List[Statement]) -> List[Statement]:
        hoisted = []
        new_stmts = []
        for stmt in stmts:
            if isinstance(stmt, MethodDeclaration):
                if self.current_function:
                    new_name = f"{self.current_function}_{stmt.name}"
                else:
                    new_name = stmt.name
                stmt.name = new_name
                self.original_functions[new_name] = stmt
                hoisted.append(stmt)
            else:
                new_stmts.append(stmt)
        self.hoisted_functions.extend(hoisted)
        return new_stmts

    def _forward_declare(self, node: MethodDeclaration):
        if node.name == 'main':
            return
        if node.type_params:
            return
        ret_type_c = self._type_to_c(node.return_type or 'void', for_signature=True)
        params = []
        if self.current_class_name:
            params.append("ely_value* self")
        params.extend([f"{self._type_to_c(p.type, for_signature=True)} {p.name}" for p in node.parameters])
        param_str = ", ".join(params)
        full_name = self._method_full_name(node.name)
        self.code.append(f"{ret_type_c} {full_name}({param_str});")

    def _gen_function(self, node: MethodDeclaration):
        if node.name == '_global_init':
            return
        if node.type_params:
            return

        func_name = self._method_full_name(node.name)
        is_main = (func_name == 'main')
        ret_type_c = 'int' if is_main else self._type_to_c(node.return_type or 'void', for_signature=True)

        params = []
        if self.current_class_name:
            params.append("ely_value* self")
        params.extend([f"{self._type_to_c(p.type, for_signature=True)} {p.name}" for p in node.parameters])
        param_str = ", ".join(params)

        old_main = self.main_code
        self.main_code = []
        self.indent = 0
        self.inside_func = True
        self.func_name = func_name
        old_function = self.current_function
        self.current_function = func_name
        self.func_return_type = node.return_type or 'void'
        self.hoisted_functions = []

        self.emit_to_main(f"{ret_type_c} {func_name}({param_str}) {{")
        self.indent += 1

        if is_main:
            self.emit_to_main("gc_init();")
            if self.global_vars_to_init and not self.is_module:
                self.emit_to_main("_global_init();")

        self._push_scope()

        for p in node.parameters:
            self.var_types[p.name] = p.type
            self.emit_to_main(f"gc_add_root((void**)&{p.name});")
            if self.scope_roots:
                self.scope_roots[-1].append(p.name)

        if self.current_class_name:
            self.var_types['self'] = self.current_class_name
            self.emit_to_main("gc_add_root((void**)&self);")
            if self.scope_roots:
                self.scope_roots[-1].append('self')

        body_stmts = self._hoist_nested_functions(node.body)
        for stmt in body_stmts:
            self.gen_statement(stmt)

        self._pop_scope()
        self.indent -= 1
        self.emit_to_main("}")
        self.inside_func = False
        self.func_name = None
        self.current_function = old_function

        for hoisted in self.hoisted_functions:
            self._gen_function(hoisted)

        old_main.extend(self.main_code)
        self.main_code = old_main