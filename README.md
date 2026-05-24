# Ely Language

<a href="https://ely-language.github.io/">Site</a>

**Ely is a hybrid-typed, compiled programming language with C-like syntax that compiles to C++.**

## Hybrid Typing
Ely features both dynamic and static typing. This makes many tasks simpler: prototyping, easier interaction with text files – and much more, all with a human touch – the language's key advantage over its competitors.
#### Static Typing
Static types in Ely are compiled to native types and deliver high performance. Because they are close to native types, operations with native static typing and its variables are almost instantaneous.
**Static typing in Ely works similarly to C:**
```cpp
// int
int a = 2;
int b = 3;
print(a + b);
// float
flt fa = 12.0;
// strings
str myStr = "Hello from Ely";
// f-strings
str myF = f"{myStr} with {fa}";
```
#### Dynamic Typing
Dynamic typing in Ely is implemented closer to Python, though, thanks to compilation to C++, it is slightly faster.
The language uses lazy type inference for dynamic types:
```cpp
dynStr = "This is dynamic!";
dyn = 2;
dyn = dynStr; // Also will work!
// Or you can make a declaration with any
any anDyn = "The same backend!"; // It will work like a case without 'any'
```
#### Arrays
A special case is arrays. They can be either static or dynamic:
```cpp
arr myIntArr<int> = [2, 3, 4]; // can contain only int elements
arr anyArr = ["hi", 2, 3.5] // can contain anything
```

## Function-Oriented Programming (FOP)
Ely as a language is neither purely FOP nor OOP. However, both paradigms are implemented fairly well. It should be noted that the language has an entry point:
```cpp
public int func main() {
    // your code here
}
```
As you can see, the language emphasizes code readability in declarations. To declare a function you simply write the return type, followed by the keyword `func`, and then the name. For a dynamic return type you can omit the type, but it is recommended, for certainty, to specify `any` as the type.

## Object-Oriented Programming (OOP)
OOP in the language is not entirely conventional in its declaration style, but overall it is convenient and easy to pick up.
Example:
```cpp
class Cat {
    wait str name;
    wait str color;
    wait int age;
    
    public void func info() {
        print(f"This is {color} {age}-years old cat {name}");
    } 
} 
```
This example clearly shows the main features: wait-fields. These fields request values when creating an object, which must be provided:
```cpp
Cat kitten = new Cat("Pie", "gray", 1); // name, color, age
```
Declarations are familiar. More details about OOP, inheritance, and interfaces can be found in the documentation.

## Notes
**It is impossible not to mention the features and advantages of the language that reveal themselves in the details:**
 - its own generational Garbage Collector written in C
 - asynchronous features at the base level
 - compatibility between static and dynamic types: the compiler creates conversions automatically.
 - manager.json – a configuration system that makes work easier for both the user and the compiler.
 - ebt commands: allow you to create and compile a project
 - elp – a custom package manager (currently in testing)

# Quick Start
 - Download and install ElySpruce or another up‑to‑date compiler for the language.
 - Download and install g++ or clang for full compilation if you don't have them yet.
 - If you use VS Code: download and install the VS Code extension (available on the site)
 - Navigate to the folder where you want to create your project
 - Use `ebt project [project name]` in that folder
 - Configure manager.json
 - In the main file (specified in the manager as `enter` – make sure you look at `enter` at the root of the manager, not inside `output`), write:
   ```cpp
   public int func main() {
       print("Hello world!");
   }
   ```
 - Compile with the command `ebt build manager.json` and run the executable from the output/ folder (the .exe file will have the name specified in the manager under `output`)

#### For more, see the documentation
*Made in Russia. Inspired for humanity.*
**Have fun!**