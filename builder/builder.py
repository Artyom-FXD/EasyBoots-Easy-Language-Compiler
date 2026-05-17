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
    def __init__(self, config_path: Path, compiler_path=None,
                 young_mb=None, old_mb=None, target=None):
        self.config_path = config_path.resolve()
        self.project_root = self.config_path.parent
        self.target = target
        with open(self.config_path, 'r', encoding='utf-8') as f:
            self.config = json.load(f)
        self.compiler_path = compiler_path          # явный путь из аргументов
        self.gc_young_mb = young_mb if young_mb else 16
        self.gc_old_mb = old_mb if old_mb else 8
        self.optimization = 'hard'
        self.debug = False
        self.build_dir = self.project_root / 'build'
        self.output_dir = self.project_root / 'output'
        self.libs_dir = self.project_root / 'libs'
        self.compiler_runtime = Path(__file__).parent.parent / 'runtime'

    # ------------------------------------------------------------------
    # Создаём g++.exe из gcc.exe, если его нет
    # ------------------------------------------------------------------
    def _ensure_gpp(self, gcc_path: Path):
        """Копирует gcc.exe -> g++.exe, если g++.exe отсутствует."""
        gxx = gcc_path.with_name('g++.exe') if sys.platform == 'win32' else gcc_path.with_name('g++')
        if not gxx.exists():
            try:
                shutil.copy2(gcc_path, gxx)
                print(f"Created {gxx.name} from {gcc_path.name}")
            except OSError as e:
                print(f"Warning: could not create {gxx.name} ({e}).")
                return False
        return True

    # ------------------------------------------------------------------
    # Универсальный поиск C++ компилятора (g++ > gcc > clang++)
    # ------------------------------------------------------------------
    def _find_compiler(self) -> Tuple[Optional[str], Optional[str], List[str]]:
        extra_flags = []
        if self.compiler_path:
            p = Path(self.compiler_path)
            if p.exists():
                return p.stem, str(p), extra_flags

        # Ищем g++ (предпочтительнее), потом gcc
        for name in ['g++', 'gcc']:
            path = shutil.which(name)
            if path:
                return name, path, extra_flags

        # Локальные папки MinGW
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

    # ------------------------------------------------------------------
    # Компиляция C‑файла рантайма
    # ------------------------------------------------------------------
    def _compile_runtime(self, compiler: str, comp_path: str,
                         src: Path, obj: Path, defines=None) -> bool:
        cmd = [comp_path, '-c', str(src), '-o', str(obj)]
        # Для g++/clang++ добавляем -x c
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

    # ------------------------------------------------------------------
    # Основной метод сборки
    # ------------------------------------------------------------------
    def build(self) -> bool:
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

        # Генерация C++ кода
        codegen = CppCodeGen(debug=self.debug)
        cpp_code = codegen.generate(Program(all_statements))
        cpp_file = self.build_dir / 'output.cpp'
        cpp_file.parent.mkdir(parents=True, exist_ok=True)
        cpp_file.write_text(cpp_code, encoding='utf-8')

        # Компилятор ищем один раз
        compiler, comp_path, extra_flags = self._find_compiler()
        if not compiler:
            print("No C++ compiler found. Please install MinGW (gcc/g++) or run 'ebt install-compiler'.")
            return False

        # Компиляция основного файла
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
        # Принудительный режим C++ для gcc/clang, если они не g++
        if compiler in ('gcc', 'clang'):
            cmd.extend(['-x', 'c++'])
        try:
            subprocess.run(cmd, check=True, capture_output=True, text=True)
        except subprocess.CalledProcessError as e:
            print(f"Compilation of main project failed:\n{e.stderr}")
            return False

        # Компиляция рантайма
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

        # Линковка
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
        self.build_runtime = self.build_dir / 'runtime'
        if self.compiler_runtime.exists():
            if self.build_runtime.exists():
                shutil.rmtree(self.build_runtime)
            shutil.copytree(self.compiler_runtime, self.build_runtime)
            return True
        print("Error: runtime directory not found.")
        return False

    def _collect_sources(self) -> list:
        """Рекурсивно собирает все .ely файлы, начиная с главного."""
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
            collected[abs_path] = current  # сохраняем относительный путь для диагностики

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
        RED, BOLD, RESET = '\033[91m', '\033[1m', '\033[0m'
        print(f"{BOLD}{RED}Semantic errors:{RESET}")
        for e in errors:
            print(f"  {e}")