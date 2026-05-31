# JSON Module

<a href="https://ely-language.github.io/">Site</a>

**Ely standard module for JSON parsing and serialization. Provides a `JSON` class and utility functions with a native C backend.**

## Overview
The JSON module enables Ely programs to parse, validate, and stringify JSON data. It wraps a native C parser for maximum performance — JSON operations are compiled to machine code with zero overhead.

## Hybrid Typing
Like Ely itself, the module bridges static and dynamic worlds. Parsed JSON returns `any` — you can work with it dynamically. Stringified output uses `str` for guaranteed text output.

### Static Typing
Declare types explicitly for predictable behaviour:
```cpp
JSON j = JSON("{\"name\": \"Ely\"}");
any parsed = j.parse();
bool valid = j.isValid();
str output = j.stringify(parsed);
```

### Dynamic Typing
JSON pairs naturally with Ely's dynamic types:
```cpp
any j = JSON("{\"version\": 26.5}");
any data = j.parse();
print(j.stringify(data));
```

## Class: JSON
The main entry point. Construct with a JSON string — everything else is method calls.

| Method | Returns | Description |
|--------|---------|-------------|
| `parse()` | any | Parse the JSON string into an Ely dynamic value |
| `isValid()` | bool | Check whether the content is valid JSON |
| `stringify(any)` | str | Convert an Ely value back to a JSON string |

## Global Utilities
Stand-alone functions that don't require a JSON instance:

| Function | Signature | Description |
|----------|-----------|-------------|
| `json_parse_str_wrapper` | `any func(str)` | Parse a string into a dynamic value |
| `json_is_valid_wrapper` | `bool func(str)` | Validate a string as JSON |
| `json_stringify` | `str func(any)` | Serialize any value to JSON text |

## Example
```cpp
using "json";

// Parse a JSON string
JSON j = JSON("{\"name\": \"Ely\", \"version\": 26.5}");
any data = j.parse();

// Validate
println("Is valid: " + j.isValid());

// Round-trip: stringify back
str output = j.stringify(data);
println("Stringified: " + output);

// Use global utilities
println("Check: " + json_is_valid_wrapper("[1, 2, 3]"));
any parsed = json_parse_str_wrapper("[1, 2, 3]");
println("Reparsed: " + json_stringify(parsed));
```

## Notes
 - Backed by native C code (`json_native.c`) — parsing and serialization run at native speed
 - The `any` type is used for parsed JSON values, enabling dynamic access to objects and arrays
 - `stringify()` works with any Ely value — objects, arrays, strings, numbers, and booleans
 - `isValid()` returns false for malformed JSON without throwing exceptions
 - The module is statically linked — no external dependencies required

## Quick Start
 - Ensure you have an Ely project with `manager.json`
 - Add `"json": "modules/json/elymodule.json"` to the `modules` field
 - Or run `elp install json`
 - Import with `using "modules/json/link.ely";`
 - Start parsing JSON

*Made in Russia. Inspired for humanity.*
**Have fun!**