from dataclasses import dataclass, field
from typing import List, Optional, Any


@dataclass
class Expression:
    """
    Base class for all expression nodes in the AST.

    Stores source position (line, column) for error reporting.

    Базовый класс для всех узлов выражений в AST.
    Хранит позицию в исходнике (строка, колонка) для сообщения об ошибках.
    """
    line: int
    col: int


@dataclass
class Identifier(Expression):
    """
    Represents an identifier expression (variable name, function name, etc.).

    Представляет выражение-идентификатор (имя переменной, функции и т.д.).
    """
    name: str


@dataclass
class Literal(Expression):
    """
    Represents a literal value (number, string, boolean, null).

    Представляет литеральное значение (число, строка, булево, null).
    """
    value: Any


@dataclass
class BinaryOp(Expression):
    """
    Represents a binary operation (e.g. a + b, a * b).

    Представляет бинарную операцию (например, a + b, a * b).
    """
    left: Expression
    operator: str
    right: Expression


@dataclass
class UnaryOp(Expression):
    """
    Represents a unary operation (e.g. -x, !flag).

    Представляет унарную операцию (например, -x, !flag).
    """
    operator: str
    operand: Expression


@dataclass
class Call(Expression):
    """
    Represents a function/method call (e.g. foo(a, b)).

    Представляет вызов функции/метода (например, foo(a, b)).
    """
    callee: Expression
    arguments: List[Expression]


@dataclass
class MemberAccess(Expression):
    """
    Represents member access (e.g. obj.field).

    Представляет доступ к члену (например, obj.field).
    """
    object: Expression
    member: str


@dataclass
class Assignment(Expression):
    """
    Represents an assignment expression (e.g. a = b, a += b).

    Представляет выражение присваивания (например, a = b, a += b).
    """
    target: Expression
    value: Expression
    operator: str = '='


@dataclass
class TagAnnotation(Expression):
    """
    Represents a tag annotation (e.g. @tag_name(args)).

    Представляет аннотацию-тег (например, @tag_name(args)).
    """
    name: str
    arguments: List[Expression]


@dataclass
class Conditional(Expression):
    """
    Represents a ternary conditional expression (cond ? then : else).

    Представляет тернарное условное выражение (cond ? then : else).
    """
    condition: Expression
    then_expr: Expression
    else_expr: Expression


@dataclass
class Statement:
    """
    Base class for all statement nodes in the AST.

    Stores source position (line, column) for error reporting.

    Базовый класс для всех узлов инструкций в AST.
    Хранит позицию в исходнике (строка, колонка) для сообщения об ошибках.
    """
    line: int
    col: int


@dataclass
class ExpressionStatement(Statement):
    """
    Wraps an expression as a standalone statement.

    Оборачивает выражение в самостоятельную инструкцию.
    """
    expression: Expression


@dataclass
class VariableDeclaration(Statement):
    """
    Represents a variable declaration (e.g. var x: int = 5).

    Представляет объявление переменной (например, var x: int = 5).
    """
    modifier: Optional[str]
    type: str
    name: str
    initializer: Optional[Expression]
    tag: Optional[TagAnnotation] = None


@dataclass
class Parameter:
    """
    Represents a function/method parameter.

    Представляет параметр функции/метода.
    """
    type: str
    name: str


@dataclass
class IfStatement(Statement):
    """
    Represents an if-else statement.

    Представляет условный оператор if-else.
    """
    condition: Expression
    then_body: List[Statement]
    else_body: Optional[List[Statement]]


@dataclass
class WhileLoop(Statement):
    """
    Represents a while loop.

    Представляет цикл while.
    """
    condition: Expression
    body: List[Statement]


@dataclass
class ForLoop(Statement):
    """
    Represents a C-style for loop (init; condition; update).

    Представляет C-подобный цикл for (init; condition; update).
    """
    init: Optional[Statement]
    condition: Optional[Expression]
    update: Optional[Expression]
    body: List[Statement]


@dataclass
class ForEachLoop(Statement):
    """
    Represents a foreach loop iterating over a collection.

    Представляет цикл foreach для итерации по коллекции.
    """
    item_decl: Statement
    iterable: Expression
    body: List[Statement]


