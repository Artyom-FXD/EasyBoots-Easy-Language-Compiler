import sys, os
from typing import List, Optional, Any, Dict
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from parser import *
from codegen.utils_codegen import CodeGenUtils

class FuncCodeGen(CodeGenUtils):
    """Functions Generation. Second layer."""
    def __init__(self, debug=False, is_module=False):
        super().__init__(debug, is_module)
        self.current_function: Optional[str] = None
        self.func_return_type: Optional[str] = None
        self.inside_func: bool = False
        self.hoisted_functions: List[MethodDeclaration] = []
        self.extern_functions: Dict[str, ExternFunction] = {}
        self.generic_instances: Dict = {}

    # -------------------------------------------------------------------
    # Forward-объявления
    # -------------------------------------------------------------------
    def forward_declare(self, node: MethodDeclaration):
        if node.name == 'main':
            return
        if node.type_params:
            return
        is_static = (node.modifier == 'static')
        ret = self.type_to_cpp(node.return_type or 'void', for_signature=True)
        params = []
        if self.current_class_name and not is_static:
            params.append(f"{self.current_class_name}* self")
        for p in node.parameters:
            params.append(f"{self.type_to_cpp(p.type, for_signature=True, is_param=True)} {p.name}")
        full_name = self.method_full_name(node.name)
        self.emit(f"{ret} {full_name}({', '.join(params)});")

    def forward_declare_static(self, cls: ClassDeclaration, method: MethodDeclaration):
        full_name = self.method_full_name(method.name)
        ret = self.type_to_cpp(method.return_type or 'void', for_signature=True)
        params = ', '.join([f"{self.type_to_cpp(p.type, for_signature=True, is_param=True)} {p.name}" for p in method.parameters])
        self.emit(f"{ret} {full_name}({params});")

    # -------------------------------------------------------------------
    # Генерация тел функций
    # -------------------------------------------------------------------
    def gen_function(self, node: MethodDeclaration):
        if node.name == '_global_init':
            return
        if node.type_params:
            return

        func_name = self.method_full_name(node.name)
        is_static = (node.modifier == 'static')
        is_main = (func_name == 'main')
        is_constructor = func_name.endswith('_constructor')

        is_async = node.is_async
        if is_main:
            ret_cpp = 'int'
        else:
            ret_cpp = self.type_to_cpp(node.return_type or 'void', for_signature=True)

        # Сигнатура
        sig_params = []
        if self.current_class_name and not is_static and not is_constructor:
            sig_params.append(f"{self.current_class_name}* self")
        for p in node.parameters:
            sig_params.append(f"{self.type_to_cpp(p.type, for_signature=True, is_param=True)} {p.name}")
        param_str = ", ".join(sig_params)

        old_method = self.method_code
        self.method_code = []
        self.indent = 0
        self.inside_func = True
        self.func_name = func_name
        old_function = self.current_function
        self.current_function = func_name
        self.func_return_type = node.return_type or 'void'
        self.hoisted_functions = []

        self.emit_to_method(f"{ret_cpp} {func_name}({param_str}) {{")
        self.indent += 1

        if is_main:
            self.emit_to_method("gc_init();")
            self.emit_to_method("_global_init();")
            self.emit_to_method("gc_set_enabled(1);")
            self.emit_to_method('#ifdef _WIN32')
            self.emit_to_method('{')
            self.emit_to_method('    char _exe_path[1024];')
            self.emit_to_method('    GetModuleFileNameA(NULL, _exe_path, sizeof(_exe_path));')
            self.emit_to_method('    char* _last_slash = strrchr(_exe_path, \'\\\\\');')
            self.emit_to_method('    if (_last_slash) *_last_slash = \'\\0\';')
            self.emit_to_method('    SetCurrentDirectoryA(_exe_path);')
            self.emit_to_method('}')
            self.emit_to_method('#else')
            self.emit_to_method('    char _exe_path[1024];')
            self.emit_to_method('    if (readlink("/proc/self/exe", _exe_path, sizeof(_exe_path)) != -1) {')
            self.emit_to_method('        char* _last_slash = strrchr(_exe_path, \'/\');')
            self.emit_to_method('        if (_last_slash) *_last_slash = \'\\0\';')
            self.emit_to_method('        chdir(_exe_path);')
            self.emit_to_method('    }')
            self.emit_to_method('#endif')

        self.push_scope()

        # Регистрируем self
        if self.current_class_name and not is_static and not is_constructor:
            self.var_types['self'] = self.current_class_name

        # Параметры и корни
        for p in node.parameters:
            self.var_types[p.name] = p.type
            ctype = self.type_to_cpp(p.type, is_param=True)
            if ctype == 'ely_value*':
                self.emit_to_method(f"gc_add_root((void**)&{p.name});")
                if self.scope_roots:
                    self.scope_roots[-1].append(p.name)

        body_stmts = self._hoist_nested_functions(node.body)
        for stmt in body_stmts:
            self.gen_statement(stmt)

        self.pop_scope()
        self.indent -= 1
        self.emit_to_method("}")

        self.inside_func = False
        self.current_function = old_function

        for hoisted in self.hoisted_functions:
            self.gen_function(hoisted)

        old_method.extend(self.method_code)
        self.method_code = old_method

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

    # -------------------------------------------------------------------
    # Диспетчер операторов
    # -------------------------------------------------------------------
    def gen_statement(self, stmt: Statement):
        if isinstance(stmt, GlobalCBlock):
            return
        if isinstance(stmt, ExpressionStatement):
            expr = self.gen_expression(stmt.expression)
            if expr:
                self.emit_to_method(f"{expr};")
        elif isinstance(stmt, VariableDeclaration):
            self._gen_local_variable(stmt)
        elif isinstance(stmt, MethodDeclaration):
            self.gen_function(stmt)
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
            self.emit_to_method("break;")
        elif isinstance(stmt, Assignment):
            expr = self.gen_expression(stmt)
            if expr:
                self.emit_to_method(f"{expr};")

    # -------------------------------------------------------------------
    # Диспетчер выражений
    # -------------------------------------------------------------------
    def gen_expression(self, expr: Expression) -> Optional[str]:
        if isinstance(expr, Literal):
            return self._gen_literal(expr)
        elif isinstance(expr, SuperCall):
            return self._gen_super_call(expr)
        elif isinstance(expr, AwaitExpression):
            arg = self.gen_expression(expr.expression)
            return f"({arg}).get()"
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
        elif isinstance(expr, TypeOfExpression):
            arg = self.gen_expression(expr.argument)
            return f"ely_value_new_string(ely_typeof({arg}))"
        elif isinstance(expr, FieldsExpression):
            arg = self.gen_expression(expr.argument)
            return f"ely_value_get_fields({arg})"
        elif isinstance(expr, MethodsExpression):
            arg = self.gen_expression(expr.argument)
            return f"ely_value_get_methods({arg})"
        else:
            self.error(f"Unknown expression type: {type(expr).__name__}", expr)
            return None

    # -------------------------------------------------------------------
    # Литералы
    # -------------------------------------------------------------------
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
            return f'ely_value_new_string("{escaped}")'   # (char*) убран
        else:
            return "ely_value_new_null()"

    # -------------------------------------------------------------------
    # Идентификаторы и доступ к членам
    # -------------------------------------------------------------------
    def _gen_identifier(self, node: Identifier) -> str:
        name = node.name
        if name == 'self' and self.current_class_name:
            return "this"

        if name in self.classes_ast:
            return name

        if self.current_class_name:
            cls = self.classes_ast.get(self.current_class_name)
            if cls:
                for sf in cls.static_fields:
                    if sf.name == name:
                        return f"{self.current_class_name}::{sf.name}"
                for sm in cls.static_methods:
                    if sm.name == name:
                        return f"{self.current_class_name}::{sm.name}"

                if self._is_field_in_hierarchy(cls, name):
                    field_type = self._get_field_type_in_hierarchy(cls, name)
                    if field_type == 'str':
                        return f"ely_value_new_string(this->{name})"
                    elif field_type in ('int','uint','more','umore','byte','ubyte'):
                        return f"ely_value_new_int(this->{name})"
                    elif field_type in ('flt','double'):
                        return f"ely_value_new_double(this->{name})"
                    elif field_type == 'bool':
                        return f"ely_value_new_bool(this->{name})"
                    else:
                        return f"this->{name}"

        if name in self.global_types:
            return name
        # Ищем переменную в текущем и всех родительских scope'ах
        found_type = None
        if name in self.var_types:
            found_type = self.var_types[name]
        else:
            for scope in reversed(self.scopes):
                if name in scope:
                    found_type = scope[name]
                    break

        if found_type is not None:
            t = found_type
            if t in ('int','uint','more','umore','byte','ubyte'):
                return f"ely_value_new_int({name})"
            elif t in ('flt','double'):
                return f"ely_value_new_double({name})"
            elif t == 'bool':
                return f"ely_value_new_bool({name})"
            elif t == 'str':
                return f"ely_value_new_string({name})"
            elif t in self.classes_ast:
                return name
            else:
                return name

        self.ensure_identifier(name, node.line, node.col)
        return name

    def _get_field_type_in_hierarchy(self, cls: ClassDeclaration, field: str) -> Optional[str]:
        for f in cls.fields:
            if f.name == field:
                return f.type
        if cls.extends and cls.extends in self.classes_ast:
            return self._get_field_type_in_hierarchy(self.classes_ast[cls.extends], field)
        return None

    # -------------------------------------------------------------------
    # Присваивание – static member
    # -------------------------------------------------------------------
    def _gen_assignment(self, node: Assignment) -> str:
        # Присваивание в индекс
        if isinstance(node.target, IndexExpression):
            target_code = self.gen_expression(node.target.target)
            index_code = self.gen_expression(node.target.index)
            value_code = self.gen_expression(node.value)
            return f"ely_value_set_index({target_code}, {index_code}, {value_code});"

        # --- Прямое присваивание полю текущего класса ---
        if isinstance(node.target, Identifier) and self.current_class_name:
            cls = self.classes_ast.get(self.current_class_name)
            if cls:
                # Статическое поле?
                for sf in cls.static_fields:
                    if sf.name == node.target.name:
                        raw_value = self.gen_expression(node.value)
                        if node.operator != '=':
                            binary = BinaryOp(node.line, node.col, node.target, node.operator[:-1], node.value)
                            value_code = self.gen_expression(binary)
                        else:
                            value_code = raw_value
                        # Статические поля — ely_value*, если значение не ely_value*, оборачиваем
                        if not value_code.strip().startswith('ely_value_'):
                            # Если это литерал или нативный тип, нужно создать ely_value*
                            src_type = self.get_expression_type(node.value)
                            if src_type in ('int','uint','more','umore','byte','ubyte'):
                                value_code = f"ely_value_new_int({value_code})"
                            elif src_type in ('flt','double'):
                                value_code = f"ely_value_new_double({value_code})"
                            elif src_type == 'bool':
                                value_code = f"ely_value_new_bool({1 if value_code=='true' else 0})"
                            elif src_type == 'str':
                                value_code = f"ely_value_new_string({value_code})"
                        return f"{self.current_class_name}::{node.target.name} = {value_code};"

                # Поле экземпляра
                if self._is_field_in_hierarchy(cls, node.target.name):
                    raw_value = self.gen_expression(node.value)
                    if node.operator != '=':
                        binary = BinaryOp(node.line, node.col, node.target, node.operator[:-1], node.value)
                        value_code = self.gen_expression(binary)
                    else:
                        value_code = raw_value

                    field_type = self._get_field_type_in_hierarchy(cls, node.target.name)
                    src_type = self.get_expression_type(node.value)
                    if field_type == 'str':
                        if 'ely_value_new_string' in value_code:
                            value_code = f"ely_str_dup(ely_value_to_string({value_code}))"
                        else:
                            value_code = f"ely_str_dup({value_code})"
                    elif field_type in ('int','uint','more','umore','byte','ubyte'):
                        if src_type not in ('int','uint','more','umore','byte','ubyte'):
                            value_code = f"ely_value_as_int({value_code})"
                    elif field_type in ('flt','double'):
                        if src_type not in ('flt','double'):
                            value_code = f"ely_value_as_double({value_code})"
                    elif field_type == 'bool':
                        if src_type != 'bool':
                            value_code = f"ely_value_as_bool({value_code})"
                    return f"this->{node.target.name} = {value_code};"

        # --- Присваивание локальной нативной переменной ---
        if isinstance(node.target, Identifier):
            target_type = None
            if node.target.name in self.var_types:
                target_type = self.var_types[node.target.name]
            else:
                for scope in reversed(self.scopes):
                    if node.target.name in scope:
                        target_type = scope[node.target.name]
                        break
            if target_type in ('int','uint','more','umore','byte','ubyte','flt','double','bool','str','char'):
                raw_value = self.gen_expression(node.value)
                if node.operator != '=':
                    binary = BinaryOp(node.line, node.col, node.target, node.operator[:-1], node.value)
                    value_code = self.gen_expression(binary)
                else:
                    value_code = raw_value
                if target_type == 'str':
                    value_code = f"ely_str_dup(ely_value_to_string({value_code}))"
                elif target_type in ('int','uint','more','umore','byte','ubyte'):
                    value_code = f"ely_value_as_int({value_code})"
                elif target_type in ('flt','double'):
                    value_code = f"ely_value_as_double({value_code})"
                elif target_type == 'bool':
                    value_code = f"ely_value_as_bool({value_code})"
                return f"{node.target.name} = {value_code};"

        # --- Общий случай ---
        target_code = self.gen_expression(node.target)
        raw_value = self.gen_expression(node.value)
        if node.operator != '=':
            binary = BinaryOp(node.line, node.col, node.target, node.operator[:-1], node.value)
            value_code = self.gen_expression(binary)
        else:
            value_code = raw_value

        if isinstance(node.target, MemberAccess):
            obj_type = self.get_expression_type(node.target.object)
            if obj_type in self.classes_ast:
                # Статические поля
                for sf in cls.static_fields:
                    if sf.name == node.target.member:
                        value_code = self.gen_expression(node.value)
                        if node.operator != '=':
                            binary = BinaryOp(node.line, node.col, node.target, node.operator[:-1], node.value)
                            value_code = self.gen_expression(binary)
                        return f"{obj_type}::{sf.name} = {value_code};"
                cls = self.classes_ast[obj_type]
                # Свойства с сеттером
                for prop in cls.properties:
                    if prop.name == node.target.member and prop.setter:
                        obj_c = self.gen_expression(node.target.object)
                        val = value_code
                        if prop.type == 'str':
                            val = f"ely_value_to_string({val})"
                        return f"{obj_c}->{prop.setter.name}({val});"
                # Свойство через сеттер set<Name>
                setter_name = f"set{node.target.member[0].upper()}{node.target.member[1:]}"
                for m in cls.all_methods:
                    if m.name == setter_name and len(m.parameters) == 1:
                        obj_c = self.gen_expression(node.target.object)
                        param_type = m.parameters[0].type
                        val = value_code
                        if param_type == 'str':
                            val = f"ely_value_to_string({val})"
                        elif param_type in ('int','uint','more','umore','byte','ubyte'):
                            val = f"ely_value_as_int({val})"
                        elif param_type in ('flt','double'):
                            val = f"ely_value_as_double({val})"
                        elif param_type == 'bool':
                            val = f"ely_value_as_bool({val})"
                        return f"{obj_c}->{setter_name}({val});"
                # Обычные поля
                if self._is_field_in_hierarchy(cls, node.target.member):
                    obj_c = self.gen_expression(node.target.object)
                    field_type = self._get_field_type_in_hierarchy(cls, node.target.member)
                    src_type = self.get_expression_type(node.value)
                    if field_type == 'str':
                        if src_type == 'str':
                            value_code = f"ely_str_dup({value_code})"
                        else:
                            value_code = f"ely_str_dup(ely_value_to_string({value_code}))"
                    elif field_type in ('int','uint','more','umore','byte','ubyte'):
                        if src_type not in ('int','uint','more','umore','byte','ubyte'):
                            value_code = f"ely_value_as_int({value_code})"
                    elif field_type in ('flt','double'):
                        if src_type not in ('flt','double'):
                            value_code = f"ely_value_as_double({value_code})"
                    elif field_type == 'bool':
                        if src_type != 'bool':
                            value_code = f"ely_value_as_bool({value_code})"
                    return f"{obj_c}->{node.target.member} = {value_code};"
            obj = self.gen_expression(node.target.object)
            return f"ely_value_set_key({obj}, \"{node.target.member}\", {value_code})"

        if '::' in target_code:
            return f"{target_code} = {value_code};"

        return f"{target_code} = {value_code};"

    def _gen_member_access(self, node: MemberAccess) -> str:
        obj_code = self.gen_expression(node.object)
        obj_type = self.get_expression_type(node.object)

        # Пространства имён
        ns_name = obj_code
        if ns_name in self.namespaces:
            ns_members = self.namespaces[ns_name]
            if node.member in ns_members:
                return ns_members[node.member]
            else:
                self.error(f"Namespace '{ns_name}' has no member '{node.member}'", node)
                return "ely_value_new_null()"

        # Классы: статические поля/методы или поля экземпляра
        if obj_type in self.classes_ast:
            cls = self.classes_ast[obj_type]
            # Статические поля
            for sf in cls.static_fields:
                if sf.name == node.member:
                    return f"{obj_type}::{sf.name}"
            # Статические методы
            for sm in cls.static_methods:
                if sm.name == node.member:
                    return f"{obj_type}::{sm.name}"
            # Поля экземпляра – возвращаем голый указатель, без обёртки
            if self._is_field_in_hierarchy(cls, node.member):
                return f"{obj_code}->{node.member}"
            # Свойство через геттер get<Name>
            getter_name = f"get{node.member[0].upper()}{node.member[1:]}"
            for m in cls.all_methods:
                if m.name == getter_name and len(m.parameters) == 0:
                    return f"({obj_code}->{getter_name}())"
            self.error(f"Class '{obj_type}' has no member '{node.member}'", node)
            return "ely_value_new_null()"

        # Для остальных типов – общий доступ через ключ
        return f"ely_value_get_key({obj_code}, \"{node.member}\")"

    def _is_field_in_hierarchy(self, cls: ClassDeclaration, field: str) -> bool:
        if cls is None:
            return False
        if field in [f.name for f in cls.fields]:
            return True
        if cls.extends and cls.extends in self.classes_ast:
            return self._is_field_in_hierarchy(self.classes_ast[cls.extends], field)
        return False

    # -------------------------------------------------------------------
    # Вызовы функций и методов
    # -------------------------------------------------------------------
    def _gen_call(self, node: Call) -> str:
        if isinstance(node.callee, MemberAccess):
            return self._gen_method_call(node)
        if isinstance(node.callee, AwaitExpression):
            arg = self.gen_expression(node.callee.expression)
            return f"({arg}).get()"
        if not isinstance(node.callee, Identifier):
            self.error("Call target must be identifier", node)
            return "ely_value_new_null()"

        func_name = node.callee.name

        # Конструктор
        if func_name.endswith('_constructor'):
            return self._gen_constructor_call(node, func_name)

        # Старые статические методы (ClassName_method)
        if '_' in func_name and not func_name.startswith('__'):
            parts = func_name.split('_', 1)
            if parts[0] in self.classes_ast:
                cls = self.classes_ast[parts[0]]
                for sm in cls.static_methods:
                    if sm.name == parts[1]:
                        args = [self.gen_expression(a) for a in node.arguments]
                        return f"{parts[0]}::{sm.name}({', '.join(args)})"
                self.error(f"Static method '{func_name}' not found in class '{parts[0]}'", node)
                return "ely_value_new_null()"

        # Оригинальные функции
        if func_name in self.original_functions:
            func_node = self.original_functions[func_name]
            if func_node.is_async:
                args_code = ', '.join([self.gen_expression(a) for a in node.arguments])
                return f"ElyEventLoop::instance().run([&]() {{ return {func_name}({args_code}); }})"
            if func_node.type_params:
                return self._gen_generic_call(node, func_node)
            args = []
            for i, arg in enumerate(node.arguments):
                code = self.gen_expression(arg)
                if i < len(func_node.parameters):
                    expected_c = self.type_to_cpp(func_node.parameters[i].type, is_param=True)
                    code = self._convert_to_c_type_expr(code, expected_c)
                args.append(code)
            return f"{func_name}({', '.join(args)})"

        # fields / methods
        if func_name == 'fields':
            if len(node.arguments) != 1:
                self.error("fields() expects 1 argument", node)
                return "ely_value_new_null()"
            arg = self.gen_expression(node.arguments[0])
            return f"ely_value_get_fields({arg})"
        if func_name == 'methods':
            if len(node.arguments) != 1:
                self.error("methods() expects 1 argument", node)
                return "ely_value_new_null()"
            arg = self.gen_expression(node.arguments[0])
            return f"ely_value_get_methods({arg})"

        # Встроенные функции
        if func_name in self.builtin_signatures:
            c_name, ret_ely, param_ctypes = self.builtin_signatures[func_name]
            args = []
            for i, arg in enumerate(node.arguments):
                code = self.gen_expression(arg)
                if i < len(param_ctypes):
                    c_type = param_ctypes[i]
                    if c_type == 'ely_value*' or c_type == 'void*' or c_type == 'any':
                        pass
                    elif c_type == 'char*':
                        # если уже есть ely_value_new_string, не оборачиваем повторно
                        if 'ely_value_new_string' not in code:
                            code = f"ely_value_new_string({code})"
                        code = f"ely_value_to_string({code})"
                    elif c_type in ('int', 'long long', 'unsigned int', 'size_t'):
                        code = f"ely_value_as_int({code})"
                    elif c_type == 'double':
                        code = f"ely_value_as_double({code})"
                args.append(code)
            call_expr = f"{c_name}({', '.join(args)})"
            return self._wrap_result(call_expr, ret_ely)

        # Extern-функции (включая найденные из cCode/cppCode)
        if func_name in self.extern_functions:
            ext = self.extern_functions[func_name]
            ret = ext.return_type or 'void'
            args = []
            for i, arg in enumerate(node.arguments):
                code = self.gen_expression(arg)
                if i < len(ext.parameters):
                    raw_type = ext.parameters[i].type.strip()
                    # Приводим к каноническому виду
                    if raw_type in ('char*', 'const char*', 'char *', 'const char *'):
                        c_type = 'char*'
                    elif raw_type in ('int', 'long', 'long long', 'unsigned', 'unsigned int', 'size_t'):
                        c_type = 'int'
                    elif raw_type in ('float', 'double'):
                        c_type = 'double'
                    elif raw_type == 'bool':
                        c_type = 'bool'
                    else:
                        c_type = 'ely_value*'

                    if c_type == 'char*':
                        if '->' in code and 'ely_value_new_string' not in code:
                            code = f"ely_value_new_string({code})"
                        code = f"ely_value_to_string({code})"
                    elif c_type == 'int':
                        code = f"ely_value_as_int({code})"
                    elif c_type == 'double':
                        code = f"ely_value_as_double({code})"
                    elif c_type == 'bool':
                        code = f"ely_value_as_bool({code})"
                args.append(code)
            call_expr = f"{func_name}({', '.join(args)})"
            # Преобразуем C-тип возврата в Ely-тип для _wrap_result
            if ret == 'char*' or ret == 'const char*':
                ely_ret = 'str'
            elif ret in ('int', 'long', 'long long', 'unsigned', 'unsigned int', 'size_t'):
                ely_ret = 'int'
            elif ret in ('float', 'double'):
                ely_ret = 'double'
            elif ret == 'bool':
                ely_ret = 'bool'
            else:
                ely_ret = 'any'
            return self._wrap_result(call_expr, ely_ret)

        # Методы текущего класса
        if self.current_class_name:
            cls = self.classes_ast.get(self.current_class_name)
            if cls:
                for m in cls.all_methods:
                    if m.name == func_name:
                        args = [self.gen_expression(a) for a in node.arguments]
                        for i, arg in enumerate(node.arguments):
                            if i < len(m.parameters):
                                expected = self.type_to_cpp(m.parameters[i].type, is_param=True)
                                args[i] = self._convert_to_c_type_expr(args[i], expected)
                        return f"this->{func_name}({', '.join(args)})"

        self.error(f"Unknown function '{func_name}'", node)
        return "ely_value_new_null()"

    def _gen_method_call(self, node: Call) -> str:
        obj = node.callee.object
        method = node.callee.member
        obj_type = self.get_expression_type(obj)
        obj_code = self.gen_expression(obj)
        if obj_code is None:
            return "ely_value_new_null()"

        if obj_type in self.classes_ast:
            cls = self.classes_ast[obj_type]
            for sm in cls.static_methods:
                if sm.name == method:
                    args = [self.gen_expression(a) for a in node.arguments]
                    for i, arg in enumerate(node.arguments):
                        if i < len(sm.parameters):
                            expected = self.type_to_cpp(sm.parameters[i].type, is_param=True)
                            args[i] = self._convert_to_c_type_expr(args[i], expected)
                    return f"{obj_type}::{sm.name}({', '.join(args)})"

        # Интерфейсы – виртуальный вызов
        if obj_type in self.interfaces_ast:
            iface = self.interfaces_ast[obj_type]
            # Проверяем, есть ли метод в интерфейсе
            method_exists = any(m.name == method for m in iface.methods)
            if not method_exists:
                self.error(f"Interface '{obj_type}' has no method '{method}'", node)
                return "ely_value_new_null()"
            args = [self.gen_expression(a) for a in node.arguments]
            return f"({obj_code}->{method}({', '.join(args)}))"

        # Встроенные методы для конкретных типов
        if obj_type.startswith('arr<'):
            return self._gen_array_method(obj_code, method, node.arguments)
        if obj_type.startswith('dict<'):
            return self._gen_dict_method(obj_code, method, node.arguments)
        if obj_type == 'str':
            return self._gen_str_method(obj_code, method, node.arguments)
        if obj_type in ('int','uint','more','umore','flt','double'):
            return self._gen_num_method(obj_code, method, obj_type)

        # Методы экземпляров классов
        if obj_type in self.classes_ast:
            cls = self.classes_ast[obj_type]
            method_node = None
            for m in cls.all_methods:
                if m.name == method:
                    method_node = m
                    break
            if method_node:
                args = []
                for i, arg in enumerate(node.arguments):
                    code = self.gen_expression(arg)
                    if i < len(method_node.parameters):
                        expected = self.type_to_cpp(method_node.parameters[i].type, is_param=True)
                        code = self._convert_to_c_type_expr(code, expected)
                    args.append(code)
                return f"({obj_code}->{method}({', '.join(args)}))"
            else:
                self.error(f"Class '{obj_type}' has no method '{method}'", node)
                return "ely_value_new_null()"

        # Для any (или неизвестного типа) – динамическая диспетчеризация через ely_value_call_method
        args_code = [self.gen_expression(a) for a in node.arguments]
        argc = len(args_code)
        if argc == 0:
            return f"ely_value_call_method({obj_code}, \"{method}\", NULL, 0)"
        # Создаём временный массив
        arr_name = f"__args_{self.temp_counter}"
        self.temp_counter += 1
        # Генерируем объявление массива и заполнение
        self.emit_to_method(f"ely_value* {arr_name}[] = {{ {', '.join(args_code)} }};")
        return f"ely_value_call_method({obj_code}, \"{method}\", {arr_name}, {argc})"

    def _gen_constructor_call(self, node: Call, func_name: str) -> str:
        class_name = func_name[:-len('_constructor')]
        cls = self.classes_ast.get(class_name)
        if not cls:
            self.error(f"Unknown class {class_name}", node)
            return "ely_value_new_null()"
        args = [self.gen_expression(a) for a in node.arguments]
        params = self.collect_constructor_params(cls)
        for i, param in enumerate(params):
            if i < len(args):
                args[i] = self._convert_to_c_type_expr(args[i], self.type_to_cpp(param.type, is_param=True))
        return f"(new {class_name}({', '.join(args)}))"

    # -------------------------------------------------------------------
    # Арифметика и сравнения (двоичные и унарные)
    # -------------------------------------------------------------------
    def _gen_binary_op(self, node: BinaryOp) -> str:
        left = self.gen_expression(node.left)
        right = self.gen_expression(node.right)
        op = node.operator
        left_type = self.get_expression_type(node.left)

        # Операторные методы классов
        if left_type in self.classes_ast:
            ops = {'+':'__add','-':'__sub','*':'__mul','/':'__div','%':'__mod',
                '==':'__eq','!=':'__ne','<':'__lt','<=':'__le','>':'__gt','>=':'__ge'}
            method_name = ops.get(op)
            if method_name:
                cls = self.classes_ast[left_type]
                for m in cls.all_methods:
                    if m.name == method_name and len(m.parameters) >= 1:
                        expected = m.parameters[0].type
                        right = self._convert_to_c_type_expr(right, self.type_to_cpp(expected, is_param=True))
                        return f"({left}->{method_name}({right}))"

        op_map = {'+':'add','-':'sub','*':'mul','/':'div','%':'mod',
                '==':'eq','!=':'ne','<':'lt','<=':'le','>':'gt','>=':'ge',
                '&&':'and','||':'or'}

        def wrap(operand, expr):
            t = self.get_expression_type(expr)
            if 'ely_value_new_' in operand:
                return operand
            if t == 'str':
                return f"ely_value_new_string({operand})"
            elif t in ('int','uint','more','umore','byte','ubyte'):
                return f"ely_value_new_int({operand})"
            elif t in ('flt','double'):
                return f"ely_value_new_double({operand})"
            elif t == 'bool':
                return f"ely_value_new_bool({operand})"
            return operand
        left = wrap(left, node.left)
        right = wrap(right, node.right)

        func = f"ely_value_{op_map.get(op, op)}"
        return f"{func}({left}, {right})"

    def _gen_unary_op(self, node: UnaryOp) -> str:
        operand = self.gen_expression(node.operand)
        op = node.operator
        if op == '!':
            if 'ely_value_new_' in operand:
                return f"ely_value_not({operand})"
            else:
                return f"ely_value_not(ely_value_new_bool({operand}))"
        if op == '-':
            t = self.get_expression_type(node.operand)
            if t in ('int','uint','more','umore','byte','ubyte'):
                if 'ely_value_new_' in operand:
                    return f"ely_value_neg({operand})"
                else:
                    return f"ely_value_neg(ely_value_new_int({operand}))"
            elif t in ('flt','double'):
                if 'ely_value_new_' in operand:
                    return f"ely_value_neg({operand})"
                else:
                    return f"ely_value_neg(ely_value_new_double({operand}))"
            else:
                return f"ely_value_neg({operand})"
        if op == '&': return f"(&{operand})"
        return f"{op}{operand}"

    # -------------------------------------------------------------------
    # Условный оператор
    # -------------------------------------------------------------------
    def _gen_conditional(self, node: Conditional) -> str:
        cond = self.gen_expression(node.condition)
        then_expr = self.gen_expression(node.then_expr)
        else_expr = self.gen_expression(node.else_expr)
        return f"((ely_value_as_bool({cond})) ? {then_expr} : {else_expr})"

    # -------------------------------------------------------------------
    # F-строки, массивы, словари, индексация
    # -------------------------------------------------------------------
    def _gen_fstring(self, node: FString) -> str:
        if not node.parts: return 'ely_value_new_string("")'
        result = None
        for part in node.parts:
            if isinstance(part, str):
                escaped = part.replace('"','\\"').replace('\n','\\n')
                part_expr = f'ely_value_new_string("{escaped}")'
            else:
                part_expr = self.gen_expression(part)
            result = part_expr if result is None else f'ely_value_add({result}, {part_expr})'
        return result

    def _gen_array_literal(self, node: ArrayLiteral) -> str:
        if not node.elements: return "ely_value_new_array(arr_new())"
        elems = []
        for elem in node.elements:
            tmp = f"__tmp_ary_{self.temp_counter}"
            self.temp_counter += 1
            self.emit_to_method(f"ely_value* {tmp} = {self.gen_expression(elem)};")
            elems.append(tmp)
        arr_var = f"__arr_{self.temp_counter}"
        self.temp_counter += 1
        self.emit_to_method(f"arr* {arr_var} = arr_new();")
        for e in elems:
            self.emit_to_method(f"arr_push({arr_var}, {e});")
        return f"ely_value_new_array({arr_var})"

    def _gen_dict_literal(self, node: DictLiteral) -> str:
        if not node.pairs: return "ely_value_new_object(dict_new_str())"
        pairs = []
        for pair in node.pairs:
            key_tmp = f"__tmp_key_{self.temp_counter}"
            self.temp_counter += 1
            val_tmp = f"__tmp_val_{self.temp_counter}"
            self.temp_counter += 1
            self.emit_to_method(f"ely_value* {key_tmp} = {self.gen_expression(pair.key)};")
            self.emit_to_method(f"ely_value* {val_tmp} = {self.gen_expression(pair.value)};")
            pairs.append((key_tmp, val_tmp))
        dict_var = f"__dict_{self.temp_counter}"
        self.temp_counter += 1
        self.emit_to_method(f"dict* {dict_var} = dict_new_str();")
        for key, val in pairs:
            self.emit_to_method(f"dict_set_str({dict_var}, {key}->u.string_val, {val});")
        return f"ely_value_new_object({dict_var})"

    def _gen_index_expression(self, node: IndexExpression) -> str:
        target = self.gen_expression(node.target)
        index = self.gen_expression(node.index)
        return f"ely_value_index({target}, {index})"

    # -------------------------------------------------------------------
    # Управляющие конструкции
    # -------------------------------------------------------------------
    def _gen_if(self, node: IfStatement):
        cond = self.gen_expression(node.condition)
        self.emit_to_method(f"if (ely_value_as_bool({cond})) {{")
        self.indent += 1
        self.push_scope()
        for stmt in node.then_body: self.gen_statement(stmt)
        self.pop_scope()
        self.indent -= 1
        if node.else_body:
            self.emit_to_method("} else {")
            self.indent += 1
            self.push_scope()
            for stmt in node.else_body: self.gen_statement(stmt)
            self.pop_scope()
            self.indent -= 1
        self.emit_to_method("}")

    def _gen_while(self, node: WhileLoop):
        cond = self.gen_expression(node.condition)
        self.emit_to_method(f"while (ely_value_as_bool({cond})) {{")
        self.indent += 1
        self.push_scope()
        for stmt in node.body: self.gen_statement(stmt)
        self.pop_scope()
        self.indent -= 1
        self.emit_to_method("}")

    def _gen_for(self, node: ForLoop):
        self.push_scope()
        init_part = ";"
        if node.init:
            if isinstance(node.init, VariableDeclaration):
                self._gen_local_variable(node.init)
            elif isinstance(node.init, ExpressionStatement):
                init_part = self.gen_expression(node.init.expression) + ";"
        cond_part = "1" if not node.condition else f"ely_value_as_bool({self.gen_expression(node.condition)})"
        update_part = "" if not node.update else self.gen_expression(node.update).rstrip(';')
        self.emit_to_method(f"for ({init_part} {cond_part}; {update_part}) {{")
        self.indent += 1
        for stmt in node.body: self.gen_statement(stmt)
        self.indent -= 1
        self.pop_scope()
        self.emit_to_method("}")

    def _gen_foreach(self, node: ForEachLoop):
        iter_type = self.get_expression_type(node.iterable)
        iter_code = self.gen_expression(node.iterable)

        # Поддержка классов с __iter__
        if iter_type in self.classes_ast:
            # Вызываем __iter__
            iter_val = f"__iter_{self.temp_counter}"
            self.temp_counter += 1
            self.emit_to_method(f"ely_value* {iter_val} = ({iter_code}->__iter__());")
            self.emit_to_method(f"gc_add_root((void**)&{iter_val});")
            # Цикл по массиву
            self.emit_to_method(f"for (size_t __i = 0; __i < ely_array_len({iter_val}); __i++) {{")
            self.indent += 1
            self.emit_to_method(f"ely_value* __elem = ely_array_get({iter_val}, __i);")
            self.emit_to_method(f"gc_add_root((void**)&__elem);")
            # Объявляем переменную цикла
            if isinstance(node.item_decl, VariableDeclaration):
                decl = node.item_decl
                c_type = self.type_to_cpp(decl.type) if decl.type else 'ely_value*'
                self.emit_to_method(f"{c_type} {decl.name} = __elem;")
                if c_type == 'ely_value*':
                    self.emit_to_method(f"gc_add_root((void**)&{decl.name});")
                self.var_types[decl.name] = decl.type or 'any'
            # Тело
            for stmt in node.body:
                self.gen_statement(stmt)
            self.emit_to_method(f"gc_remove_root((void**)&__elem);")
            self.indent -= 1
            self.emit_to_method("}")
            self.emit_to_method(f"gc_remove_root((void**)&{iter_val});")
            return

        # Старая логика для arr< и dict<
        if iter_type.startswith('arr<'):
            self.emit_to_method(f"for (size_t __i = 0; __i < ely_array_len({iter_code}); __i++) {{")
            self.indent += 1
            elem = f"ely_array_get({iter_code}, __i)"
            # Сразу вставляем объявление переменной и тело (без промежуточной __elem)
            if isinstance(node.item_decl, VariableDeclaration):
                decl = node.item_decl
                c_type = self.type_to_cpp(decl.type) if decl.type else 'ely_value*'
                self.emit_to_method(f"{c_type} {decl.name} = {elem};")
                if c_type == 'ely_value*':
                    self.emit_to_method(f"gc_add_root((void**)&{decl.name});")
                self.var_types[decl.name] = decl.type or 'any'
            for stmt in node.body:
                self.gen_statement(stmt)
            self.indent -= 1
            self.emit_to_method("}")
        elif iter_type.startswith('dict<'):
            keys_var = f"__keys_{self.temp_counter}"
            self.temp_counter += 1
            self.emit_to_method(f"ely_value* {keys_var} = ely_dict_keys({iter_code});")
            self.emit_to_method(f"for (size_t __i = 0; __i < ely_array_len({keys_var}); __i++) {{")
            self.indent += 1
            self.emit_to_method(f"ely_value* __key = ely_array_get({keys_var}, __i);")
            self.emit_to_method(f"ely_value* __value = ely_dict_get({iter_code}, __key);")
            if isinstance(node.item_decl, VariableDeclaration):
                decl = node.item_decl
                c_type = self.type_to_cpp(decl.type) if decl.type else 'ely_value*'
                self.emit_to_method(f"{c_type} {decl.name} = __value;")
                if c_type == 'ely_value*':
                    self.emit_to_method(f"gc_add_root((void**)&{decl.name});")
                self.var_types[decl.name] = decl.type or 'any'
            for stmt in node.body:
                self.gen_statement(stmt)
            self.indent -= 1
            self.emit_to_method("}")
            self.emit_to_method(f"ely_value_free({keys_var});")
        else:
            self.error(f"foreach not supported for {iter_type}", node.iterable)

    def _emit_foreach_elem(self, node: ForEachLoop, val_code: str):
        if isinstance(node.item_decl, VariableDeclaration):
            decl_type = node.item_decl.type or 'any'
            c_type = self.type_to_cpp(decl_type)
            self.emit_to_method(f"{c_type} {node.item_decl.name} = {val_code};")
            self.var_types[node.item_decl.name] = decl_type
            if c_type == 'ely_value*':
                self.emit_to_method(f"gc_add_root((void**)&{node.item_decl.name});")
                if self.scope_roots:
                    self.scope_roots[-1].append(node.item_decl.name)

    def _gen_match(self, node: MatchStatement):
        expr = self.gen_expression(node.expression)
        self.emit_to_method(f"switch ({expr}) {{")
        self.indent += 1
        for case in node.cases:
            self.emit_to_method(f"case {self.gen_expression(case.value)}: {{")
            self.indent += 1
            for stmt in case.body: self.gen_statement(stmt)
            self.emit_to_method("break;")
            self.indent -= 1
            self.emit_to_method("}")
        if node.default_body:
            self.emit_to_method("default: {")
            self.indent += 1
            for stmt in node.default_body: self.gen_statement(stmt)
            self.indent -= 1
            self.emit_to_method("}")
        self.indent -= 1
        self.emit_to_method("}")

    def _gen_asafe(self, node: AsafeBlock):
        param = node.except_handler.parameter if node.except_handler else '__ex'
        self.emit_to_method(f"ely_value* volatile {param} = NULL;")
        self.var_types[param] = 'any'
        self.emit_to_method(f"gc_add_root((void**)&{param});")
        if self.scope_roots: self.scope_roots[-1].append(param)
        self.emit_to_method("int __ex_result = setjmp(__ex_buf);")
        self.emit_to_method("if (__ex_result == 0) {")
        self.indent += 1; self.push_scope()
        for stmt in node.body: self.gen_statement(stmt)
        self.pop_scope(); self.indent -= 1
        self.emit_to_method("} else {")
        self.indent += 1
        if node.except_handler:
            self.emit_to_method(f"{param} = __ex_value;")
            for stmt in node.except_handler.body: self.gen_statement(stmt)
            self.emit_to_method("__ex_value = NULL;")
        self.indent -= 1
        self.emit_to_method("}")

    def _gen_throw(self, node: ThrowStatement):
        val = self.gen_expression(node.value)
        self.emit_to_method(f"__ex_value = {val};")
        self.emit_to_method("longjmp(__ex_buf, 1);")

    def _gen_giveback(self, node: GivebackStatement):
        if node.value:
            self.emit_to_method(f"return {self.gen_expression(node.value)};")
        else:
            self.emit_to_method("return;")

    def _gen_return(self, node: ReturnStatement):
        if not self.current_function:
            self.error("return outside function", node)
            return
        if node.value:
            val = self.gen_expression(node.value)
            val_type = self.get_expression_type(node.value)
            # Если возвращаемый тип функции – ely_value* (по умолчанию), оборачиваем нативные значения
            if self.func_return_type and self.func_return_type != 'void':
                cpp_ret = self.type_to_cpp(self.func_return_type, for_signature=True)
                if cpp_ret == 'ely_value*':
                    if val_type == 'str' and not val.startswith('ely_value_new_'):
                        val = f"ely_value_new_string({val})"
                    elif val_type in ('int','uint','more','umore','byte','ubyte') and not val.startswith('ely_value_new_'):
                        val = f"ely_value_new_int({val})"
                    elif val_type in ('flt','double') and not val.startswith('ely_value_new_'):
                        val = f"ely_value_new_double({val})"
                    elif val_type == 'bool' and not val.startswith('ely_value_new_'):
                        val = f"ely_value_new_bool({val})"
            if self.current_function == 'main':
                self.emit_to_method(f"return ely_value_as_int({val});")
            else:
                self.emit_to_method(f"return {val};")
        else:
            self.emit_to_method("return 0;" if self.current_function == 'main' else "return;")

    def _gen_collapse(self, node: CollapseStatement):
        if node.name in self.var_types:
            del self.var_types[node.name]

    # -------------------------------------------------------------------
    # Локальные переменные
    # -------------------------------------------------------------------
    def _gen_local_variable(self, node: VariableDeclaration):
        resolved = self.resolve_type_alias(node.type)
        if resolved == 'void':
            self.error("void variable", node)
            return
        is_class = resolved in self.classes_ast or resolved in self.interfaces_ast
        is_native = resolved in ('int','uint','more','umore','byte','ubyte','flt','double','bool','str','char')
        c_type = f"{resolved}*" if is_class else self.type_to_cpp(resolved)

        init_code = None
        if node.initializer:
            init_code = self.gen_expression(node.initializer)
            if is_native:
                if resolved == 'str':
                    init_code = f"ely_str_dup(ely_value_to_string({init_code}))"
                elif resolved in ('int','uint','more','umore','byte','ubyte'):
                    init_code = f"ely_value_as_int({init_code})"
                elif resolved in ('flt','double'):
                    init_code = f"ely_value_as_double({init_code})"
                elif resolved == 'bool':
                    init_code = f"ely_value_as_bool({init_code})"

        if init_code:
            self.emit_to_method(f"{c_type} {node.name} = {init_code};")
        else:
            if is_native:
                default = "0" if resolved != 'str' else "nullptr"
                if resolved == 'flt' or resolved == 'double': default = "0.0"
                if resolved == 'bool': default = "0"
                self.emit_to_method(f"{c_type} {node.name} = {default};")
            elif is_class:
                self.emit_to_method(f"{c_type} {node.name} = nullptr;")
            else:
                self.emit_to_method(f"ely_value* {node.name} = ely_value_new_null();")

        self.var_types[node.name] = resolved
        if is_class or (not is_native and resolved == 'any') or (not is_native and not is_class):
            self.emit_to_method(f"gc_add_root((void**)&{node.name});")
            if self.scope_roots:
                self.scope_roots[-1].append(node.name)

    # -------------------------------------------------------------------
    # Вспомогательные методы преобразования типов
    # -------------------------------------------------------------------
    def _convert_to_c_type_expr(self, expr_code: str, target_c_type: str) -> str:
        if target_c_type == 'char*':
            return f"ely_value_to_string({expr_code})"
        if target_c_type in ('int', 'long long', 'unsigned int', 'unsigned long long', 'signed char', 'unsigned char'):
            return f"ely_value_as_int({expr_code})"
        if target_c_type in ('float', 'double'):
            return f"ely_value_as_double({expr_code})"
        return expr_code

    def _convert_to_ctype(self, expr_node: Expression, expr_code: str, target_type: str) -> str:
        # Если код уже является созданием ely_value*, не оборачиваем повторно
        if 'ely_value_new_' in expr_code:
            return expr_code

        if target_type == 'any' or target_type == 'ely_value*':
            src = self.get_expression_type(expr_node)
            if src in ('int', 'uint', 'more', 'umore', 'byte', 'ubyte'):
                return f"ely_value_new_int({expr_code})"
            if src in ('double', 'flt'):
                return f"ely_value_new_double({expr_code})"
            if src == 'bool':
                return f"ely_value_new_bool({expr_code})"
            if src == 'str':
                return f"ely_value_new_string({expr_code})"
            return expr_code
        c_target = self.type_to_cpp(target_type, is_param=True)
        return self._convert_to_c_type_expr(expr_code, c_target)

    def _convert_value(self, value_code: str, from_type: str, to_type: str) -> str:
        if from_type in self.classes_ast and to_type in self.classes_ast:
            return value_code
        if from_type == 'any' or not from_type:
            if to_type == 'int': return f'ely_value_new_int(ely_value_as_int({value_code}))'
            if to_type in ('flt','double'): return f'ely_value_new_double(ely_value_as_double({value_code}))'
            if to_type == 'bool': return f'ely_value_new_bool(ely_value_as_bool({value_code}))'
            if to_type == 'str': return f'ely_value_new_string(ely_value_to_string({value_code}))'
        if self.is_numeric(from_type) and self.is_numeric(to_type):
            if to_type == 'int': return f'ely_value_new_int(ely_value_as_int({value_code}))'
            if to_type in ('flt','double'): return f'ely_value_new_double(ely_value_as_double({value_code}))'
        return f'ely_value_new_string(ely_value_to_string({value_code}))'

    def _wrap_result(self, call_expr: str, return_type: str) -> str:
        if return_type == 'void':
            return f"({{ {call_expr}; ely_value_new_null(); }})"
        if return_type in ('int', 'uint', 'more', 'umore', 'byte', 'ubyte'):
            return f"ely_value_new_int({call_expr})"
        if return_type in ('double', 'flt'):
            return f"ely_value_new_double({call_expr})"
        if return_type == 'bool':
            return f"ely_value_new_bool({call_expr})"
        if return_type == 'str':
            return f"ely_value_new_string({call_expr})"
        if return_type in ('object', 'dict'):
            return f"ely_value_new_object({call_expr})"
        if return_type == 'array' or return_type.startswith('arr<'):
            return f"ely_value_new_array({call_expr})"
        return call_expr

    # -------------------------------------------------------------------
    # Методы встроенных типов (полные реализации)
    # -------------------------------------------------------------------
    def _gen_array_method(self, obj_code: str, method: str, args: List[Expression]) -> str:
        args_code = [self.gen_expression(a) for a in args]
        if method == 'push':
            if len(args_code) != 1: self.error("push() expects 1 argument")
            val = self._convert_to_ctype(args[0], args_code[0], 'any')
            return f"ely_array_push({obj_code}, {val})"
        elif method == 'pop':
            return f"ely_array_pop({obj_code})"
        elif method == 'len':
            return self._wrap_result(f"ely_array_len({obj_code})", 'int')
        elif method == 'insert':
            if len(args_code) != 2: self.error("insert() expects 2 arguments")
            idx = self._convert_to_ctype(args[0], args_code[0], 'int')
            val = self._convert_to_ctype(args[1], args_code[1], 'any')
            return f"ely_array_insert({obj_code}, {idx}, {val})"
        elif method == 'remove':
            if len(args_code) != 1: self.error("remove() expects 1 argument")
            val = self._convert_to_ctype(args[0], args_code[0], 'any')
            return f"ely_array_remove_value({obj_code}, {val})"
        elif method == 'index':
            if len(args_code) != 1: self.error("index() expects 1 argument")
            val = self._convert_to_ctype(args[0], args_code[0], 'any')
            return self._wrap_result(f"ely_array_index({obj_code}, {val})", 'int')
        else:
            self.error(f"Unknown array method '{method}'")
            return ""

    def _gen_dict_method(self, obj_code: str, method: str, args: List[Expression]) -> str:
        args_code = [self.gen_expression(a) for a in args]
        if method == 'keys':
            return self._wrap_result(f"ely_dict_keys({obj_code})", 'arr<str>')
        elif method == 'del':
            if len(args_code) != 1: self.error("del() expects 1 argument")
            key = self._convert_to_ctype(args[0], args_code[0], 'any')
            return f"ely_dict_del({obj_code}, {key})"
        elif method == 'has':
            if len(args_code) != 1: self.error("has() expects 1 argument")
            key = self._convert_to_ctype(args[0], args_code[0], 'any')
            return self._wrap_result(f"ely_dict_has({obj_code}, {key})", 'bool')
        elif method == 'toJson':
            return self._wrap_result(f"ely_dict_to_json({obj_code})", 'str')
        else:
            self.error(f"Unknown dict method '{method}'")
            return ""

    def _gen_str_method(self, obj_code: str, method: str, args: List[Expression]) -> str:
        args_code = [self.gen_expression(a) for a in args]
        if method == 'len':
            return self._wrap_result(f"ely_str_len(({obj_code})->u.string_val)", 'int')
        elif method == 'concat':
            if len(args_code) != 1: self.error("concat() expects 1 argument")
            other = self._convert_to_ctype(args[0], args_code[0], 'str')
            return self._wrap_result(f"ely_str_concat(({obj_code})->u.string_val, {other})", 'str')
        elif method == 'substr':
            if len(args_code) != 2: self.error("substr() expects 2 arguments")
            start = self._convert_to_ctype(args[0], args_code[0], 'int')
            length = self._convert_to_ctype(args[1], args_code[1], 'int')
            return self._wrap_result(f"ely_str_substr(({obj_code})->u.string_val, {start}, {length})", 'str')
        elif method == 'trim':
            return self._wrap_result(f"ely_str_trim(({obj_code})->u.string_val)", 'str')
        elif method == 'replace':
            if len(args_code) != 2: self.error("replace() expects 2 arguments")
            old = self._convert_to_ctype(args[0], args_code[0], 'str')
            new = self._convert_to_ctype(args[1], args_code[1], 'str')
            return self._wrap_result(f"ely_str_replace(({obj_code})->u.string_val, {old}, {new})", 'str')
        else:
            self.error(f"Unknown string method '{method}'")
            return ""

    def _gen_num_method(self, obj_code: str, method: str, obj_type: str) -> str:
        if method == 'toStr':
            return self._wrap_result(f"ely_value_to_string({obj_code})", 'str')
        elif method == 'abs':
            return self._wrap_result(f"ely_value_abs({obj_code})", obj_type)
        else:
            self.error(f"Unknown number method '{method}'")
            return ""

    # -------------------------------------------------------------------
    # Специализации generics
    # -------------------------------------------------------------------
    def _gen_generic_call(self, node: Call, func_node: MethodDeclaration) -> str:
        bindings = {}
        for arg, param in zip(node.arguments, func_node.parameters):
            arg_type = self.get_expression_type(arg)
            if param.type in func_node.type_params:
                bindings[param.type] = arg_type
        missing = [tp for tp in func_node.type_params if tp not in bindings]
        if missing:
            self.error(f"Could not infer type parameters: {missing}", node)
            return "ely_value_new_null()"
        key = (func_node.name, tuple(bindings.values()))
        if key not in self.generic_instances:
            spec_name = self._generate_specialization(func_node, bindings)
            self.generic_instances[key] = spec_name
        else:
            spec_name = self.generic_instances[key]
        args = [self.gen_expression(a) for a in node.arguments]
        return f"{spec_name}({', '.join(args)})"

    def _generate_specialization(self, func_node: MethodDeclaration, mapping: dict) -> str:
        def subst(s):
            if s is None: return s
            for tp, ct in mapping.items():
                s = s.replace(tp, ct)
            return s
        new_params = [Parameter(type=subst(p.type), name=p.name) for p in func_node.parameters]
        new_ret = subst(func_node.return_type)
        new_body = []
        for stmt in func_node.body:
            if isinstance(stmt, VariableDeclaration):
                new_body.append(VariableDeclaration(
                    stmt.line, stmt.col, stmt.modifier, subst(stmt.type), stmt.name, stmt.initializer, stmt.tag
                ))
            else:
                new_body.append(stmt)
        suffix = '_'.join(str(ct) for ct in mapping.values())
        spec_name = f"{func_node.name}_{suffix}"
        new_func = MethodDeclaration(
            func_node.line, func_node.col, new_ret, spec_name, new_params, new_body,
            func_node.modifier, type_params=[]
        )
        old_func = self.method_code
        self.method_code = []
        self.gen_function(new_func)
        spec_code = "\n".join(self.method_code)
        self.method_code = old_func
        self.specializations.append(spec_code)
        return spec_name
    
    def _gen_super_call(self, node: SuperCall) -> str:
        if not self.current_class_name:
            self.error("super used outside class", node)
            return "ely_value_new_null()"

        cls = self.classes_ast.get(self.current_class_name)
        if not cls or not cls.extends:
            self.error("class has no parent", node)
            return "ely_value_new_null()"

        parent_name = cls.extends
        parent_cls = self.classes_ast.get(parent_name)
        if not parent_cls:
            self.error(f"parent class '{parent_name}' not found", node)
            return "ely_value_new_null()"

        # Ищем метод в родителе
        method_node = None
        for m in parent_cls.all_methods:
            if m.name == node.method:
                method_node = m
                break
        if not method_node:
            self.error(f"Method '{node.method}' not found in parent class '{parent_name}'", node)
            return "ely_value_new_null()"

        # Генерируем аргументы с конвертацией
        args = []
        for i, arg in enumerate(node.arguments):
            code = self.gen_expression(arg)
            if i < len(method_node.parameters):
                expected_c = self.type_to_cpp(method_node.parameters[i].type, is_param=True)
                code = self._convert_to_c_type_expr(code, expected_c)
            args.append(code)

        return f"{parent_name}::{node.method}({', '.join(args)})"