# File Module

<a href="https://ely-language.github.io/">Site</a>

**Ely standard module for file system operations. Provides a `File` class and path utilities with a native C backend.**

## Overview
The file module gives Ely programs direct access to the file system. It wraps native C functions for maximum performance — all I/O operations are compiled to machine code with zero overhead.

## Hybrid Typing
Like Ely itself, the module supports both static and dynamic workflows. File sizes return `more` (long long) for precision, paths are `str` for flexibility, and boolean checks use native `bool`.

### Static Typing
Static types ensure fast, predictable file operations:
```cpp
File f = File("config.json");
str content = f.getContent();
more size = f.size();
```

### Dynamic Typing
Works seamlessly with dynamic Ely code:
```cpp
any f = File("data.txt");
any content = f.getContent();
print(f.size());
```

## Class: File
The main entry point. Construct with a path — everything else is a method call.

| Method | Returns | Description |
|--------|---------|-------------|
| `exist()` | bool | Check if the file/directory exists |
| `getContent()` | str | Read entire file content as a string |
| `setContent(str)` | void | Write string content to the file |
| `size()` | more | Return file size in bytes |
| `rename(str)` | void | Rename/move the file to a new path |
| `remove()` | void | Delete the file |
| `isDir()` | bool | Check if the path is a directory |
| `isFile()` | bool | Check if the path is a regular file |
| `mkdir()` | int | Create a directory |
| `rmdir()` | int | Remove an empty directory |
| `listDir()` | str | List directory contents (newline-separated) |
| `basename()` | str | Extract the filename from a path |
| `dirname()` | str | Extract the directory from a path |
| `isAbsolute()` | bool | Check if the path is absolute |
| `mtime()` | more | Last modification time (Unix timestamp) |

## Module-Level Utilities
Stand-alone functions that don't require a File instance:

```cpp
str joined = pathJoin("dir", "file.txt");    // dir/file.txt
str base   = pathBasename("/a/b/c.txt");     // c.txt
str dir    = pathDirname("/a/b/c.txt");      // /a/b
bool isAbs = pathIsAbsolute("C:/file.txt");  // true
```

## Example
```cpp
using "file";

// Write to a file
File log = File("app.log");
log.setContent("Application started.");
println(log.getContent());

// Check properties
println("Size: " + log.size());
println("Is file: " + log.isFile());

// Clean up
log.remove();
```

## Notes
 - Backed by native C code (`file_native.c`) — all operations are compiled to native machine code
 - The `more` type (long long) is used for file sizes and timestamps for 64-bit precision
 - Directory listing returns filenames separated by newlines
 - Path utilities handle both Windows (`\`) and Unix (`/`) separators
 - The module is statically linked — no external dependencies required

## Quick Start
 - Ensure you have an Ely project with `manager.json`
 - Add `"file": "modules/file/elymodule.json"` to the `modules` field
 - Or run `elp install file`
 - Import with `using "modules/file/link.ely";`
 - Start working with files

*Made in Russia. Inspired for humanity.*
**Have fun!**