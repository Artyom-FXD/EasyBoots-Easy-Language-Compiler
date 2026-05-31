import json
import hashlib
import subprocess
import shutil
import sys
from pathlib import Path
from typing import List, Optional, Tuple

sys.path.insert(0, str(Path(__file__).parent.parent))
from lexer_module import Lexer
from parser import *
from codegen.codegen import CppCodeGen

# ---------------------------------------------------------------------------
# Terminal color and style constants (no emoji)
# ---------------------------------------------------------------------------
class TC:
    """ANSI terminal color/style codes."""
    RED    = '\033[91m'
    GREEN  = '\033[92m'
    YELLOW = '\033[93m'
    BLUE   = '\033[94m'
    CYAN   = '\033[96m'
    WHITE  = '\033[97m'
    BOLD   = '\033[1m'
    DIM    = '\033[2m'
    RESET  = '\033[0m'

    @staticmethod
    def tag(label: str) -> str:
        """Return a coloured tag like [INFO], [OK], [ERROR], [WARN], [SKIP]."""
        t = label.upper()
        if t == 'INFO':
            return f"{TC.BLUE}{TC.BOLD}[{t}]{TC.RESET}"
        if t == 'OK':
            return f"{TC.GREEN}{TC.BOLD}[{t}]{TC.RESET}"
        if t == 'ERROR':
            return f"{TC.RED}{TC.BOLD}[{t}]{TC.RESET}"
        if t == 'WARN':
            return f"{TC.YELLOW}{TC.BOLD}[{t}]{TC.RESET}"
        if t == 'SKIP':
            return f"{TC.DIM}[{t}]{TC.RESET}"
        if t == 'BUILD':
            return f"{TC.CYAN}{TC.BOLD}[{t}]{TC.RESET}"
        return f"[{label}]"


