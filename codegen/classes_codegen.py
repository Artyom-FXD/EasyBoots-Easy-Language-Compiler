import sys
import os
from typing import List, Optional

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from parser import *
from codegen.funcs_codegen import FuncCodeGen


class ClassCodeGen(FuncCodeGen):
    """Генерация C++ классов вместо C-структур с ручной vtable."""

    def gen_class_full(self, cls: ClassDeclaration):
        name = cls.name
        parent = cls.extends
        sealed_kw = " final" if cls.is_sealed else ""
        parent_ref = f" : public {parent}" if parent and parent in self.classes_ast else ""
        self.emit(f"class {name}{sealed_kw}{parent_ref} {{")
        self.emit("public:")
        self.indent += 1

        # Поля экземпляра
        for f in cls.fields:
            if f.modifier != 'static':
                ctype = self.type_to_cpp(f.type, is_field=True)
                self.emit(f"{ctype} {f.name};")

        # Статические поля
        for sf in cls.static_fields:
            self.emit(f"static ely_value* {sf.name};")

        old_emit = self.emit_to_method
        self.emit_to_method = self.emit

        # Конструктор (нужен всегда, даже для абстрактных классов)
        self._gen_constructor_decl(cls)

        # Методы
        for method in cls.methods:
            if method.name == name or method.name == f"{name}_constructor":
                continue
            self._gen_method(cls, method)

        # Свойства
        for prop in cls.properties:
            if prop.getter:
                self._gen_method(cls, prop.getter)
            if prop.setter:
                self._gen_method(cls, prop.setter)

        self.emit_to_method = old_emit
        self.indent -= 1
        self.emit("};")

    def _gen_constructor_decl(self, cls: ClassDeclaration):
        name = cls.name
        parent = cls.extends
        params = self.collect_constructor_params(cls)
        param_str = ', '.join([f"{self.type_to_cpp(p.type, is_param=True)} {p.name}" for p in params])

        self.emit(f"{name}({param_str})")

        # Список инициализации (родительский конструктор)
        init_list = []
        if parent and parent in self.classes_ast:
            # Вычисляем количество параметров для всех предков (не включая сам класс)
            ancestor_wait_count = 0
            cur = cls
            while cur.extends and cur.extends in self.classes_ast:
                cur = self.classes_ast[cur.extends]
                ancestor_wait_count += len(cur.wait_fields)
            # Параметры для родителя = первые ancestor_wait_count параметров из полного списка
            p_args = ', '.join([p.name for p in params[:ancestor_wait_count]])
            init_list.append(f"{parent}({p_args})")

        if init_list:
            self.emit(f"    : {', '.join(init_list)}")

        self.emit("    {")
        self.indent += 1
        self._gen_constructor_body(cls, params)
        self.indent -= 1
        self.emit("    }")

    def _gen_constructor_body(self, cls: ClassDeclaration, params: List[Parameter]):
        name = cls.name
        parent = cls.extends

        own_wait = cls.wait_fields
        # Суммарное количество wait-полей всех предков (без текущего класса)
        parent_wait_len = 0
        cur = cls
        while cur.extends and cur.extends in self.classes_ast:
            cur = self.classes_ast[cur.extends]
            parent_wait_len += len(cur.wait_fields)

        # Инициализация wait-полей из параметров
        for i, f in enumerate(own_wait):
            param_name = params[parent_wait_len + i].name
            if f.type == 'str':
                self.emit(f"this->{f.name} = ely_str_dup({param_name});")
            else:
                self.emit(f"this->{f.name} = {param_name};")

        # Инициализация обычных полей
        for f in cls.fields:
            if f.modifier == 'static' or f in cls.wait_fields:
                continue
            default = self._default_value_for_type(f.type)
            if f.initializer:
                init_val = self.gen_expression(f.initializer)
                ctype = self.type_to_cpp(f.type, is_field=True)
                if ctype == 'char*':
                    init_val = f"ely_str_dup(ely_value_to_string({init_val}))"
                elif ctype in ('int', 'long long', 'unsigned int', 'unsigned long long',
                            'signed char', 'unsigned char'):
                    init_val = f"ely_value_as_int({init_val})"
                elif ctype in ('float', 'double'):
                    init_val = f"ely_value_as_double({init_val})"
                default = init_val
            self.emit(f"this->{f.name} = {default};")

        # Пользовательский код конструктора
        user_ctor = None
        for m in cls.methods:
            if m.name == name or m.name == f"{name}_constructor":
                user_ctor = m
                break
        if user_ctor:
            old_func = self.current_function
            old_class = self.current_class_name
            self.current_function = f"{name}_constructor"
            self.current_class_name = name
            for stmt in user_ctor.body:
                self.gen_statement(stmt)
            self.current_class_name = old_class
            self.current_function = old_func

    def _gen_method(self, cls: ClassDeclaration, method: MethodDeclaration):
        is_static = method.modifier == 'static'
        is_virtual = not is_static and not method.name.endswith('_constructor')
        override = method.is_override

        virt = "virtual " if is_virtual or method.is_abstract else ""
        static_kw = "static " if is_static else ""
        override_kw = " override" if override else ""

        ret = self.type_to_cpp(method.return_type or 'void', for_signature=True)
        params = ', '.join([f"{self.type_to_cpp(p.type, for_signature=True, is_param=True)} {p.name}"
                            for p in method.parameters])

        if method.is_abstract:
            self.emit(f"{virt}{static_kw}{ret} {method.name}({params}){override_kw} = 0;")
            return

        self.emit(f"{virt}{static_kw}{ret} {method.name}({params}){override_kw} {{")
        self.indent += 1

        old_class = self.current_class_name
        self.current_class_name = cls.name

        old_func = self.current_function
        self.current_function = f"{cls.name}_{method.name}"
        self.push_scope()

        if not is_static:
            self.var_types['self'] = cls.name

        for p in method.parameters:
            self.var_types[p.name] = p.type
            ctype = self.type_to_cpp(p.type, is_param=True)
            if ctype == 'ely_value*':
                self.emit(f"gc_add_root((void**)&{p.name});")
                if self.scope_roots:
                    self.scope_roots[-1].append(p.name)

        for stmt in method.body:
            self.gen_statement(stmt)

        self.pop_scope()
        self.indent -= 1
        self.emit("}")
        self.current_function = old_func
        self.current_class_name = old_class

    # -------------------------------------------------------------------
    # Статические поля и методы (объявления вне класса)
    # -------------------------------------------------------------------
    def gen_static_field_definitions(self):
        for cls in self.classes_ast.values():
            for sf in cls.static_fields:
                self.emit(f"ely_value* {cls.name}::{sf.name} = ely_value_new_int(0);")

    def gen_static_method_out_of_class(self, cls: ClassDeclaration, method: MethodDeclaration):
        """Статический метод, определённый вне класса."""
        full_name = f"{cls.name}::{method.name}"
        ret = self.type_to_cpp(method.return_type or 'void', for_signature=True)
        params = ', '.join([f"{self.type_to_cpp(p.type, for_signature=True, is_param=True)} {p.name}"
                            for p in method.parameters])
        self.emit(f"{ret} {full_name}({params}) {{")
        self.indent += 1
        old_func = self.current_function
        self.current_function = full_name
        self.push_scope()
        for p in method.parameters:
            self.var_types[p.name] = p.type
            if self.type_to_cpp(p.type, is_param=True) == 'ely_value*':
                self.emit_to_method(f"gc_add_root((void**)&{p.name});")
        for stmt in method.body:
            self.gen_statement(stmt)
        self.pop_scope()
        self.indent -= 1
        self.emit("}")
        self.current_function = old_func

    # -------------------------------------------------------------------
    # Вспомогательные
    # -------------------------------------------------------------------
    def _default_value_for_type(self, ely_type: str) -> str:
        t = self.resolve_type_alias(ely_type)
        if t == 'str':
            return "nullptr"
        if t in ('int', 'uint', 'more', 'umore', 'byte', 'ubyte'):
            return "0"
        if t in ('flt', 'double'):
            return "0.0"
        if t == 'bool':
            return "false"
        return "nullptr"

    def gen_class_info(self, cls: ClassDeclaration):
        name = cls.name
        fields = [f.name for f in cls.fields if f.modifier != 'static']
        types = [f.type for f in cls.fields if f.modifier != 'static']
        self.emit(f"static const char* {name}_field_names[] = {{ {', '.join(f'"{f}"' for f in fields)} }};")
        self.emit(f"static const char* {name}_field_types[] = {{ {', '.join(f'"{t}"' for t in types)} }};")
        self.emit(f"static ely_class_info {name}_class_info = {{ \"{name}\", {len(fields)}, {name}_field_names, {name}_field_types }};")

    def collect_constructor_params(self, cls: ClassDeclaration) -> List[Parameter]:
        """Собирает параметры конструктора из всех wait-полей цепочки наследования,
        начиная с самого верхнего предка."""
        params = []
        # Строим цепочку от базового класса к текущему
        hierarchy = []
        cur = cls
        while cur:
            hierarchy.insert(0, cur)   # вставляем в начало, чтобы предки шли раньше
            cur = self.classes_ast.get(cur.extends) if cur.extends else None
        for c in hierarchy:
            for f in c.wait_fields:
                params.append(Parameter(type=f.type, name=f.name))
        return params