@dataclass
class MatchStatement(Statement):
    """
    Represents a match (switch) statement.

    Представляет оператор match (switch).
    """
    expression: Expression
    cases: List['Case']
    default_body: Optional[List[Statement]]


@dataclass
class Case:
    """
    Represents a single case branch inside a match statement.

    Представляет отдельную ветку case внутри оператора match.
    """
    value: Expression
    body: List[Statement]
    line: int = 0
    col: int = 0


@dataclass
class AsafeBlock(Statement):
    """
    Represents an exception-safe block (asafe).

    Представляет блок безопасного выполнения (asafe) с обработкой исключений.
    """
    body: List[Statement]
    except_handler: Optional['ExceptHandler']


@dataclass
class ExceptHandler:
    """
    Represents an exception handler inside an asafe block.

    Представляет обработчик исключения внутри блока asafe.
    """
    exception_type: str
    parameter: Optional[str]
    body: List[Statement]


@dataclass
class GivebackStatement(Statement):
    """
    Represents a 'giveback' statement that yields/returns ownership.

    Представляет оператор giveback, передающий владение значением.
    """
    value: Optional[Expression]


@dataclass
class ReturnStatement(Statement):
    """
    Represents a return statement.

    Представляет оператор return.
    """
    value: Optional[Expression]


@dataclass
class CollapseStatement(Statement):
    """
    Represents a 'collapse' statement referencing a declaration.

    Представляет оператор collapse, ссылающийся на объявление.
    """
    name: str


@dataclass
class BreakStatement(Statement):
    """
    Represents a break statement inside a loop.

    Представляет оператор break внутри цикла.
    """
    pass


@dataclass
class UsingDirective(Statement):
    """
    Represents a 'using' module import directive.

    Представляет директиву импорта модуля using.
    """
    module: str


@dataclass
class OpMemDirective(Statement):
    """
    Represents an __opmem directive for memory operations.

    Представляет директиву __opmem для операций с памятью.
    """
    memory_type: str
    data_type: str
    data_memory: Optional[str]
    expression: Expression


@dataclass
class Program:
    """
    Root AST node representing the entire compiled program.

    Корневой узел AST, представляющий всю компилируемую программу.
    """
    statements: List[Statement]


@dataclass
class StructDeclaration(Statement):
    """
    Represents a struct declaration.

    Представляет объявление структуры.
    """
    name: str
    fields: List[VariableDeclaration]
    type_params: List[str] = field(default_factory=list)


@dataclass
class TypeAlias(Statement):
    """
    Represents a type alias declaration (type Name = TargetType).

    Представляет объявление псевдонима типа (type Name = TargetType).
    """
    name: str
    target_type: str


@dataclass
class NamespaceDeclaration(Statement):
    """
    Represents a namespace declaration containing nested statements.

    Представляет объявление пространства имён с вложенными инструкциями.
    """
    name: str
    body: List[Statement]


@dataclass
class ExternFunction(Statement):
    """
    Represents an external function declaration (no body).

    Представляет объявление внешней функции (без тела).
    """
    name: str
    parameters: List[Parameter]
    return_type: Optional[str]


@dataclass
class ConstDeclaration(Statement):
    """
    Represents a constant declaration.

    Представляет объявление константы.
    """
    name: str
    type: str
    value: Expression


@dataclass
class StaticVariable(Statement):
    """
    Represents a static variable declaration.

    Представляет объявление статической переменной.
    """
    name: str
    type: str
    initializer: Optional[Expression]


@dataclass
class FString(Expression):
    """
    Represents an f-string literal with interpolated parts.

    Представляет f-строковый литерал с интерполированными частями.
    """
    parts: List[Any]


@dataclass
class ArrayLiteral(Expression):
    """
    Represents an array literal (e.g. [1, 2, 3]).

    Представляет литерал массива (например, [1, 2, 3]).
    """
    elements: List[Expression]