class ProjectBuilder:
    """
    Orchestrates the end-to-end build pipeline for an Ely language project.

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
        self.force_rebuild = False     # полная пересборка
        self.build_dir = self.project_root / 'build'
        self.output_dir = self.project_root / 'output'
        self.libs_dir = self.project_root / 'libs'
        self.compiler_runtime = Path(__file__).parent.parent / 'runtime'
        # Файл кэша сборки
        self.cache_path = self.build_dir / 'cache.json'

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
                print(f"  {TC.tag('OK')} Created {gxx.name} from {gcc_path.name}")
            except OSError as e:
                print(f"  {TC.tag('WARN')} Could not create {gxx.name}: {e}")
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
            print(f"\n{TC.tag('ERROR')} Runtime compilation failed: {src.name}")
            self._show_compiler_error(e.stderr, str(src))
            return False

    def _file_hash(self, path: Path) -> str:
        """Вычисляет SHA256 хэш содержимого файла."""
        try:
            h = hashlib.sha256()
            with open(path, 'rb') as f:
                for chunk in iter(lambda: f.read(65536), b''):
                    h.update(chunk)
            return h.hexdigest()
        except (OSError, IOError):
            return ''

    def _load_cache(self) -> dict:
        """Загружает кэш сборки из build/cache.json."""
        if not self.cache_path.exists():
            return {}
        try:
            with open(self.cache_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return {}

    def _save_cache(self, cache: dict):
        """Сохраняет кэш сборки в build/cache.json."""
        self.cache_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.cache_path, 'w', encoding='utf-8') as f:
            json.dump(cache, f, indent=2, sort_keys=True)

    def _sources_changed(self, sources: List[Path], cache: dict) -> bool:
        """
        Проверяет, изменились ли какие-либо исходные файлы с последней сборки.
        Возвращает True, если нужна перегенерация.
        """
        cached_hashes = cache.get('source_hashes', {})
        new_hashes = {}
        changed = False
        for src in sources:
            abs_path = str(src.resolve())
            h = self._file_hash(src)
            new_hashes[abs_path] = h
            cached_h = cached_hashes.get(abs_path)
            if cached_h != h:
                changed = True
        # Обновляем хэши в кэше (сохраняем в _save_cache)
        cache['source_hashes'] = new_hashes
        return changed

    def _runtime_o_files_uptodate(self, obj_files: List[Path]) -> bool:
        """Проверяет, что все runtime .o файлы существуют и актуальны."""
        for obj in obj_files:
            if not obj.exists():
                return False
            # Сверяем хэш исходника (если есть кэш)
        return True

    # ------------------------------------------------------------------
    # Project info display
    # ------------------------------------------------------------------
    def _print_project_info(self, sources: List[Path]):
        """Print a coloured project information block before building."""
        name = self.config.get('name', 'unknown')
        out_cfg = self.config.get('output', {}).get('enter', {})
        exe_name = out_cfg.get('name', 'a.out')
        exe_type = out_cfg.get('type', 'exe')
        entry = self.config.get('enter', '?')
        modules = self.config.get('modules', {})

        hdr = f"{TC.BOLD}{TC.WHITE}"
        dim = f"{TC.DIM}"
        rst = TC.RESET

        print(f"\n{hdr}  Project: {name}{rst}")
        print(f"  {dim}Entry point:{rst} {entry}")
        print(f"  {dim}Source files:{rst} {len(sources)}")
        print(f"  {dim}Output:{rst} {exe_name} ({exe_type})")
        print(f"  {dim}Modules:{rst} {', '.join(modules.keys()) if modules else 'none'}")
        print(f"  {dim}GC heap:{rst} {self.gc_young_mb} MiB young / {self.gc_old_mb} MiB old")
        opt_str = {'none': 'off', 'soft': 'light (O1)', 'hard': 'full (O2)'}.get(self.optimization, self.optimization)
        print(f"  {dim}Optimization:{rst} {opt_str}  {dim}Debug:{rst} {'on' if self.debug else 'off'}")

    def build_module(self, module_name: str) -> bool:
        """
        Build a named module from stdmodules/<name>/manager.json or modules/<name>.ely.

        :param module_name: Name of the module to build.
        :returns: True if the build succeeded, False otherwise.

        Собирает модуль по имени из stdmodules/<name>/manager.json.
        :param module_name: Имя модуля для сборки.
        :returns: True, если сборка прошла успешно, иначе False.
        """
        # 1. Пробуем найти stdmodules/<name>/manager.json
        stdmodule_config = Path(__file__).parent.parent / 'stdmodules' / module_name / 'manager.json'
        if stdmodule_config.exists():
            builder = ProjectBuilder(stdmodule_config,
                                     compiler_path=self.compiler_path,
                                     young_mb=self.gc_young_mb,
                                     old_mb=self.gc_old_mb,
                                     target=self.target)
            builder.optimization = self.optimization
            builder.debug = self.debug
            builder.force_rebuild = self.force_rebuild
            return builder.build()

        # 2. Пробуем modules/<name>.ely (одиночный файл-модуль)
        modules_config = self.config.get('modules', {})
        if module_name in modules_config:
            module_path = self.project_root / modules_config[module_name]
            if module_path.exists():
                # Создаём временный конфиг для одиночного файла
                temp_config = {
                    "name": module_name,
                    "version": "1.0.0",
                    "stx": {"processType": "module"},
                    "output": {
                        "libmain": str(module_path.relative_to(self.project_root)),
                        "native": False,
                        "nativeSources": [],
                        "elyfile": []
                    }
                }
                builder = ProjectBuilder.from_config(temp_config, self.project_root,
                                                     compiler_path=self.compiler_path,
                                                     young_mb=self.gc_young_mb,
                                                     old_mb=self.gc_old_mb,
                                                     target=self.target)
                builder.optimization = self.optimization
                builder.debug = self.debug
                builder.force_rebuild = self.force_rebuild
                return builder.build()

        print(f"\n{TC.tag('ERROR')} Module '{module_name}' not found")
        return False

    @classmethod
    def from_config(cls, config: dict, project_root: Path,
                    compiler_path=None, young_mb=None, old_mb=None, target=None):
        """
        Create a ProjectBuilder from an in-memory config dictionary.
        Used for temporary module builds without a manager.json file.

        Создаёт ProjectBuilder из словаря конфигурации в памяти.
        Используется для временной сборки модулей без manager.json.
        """
        import tempfile
        # Create a temporary manager.json
        tmp_dir = Path(tempfile.mkdtemp(prefix='elybuild_'))
        tmp_config = tmp_dir / 'manager.json'
        with open(tmp_config, 'w', encoding='utf-8') as f:
            json.dump(config, f)
        builder = cls(tmp_config, compiler_path=compiler_path,
                      young_mb=young_mb, old_mb=old_mb, target=target)
        # Override project_root and fix derived paths
        builder._project_root_override = project_root
        builder.build_dir = project_root / 'build'
        builder.output_dir = project_root / 'output'
        builder.libs_dir = project_root / 'libs'
        builder.cache_path = builder.build_dir / 'cache.json'
        return builder

    def build(self) -> bool:
        """
        Execute the full build pipeline: parse, analyse, generate, compile, and link.

        :returns: True if the build succeeded, False otherwise.

        Выполняет полный цикл сборки: разбор, анализ, генерацию, компиляцию и компоновку.
        :returns: True, если сборка прошла успешно, иначе False.
        """
        # Определяем processType
        process_type = self.config.get('stx', {}).get('processType', 'console')

        if process_type == 'module':
            return self._build_module()

        # ===== 1. Подготовка рантайма =====
        if not self._prepare_runtime():
            return False

        # ===== 2. Сбор исходников =====
        sources = self._collect_sources()
        if not sources:
            return False

        # ----- Вывод информации о проекте -----
        self._print_project_info(sources)

        # ===== 3. Проверка кэша (инкрементальная сборка) =====
        cache = self._load_cache()
        need_generate = self.force_rebuild or self._sources_changed(sources, cache)
        cpp_file = self.build_dir / 'output.cpp'
        cpp_file.parent.mkdir(parents=True, exist_ok=True)

        output_exe_name = self.config.get('output', {}).get('enter', {}).get('name', 'a.out')
        output_exe = self.output_dir / output_exe_name
        output_exe.parent.mkdir(parents=True, exist_ok=True)

        main_obj = self.build_dir / 'output.o'

        need_recompile = need_generate
        need_relink = True

        # Если исходники не изменились, проверяем что output.o свежий
        if not need_generate:
            if main_obj.exists() and main_obj.stat().st_mtime >= cpp_file.stat().st_mtime if cpp_file.exists() else False:
                need_recompile = False
            # Если exe уже существует и новее всех .o, линковку тоже можно пропустить
            rt_obj = self.build_dir / 'runtime.o'
            gc_obj = self.build_dir / 'gc.o'
            coll_obj = self.build_dir / 'collections.o'
            all_objs_exist = all(o.exists() for o in [main_obj, rt_obj, gc_obj, coll_obj])
            if all_objs_exist and output_exe.exists():
                exe_mtime = output_exe.stat().st_mtime
                if all(exe_mtime >= o.stat().st_mtime for o in [main_obj, rt_obj, gc_obj, coll_obj]):
                    need_relink = False

        # ===== 4. Парсинг + семантика + кодогенерация (только если нужно) =====
        if need_generate:
            print(f"\n{TC.tag('BUILD')} Changes detected, recompiling Ely sources...")
            all_statements = []
            # Собираем исходники с каждого файла, сразу выводим ошибки парсера
            parser_errors_occurred = False
            for src in sources:
                with open(src, 'r', encoding='utf-8') as f:
                    source_text = f.read()
                lexer = Lexer(source_text)
                parser = Parser(lexer)
                prog = parser.parse()
                if parser.errors:
                    parser_errors_occurred = True
                    self._show_parser_errors(src, source_text, parser.errors)
                if prog:
                    all_statements.extend(prog.statements)
            if parser_errors_occurred:
                return False

            decls = []
            bodies = []
            for stmt in all_statements:
                if isinstance(stmt, (ClassDeclaration, InterfaceDeclaration, MethodDeclaration, NamespaceDeclaration)):
                    decls.append(stmt)
                else:
                    bodies.append(stmt)
            all_statements = decls + bodies

            sem = SemanticAnalyzer()
            errors = sem.analyze(Program(all_statements))
            if errors:
                self._show_semantic_errors(errors)
                return False
            print(f"  {TC.tag('OK')} Semantic analysis passed")

            codegen = CppCodeGen(debug=self.debug)
            cpp_code = codegen.generate(Program(all_statements))
            cpp_file.write_text(cpp_code, encoding='utf-8')
            print(f"  {TC.tag('OK')} C++ code generated -> {cpp_file.name}")
            need_recompile = True
            need_relink = True
        else:
            print(f"\n{TC.tag('SKIP')} No source changes detected, skipping Ely compilation.")

        # ===== 5. Поиск компилятора C++ =====
        print(f"\n{TC.tag('INFO')} Searching for C++ compiler...")
        compiler, comp_path, extra_flags = self._find_compiler()
        if not compiler:
            print(f"\n{TC.tag('ERROR')} No C++ compiler found.")
            print(f"  {TC.DIM}Please install MinGW (gcc/g++) or run 'ebt install-compiler'.{TC.RESET}")
            return False
        print(f"  {TC.tag('OK')} Using {compiler} -> {comp_path}")

        # ===== 6. Компиляция output.cpp -> output.o =====
        if need_recompile:
            print(f"  {TC.tag('BUILD')} Compiling {cpp_file.name} -> {main_obj.name}...")
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
            cmd.append('-fexceptions')
            cmd.append('-std=c++20')
            if compiler in ('gcc', 'clang'):
                cmd.extend(['-x', 'c++'])
            try:
                subprocess.run(cmd, check=True, capture_output=True, text=True)
                print(f"    {TC.tag('OK')} Compilation succeeded")
            except subprocess.CalledProcessError as e:
                print(f"\n{TC.tag('ERROR')} C++ compilation failed")
                self._show_compiler_error(e.stderr, str(cpp_file))
                return False
        else:
            print(f"  {TC.tag('SKIP')} output.o is up to date, skipping compilation.")

        # ===== 7. Компиляция runtime файлов (всегда проверяем актуальность) =====
        print(f"\n{TC.tag('INFO')} Compiling runtime...")
        rt_obj = self.build_dir / 'runtime.o'
        if self.force_rebuild or not rt_obj.exists():
            if not self._compile_runtime(compiler, comp_path,
                                         self.build_dir / 'runtime' / 'ely_runtime.c', rt_obj):
                return False
        else:
            print(f"  {TC.tag('SKIP')} ely_runtime.o up to date")
        gc_obj = self.build_dir / 'gc.o'
        if self.force_rebuild or not gc_obj.exists():
            if not self._compile_runtime(compiler, comp_path,
                                         self.build_dir / 'runtime' / 'ely_gc.c', gc_obj,
                                         [f'GC_YOUNG_SIZE_MB={self.gc_young_mb}',
                                          f'GC_OLD_INITIAL_SIZE_MB={self.gc_old_mb}']):
                return False
        else:
            print(f"  {TC.tag('SKIP')} ely_gc.o up to date")
        coll_obj = self.build_dir / 'collections.o'
        if self.force_rebuild or not coll_obj.exists():
            if not self._compile_runtime(compiler, comp_path,
                                         self.build_dir / 'runtime' / 'collections.c', coll_obj):
                return False
        else:
            print(f"  {TC.tag('SKIP')} collections.o up to date")

        # ===== 7.5 Компиляция нативных C-файлов модулей =====
        native_objs = []
        modules_config = self.config.get('modules', {})
        for module_name, module_ely_rel in modules_config.items():
            # Ищем elymodule.json: поднимаемся от src/file.ely → ../elymodule.json
            ely_path = (self.project_root / module_ely_rel).resolve()
            if ely_path.name == 'elymodule.json':
                elymodule_json = ely_path
            else:
                elymodule_json = ely_path.parent / 'elymodule.json'
            if not elymodule_json.exists():
                continue
            try:
                with open(elymodule_json, 'r', encoding='utf-8') as f:
                    mod_cfg = __import__('json').load(f)
            except Exception:
                continue
            mod_out = mod_cfg.get('output', {})
            mod_native = mod_out.get('native', False)
            mod_native_srcs = mod_out.get('nativeSources', [])
            if not mod_native or not mod_native_srcs:
                continue

            print(f"\n{TC.tag('BUILD')} Compiling native sources for module '{module_name}' ({len(mod_native_srcs)} files)...")
            for rel_src in mod_native_srcs:
                src_path = (elymodule_json.parent / rel_src).resolve()
                if not src_path.exists():
                    print(f"  {TC.tag('WARN')} Native source not found: {rel_src}")
                    continue
                obj_path = self.build_dir / (f'{module_name}_' + src_path.stem + '.o')
                is_cpp = src_path.suffix in ('.cpp', '.cxx', '.cc')
                ncmd = [comp_path, '-c', str(src_path), '-o', str(obj_path)]
                if not is_cpp and compiler in ('g++', 'c++'):
                    ncmd.insert(1, '-x')
                    ncmd.insert(2, 'c')
                if self.optimization == 'hard':
                    ncmd.append('-O2')
                ncmd.append(f'-I{self.build_dir}/runtime')
                ncmd.append(f'-I{src_path.parent}')
                if is_cpp:
                    ncmd.append('-std=c++20')
                try:
                    subprocess.run(ncmd, check=True, capture_output=True, text=True)
                    native_objs.append(obj_path)
                    print(f"    {TC.tag('OK')} {rel_src} -> {obj_path.name}")
                except subprocess.CalledProcessError as e:
                    print(f"\n{TC.tag('ERROR')} Native compilation failed: {rel_src}")
                    self._show_compiler_error(e.stderr, str(src_path))
                    return False

        # ===== 8. Линковка =====
        if need_relink:
            print(f"\n{TC.tag('BUILD')} Linking...")
            link_cmd = [comp_path, '-static', '-mconsole', '-o', str(output_exe),
                        str(main_obj), str(rt_obj), str(coll_obj), str(gc_obj)]
            # Добавляем нативные объектные файлы модулей
            for nobj in native_objs:
                link_cmd.append(str(nobj))
            if compiler in ('gcc', 'g++', 'c++'):
                link_cmd.append('-lstdc++')
            if self.optimization == 'hard':
                link_cmd.append('-O2')
            try:
                subprocess.run(link_cmd, check=True, capture_output=True, text=True)
                print(f"\n  {TC.GREEN}{TC.BOLD}BUILD SUCCESS{TC.RESET}")
                print(f"  {TC.BOLD}{TC.WHITE}Executable:{TC.RESET} {output_exe}")
            except subprocess.CalledProcessError as e:
                print(f"\n{TC.tag('ERROR')} Linking failed")
                self._show_compiler_error(e.stderr, str(output_exe))
                return False
        else:
            print(f"\n  {TC.tag('SKIP')} {output_exe.name} is up to date, skipping link.")

        # ===== 9. Сохраняем кэш =====
        self._save_cache(cache)

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
        print(f"\n{TC.tag('ERROR')} Runtime directory not found at {self.compiler_runtime}")
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
            print(f"\n{TC.tag('ERROR')} 'enter' not specified in manager.json")
            return []
        main_path = (self.project_root / main_file).resolve()
        if not main_path.exists() or not main_path.is_file():
            print(f"\n{TC.tag('ERROR')} Main file not found: {main_path}")
            return []

        collected = {}
        pending = [main_path]

        # Добавляем все модули из поля 'modules' в manager.json (даже без using)
        modules_config = self.config.get('modules', {})
        for module_name, module_path in modules_config.items():
            candidate = (self.project_root / module_path).resolve()
            if candidate.exists():
                pending.append(candidate)
            else:
                pkg_candidate = self._resolve_package_module(module_path)
                if pkg_candidate:
                    pending.append(pkg_candidate)
                else:
                    print(f"  {TC.tag('WARN')} Module '{module_name}' not found at: {candidate}")

        while pending:
            current = pending.pop()
            abs_path = current.resolve()
            if abs_path in collected:
                continue

            # Если путь ведёт к elymodule.json — читаем linkfile и подставляем link.ely
            if abs_path.name == 'elymodule.json':
                # Не добавляем сам json в collected — он не является исходником .ely
                try:
                    with open(abs_path, 'r', encoding='utf-8') as f:
                        meta = json.load(f)
                    linkfile = meta.get('linkfile', 'link.ely')
                    link_path = abs_path.parent / linkfile
                    if link_path.exists():
                        pending.append(link_path)
                    else:
                        print(f"  {TC.tag('WARN')} linkfile not found: {link_path}")
                except Exception:
                    pass
                continue

            collected[abs_path] = current

            with open(abs_path, 'r', encoding='utf-8') as f:
                source = f.read()

            lexer = Lexer(source)
            parser = Parser(lexer)
            prog = parser.parse()
            if parser.errors:
                for err in parser.errors:
                    print(f"{TC.YELLOW}{TC.BOLD}  {err}{TC.RESET}")
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
                            print(f"  {TC.tag('WARN')} Module '{module}' not found in manager.json")
                            continue
                    candidate = (abs_path.parent / module).resolve()
                    if candidate.exists():
                        pending.append(candidate)
                    else:
                        # Попробовать найти через modules_config (может указывать на elymodule.json)
                        modules_config2 = self.config.get('modules', {})
                        if module in modules_config2:
                            mod_candidate = (self.project_root / modules_config2[module]).resolve()
                            if mod_candidate.exists():
                                pending.append(mod_candidate)
                                continue
                        # Попробовать найти как пакет в ely_packages/
                        pkg_candidate = self._resolve_package_module(module)
                        if pkg_candidate:
                            pending.append(pkg_candidate)
                        else:
                            print(f"  {TC.tag('WARN')} Module file not found: {candidate}")

        return list(collected.keys())

    # ------------------------------------------------------------------
    # Error display helpers
    # ------------------------------------------------------------------
    def _show_semantic_errors(self, errors):
        """Print semantic analysis errors with coloured, structured output."""
        total = len(errors)
        print(f"\n{TC.tag('ERROR')} {TC.BOLD}{TC.RED}Semantic errors ({total}):{TC.RESET}")
        for i, e in enumerate(errors, 1):
            msg = str(e)
            # Try to parse "file:line:col: message" format
            if ':' in msg:
                print(f"\n  {TC.DIM}{i}/{total}{TC.RESET} {TC.YELLOW}{TC.BOLD}{msg}{TC.RESET}")
            else:
                print(f"  {TC.DIM}{i}/{total}{TC.RESET} {TC.YELLOW}{msg}{TC.RESET}")
        print()

    def _show_parser_errors(self, src_path: Path, source_text: str, errors: list):
        """Print parser errors with source context, line numbers, and carets."""
        lines = source_text.split('\n')
        src_display = str(src_path)
        total = len(errors)
        print(f"\n{TC.tag('ERROR')} {TC.BOLD}{TC.RED}Parser errors ({total}) in {src_display}:{TC.RESET}")

        for i, err in enumerate(errors, 1):
            err_str = str(err)
            line = getattr(err, 'line', None)
            col = getattr(err, 'col', None)

            print(f"\n  {TC.DIM}--- error {i}/{total}{TC.RESET}")

            if line is not None and 1 <= line <= len(lines):
                source_line = lines[line - 1]
                if col is not None and col > 0:
                    print(f"  {TC.DIM}{src_display}:{line}:{col}{TC.RESET}")
                    print(f"  {TC.DIM}{line:>4} |{TC.RESET}")
                    print(f"  {TC.DIM}{'':>4} |{TC.RESET} {source_line}")
                    pointer = ' ' * col + f"{TC.RED}{TC.BOLD}^--- {err_str}{TC.RESET}"
                    print(f"  {TC.DIM}{'':>4} |{TC.RESET} {pointer}")
                else:
                    print(f"  {TC.DIM}{src_display}:{line}{TC.RESET}")
                    print(f"  {TC.DIM}{line:>4} |{TC.RESET}")
                    print(f"  {TC.DIM}{'':>4} |{TC.RESET} {source_line}")
                    print(f"  {TC.DIM}{'':>4} |{TC.RESET} {TC.RED}{TC.BOLD}^--- {err_str}{TC.RESET}")
            else:
                # No line/col info — just print the message
                print(f"  {TC.DIM}{src_display}{TC.RESET}")
                print(f"  {TC.RED}{TC.BOLD}{err_str}{TC.RESET}")
        print()

    # ==================================================================
    # Module build pipeline (processType = "module")
    # ==================================================================

    def _build_module(self) -> bool:
        """
        Build a module package: parse libmain, generate C++ code, compile to
        static library (.lib/.a), generate link.ely wrapper, .h header,
        elymodule.json, and copy elyfile assets into output/<name>/.
        """
        name = self.config.get('name', 'module')
        out_cfg = self.config.get('output', {})
        native = out_cfg.get('native', True)
        libmain_rel = out_cfg.get('libmain', 'src/lib.ely')
        elyfile_list = out_cfg.get('elyfile', [])
        native_sources = out_cfg.get('nativeSources', [])

        output_pkg_dir = self.output_dir / name
        output_lib_dir = output_pkg_dir / 'lib'
        output_include_dir = output_pkg_dir / 'include'
        output_ely_dir = output_pkg_dir / 'ely'

        # Убеждаемся, что все нужные папки существуют
        output_pkg_dir.mkdir(parents=True, exist_ok=True)
        self.build_dir.mkdir(parents=True, exist_ok=True)

        # ----- 1. Собрать исходники из libmain -----
        libmain_path = (self.project_root / libmain_rel).resolve()
        if not libmain_path.exists():
            print(f"\n{TC.tag('ERROR')} libmain not found: {libmain_path}")
            return False

        sources = self._collect_module_sources(libmain_path)
        if not sources:
            return False

        print(f"\n{TC.BOLD}{TC.WHITE}  Module: {name}{TC.RESET}")
        print(f"  {TC.DIM}libmain:{TC.RESET} {libmain_rel}")
        print(f"  {TC.DIM}Source files:{TC.RESET} {len(sources)}")
        print(f"  {TC.DIM}Native:{TC.RESET} {'yes' if native else 'no'}")
        print(f"  {TC.DIM}Output:{TC.RESET} {output_pkg_dir}/")

        # ----- 1.5 Подготовка рантайма (нужны хедеры для компиляции) -----
        if not self._prepare_runtime():
            return False

        # ----- 2. Парсинг + семантика -----
        print(f"\n{TC.tag('BUILD')} Parsing module sources...")
        all_statements = []
        parser_errors_occurred = False
        for src in sources:
            with open(src, 'r', encoding='utf-8') as f:
                source_text = f.read()
            lexer = Lexer(source_text)
            parser = Parser(lexer)
            prog = parser.parse()
            if parser.errors:
                parser_errors_occurred = True
                self._show_parser_errors(src, source_text, parser.errors)
            if prog:
                all_statements.extend(prog.statements)
        if parser_errors_occurred:
            return False

        sem = SemanticAnalyzer()
        errors = sem.analyze(Program(all_statements))
        if errors:
            self._show_semantic_errors(errors)
            return False
        print(f"  {TC.tag('OK')} Semantic analysis passed")

        # ----- 3. Извлечь публичные символы -----
        public_funcs = self._extract_public_functions(all_statements)
        pub_names = [f[0] for f in public_funcs]
        print(f"  {TC.tag('OK')} Public exports: {', '.join(pub_names) if pub_names else '(none)'}")

        # ----- 4. Генерация C++ кода -----
        cpp_file = self.build_dir / 'output.cpp'
        codegen = CppCodeGen(debug=self.debug)
        cpp_code = codegen.generate(Program(all_statements))
        cpp_file.write_text(cpp_code, encoding='utf-8')
        print(f"  {TC.tag('OK')} C++ code generated -> {cpp_file.name}")

        # ----- 5. Поиск компилятора -----
        print(f"\n{TC.tag('INFO')} Searching for C++ compiler...")
        compiler, comp_path, extra_flags = self._find_compiler()
        if not compiler:
            print(f"\n{TC.tag('ERROR')} No C++ compiler found.")
            return False
        print(f"  {TC.tag('OK')} Using {compiler} -> {comp_path}")

        # Убеждаемся, что g++ есть
        if compiler == 'gcc':
            gcc_path = Path(comp_path)
            if gcc_path.name == 'gcc.exe' or gcc_path.name == 'gcc':
                self._ensure_gpp(gcc_path)
                compiler = 'g++'
                comp_path = str(gcc_path.with_name('g++.exe' if sys.platform == 'win32' else 'g++'))

        # ----- 6. Компиляция output.cpp -> output.o -----
        main_obj = self.build_dir / 'output.o'
        print(f"\n{TC.tag('BUILD')} Compiling {cpp_file.name} -> {main_obj.name}...")
        cmd = [comp_path, '-c', str(cpp_file), '-o', str(main_obj)]
        if self.optimization == 'hard':
            cmd.append('-O2')
        elif self.optimization == 'soft':
            cmd.append('-O1')
        if self.debug:
            cmd.append('-g')
        cmd.append(f'-I{self.build_dir}/runtime')
        cmd.append('-fexceptions')
        cmd.append('-std=c++20')
        try:
            subprocess.run(cmd, check=True, capture_output=True, text=True)
            print(f"  {TC.tag('OK')} Compilation succeeded")
        except subprocess.CalledProcessError as e:
            print(f"\n{TC.tag('ERROR')} C++ compilation failed")
            self._show_compiler_error(e.stderr, str(cpp_file))
            return False

        # ----- 6.5 Компиляция native C-файлов -----
        native_objs = []
        if native and native_sources:
            print(f"\n{TC.tag('BUILD')} Compiling native sources ({len(native_sources)} files)...")
            for rel_path in native_sources:
                src_path = (self.project_root / rel_path).resolve()
                if not src_path.exists():
                    print(f"  {TC.tag('WARN')} Native source not found: {rel_path}")
                    continue
                obj_path = self.build_dir / (src_path.stem + '.o')
                # Определяем язык по расширению
                is_cpp = src_path.suffix in ('.cpp', '.cxx', '.cc')
                ncmd = [comp_path, '-c', str(src_path), '-o', str(obj_path)]
                if not is_cpp and compiler in ('g++', 'c++'):
                    ncmd.insert(1, '-x')
                    ncmd.insert(2, 'c')
                if self.optimization == 'hard':
                    ncmd.append('-O2')
                ncmd.append(f'-I{self.build_dir}/runtime')
                ncmd.append(f'-I{self.project_root}/src')
                if is_cpp:
                    ncmd.append('-std=c++20')
                try:
                    subprocess.run(ncmd, check=True, capture_output=True, text=True)
                    native_objs.append(obj_path)
                    print(f"  {TC.tag('OK')} {rel_path} -> {obj_path.name}")
                except subprocess.CalledProcessError as e:
                    print(f"\n{TC.tag('ERROR')} Native compilation failed: {rel_path}")
                    self._show_compiler_error(e.stderr, str(src_path))
                    return False

        # ----- 7. Статическая библиотека (.lib / .a) -----
        if native:
            output_lib_dir.mkdir(parents=True, exist_ok=True)
            lib_file = output_lib_dir / f'{name}.lib'
            print(f"\n{TC.tag('BUILD')} Creating static library {lib_file.name}...")
            # ar rcs на mingw — собираем все объектные файлы
            all_objs_for_lib = [main_obj] + native_objs
            ar_exe = Path(comp_path).with_name('ar.exe')
            if not ar_exe.exists():
                ar_exe = shutil.which('ar')
                if not ar_exe:
                    print(f"  {TC.tag('WARN')} ar.exe not found, skipping static library. Copying .o instead.")
                    shutil.copy2(main_obj, lib_file.with_suffix('.o'))
                else:
                    ar_exe = Path(ar_exe)
            if ar_exe and ar_exe.exists():
                try:
                    ar_cmd = [str(ar_exe), 'rcs', str(lib_file)] + [str(o) for o in all_objs_for_lib]
                    subprocess.run(ar_cmd, check=True, capture_output=True, text=True)
                    print(f"  {TC.tag('OK')} Static library created: {lib_file}")
                except subprocess.CalledProcessError as e:
                    print(f"  {TC.tag('WARN')} ar failed: {e.stderr}. Copying .o instead.")
                    shutil.copy2(main_obj, lib_file.with_suffix('.o'))
            else:
                shutil.copy2(main_obj, lib_file.with_suffix('.o'))

            # ----- 8. Генерация .h заголовка -----
            output_include_dir.mkdir(parents=True, exist_ok=True)
            h_file = output_include_dir / f'{name}.h'
            print(f"  {TC.tag('BUILD')} Generating {h_file.name}...")
            with open(h_file, 'w', encoding='utf-8') as hf:
                hf.write(f"// Auto-generated header for module {name}\n")
                hf.write(f"#ifndef ELY_MODULE_{name.upper()}_H\n")
                hf.write(f"#define ELY_MODULE_{name.upper()}_H\n\n")
                hf.write('#include "ely_runtime.h"\n\n')
                for func_name, ret_type, params in public_funcs:
                    c_ret = self._ely_to_c_type(ret_type)
                    c_params = ', '.join([f"{self._ely_to_c_type(pt)} {pn}" for pt, pn in params])
                    hf.write(f"extern {c_ret} {func_name}({c_params});\n")
                hf.write("\n#endif\n")
            print(f"  {TC.tag('OK')} Header generated: {h_file}")

        # ----- 9. Генерация link.ely -----
        link_file = output_pkg_dir / 'link.ely'
        print(f"\n{TC.tag('BUILD')} Generating link.ely wrapper...")
        with open(link_file, 'w', encoding='utf-8') as lf:
            lf.write(f"// Auto-generated link wrapper for module {name}\n")
            lf.write(f"// language_version: 26.5\n")
            lf.write(f"// Do not edit manually.\n\n")
            for func_name, ret_type, params in public_funcs:
                param_str = ', '.join([f"{pt} {pn}" for pt, pn in params])
                lf.write(f"public {ret_type} func {func_name}({param_str}) {{}}\n")
        print(f"  {TC.tag('OK')} link.ely -> {link_file}")

        # ----- 10. Копирование elyfile -----
        if elyfile_list:
            output_ely_dir.mkdir(parents=True, exist_ok=True)
            print(f"\n{TC.tag('INFO')} Copying elyfile assets...")
            for rel_path in elyfile_list:
                src_path = (self.project_root / rel_path).resolve()
                dst_path = output_ely_dir / Path(rel_path).name
                if src_path.exists():
                    shutil.copy2(src_path, dst_path)
                    print(f"  {TC.tag('OK')} {rel_path} -> {dst_path}")
                else:
                    print(f"  {TC.tag('WARN')} elyfile not found: {rel_path}")

        # ----- 11. Генерация elymodule.json -----
        print(f"\n{TC.tag('BUILD')} Generating elymodule.json...")
        include_files = ['link.ely', 'elymodule.json']
        if native:
            include_files.append(f'lib/{name}.lib')
            include_files.append(f'include/{name}.h')
        for rel in elyfile_list:
            include_files.append(f'ely/{Path(rel).name}')
        elymodule = {
            "name": name,
            "version": self.config.get('version', '0.1.0'),
            "language_version": "26.5",
            "stx": {"processType": "module"},
            "description": self.config.get('description', ''),
            "author": self.config.get('author', ''),
            "linkfile": "link.ely",
            "exports": pub_names,
            "include": include_files
        }
        elymodule_path = output_pkg_dir / 'elymodule.json'
        with open(elymodule_path, 'w', encoding='utf-8') as ef:
            json.dump(elymodule, ef, indent=4)
        print(f"  {TC.tag('OK')} elymodule.json -> {elymodule_path}")

        print(f"\n  {TC.GREEN}{TC.BOLD}BUILD SUCCESS{TC.RESET}")
        print(f"  {TC.BOLD}{TC.WHITE}Module:{TC.RESET} {output_pkg_dir}/")
        self.output_name = str(output_pkg_dir)
        return True

    # ------------------------------------------------------------------
    # Module helper methods
    # ------------------------------------------------------------------

    def _collect_module_sources(self, libmain_path: Path) -> list:
        """Collect all .ely files reachable from libmain via `using` directives."""
        collected = {}
        pending = [libmain_path]

        while pending:
            current = pending.pop()
            abs_path = current.resolve()
            if abs_path in collected:
                continue
            if not abs_path.exists():
                print(f"  {TC.tag('WARN')} File not found: {abs_path}")
                continue
            collected[abs_path] = current

            with open(abs_path, 'r', encoding='utf-8') as f:
                source = f.read()

            lexer = Lexer(source)
            parser = Parser(lexer)
            prog = parser.parse()
            if parser.errors:
                for err in parser.errors:
                    print(f"{TC.YELLOW}{TC.BOLD}  {err}{TC.RESET}")
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
                            print(f"  {TC.tag('WARN')} Module '{module}' not found in manager.json")
                            continue
                    candidate = (abs_path.parent / module).resolve()
                    if candidate.exists():
                        pending.append(candidate)
                    else:
                        # Попробовать найти как путь к elymodule.json пакета
                        pkg_candidate = self._resolve_package_module(module)
                        if pkg_candidate:
                            pending.append(pkg_candidate)
                        else:
                            print(f"  {TC.tag('WARN')} Module file not found: {candidate}")

        return list(collected.keys())

    def _resolve_package_module(self, module_name: str) -> Optional[Path]:
        """Try to find a module in ely_packages/."""
        pkg_dir = self.project_root / 'ely_packages' / module_name
        if pkg_dir.exists():
            elymodule_json = pkg_dir / 'elymodule.json'
            if elymodule_json.exists():
                with open(elymodule_json, 'r', encoding='utf-8') as f:
                    meta = json.load(f)
                linkfile = meta.get('linkfile', 'link.ely')
                link_path = pkg_dir / linkfile
                if link_path.exists():
                    return link_path
        return None

    def _extract_public_functions(self, statements: list) -> list:
        """Extract (name, return_type, [(param_type, param_name), ...]) from public methods."""
        result = []
        for stmt in statements:
            if isinstance(stmt, MethodDeclaration) and stmt.modifier == 'public':
                params = [(p.type, p.name) for p in stmt.parameters]
                result.append((stmt.name, stmt.return_type or 'void', params))
        return result

    @staticmethod
    def _ely_to_c_type(ely_type: str) -> str:
        """Convert Ely type name to C type for .h generation."""
        mapping = {
            'void': 'void',
            'int': 'int',
            'uint': 'unsigned int',
            'more': 'long long',
            'umore': 'unsigned long long',
            'flt': 'float',
            'double': 'double',
            'bool': 'int',
            'str': 'char*',
            'any': 'void*',
            'char': 'char',
            'byte': 'signed char',
            'ubyte': 'unsigned char'
        }
        return mapping.get(ely_type, 'int')

    # ------------------------------------------------------------------
    # Static compiler error display
    # ------------------------------------------------------------------
    @staticmethod
    def _show_compiler_error(stderr_text: str, context_hint: str = ''):
        """Print C/C++ compiler/linker errors with highlighted keywords."""
        # Keywords to highlight
        keywords = ['error:', 'Error:', 'ERROR:', 'undefined reference',
                    'collect2:', 'ld returned']
        for line in stderr_text.strip().split('\n'):
            stripped = line.strip()
            if any(kw in stripped for kw in keywords):
                print(f"  {TC.RED}{TC.BOLD}{stripped}{TC.RESET}")
            elif stripped.startswith(('In file', 'from', 'note:')):
                print(f"  {TC.DIM}{stripped}{TC.RESET}")
            else:
                print(f"  {TC.YELLOW}{stripped}{TC.RESET}")
