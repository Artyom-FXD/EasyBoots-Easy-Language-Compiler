import json
import subprocess
import shutil
import sys
from pathlib import Path
from typing import List, Optional, Tuple

sys.path.insert(0, str(Path(__file__).parent.parent))
from lexer_module import Lexer
from parser import *
from codegen.codegen import CppCodeGen


class ProjectBuilder:
    """
    Orchestrates the end‑to‑end build pipeline for an Ely language project.

    Responsible for parsing source files, performing semantic analysis, generating C++ code,
    compiling runtime dependencies, and linking the final executable.

    Координирует полный цикл сборки проекта на языке Ely: разбор исходников,
    семантический анализ, генерацию C++ кода, компиляцию рантайма и компоновку.
    """

    def __init__(self, config_path: Path, compiler_path=None,
                 young_mb=None, old_mb=None, target=None):
        """
        Initialise the builder with project configuration.

        :param config_path: Path to the project configuration file (manager.json).
        :param compiler_path: Explicit path to the C++ compiler (optional).
        :param young_mb: Young generation size for the GC in MiB.
        :param old_mb:  Old generation initial size for the GC in MiB.
        :param target:  Build target identifier (optional).

        Инициализирует сборщик конфигурацией проекта.
        :param config_path: Путь к файлу конфигурации проекта (manager.json).
        :param compiler_path: Явный путь к C++ компилятору (необязательно).
        :param young_mb: Размер молодого поколения GC в МиБ.
        :param old_mb:  Начальный размер старого поколения GC в МиБ.
        :param target:  Идентификатор целевой платформы (необязательно).
        """
        self.config_path = config_path.resolve()
        self.project_root = self.config_path.parent
        self.target = target
        with open(self.config_path, 'r', encoding='utf-8') as f:
            self.config = json.load(f)
        self.compiler_path = compiler_path
        self.gc_young_mb = young_mb if young_mb else 16
        self.gc_old_mb = old_mb if old_mb else 8
        self.optimization = 'hard'
        self.debug = False
        self.build_dir = self.project_root / 'build'
        self.output_dir = self.project_root / 'output'
        self.libs_dir = self.project_root / 'libs'
        self.compiler_runtime = Path(__file__).parent.parent / 'runtime'

    def _ensure_gpp(self, gcc_path: Path):
        """
        Create g++.exe by copying gcc.exe if the former does not exist.

        :param gcc_path: Path to the existing gcc.exe.
        :returns: True if g++ is available (existing or created), False otherwise.

        Создаёт g++.exe копированием gcc.exe, если g++.exe отсутствует.
        :param gcc_path: Путь к существующему gcc.exe.
        :returns: True, если g++ доступен, иначе False.
        """
        gxx = gcc_path.with_name('g++.exe') if sys.platform == 'win32' else gcc_path.with_name('g++')
        if not gxx.exists():
            try:
                shutil.copy2(gcc_path, gxx)
                print(f"Created {gxx.name} from {gcc_path.name}")
            except OSError as e:
                print(f"Warning: could not create {gxx.name} ({e}).")
                return False
        return True

    def _find_compiler(self) -> Tuple[Optional[str], Optional[str], List[str]]:
        """
        Locate a suitable C++ compiler (g++ > gcc > clang++) on the system.

        :returns: A tuple of (compiler_binary_name, compiler_path, extra_flags).

        Ищет подходящий C++ компилятор (g++ > gcc > clang++) в системе.
        :returns: Кортеж (имя_компилятора, путь_компилятора, дополнительные_флаги).
        """
        extra_flags = []
        if self.compiler_path:
            p = Path(self.compiler_path)
            if p.exists():
                return p.stem, str(p), extra_flags

        for name in ['g++', 'gcc']:
            path = shutil.which(name)
            if path:
                return name, path, extra_flags

        search_roots = [
            Path(r"D:\utils\mingw64\bin"),
            Path(r"C:\mingw64\bin"),
            Path(r"C:\msys64\mingw64\bin")
        ]
        for root in search_roots:
            for exe in ['g++.exe', 'gcc.exe']:
                p = root / exe
                if p.exists():
                    return ('g++' if 'g++' in exe else 'gcc'), str(p), extra_flags

        return None, None, []

    def _compile_runtime(self, compiler: str, comp_path: str,
                         src: Path, obj: Path, defines=None) -> bool:
        """
        Compile a single runtime C source file into an object file.

        :param compiler: Compiler binary name (e.g. g++, gcc).
        :param comp_path: Full path to the compiler executable.
        :param src:  Source file to compile.
        :param obj:  Output object file path.
        :param defines: List of preprocessor define flags.
        :returns: True on success, False on failure.

        Компилирует один C-файл рантайма в объектный файл.
        :param compiler: Имя бинарника компилятора (например, g++, gcc).
        :param comp_path: Полный путь к исполняемому файлу компилятора.
        :param src:  Исходный файл для компиляции.
        :param obj:  Путь к выходному объектному файлу.
        :param defines: Список флагов препроцессора.
        :returns: True в случае успеха, False при ошибке.
        """
        cmd = [comp_path, '-c', str(src), '-o', str(obj)]
        if compiler in ('g++', 'c++', 'clang++'):
            cmd.insert(1, '-x')
            cmd.insert(2, 'c')
        if self.optimization == 'hard':
            cmd.append('-O2')
        if defines:
            for d in defines:
                cmd.append(f'-D{d}')
        cmd.append(f'-I{self.build_dir}/runtime')
        try:
            subprocess.run(cmd, check=True, capture_output=True, text=True)
            return True
        except subprocess.CalledProcessError as e:
            print(f"Compilation of {src.name} failed:\n{e.stderr}")
            return False

    def build(self) -> bool:
        """
        Execute the full build pipeline: parse, analyse, generate, compile, and link.

        :returns: True if the build succeeded, False otherwise.

        Выполняет полный цикл сборки: разбор, анализ, генерацию, компиляцию и компоновку.
        :returns: True, если сборка прошла успешно, иначе False.
        """
        if not self._prepare_runtime():
            return False

        sources = self._collect_sources()
        if not sources:
            return False

        all_statements = []
        for src in sources:
            with open(src, 'r', encoding='utf-8') as f:
                lexer = Lexer(f.read())
            parser = Parser(lexer)
            prog = parser.parse()
            if parser.errors:
                return False
            all_statements.extend(prog.statements)
        decls = []
        bodies = []
        for stmt in all_statements:
            if isinstance(stmt, (ClassDeclaration, InterfaceDeclaration, MethodDeclaration)):
                decls.append(stmt)
            else:
                bodies.append(stmt)
        all_statements = decls + bodies

        sem = SemanticAnalyzer()
        errors = sem.analyze(Program(all_statements))
        if errors:
            self._show_semantic_errors(errors)
            return False
        print("✓ Analysis successful")

        codegen = CppCodeGen(debug=self.debug)
        cpp_code = codegen.generate(Program(all_statements))
        cpp_file = self.build_dir / 'output.cpp'
        cpp_file.parent.mkdir(parents=True, exist_ok=True)
        cpp_file.write_text(cpp_code, encoding='utf-8')

        compiler, comp_path, extra_flags = self._find_compiler()
        if not compiler:
            print("No C++ compiler found. Please install MinGW (gcc/g++) or run 'ebt install-compiler'.")
            return False

        main_obj = self.build_dir / 'output.o'
        cmd = [comp_path, '-c', str(cpp_file), '-o', str(main_obj)]
        if compiler == 'gcc':
            cmd += ['-x', 'c++']
        if self.optimization == 'hard':
            cmd.append('-O2')
        elif self.optimization == 'soft':
            cmd.append('-O1')
        if self.debug:
            cmd.append('-g')
        cmd.append(f'-I{self.build_dir}/runtime')
        cmd.append('-fno-exceptions')
        cmd.append('-std=c++20')
        if compiler in ('gcc', 'clang'):
            cmd.extend(['-x', 'c++'])
        try:
            subprocess.run(cmd, check=True, capture_output=True, text=True)
        except subprocess.CalledProcessError as e:
            print(f"Compilation of main project failed:\n{e.stderr}")
            return False

        rt_obj = self.build_dir / 'runtime.o'
        if not self._compile_runtime(compiler, comp_path,
                                     self.build_dir / 'runtime' / 'ely_runtime.c', rt_obj):
            return False
        gc_obj = self.build_dir / 'gc.o'
        if not self._compile_runtime(compiler, comp_path,
                                     self.build_dir / 'runtime' / 'ely_gc.c', gc_obj,
                                     [f'GC_YOUNG_SIZE_MB={self.gc_young_mb}',
                                      f'GC_OLD_INITIAL_SIZE_MB={self.gc_old_mb}']):
            return False
        coll_obj = self.build_dir / 'collections.o'
        if not self._compile_runtime(compiler, comp_path,
                                     self.build_dir / 'runtime' / 'collections.c', coll_obj):
            return False

        output_exe_name = self.config.get('output', {}).get('enter', {}).get('name', 'a.out')
        output_exe = self.output_dir / output_exe_name
        output_exe.parent.mkdir(parents=True, exist_ok=True)

        link_cmd = [comp_path, '-static', '-mconsole', '-o', str(output_exe),
                    str(main_obj), str(rt_obj), str(coll_obj), str(gc_obj)]
        if compiler in ('gcc', 'g++', 'c++'):
            link_cmd.append('-lstdc++')
        if self.optimization == 'hard':
            link_cmd.append('-O2')
        try:
            subprocess.run(link_cmd, check=True, capture_output=True, text=True)
            print(f"✓ Executable created: {output_exe}")
        except subprocess.CalledProcessError as e:
            print(f"Linking failed:\n{e.stderr}")
            return False

        self.output_name = str(output_exe)
        return True

    def _prepare_runtime(self) -> bool:
        """
        Copy the runtime directory into the build directory.

        :returns: True if the runtime was prepared successfully, False otherwise.

        Копирует директорию рантайма в директорию сборки.
        :returns: True, если рантайм подготовлен успешно, иначе False.
        """
        self.build_runtime = self.build_dir / 'runtime'
        if self.compiler_runtime.exists():
            if self.build_runtime.exists():
                shutil.rmtree(self.build_runtime)
            shutil.copytree(self.compiler_runtime, self.build_runtime)
            return True
        print("Error: runtime directory not found.")
        return False

    def _collect_sources(self) -> list:
        """
        Recursively collect all .ely source files starting from the main entry point,
        following `using` directives to discover modules.

        :returns: A list of resolved absolute file paths.

        Рекурсивно собирает все .ely исходные файлы, начиная с главной точки входа,
        следуя директивам using для обнаружения модулей.
        :returns: Список абсолютных путей к файлам.
        """
        main_file = self.config.get('enter')
        if not main_file:
            print("Error: 'enter' not specified in manager.json")
            return []
        main_path = (self.project_root / main_file).resolve()
        if not main_path.exists() or not main_path.is_file():
            print(f"Error: main file not found: {main_path}")
            return []

        collected = {}
        pending = [main_path]

        while pending:
            current = pending.pop()
            abs_path = current.resolve()
            if abs_path in collected:
                continue
            collected[abs_path] = current

            with open(abs_path, 'r', encoding='utf-8') as f:
                source = f.read()

            lexer = Lexer(source)
            parser = Parser(lexer)
            prog = parser.parse()
            if parser.errors:
                for err in parser.errors:
                    print(err)
                return []

            for stmt in prog.statements:
                if isinstance(stmt, UsingDirective):
                    module = stmt.module
                    if module.startswith('"') and module.endswith('"'):
                        module = module[1:-1]
                    elif module not in ('"', '') and not module.startswith('"'):
                        modules_config = self.config.get('modules', {})
                        if module in modules_config:
                            module = modules_config[module]
                        else:
                            print(f"Warning: module '{module}' not found in manager.json")
                            continue
                    candidate = (abs_path.parent / module).resolve()
                    if candidate.exists():
                        pending.append(candidate)
                    else:
                        print(f"Warning: module file not found: {candidate}")

        return list(collected.keys())

    def _show_semantic_errors(self, errors):
        """
        Print semantic analysis errors to the console in a formatted style.

        :param errors: A list of error message strings.

        Выводит ошибки семантического анализа в консоль в форматированном виде.
        :param errors: Список строк с сообщениями об ошибках.
        """
        RED, BOLD, RESET = '\033[91m', '\033[1m', '\033[0m'
        print(f"{BOLD}{RED}Semantic errors:{RESET}")
        for e in errors:
            print(f"  {e}")