@dataclass
class DictPair:
    """
    Represents a single key-value pair in a dictionary literal.

    Представляет пару ключ-значение в литерале словаря.
    """
    key: Expression
    value: Expression


@dataclass
class DictLiteral(Expression):
    """
    Represents a dictionary literal (e.g. {a: 1, b: 2}).

    Представляет литерал словаря (например, {a: 1, b: 2}).
    """
    pairs: List[DictPair]


@dataclass
class IndexExpression(Expression):
    """
    Represents an index expression (e.g. arr[i]).

    Представляет выражение индексации (например, arr[i]).
    """
    target: Expression
    index: Expression


@dataclass
class ThrowStatement(Statement):
    """
    Represents a throw statement for exception raising.

    Представляет оператор throw для генерации исключения.
    """
    value: Expression


@dataclass
class TypeOfExpression(Expression):
    """
    Represents a typeof expression that queries the type of an argument.

    Представляет выражение typeof, запрашивающее тип аргумента.
    """
    argument: Expression


@dataclass
class FieldsExpression(Expression):
    """
    Represents a 'fields' expression that queries an object's fields.

    Представляет выражение fields, запрашивающее поля объекта.
    """
    argument: Expression


@dataclass
class MethodsExpression(Expression):
    """
    Represents a 'methods' expression that queries an object's methods.

    Представляет выражение methods, запрашивающее методы объекта.
    """
    argument: Expression


@dataclass
class GlobalCBlock(Statement):
    """
    Represents a global C code block (cCode { ... }).

    Представляет глобальный блок C-кода (cCode { ... }).
    """
    code: str


@dataclass
class MethodDeclaration(Statement):
    """
    Represents a method or function declaration with its body.

    Представляет объявление метода или функции с телом.
    """
    return_type: Optional[str]
    name: str
    parameters: List[Parameter]
    body: List[Statement]
    return_memory: Optional[str] = None
    modifier: Optional[str] = None
    type_params: List[str] = field(default_factory=list)
    is_override: bool = False
    is_abstract: bool = False
    is_async: bool = False


@dataclass
class AwaitExpression(Expression):
    """
    Represents an await expression for asynchronous operations.

    Представляет выражение await для асинхронных операций.
    """
    expression: Expression


@dataclass
class PropertyDeclaration:
    """
    Represents a property declaration with optional getter/setter.

    Представляет объявление свойства с опциональными геттером/сеттером.
    """
    name: str
    type: str
    getter: Optional[MethodDeclaration]
    setter: Optional[MethodDeclaration]


@dataclass
class ClassDeclaration(Statement):
    """
    Represents a class declaration with fields, methods, and inheritance.

    Представляет объявление класса с полями, методами и наследованием.
    """
    name: str
    extends: Optional[str]
    methods: List[MethodDeclaration]
    type_params: List[str] = field(default_factory=list)
    fields: List[VariableDeclaration] = field(default_factory=list)
    wait_fields: List[VariableDeclaration] = field(default_factory=list)
    super_args: List[Expression] = field(default_factory=list)
    all_methods: List[MethodDeclaration] = field(default_factory=list)
    static_fields: List[VariableDeclaration] = field(default_factory=list)
    static_methods: List[MethodDeclaration] = field(default_factory=list)
    properties: List[PropertyDeclaration] = field(default_factory=list)
    is_sealed: bool = False
    is_abstract: bool = False
    impl_interfaces: List[str] = field(default_factory=list)


@dataclass
class SuperCall(Expression):
    """
    Represents a super() call to access a parent class member.

    Представляет вызов super() для доступа к члену родительского класса.
    """
    method: Optional[str]
    arguments: List[Expression]


@dataclass
class InterfaceDeclaration(Statement):
    """
    Represents an interface declaration with abstract methods.

    Представляет объявление интерфейса с абстрактными методами.
    """
    name: str
    methods: List[MethodDeclaration]


@dataclass
class ImplDeclaration(Statement):
    """
    Represents an implementation declaration (impl Interface for Class).

    Представляет объявление реализации (impl Интерфейс для Класса).
    """
    class_name: str
    interface_name: str
    methods: List[MethodDeclaration]