from .token import Token, TokenType

class Lexer:
    """
    Performs lexical analysis (tokenisation) of Ely source code.

    Выполняет лексический анализ (токенизацию) исходного кода Ely.
    """

    def __init__(self, source: str):
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
            'static': TokenType.STATIC,
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
            'fields': TokenType.FIELDS,
            'methods': TokenType.METHODS,
            'wait': TokenType.WAIT,
            'super': TokenType.SUPER,
        }

        self.two_char_ops = {
            '+=', '-=', '*=', '/=', '==', '!=', '<=', '>=', '&&', '||', '??', '->', '=>'
        }

    def tokenize(self, debug=False):
        """
        Tokenise the entire source code and return a list of tokens.

        Токенизирует весь исходный код и возвращает список токенов.
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

            # Multiline f-string: f"""..."""
            if (ch == 'f' or ch == 'F') and self._peek(1) == '"' and self._peek(2) == '"' and self._peek(3) == '"':
                self._advance()  # consume 'f'
                self._read_multiline_fstring()
                continue

            # Multiline string: """..."""
            if ch == '"' and self._peek(1) == '"' and self._peek(2) == '"':
                self._read_multiline_string()
                continue

            # Single-line f-string: f"..." or f'...'
            if (ch == 'f' or ch == 'F') and (self._peek(1) == '"' or self._peek(1) == "'"):
                self._advance()  # consume 'f'
                self._read_fstring(self._peek())  # pass the quote char
                continue

            # cCode block
            if self.source[self.pos:self.pos+5] == 'cCode':
                self._read_c_code()
                continue

            # cppCode block
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
        Move to the next character in the source, updating line and column counters.

        Переходит к следующему символу в исходном коде, обновляя счётчики строки и колонки.
        """
        if self.pos < len(self.source) and self.source[self.pos] == '\n':
            self.line += 1
            self.col = 1
        else:
            self.col += 1
        self.pos += 1

    def _peek(self, offset=0):
        """
        Return the character at position pos + offset without advancing.

        Возвращает символ в позиции pos + offset без продвижения.
        """
        idx = self.pos + offset
        return self.source[idx] if 0 <= idx < len(self.source) else None

    def _match(self, expected):
        """
        If the current character matches `expected`, advance and return True.

        Если текущий символ совпадает с `expected`, продвинуться и вернуть True.
        """
        if self._peek() == expected:
            self._advance()
            return True
        return False

    def _skip_whitespace(self):
        """
        Skip over spaces, tabs, carriage returns and newlines.

        Пропускает пробелы, табуляции, возврат каретки и переводы строк.
        """
        while self.pos < len(self.source):
            ch = self.source[self.pos]
            if ch in ' \t\r\n':
                self._advance()
            else:
                break

    def _skip_comment(self) -> bool:
        """
        Skip a single-line (// ...) or multi-line (/* ... */) comment.

        Пропускает однострочный (// ...) или многострочный (/* ... */) комментарий.
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
        Create a token and append it to the token list.

        Создаёт токен и добавляет его в список токенов.
        """
        token = Token(token_type, lexeme, line, col, value)
        self.tokens.append(token)
        if self.debug:
            print(f"DEBUG: {token}")

    def _error(self, context: str):
        """
        Raise a SyntaxError for an unterminated literal.

        Вызывает SyntaxError для незавершённого литерала.
        """
        raise SyntaxError(f"Unterminated {context} at line {self.line}, column {self.col}")

    def _read_identifier_or_keyword(self):
        """
        Read an identifier or keyword and emit the corresponding token.

        Читает идентификатор или ключевое слово и выдаёт соответствующий токен.
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
        Read a numeric literal (integer or floating-point) and emit a NUMBER token.

        Читает числовой литерал (целое или с плавающей точкой) и выдаёт токен NUMBER.
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
        Read a double-quoted string literal and emit a STRING token.

        Читает строковой литерал в двойных кавычках и выдаёт токен STRING.
        """
        start_col = self.col
        start_pos = self.pos
        self._advance()  # opening quote

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
            self._error("string literal")

        raw_lexeme = self.source[start_pos:self.pos]
        value = ''.join(chars)
        self._add_token(TokenType.STRING, raw_lexeme, self.line, start_col, value)

    def _read_fstring(self, quote_char):
        """
        Read a single-line f-string literal and emit an FSTRING token.

        Читает однострочный f-строковый литерал и выдаёт токен FSTRING.
        """
        start_col = self.col
        start_pos = self.pos
        self._advance()  # opening quote

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
            self._error("f-string literal")

        raw_lexeme = self.source[start_pos:self.pos]
        value = ''.join(chars)
        self._add_token(TokenType.FSTRING, raw_lexeme, self.line, start_col, value)

    def _read_multiline_string(self):
        """
        Read a multiline string literal (\"\"\"...\"\"\") and emit a MULTILINE_STRING token.

        Читает многострочный строковой литерал (\"\"\"...\"\"\") и выдаёт токен MULTILINE_STRING.
        """
        start_col = self.col
        start_pos = self.pos
        self._advance()  # first quote
        self._advance()  # second quote
        self._advance()  # third quote

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

            if ch == '"' and self.pos + 2 < len(self.source) and self.source[self.pos+1] == '"' and self.source[self.pos+2] == '"':
                self._advance()
                self._advance()
                self._advance()
                break

            chars.append(ch)
            self._advance()
        else:
            self._error("multiline string")

        raw_lexeme = self.source[start_pos:self.pos]
        value = ''.join(chars)
        self._add_token(TokenType.MULTILINE_STRING, raw_lexeme, self.line, start_col, value)

    def _read_multiline_fstring(self):
        """
        Read a multiline f-string literal (f\"\"\"...\"\"\") and emit an FSTRING_MULTILINE token.

        Читает многострочный f-строковый литерал (f\"\"\"...\"\"\") и выдаёт токен FSTRING_MULTILINE.
        """
        start_col = self.col
        start_pos = self.pos
        # we already consumed 'f', now consume the three opening quotes
        self._advance()  # first quote
        self._advance()  # second quote
        self._advance()  # third quote

        end_pos = self.pos
        depth = 0
        while end_pos < len(self.source):
            ch = self.source[end_pos]
            if ch == '{':
                depth += 1
            elif ch == '}':
                depth -= 1
            elif ch == '"' and end_pos + 2 < len(self.source) and \
                 self.source[end_pos+1] == '"' and self.source[end_pos+2] == '"' and depth == 0:
                break
            end_pos += 1
        else:
            self._error("multiline f-string")

        content = self.source[self.pos:end_pos]
        self.pos = end_pos
        self._advance()  # first quote
        self._advance()  # second quote
        self._advance()  # third quote

        raw_lexeme = self.source[start_pos:self.pos]
        self._add_token(TokenType.FSTRING_MULTILINE, raw_lexeme, self.line, start_col, value=content)

    def _read_c_code(self):
        """
        Read a cCode { ... } block and emit a CCODE token with the raw code as value.

        Читает блок cCode { ... } и выдаёт токен CCODE, сохраняя сырой код как значение.
        """
        self._skip_whitespace()
        self.pos += 5  # skip 'cCode'
        self.col += 5
        self._skip_whitespace()
        line = self.line
        start_col = self.col
        if self.pos >= len(self.source) or self.source[self.pos] != '{':
            self._add_unknown_token()
            return
        self._advance()  # consume '{'
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
        self._add_token(TokenType.CCODE, code, line, start_col, value=code)

    def _read_cpp_code(self):
        """
        Read a cppCode { ... } block and emit a CPPCODE token with the raw code as value.

        Читает блок cppCode { ... } и выдаёт токен CPPCODE, сохраняя сырой код как значение.
        """
        self._skip_whitespace()
        self.pos += 7  # skip 'cppCode'
        self.col += 7
        self._skip_whitespace()
        line = self.line
        start_col = self.col
        if self.pos >= len(self.source) or self.source[self.pos] != '{':
            self._add_unknown_token()
            return
        self._advance()  # consume '{'
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
        self._add_token(TokenType.CPPCODE, code, line, start_col, value=code)

    def _try_read_two_char_operator(self) -> bool:
        """
        Attempt to read a two-character operator (e.g. '==', '+=') and emit the appropriate token.

        Пытается прочитать двухсимвольный оператор (например, '==', '+=') и выдать соответствующий токен.
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
            self._add_token(token_type, two_chars, self.line, start_col)
            return True
        return False

    def _try_read_one_char_operator_or_delimiter(self) -> bool:
        """
        Attempt to read a single-character operator or delimiter and emit the appropriate token.

        Пытается прочитать односимвольный оператор или разделитель и выдать соответствующий токен.
        """
        ch = self.source[self.pos]
        start_col = self.col
        if ch == '&' and self._peek(1) != '&':
            self._advance()
            self._add_token(TokenType.ADDRESS, ch, self.line, start_col)
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
        Emit an UNKNOWN token for the current character and advance.

        Выдаёт токен UNKNOWN для текущего символа и продвигается.
        """
        start_col = self.col
        ch = self.source[self.pos]
        self._advance()
        self._add_token(TokenType.UNKNOWN, ch, self.line, start_col)

    # def _read_c(self):
    #     """
    #     Read a C++ code block (cppCode { ... }) verbatim.

    #     Handles brace depth and skips over string and character literals inside the block.

    #     Читает блок C++-кода (cppCode { ... }) как есть.
    #     Обрабатывает вложенность скобок и пропускает строковые/символьные литералы внутри блока.
    #     """
    #     self._skip_whitespace()
    #     self.pos += 7
    #     self.col += 7
    #     self._skip_whitespace()
    #     line = self.line
    #     start_col = self.col
    #     if self.pos >= len(self.source) or self.source[self.pos] != '{':
    #         self._add_unknown_token()
    #         return
    #     self._advance()
    #     brace_depth = 1
    #     content_start = self.pos
    #     while self.pos < len(self.source) and brace_depth > 0:
    #         ch = self.source[self.pos]
    #         if ch == '"':
    #             self._advance()
    #             while self.pos < len(self.source) and self.source[self.pos] != '"':
    #                 if self.source[self.pos] == '\\':
    #                     selfsource(self.source[self.pos]=='\\]]
    #                     self._advance()
    #                 self._advance()
    #             self._advance()
    #         elif ch == "'":
    #             self._advance()
    #             while self.pos < len( while self.source[self.pos] != "'":
    #                 if self.source[self.pos] == '\\':
    #                     self._advance()
    #                 self._advance()
    #             self._advance()
    #         elif ch == '{':
    #             brace_depth += 1
    #             self._advance()
    #         else:
    #             self._advance()
    #     if brace_depth != 0:
    #         self._add_unknown_token()
    #         return
    #     code = self.source[content_start:self.pos-1]
    #     self._add_token(TokenType.CPPCODE, code, line, start_col, code)