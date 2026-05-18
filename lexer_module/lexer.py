from .token import Token, TokenType


class Lexer:
    """
    Performs lexical analysis (tokenisation) of Ely source code.

    Converts a raw source string into a sequence of Token objects, recognising
    keywords, identifiers, numbers, strings, f-strings, operators, and delimiters.

    Выполняет лексический анализ (токенизацию) исходного кода Ely.
    Преобразует строку исходника в последовательность токенов, распознавая
    ключест
    ключевые слова, идентификаторы, числа, строки, f-строки,
    операторы и разделители.
    """

    def __init__(self, source: str):
        """
        Initialise the lexer with source code.

        :param source: The raw Ely source code string.

        Инициализирует лексер исходным кодом.
        :param source: Строка исходного кода Ely.
        """
        self.source = source
        self.pos = 0
        self.line = 1
        self.col = 1
        self.tokens = []
        self.debug = False

        self.keywords = {
            'cCode': TokenType.CCODE,
            'cppCode': TokenType.CPPCODE,
            'var': TokenType.VAR,
            'using': TokenType.USING,
            'class': TokenType.CLASS,
            'struct': TokenType.STRUCT,
            'type': TokenType.TYPE,
            'namespace': TokenType.NAMESPACE,
            'extern': TokenType.EXTERN,
            'const': TokenType.CONST,
            'static': TokenType,
            'void': TokenType.VOID,
            'func': TokenType.FUNC,
            'giveback': TokenType.GIVEBACK,
            'return': TokenType.RETURN,
            'if': TokenType.IF,
            'else': TokenType.ELSE,
            'match': TokenType.MATCH,
            'case': TokenType.CASE,
            'default': TokenType.DEFAULT,
            'break': TokenType.BREAK,
            'asafe': TokenType.ASAFE,
            'throw': TokenType.THROW,
            'except': TokenType.EXCEPT,
            'new': TokenType.NEW,
            'delete': TokenType.DELETE,
            'in': TokenType.IN,
            'is': TokenType.IS,
            'not': TokenType.NOT,
            'public': TokenType.PUBLIC,
            'private': TokenType.PRIVATE,
            'collapse': TokenType.COLLAPSE,
            'int': TokenType.INT,
            'uint': TokenType.UINT,
            'more': TokenType.MORE,
            'umore': TokenType.UMORE,
            'flt': TokenType.FLT,
            'double': TokenType.DOUBLE,
            'noised': TokenType.NOISED,
            'str': TokenType.STR,
            'char': TokenType.CHAR,
            'bool': TokenType.BOOL,
            'byte': TokenType.BYTE,
            'ubyte': TokenType.UBYTE,
            'any': TokenType.ANY,
            'true': TokenType.BOOLEAN,
            'false': TokenType.BOOLEAN,
            'NULL': TokenType.NULL,
            'for': TokenType.FOR,
            'while': TokenType.WHILE,
            'foreach': TokenType.FOREACH,
            'interface': TokenType.INTERFACE,
            'impl': TokenType.IMPL,
            'override': TokenType.OVERRIDE,
            'abstract': TokenType.ABSTRACT,
            'sealed': TokenType.SEALED,
            'async': TokenType.ASYNC,
            'await': TokenType.AWAIT,
            'sizeof': TokenType.SIZEOF,
            'typeof': TokenType.TYPEOF,
            'as': TokenType.AS,
            'arr': TokenType.ARRAY,
            'dict': TokenType.DICT,
            'generic': TokenType.GENERIC,
            'typeof': TokenType.TYPEOF,
            'fields': TokenType.FIELDS,
            'methods': TokenType.METHODS,
            'wait': TokenType.WAIT,
            'override': TokenType.OVERRIDE,
            'super': TokenType.SUPER,
            'new': TokenType.NEW
        }

        self.two_char_ops = {
            '+=', '-=', '*=', '/=', '==', '!=', '<=', '>=', '&&', '||', '??', '->', '=>'
        }

    def tokenize(self, debug=False):
        """
        Run the tokeniser on the source code and return the list of tokens.

        :param debug: If True, print each token as it is added.
        :returns: A list of Token objects.

        Запускает токенизатор на исходном коде и возвращает список токенов.
        :param debug: Если True, выводит каждый токен по мере добавления.
        :returns: Список объектов Token.
        """
        self.debug = debug
        self.tokens = []

        while self.pos < len(self.source):
            self._skip_whitespace()
            if self.pos >= len(self.source):
                break

            if self._skip_comment():
                continue

            ch = self.source[self.pos]

            if (ch == 'f' or ch == 'F') and self._peek(1) == '"' and self._peek(2) == '"' and self._peek(3) == '"':
                self._advance()
                self._read_multiline_fstring()
                continue

            if ch == '"' and self._peek(1) == '"' and self._peek(2) == '"':
                self._read_multiline_string()
                continue

            if ch == 'f' or ch == 'F':
                next_ch = self._peek(1)
                if next_ch == '"' or next_ch == "'":
                    self._advance()
                    self._read_fstring(next_ch)
                    continue

            if self.source[self.pos:self.pos+5] == 'cCode':
                self._read_c_code()
                continue

            if self.source[self.pos:self.pos+7] == 'cppCode':
                self._read_cpp_code()
                continue

            if ch.isalpha() or ch == '_':
                self._read_identifier_or_keyword()
                continue

            if ch.isdigit():
                self._read_number()
                continue

            if ch == '"':
                self._read_string()
                continue

            if self._try_read_two_char_operator():
                continue

            if self._try_read_one_char_operator_or_delimiter():
                continue

            self._add_unknown_token()

        self._add_token(TokenType.EOF, '', self.line, self.col)
        return self.tokens

    def _advance(self):
        """
        Advance the lexer position by one character, tracking line and column.

        Продвигает позицию лексера на один символ, отслеживая строку и колонку.
        """
        if self.pos < len(self.source) and self.source[self.pos] == '\n':
            self.line += 1
            self.col = 1
        else:
            self.col += 1
        self.pos += 1

    def _peek(self, offset=0):
        """
        Look ahead at a character in the source without consuming it.

        :param offset: Number of characters to look ahead.
        :returns: The character at the offset, or None if out of bounds.

        Подглядывает символ в исходнике без его потребления.
        :param offset: Количество символов для просмотра вперёд.
        :returns: Символ на указанном смещении или None за пределами строки.
        """
        idx = self.pos + offset
        return self.source[idx] if 0 <= idx < len(self.source) else None

    def _match(self, expected):
        """
        If the current character matches the expected one, advance past it.

        :param expected: The character to match.
        :returns: True if matched and consumed, False otherwise.

        Если текущий символ совпадает с ожидаемым, продвигается мимо него.
        :param expected: Ожидаемый символ.
        :returns: True при совпадении, иначе False.
        """
        if self._peek() == expected:
            self._advance()
            return True
        return False

    def _read_c_code(self):
        """
        Read a C code block (cCode { ... }) verbatim.

        Handles brace depth and skips over string and character literals inside the block.

        Читает блок C--кода (cCode { ... }) как есть.
        Обрабатывает вложенность скобок и пропускает строковые/символьные литералы внутри блока.
        """
        self._skip_whitespace()
        self.pos += 5
        self.col += 5
        self._skip_whitespace()
        line = self.line
        start_col = self.col
        if self.pos >= len(self.source) or self.source[self.pos] != '{':
            self._add_unknown_token()
            return
        self._advance()
        brace_depth = 1
        content_start = self.pos
        while self.pos < len(self.source) and brace_depth > 0:
            ch = self.source[self.pos]
            if ch == '"':
                self._advance()
                while self.pos < len(self.source) and self.source[self.pos] != '"':
                    if self.source[self.pos] == '\\':
                        self._advance()
                    self._advance()
                self._advance()
            elif ch == "'":
                self._advance()
                while self.pos < len(self.source) and self.source[self.pos] != "'":
                    if self.source[self.pos] == '\\':
                        self._advance()
                    self._advance()
                self._advance()
            elif ch == '{':
                brace_depth += 1
                self._advance()
            elif ch == '}':
                brace_depth -= 1
                self._advance()
                if brace_depth == 0:
                    break
            else:
                self._advance()
        if brace_depth != 0:
            self._add_unknown_token()
            return
        code = self.source[content_start:self.pos-1]
        self._add_token(TokenType.CCODE, code, line, start_col, code)

    def _skip_whitespace(self):
        """
        Skip over whitespace characters (space, tab, carriage return, newline).

        Пропускает пробельные символы (пробел, табуляция, возврат каретки, перевод строки).
        """
        while self.pos < len(self.source):
            ch = self.source[self.pos]
            if ch in ' \t\r\n':
                self._advance()
            else:
                break

    def _skip_comment(self) -> bool:
        """
        Skip a single-line (//) or multi-line (/* */) comment.

        :returns: True if a comment was skipped, False otherwise.

        Пропускает однострочный (//) или многострочный (/* */) комментарий.
        :returns: True, если комментарий пропущен, иначе False.
        """
        if self._peek() == '/' and self._peek(1) == '/':
            self._advance()
            self._advance()
            while self.pos < len(self.source) and self.source[self.pos] != '\n':
                self._advance()
            return True
        if self._peek() == '/' and self._peek(1) == '*':
            self._advance()
            self._advance()
            while self.pos < len(self.source):
                if self.source[self.pos] == '*' and self._peek(1) == '/':
                    self._advance()
                    self._advance()
                    break
                self._advance()
            return True
        return False

    def _add_token(self, token_type: TokenType, lexeme: str, line: int, col: int, value=None):
        """
        Create a new Token and append it to the token list.

        :param token_type: The type of the token.
        :param lexeme: The raw source lexeme.
        :param line: Line number where the token starts.
        :param col:  Column number where the token starts.
        :param value: Optional parsed value.

        Создаёт новый Token и добавляет его в список токенов.
        :param token_type: Тип токена.
        :param lexeme: Исходная лексема.
        :param line: Номер строки начала токена.
        :param col:  Номер колонки начала токена.
        :param value: Опциональное разобранное значение.
        """
        token = Token(token_type, lexeme, line, col, value)
        self.tokens.append(token)
        if self.debug:
            print(f"DEBUG: {token}")

    def _read_identifier_or_keyword(self):
        """
        Read an identifier or keyword token.

        Accumulates alphanumeric and underscore characters, then resolves
        the token type from the keyword map (defaults to IDENTIFIER).

        Читает токен идентификатора или ключевого слова.
        Накопливает буквы, цифры и подчёркивания, затем определяет
        тип токена по карте ключевых слов (по умолчанию IDENTIFIER).
        """
        start_col = self.col
        start_pos = self.pos
        while self.pos < len(self.source) and (self.source[self.pos].isalnum() or self.source[self.pos] == '_'):
            self._advance()
        lexeme = self.source[start_pos:self.pos]
        token_type = self.keywords.get(lexeme, TokenType.IDENTIFIER)
        self._add_token(token_type, lexeme, self.line, start_col)

    def _read_number(self):
        """
        Read a numeric literal (integer or floating-point).

        The parsed numeric value is stored as the token value.

        Читает числовой литерал (целое число или с плавающей точкой).
        Разобранное числовое значение сохраняется как значение токена.
        """
        start_col = self.col
        start_pos = self.pos
        while self.pos < len(self.source) and self.source[self.pos].isdigit():
            self._advance()
        if self._peek() == '.' and self._peek(1) and self._peek(1).isdigit():
            self._advance()
            while self.pos < len(self.source) and self.source[self.pos].isdigit():
                self._advance()
        lexeme = self.source[start_pos:self.pos]
        if '.' in lexeme:
            value = float(lexeme)
        else:
            value = int(lexeme)
        self._add_token(TokenType.NUMBER, lexeme, self.line, start_col, value)

    def _read_string(self):
        """
        Read a string literal (double-quoted), handling escape sequences.

        The parsed string value (with escapes resolved) is stored as the token value.

        Читает строковой литерал (в двойных кавычках), обрабатывая escape-последовательности.
        Разобранное значение строки сохраняется как значение токена.
        """
        start_col = self.col
        start_pos = self.pos
        self._advance()

        chars = []
        escaped = False

        while self.pos < len(self.source):
            ch = self.source[self.pos]

            if escaped:
                if ch == 'n':
                    chars.append('\n')
                elif ch == 't':
                    chars.append('\t')
                elif ch == 'r':
                    chars.append('\r')
                elif ch == '"':
                    chars.append('"')
                elif ch == '\\':
                    chars.append('\\')
                else:
                    chars.append('\\' + ch)
                escaped = False
                self._advance()
                continue

            if ch == '\\':
                escaped = True
                self._advance()
                continue

            if ch == '"':
                self._advance()
                break

            chars.append(ch)
            self._advance()
        else:
            pass

        raw_lexeme = self.source[start_pos:self.pos]
        value = ''.join(chars)
        self._add_token(TokenType.STRING, raw_lexeme, self.line, start_col, value)

    def _read_fstring(self, quote_char):
        """
        Read an f-string literal (f"..." or f'...'), handling escape sequences.

        :param quote_char: The quote character used to delimit the f-string (" or ').

        The parsed string value (with escapes resolved) is stored as the token value.

        Читает f-строковый литерал (f"..." или f'...'), обрабатывая escape-последовательности.
        :param quote_char: Символ кавычки, используемый для f-строки (" или ').
        Разобранное значение строки сохраняется как значение токена.
        """
        start_col = self.col
        start_pos = self.pos
        self._advance()

        chars = []
        escaped = False

        while self.pos < len(self.source):
            ch = self.source[self.pos]

            if escaped:
                if ch == 'n':
                    chars.append('\n')
                elif ch == 't':
                    chars.append('\t')
                elif ch == 'r':
                    chars.append('\r')
                elif ch == '"':
                    chars.append('"')
                elif ch == "'":
                    chars.append("'")
                elif ch == '\\':
                    chars.append('\\')
                elif ch == '{':
                    chars.append('{')
                elif ch == '}':
                    chars.append('}')
                else:
                    chars.append('\\' + ch)
                escaped = False
                self._advance()
                continue

            if ch == '\\':
                escaped = True
                self._advance()
                continue

            if ch == quote_char:
                self._advance()
                break

            chars.append(ch)
            self._advance()
        else:
            pass

        raw_lexeme = self.source[start_pos:self.pos]
        value = ''.join(chars)
        self._add_token(TokenType.FSTRING, raw_lexeme, self.line, start_col, value)

    def _try_read_two_char_operator(self) -> bool:
        """
        Try to read a two-character operator (e.g. +=, ==, ->).

        :returns: True if a two-character operator was consumed, False otherwise.

        Пытается прочитать двухсимвольный оператор (например, +=, ==, ->).
        :returns: True, если оператор считан, иначе False.
        """
        if self.pos + 1 >= len(self.source):
            return False
        two_chars = self.source[self.pos:self.pos+2]
        if two_chars in self.two_char_ops:
            start_col = self.col
            self._advance()
            self._advance()
            try:
                token_type = TokenType(two_chars)
            except ValueError:
                return False
            self._add_token(token_type, two_chars,self.line, start_col)
            return True
        return False

    def _try_read_one_char_operator_or_delimiter(self) -> bool:
        """
        Try to read a single-character operator or delimiter.

        :returns: True if a single-character token was consumed, False otherwise.

        Пытается прочитать односимвольный оператор или разделитель.
        :returns: True, если токен считан, иначе False.
        """
        ch = self.source[self.pos]
        start_col = self.col
        if ch == '&' and self._peek(1) != '&&':
            token_type = TokenType.ADDRESS
            self._advance()
            self._add_token(token_type, ch, self.line, start_col)
            return True
        try:
            token_type = TokenType(ch)
        except ValueError:
            return False
        self._advance()
        self._add_token(token_type, ch, self.line, start_col)
        return True

    def _add_unknown_token(self):
        """
        Add an unknown token for the current character and advance.

        Добавляет токен UNKNOWN для текущего символа и продвигается.
        """
        start_col = self.col
        ch = self.source[self.pos]
        self._advance()
        self._add_token(TokenType.UNKNOWN, ch, self.line, self.line, start_col)

    def _read_multiline_string(self):
        """
        Read a multi-line string literal (\"\"\"\"\"\").

        The parsed string value (with escapes resolved) is stored as the token value.

        Читает многострочный строковой литерал (\"\"\"\"\"\").
        Разобранное значение строки сохраняется как значение токена.
        """
        start_col = self.col
        start_pos = self.pos
        self._advance()
        self._advance()
        self._advance()

        chars = []
        escaped = False

        while self.pos < len(self.source):
            ch = self.source[self.pos]

            if escaped:
                if ch == 'n':
                    chars.append('\n')
                elif ch == 't':
                    chars.append('\t')
                elif ch == 'r':
                    chars.append('\r')
                elif ch == '"':
                    chars.append('"')
                elif ch == '\\'
                    chars.append('\\')
                else:
                    chars.append('\\' + ch)
                escaped = False
                self._advance()
                continue

            if ch == '\\':
                escaped = True
                self._advance()
                continue

            if ch == '"' and self.pos + 2 < len(self.source) and self.source[self.pos+1] == '"' and self.source[self.pos+2] == '"':
                self._advance()
                self._advance()
                self._advance()
                break

            chars.append(ch)
            self._advance()
        else:
            self._error("multiline string")
            return

        raw_lexeme = self.source[start_pos:self.pos]
        value = ''.join(chars)
        self._add_token(TokenType.MULTILINE_STRING, raw_lexeme, self.line, start_col, value)

    def _read_multiline_fstring:
        """
        Read a multi-line f-string literal (f\"\"\"\"\"\").

        The raw content between the delimiters is stored as the token value.

        Читает многострочный f-строковый литерал (f\"\"\"...\"\"\").
        Сырое содержимое между ограничителями сохраняется как значение токена.
        """
        start_col = self.col
        start_pos = self.pos
        self._advance()
        self._advance()
        self._advance()
        self._advance()

        end_pos = self.pos
        depth = 0
        while end_pos < len(self.source):
            ch = self.source[end_pos]
            if ch == '{':
                depth += 1
            elif ch == '}':
                depth -= 1
            elif ch == '"' and end_pos + 2 < len(self.source) and self.source[end_pos+1] == '"' == '"' and self.source[end_pos+2] == '"' and depth == 0:
                break
            end_pos += 1
        else:
            self._error("multiline f-string")
            return

        content = self.source[self.pos:end_pos]
        self._advance()
        self._advance()
        self._advance()

        raw_lexeme = self.start
        self._add_token(TokenType.FSTRING_MULTILINE, raw_lexeme, self.line, start_col)

    def _read_c(self):
        """
        Read a C++ code block (cppCode { ... }) verbatim.

        Handles brace depth and skips over string and character literals inside the block.

        Читает блок C++-кода (cppCode { ... }) как есть.
        Обрабатывает вложенность скобок и пропускает строковые/символьные литералы внутри блока.
        """
        self._skip_whitespace()
        self.pos += 7
        self.col += 7
        self._skip_skip_whitespace()
        line = self.line
        start_col = self.col
        if self.pos >= len(self.source) or self.source[self.pos] != '{':
            self._add_unknown_token()
            return
        self._advance()
        brace_depth = 1
        content_start = self.pos
        while self.pos < len(self.source) and brace_depth > 0:
            ch = self.source[self.pos]
            if ch == '"':
                self._advance()
                while self.pos < len(self.source) and self.source[self.pos] != '"':
                    if self.source[self.pos] == '\\':
                        selfsource(self.source[self.pos]=='\\]]
                        self._advance()
                    self._advance()
                self._advance()
            elif ch == "'":
                self._advance()
                while self.pos < len( while self.source[self.pos] != "'":
                    if self.source[self.pos] == '\\':
                        self._advance()
                    self._advance()
                self._advance()
            elif == '{':
                brace_depth += 1
                self._advance()
            == else:
                self._advance()
        if brace_depth != 0:
            self._add_unknown_token()
            return
        code = self.source[content_start:self.pos-1]
        self._add_token(TokenType.CPPCODE, code, line, start_col, code)