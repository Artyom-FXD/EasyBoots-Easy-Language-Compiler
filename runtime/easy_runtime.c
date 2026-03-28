#include "easy_runtime.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <time.h>
#include <stdarg.h>
#include <ctype.h>

#ifdef _WIN32
#include <windows.h>
#else
#include <unistd.h>
#include <dlfcn.h>
#endif

// -------------------------------------------------------------------
// Собственные strtoll/strtoull для Windows
// -------------------------------------------------------------------
#ifndef _WIN32
#define my_strtoll strtoll
#define my_strtoull strtoull
#else
static long long my_strtoll(char *nptr, char **endptr, int base) {
    long long val = 0;
    int sign = 1;
    if (base == 0) {
        if (*nptr == '0') {
            if (nptr[1] == 'x' || nptr[1] == 'X') base = 16;
            else base = 8;
        } else base = 10;
    }
    while (*nptr == ' ' || *nptr == '\t') nptr++;
    if (*nptr == '-') { sign = -1; nptr++; }
    else if (*nptr == '+') nptr++;
    if (base == 16 && *nptr == '0' && (nptr[1] == 'x' || nptr[1] == 'X')) nptr += 2;
    while (*nptr) {
        int digit;
        if (*nptr >= '0' && *nptr <= '9') digit = *nptr - '0';
        else if (base == 16 && *nptr >= 'a' && *nptr <= 'f') digit = *nptr - 'a' + 10;
        else if (base == 16 && *nptr >= 'A' && *nptr <= 'F') digit = *nptr - 'A' + 10;
        else break;
        if (digit >= base) break;
        val = val * base + digit;
        nptr++;
    }
    if (endptr) *endptr = (char*)nptr;
    return sign * val;
}

static unsigned long long my_strtoull(char *nptr, char **endptr, int base) {
    unsigned long long val = 0;
    if (base == 0) {
        if (*nptr == '0') {
            if (nptr[1] == 'x' || nptr[1] == 'X') base = 16;
            else base = 8;
        } else base = 10;
    }
    while (*nptr == ' ' || *nptr == '\t') nptr++;
    if (*nptr == '-') nptr++;
    else if (*nptr == '+') nptr++;
    if (base == 16 && *nptr == '0' && (nptr[1] == 'x' || nptr[1] == 'X')) nptr += 2;
    while (*nptr) {
        int digit;
        if (*nptr >= '0' && *nptr <= '9') digit = *nptr - '0';
        else if (base == 16 && *nptr >= 'a' && *nptr <= 'f') digit = *nptr - 'a' + 10;
        else if (base == 16 && *nptr >= 'A' && *nptr <= 'F') digit = *nptr - 'A' + 10;
        else break;
        if (digit >= base) break;
        val = val * base + digit;
        nptr++;
    }
    if (endptr) *endptr = (char*)nptr;
    return val;
}
#endif

// ------------------------ Консоль ------------------------
void easy_print(easy_str str) { if (str) fputs(str, stdout); }
void easy_print_int(easy_int n) { printf("%d", n); }
void easy_print_uint(easy_uint n) { printf("%u", n); }
void easy_print_more(easy_more n) { printf("%lld", n); }
void easy_print_umore(easy_umore n) { printf("%llu", n); }
void easy_print_flt(easy_flt f) { printf("%f", f); }
void easy_print_double(easy_double d) { printf("%lf", d); }
void easy_print_bool(easy_bool b) { fputs(b ? "true" : "false", stdout); }
void easy_print_char(easy_char c) { putchar(c); }
void easy_print_byte(easy_byte b) { printf("%d", (int)b); }
void easy_print_ubyte(easy_ubyte b) { printf("%u", (unsigned int)b); }
void easy_println(easy_str str) {
    if (str) {
        fputs(str, stdout);
    }
    putchar('\n');
    fflush(stdout);
}


easy_str easy_input(void) {
    static char buffer[1024];
    if (fgets(buffer, sizeof(buffer), stdin)) {
        size_t len = strlen(buffer);
        if (len && buffer[len-1] == '\n') buffer[len-1] = '\0';
        char* res = easy_alloc(len + 1);
        if (res) strcpy(res, buffer);
        return res;
    }
    return NULL;
}

easy_str easy_input_prompt(easy_str prompt) {
    if (prompt) easy_print(prompt);
    return easy_input();
}

// ------------------------ Преобразования строк в числа ------------------------
easy_int easy_str_to_int(easy_str str) {
    if (!str) return 0;
    long long v = my_strtoll(str, NULL, 10);
    return (easy_int)v;
}
easy_uint easy_str_to_uint(easy_str str) {
    if (!str) return 0;
    unsigned long long v = my_strtoull(str, NULL, 10);
    return (easy_uint)v;
}
easy_more easy_str_to_more(easy_str str) {
    if (!str) return 0;
    return my_strtoll(str, NULL, 10);
}
easy_umore easy_str_to_umore(easy_str str) {
    if (!str) return 0;
    return my_strtoull(str, NULL, 10);
}
easy_flt easy_str_to_flt(easy_str str) {
    if (!str) return 0.0f;
    return (easy_flt)strtod(str, NULL);
}
easy_double easy_str_to_double(easy_str str) {
    if (!str) return 0.0;
    return strtod(str, NULL);
}

// ------------------------ Преобразования чисел в строки ------------------------
static easy_str _int_to_str(long long n) {
    char buf[32];
    int len = snprintf(buf, sizeof(buf), "%lld", n);
    if (len < 0) return NULL;
    char* res = easy_alloc(len + 1);
    if (res) memcpy(res, buf, len + 1);
    return res;
}
static easy_str _uint_to_str(unsigned long long n) {
    char buf[32];
    int len = snprintf(buf, sizeof(buf), "%llu", n);
    if (len < 0) return NULL;
    char* res = easy_alloc(len + 1);
    if (res) memcpy(res, buf, len + 1);
    return res;
}
easy_str easy_int_to_str(easy_int n) { return _int_to_str(n); }
easy_str easy_uint_to_str(easy_uint n) { return _uint_to_str(n); }
easy_str easy_more_to_str(easy_more n) { return _int_to_str(n); }
easy_str easy_umore_to_str(easy_umore n) { return _uint_to_str(n); }
easy_str easy_flt_to_str(easy_flt f) {
    char buf[64];
    int len = snprintf(buf, sizeof(buf), "%g", (double)f);
    if (len < 0) return NULL;
    char* res = easy_alloc(len + 1);
    if (res) memcpy(res, buf, len + 1);
    return res;
}
easy_str easy_double_to_str(easy_double d) {
    char buf[64];
    int len = snprintf(buf, sizeof(buf), "%g", d);
    if (len < 0) return NULL;
    char* res = easy_alloc(len + 1);
    if (res) memcpy(res, buf, len + 1);
    return res;
}
easy_str easy_bool_to_str(easy_bool b) {
    char* s = b ? "true" : "false";
    char* res = easy_alloc(strlen(s) + 1);
    if (res) strcpy(res, s);
    return res;
}

// ------------------------ Строки ------------------------
size_t easy_str_len(easy_str str) { return str ? strlen(str) : 0; }
easy_str easy_str_dup(easy_str str) {
    if (!str) return NULL;
    char* dup = easy_alloc(strlen(str) + 1);
    if (dup) strcpy(dup, str);
    return dup;
}
easy_str easy_str_concat(easy_str a, easy_str b) {
    if (!a && !b) return NULL;
    size_t la = a ? strlen(a) : 0;
    size_t lb = b ? strlen(b) : 0;
    char* res = easy_alloc(la + lb + 1);
    if (!res) return NULL;
    if (la) memcpy(res, a, la);
    if (lb) memcpy(res + la, b, lb);
    res[la+lb] = '\0';
    return res;
}
int easy_str_cmp(easy_str a, easy_str b) {
    if (a == b) return 0;
    if (!a) return -1;
    if (!b) return 1;
    return strcmp(a, b);
}
easy_str easy_str_substr(easy_str str, size_t start, size_t len) {
    if (!str) return NULL;
    size_t slen = strlen(str);
    if (start >= slen) return easy_str_dup("");
    if (start + len > slen) len = slen - start;
    char* res = easy_alloc(len + 1);
    if (!res) return NULL;
    memcpy(res, str + start, len);
    res[len] = '\0';
    return res;
}
easy_str easy_str_trim(easy_str str) {
    if (!str) return NULL;
    while (*str && (*str == ' ' || *str == '\t' || *str == '\n')) str++;
    size_t len = strlen(str);
    while (len > 0 && (str[len-1] == ' ' || str[len-1] == '\t' || str[len-1] == '\n')) len--;
    char* res = easy_alloc(len + 1);
    if (!res) return NULL;
    memcpy(res, str, len);
    res[len] = '\0';
    return res;
}
easy_str easy_str_replace(easy_str str, easy_str old, easy_str new) {
    if (!str || !old) return easy_str_dup(str);
    size_t old_len = strlen(old);
    if (old_len == 0) return easy_str_dup(str);
    size_t new_len = new ? strlen(new) : 0;
    size_t count = 0;
    char* pos = str;
    while ((pos = strstr(pos, old))) { count++; pos += old_len; }
    if (count == 0) return easy_str_dup(str);
    size_t result_len = strlen(str) + count * (new_len - old_len);
    char* res = easy_alloc(result_len + 1);
    if (!res) return NULL;
    char* out = res;
    pos = str;
    while (*pos) {
        char* found = strstr(pos, old);
        if (found) {
            size_t before = found - pos;
            memcpy(out, pos, before);
            out += before;
            if (new) { memcpy(out, new, new_len); out += new_len; }
            pos = found + old_len;
        } else {
            strcpy(out, pos);
            break;
        }
    }
    return res;
}

// ------------------------ Математика ------------------------
easy_int easy_abs_int(easy_int n) { return n < 0 ? -n : n; }
easy_more easy_abs_more(easy_more n) { return n < 0 ? -n : n; }
easy_double easy_fabs(easy_double x) { return fabs(x); }
easy_int easy_min_int(easy_int a, easy_int b) { return a < b ? a : b; }
easy_more easy_min_more(easy_more a, easy_more b) { return a < b ? a : b; }
easy_double easy_min_double(easy_double a, easy_double b) { return a < b ? a : b; }
easy_int easy_max_int(easy_int a, easy_int b) { return a > b ? a : b; }
easy_more easy_max_more(easy_more a, easy_more b) { return a > b ? a : b; }
easy_double easy_max_double(easy_double a, easy_double b) { return a > b ? a : b; }
easy_double easy_pow(easy_double base, easy_double exp) { return pow(base, exp); }
easy_double easy_sqrt(easy_double x) { return sqrt(x); }
easy_double easy_sin(easy_double x) { return sin(x); }
easy_double easy_cos(easy_double x) { return cos(x); }
easy_double easy_tan(easy_double x) { return tan(x); }

// ------------------------ Случайные числа ------------------------
static unsigned int rand_seed = 1;
void easy_srand(easy_uint seed) { rand_seed = seed; }
easy_int easy_rand(void) {
    rand_seed = rand_seed * 1103515245 + 12345;
    return (easy_int)((rand_seed >> 16) & 0x7FFF);
}
easy_double easy_rand_double(void) {
    return (easy_double)easy_rand() / 32767.0;
}

// ------------------------ Время ------------------------
void easy_sleep(easy_uint milliseconds) {
#ifdef _WIN32
    Sleep(milliseconds);
#else
    usleep(milliseconds * 1000);
#endif
}
easy_more easy_time_now(void) {
    return (easy_more)time(NULL);
}
double easy_time_diff(easy_more start, easy_more end) {
    return (double)(end - start);
}

// ------------------------ Файлы ------------------------
typedef struct easy_file {
    FILE* fp;
} easy_file;

easy_file* easy_file_open(char* path, char* mode) {
    FILE* fp = fopen(path, mode);
    if (!fp) return NULL;
    easy_file* f = easy_alloc(sizeof(easy_file));
    if (!f) { fclose(fp); return NULL; }
    f->fp = fp;
    return f;
}
void easy_file_close(easy_file* f) {
    if (f) {
        if (f->fp) fclose(f->fp);
        easy_free(f);
    }
}
int easy_file_write(easy_file* f, char* data, size_t len) {
    if (!f || !f->fp) return -1;
    return (fwrite(data, 1, len, f->fp) == len) ? 0 : -1;
}
char* easy_file_read(easy_file* f, size_t* out_len) {
    if (!f || !f->fp) return NULL;
    char* result = NULL;
    size_t total = 0, cap = 0;
    char buf[4096];
    while (1) {
        size_t n = fread(buf, 1, sizeof(buf), f->fp);
        if (n == 0) break;
        if (total + n > cap) {
            cap = (total + n) * 2 + 1024;
            char* new_res = realloc(result, cap);
            if (!new_res) { free(result); return NULL; }
            result = new_res;
        }
        memcpy(result + total, buf, n);
        total += n;
    }
    if (out_len) *out_len = total;
    if (total == 0) {
        free(result);
        return NULL;
    }
    char* final = realloc(result, total + 1);
    if (final) result = final;
    result[total] = '\0';
    return result;
}
int easy_file_exists(char* path) {
    FILE* f = fopen(path, "r");
    if (f) { fclose(f); return 1; }
    return 0;
}
char* easy_file_read_all(char* path, size_t* out_len) {
    easy_file* f = easy_file_open(path, "rb");
    if (!f) return NULL;
    char* data = easy_file_read(f, out_len);
    easy_file_close(f);
    return data;
}
int easy_file_remove(char* path) { return remove(path); }
int easy_file_rename(char* old, char* new) { return rename(old, new); }

// ------------------------ Пути ------------------------
easy_str easy_path_join(easy_str a, easy_str b) {
    if (!a && !b) return NULL;
    if (!a) return easy_str_dup(b);
    if (!b) return easy_str_dup(a);
    size_t la = strlen(a);
    size_t lb = strlen(b);
    char* res = easy_alloc(la + lb + 2);
    if (!res) return NULL;
    strcpy(res, a);
    if (la > 0 && res[la-1] != '/' && res[la-1] != '\\')
        strcat(res, "/");
    strcat(res, b);
    return res;
}
easy_str easy_path_basename(easy_str path) {
    if (!path) return NULL;
    char* sep = strrchr(path, '/');
    if (!sep) sep = strrchr(path, '\\');
    if (!sep) return easy_str_dup(path);
    return easy_str_dup(sep + 1);
}
easy_str easy_path_dirname(easy_str path) {
    if (!path) return NULL;
    char* sep = strrchr(path, '/');
    if (!sep) sep = strrchr(path, '\\');
    if (!sep) return easy_str_dup(".");
    size_t len = sep - path;
    if (len == 0) return easy_str_dup(".");
    char* res = easy_alloc(len + 1);
    if (!res) return NULL;
    memcpy(res, path, len);
    res[len] = '\0';
    return res;
}
int easy_path_is_absolute(easy_str path) {
    if (!path) return 0;
    if (path[0] == '/' || path[0] == '\\') return 1;
#ifdef _WIN32
    if (path[0] && path[1] == ':') return 1;
#endif
    return 0;
}

// ------------------------ Динамические библиотеки ------------------------
#ifdef _WIN32
#define LIB_HANDLE HMODULE
#define LIB_LOAD(path) LoadLibraryA(path)
#define LIB_GET(lib, name) GetProcAddress((HMODULE)lib, name)
#define LIB_CLOSE(lib) FreeLibrary((HMODULE)lib)
#else
#define LIB_HANDLE void*
#define LIB_LOAD(path) dlopen(path, RTLD_LAZY)
#define LIB_GET(lib, name) dlsym(lib, name)
#define LIB_CLOSE(lib) dlclose(lib)
#endif

void* easy_load_library(char* path) {
    if (!path) return NULL;
    return (void*)LIB_LOAD(path);
}
void* easy_get_function(void* lib, char* name) {
    if (!lib || !name) return NULL;
    return LIB_GET(lib, name);
}
void easy_close_library(void* lib) {
    if (lib) LIB_CLOSE(lib);
}
int easy_call_int_int(void* func, int a, int b) {
    if (!func) return 0;
    int (*f)(int, int) = (int (*)(int, int))func;
    return f(a, b);
}
double easy_call_double_double(void* func, double a) {
    if (!func) return 0.0;
    double (*f)(double) = (double (*)(double))func;
    return f(a);
}
double easy_call_double_double_double(void* func, double a, double b) {
    if (!func) return 0.0;
    double (*f)(double, double) = (double (*)(double, double))func;
    return f(a, b);
}
char* easy_call_str_void(void* func) {
    if (!func) return NULL;
    char* (*f)(void) = (char* (*)(void))func;
    return f();
}

// ------------------------ Память ------------------------
void* easy_alloc(size_t size) { return malloc(size); }
void easy_free(void* ptr) { free(ptr); }

// ------------------------ Массивы ------------------------
easy_array* easy_array_new(size_t capacity, size_t elem_size) {
    easy_array* arr = (easy_array*)easy_alloc(sizeof(easy_array));
    if (!arr) return NULL;
    arr->data = easy_alloc(capacity * elem_size);
    if (!arr->data) {
        easy_free(arr);
        return NULL;
    }
    arr->size = 0;
    arr->capacity = capacity;
    arr->elem_size = elem_size;
    return arr;
}

void easy_array_free(easy_array* arr) {
    if (arr) {
        if (arr->data) easy_free(arr->data);
        easy_free(arr);
    }
}

int easy_array_push(easy_array* arr, void* elem) {
    if (!arr) return -1;
    if (arr->size >= arr->capacity) {
        size_t new_cap = arr->capacity * 2;
        if (new_cap == 0) new_cap = 4;
        void* new_data = easy_alloc(new_cap * arr->elem_size);
        if (!new_data) return -1;
        memcpy(new_data, arr->data, arr->size * arr->elem_size);
        easy_free(arr->data);
        arr->data = new_data;
        arr->capacity = new_cap;
    }
    memcpy((char*)arr->data + arr->size * arr->elem_size, elem, arr->elem_size);
    arr->size++;
    return 0;
}

void easy_array_pop(easy_array* arr) {
    if (arr && arr->size > 0) arr->size--;
}

void* easy_array_pop_value(easy_array* arr) {
    if (!arr || arr->size == 0) return NULL;
    arr->size--;
    return (char*)arr->data + arr->size * arr->elem_size;
}

size_t easy_array_len(easy_array* arr) {
    return arr ? arr->size : 0;
}

void* easy_array_get(easy_array* arr, size_t index) {
    if (!arr || index >= arr->size) return NULL;
    return (char*)arr->data + index * arr->elem_size;
}

void easy_array_set(easy_array* arr, size_t index, void* elem) {
    if (!arr || index >= arr->size) return;
    memcpy((char*)arr->data + index * arr->elem_size, elem, arr->elem_size);
}

size_t easy_array_size(easy_array* arr) {
    return arr ? arr->size : 0;
}

easy_array* easy_array_make(size_t count, size_t elem_size, ...) {
    easy_array* arr = easy_array_new(count, elem_size);
    if (!arr) return NULL;
    va_list args;
    va_start(args, elem_size);
    for (size_t i = 0; i < count; i++) {
        void* elem = va_arg(args, void*);
        easy_array_push(arr, elem);
    }
    va_end(args);
    return arr;
}

int easy_array_remove_value(easy_array* arr, void* value) {
    if (!arr || arr->size == 0) return -1;
    for (size_t i = 0; i < arr->size; i++) {
        if (memcmp((char*)arr->data + i * arr->elem_size, value, arr->elem_size) == 0) {
            size_t bytes_to_move = (arr->size - i - 1) * arr->elem_size;
            memmove((char*)arr->data + i * arr->elem_size,
                    (char*)arr->data + (i + 1) * arr->elem_size,
                    bytes_to_move);
            arr->size--;
            return 0;
        }
    }
    return -1;
}

int easy_array_remove_index(easy_array* arr, size_t index) {
    if (!arr || index >= arr->size) return -1;
    size_t bytes_to_move = (arr->size - index - 1) * arr->elem_size;
    memmove((char*)arr->data + index * arr->elem_size,
            (char*)arr->data + (index + 1) * arr->elem_size,
            bytes_to_move);
    arr->size--;
    return 0;
}

int easy_array_insert(easy_array* arr, size_t index, void* elem) {
    if (!arr || index > arr->size) return -1;
    if (arr->size >= arr->capacity) {
        size_t new_cap = arr->capacity * 2;
        if (new_cap == 0) new_cap = 4;
        void* new_data = easy_alloc(new_cap * arr->elem_size);
        if (!new_data) return -1;
        memcpy(new_data, arr->data, index * arr->elem_size);
        memcpy((char*)new_data + (index + 1) * arr->elem_size,
               (char*)arr->data + index * arr->elem_size,
               (arr->size - index) * arr->elem_size);
        easy_free(arr->data);
        arr->data = new_data;
        arr->capacity = new_cap;
    } else {
        memmove((char*)arr->data + (index + 1) * arr->elem_size,
                (char*)arr->data + index * arr->elem_size,
                (arr->size - index) * arr->elem_size);
    }
    memcpy((char*)arr->data + index * arr->elem_size, elem, arr->elem_size);
    arr->size++;
    return 0;
}

int easy_array_index(easy_array* arr, void* value) {
    if (!arr) return -1;
    for (size_t i = 0; i < arr->size; i++) {
        if (memcmp((char*)arr->data + i * arr->elem_size, value, arr->elem_size) == 0) {
            return (int)i;
        }
    }
    return -1;
}

// ------------------------ Словари ------------------------
static unsigned int easy_hash(char* str) {
    unsigned int hash = 5381;
    int c;
    while ((c = *str++)) hash = ((hash << 5) + hash) + c;
    return hash;
}

easy_dict* easy_dict_new(size_t capacity, size_t value_size) {
    easy_dict* dict = (easy_dict*)easy_alloc(sizeof(easy_dict));
    if (!dict) return NULL;
    dict->buckets = (easy_dict_entry**)easy_alloc(capacity * sizeof(easy_dict_entry*));
    if (!dict->buckets) {
        easy_free(dict);
        return NULL;
    }
    for (size_t i = 0; i < capacity; i++) dict->buckets[i] = NULL;
    dict->size = 0;
    dict->capacity = capacity;
    dict->value_size = value_size;
    return dict;
}

void easy_dict_free(easy_dict* dict) {
    if (!dict) return;
    for (size_t i = 0; i < dict->capacity; i++) {
        easy_dict_entry* entry = dict->buckets[i];
        while (entry) {
            easy_dict_entry* next = entry->next;
            easy_free((void*)entry->key);
            easy_free(entry->value);
            easy_free(entry);
            entry = next;
        }
    }
    easy_free(dict->buckets);
    easy_free(dict);
}

int easy_dict_set(easy_dict* dict, char* key, void* value) {
    if (!dict || !key) return -1;
    unsigned int hash = easy_hash(key);
    size_t index = hash % dict->capacity;
    easy_dict_entry* entry = dict->buckets[index];
    while (entry) {
        if (strcmp(entry->key, key) == 0) {
            memcpy(entry->value, value, dict->value_size);
            return 0;
        }
        entry = entry->next;
    }
    entry = (easy_dict_entry*)easy_alloc(sizeof(easy_dict_entry));
    if (!entry) return -1;
    entry->key = (char*)easy_str_dup(key);
    if (!entry->key) { easy_free(entry); return -1; }
    entry->value = easy_alloc(dict->value_size);
    if (!entry->value) { easy_free((void*)entry->key); easy_free(entry); return -1; }
    memcpy(entry->value, value, dict->value_size);
    entry->next = dict->buckets[index];
    dict->buckets[index] = entry;
    dict->size++;
    return 0;
}

void* easy_dict_get(easy_dict* dict, char* key) {
    if (!dict || !key) return NULL;
    unsigned int hash = easy_hash(key);
    size_t index = hash % dict->capacity;
    easy_dict_entry* entry = dict->buckets[index];
    while (entry) {
        if (strcmp(entry->key, key) == 0) return entry->value;
        entry = entry->next;
    }
    return NULL;
}

int easy_dict_has(easy_dict* dict, char* key) {
    if (!dict || !key) return 0;
    unsigned int hash = easy_hash(key);
    size_t index = hash % dict->capacity;
    easy_dict_entry* entry = dict->buckets[index];
    while (entry) {
        if (strcmp(entry->key, key) == 0) return 1;
        entry = entry->next;
    }
    return 0;
}

int easy_dict_delete(easy_dict* dict, char* key) {
    if (!dict || !key) return -1;
    unsigned int hash = easy_hash(key);
    size_t index = hash % dict->capacity;
    easy_dict_entry* entry = dict->buckets[index];
    easy_dict_entry* prev = NULL;
    while (entry) {
        if (strcmp(entry->key, key) == 0) {
            if (prev) prev->next = entry->next;
            else dict->buckets[index] = entry->next;
            easy_free((void*)entry->key);
            easy_free(entry->value);
            easy_free(entry);
            dict->size--;
            return 0;
        }
        prev = entry;
        entry = entry->next;
    }
    return -1;
}

easy_dict* easy_dict_make(size_t count, size_t key_size, size_t value_size, ...) {
    (void)key_size;
    easy_dict* dict = easy_dict_new(count, value_size);
    if (!dict) return NULL;
    va_list args;
    va_start(args, value_size);
    for (size_t i = 0; i < count; i++) {
        char* key = va_arg(args, char*);
        void* value = va_arg(args, void*);
        easy_dict_set(dict, key, value);
    }
    va_end(args);
    return dict;
}

// ------------------------ JSON сериализация (строки) ------------------------
static char* _jsonify_string(char* s) {
    if (!s) return easy_str_dup("null");
    size_t len = strlen(s);
    char* out = easy_alloc(len * 2 + 3);
    char* p = out;
    *p++ = '"';
    for (size_t i = 0; i < len; i++) {
        char c = s[i];
        if (c == '"' || c == '\\') {
            *p++ = '\\';
            *p++ = c;
        } else if (c == '\n') {
            *p++ = '\\';
            *p++ = 'n';
        } else if (c == '\r') {
            *p++ = '\\';
            *p++ = 'r';
        } else if (c == '\t') {
            *p++ = '\\';
            *p++ = 't';
        } else {
            *p++ = c;
        }
    }
    *p++ = '"';
    *p = '\0';
    char* result = easy_str_dup(out);
    easy_free(out);
    return result;
}

char* easy_dict_to_json(easy_dict* dict) {
    if (!dict) return easy_str_dup("null");
    char* result = easy_str_dup("{");
    int first = 1;
    for (size_t i = 0; i < dict->capacity; i++) {
        easy_dict_entry* entry = dict->buckets[i];
        while (entry) {
            if (!first) result = easy_str_concat(result, ",");
            first = 0;
            char* key_json = _jsonify_string(entry->key);
            result = easy_str_concat(result, key_json);
            easy_free(key_json);
            result = easy_str_concat(result, ":");
            char** valp = (char**)entry->value;
            char* val = valp ? *valp : NULL;
            char* val_json = _jsonify_string(val ? val : "null");
            result = easy_str_concat(result, val_json);
            easy_free(val_json);
            entry = entry->next;
        }
    }
    result = easy_str_concat(result, "}");
    return result;
}

char* easy_array_to_json(easy_array* arr) {
    if (!arr) return easy_str_dup("null");
    char* result = easy_str_dup("[");
    for (size_t i = 0; i < arr->size; i++) {
        if (i > 0) result = easy_str_concat(result, ",");
        if (arr->elem_size == sizeof(int)) {
            int val = *(int*)easy_array_get(arr, i);
            char buf[32];
            snprintf(buf, sizeof(buf), "%d", val);
            char* val_json = easy_str_dup(buf);
            result = easy_str_concat(result, val_json);
            easy_free(val_json);
        } else if (arr->elem_size == sizeof(long long)) {
            long long val = *(long long*)easy_array_get(arr, i);
            char buf[32];
            snprintf(buf, sizeof(buf), "%lld", val);
            char* val_json = easy_str_dup(buf);
            result = easy_str_concat(result, val_json);
            easy_free(val_json);
        } else if (arr->elem_size == sizeof(double)) {
            double val = *(double*)easy_array_get(arr, i);
            char buf[64];
            snprintf(buf, sizeof(buf), "%g", val);
            char* val_json = easy_str_dup(buf);
            result = easy_str_concat(result, val_json);
            easy_free(val_json);
        } else if (arr->elem_size == sizeof(char*)) {
            char** valp = (char**)easy_array_get(arr, i);
            char* val = valp ? *valp : NULL;
            char* val_json = _jsonify_string(val ? val : "null");
            result = easy_str_concat(result, val_json);
            easy_free(val_json);
        } else {
            result = easy_str_concat(result, "null");
        }
    }
    result = easy_str_concat(result, "]");
    return result;
}

char* easy_jsonify(easy_dict* dict) {
    if (!dict) return easy_str_dup("null");
    return easy_dict_to_json(dict);
}

// ------------------------ Парсинг JSON (easy_dictify) ------------------------
typedef struct json_parser {
    char* str;
    size_t pos;
    size_t len;
} json_parser;

static void skip_whitespace(json_parser* p) {
    while (p->pos < p->len && isspace(p->str[p->pos])) p->pos++;
}

static int peek(json_parser* p) {
    if (p->pos >= p->len) return 0;
    return p->str[p->pos];
}

static int consume(json_parser* p, char expected) {
    skip_whitespace(p);
    if (p->pos < p->len && p->str[p->pos] == expected) {
        p->pos++;
        return 1;
    }
    return 0;
}

static char* parse_string(json_parser* p) {
    if (!consume(p, '"')) return NULL;
    size_t start = p->pos;
    while (p->pos < p->len && p->str[p->pos] != '"') {
        if (p->str[p->pos] == '\\') p->pos++;
        p->pos++;
    }
    if (p->pos >= p->len) return NULL;
    size_t end = p->pos;
    consume(p, '"');
    size_t len = end - start;
    char* buf = easy_alloc(len + 1);
    if (!buf) return NULL;
    memcpy(buf, p->str + start, len);
    buf[len] = '\0';
    return buf;
}

static char* parse_number(json_parser* p) {
    char* start = p->str + p->pos;
    while (p->pos < p->len && (isdigit(p->str[p->pos]) || p->str[p->pos] == '.' || p->str[p->pos] == '-' || p->str[p->pos] == 'e' || p->str[p->pos] == 'E')) p->pos++;
    size_t len = p->pos - (start - p->str);
    char* buf = easy_alloc(len + 1);
    if (!buf) return NULL;
    memcpy(buf, start, len);
    buf[len] = '\0';
    return buf;
}

static char* parse_bool(json_parser* p) {
    if (strncmp(p->str + p->pos, "true", 4) == 0) {
        p->pos += 4;
        return easy_str_dup("true");
    } else if (strncmp(p->str + p->pos, "false", 5) == 0) {
        p->pos += 5;
        return easy_str_dup("false");
    }
    return NULL;
}

static char* parse_null(json_parser* p) {
    if (strncmp(p->str + p->pos, "null", 4) == 0) {
        p->pos += 4;
        return easy_str_dup("null");
    }
    return NULL;
}

static easy_dict* parse_object(json_parser* p);
static easy_array* parse_array(json_parser* p);
static char* parse_value(json_parser* p);

easy_dict* easy_dictify(easy_str json_str) {
    if (!json_str) return NULL;
    json_parser parser = { json_str, 0, strlen(json_str) };
    skip_whitespace(&parser);
    if (!consume(&parser, '{')) return NULL;
    easy_dict* dict = easy_dict_new(16, sizeof(char*));
    while (1) {
        skip_whitespace(&parser);
        if (peek(&parser) == '}') {
            consume(&parser, '}');
            break;
        }
        char* key = parse_string(&parser);
        if (!key) { easy_dict_free(dict); return NULL; }
        skip_whitespace(&parser);
        if (!consume(&parser, ':')) { easy_free(key); easy_dict_free(dict); return NULL; }
        char* value = parse_value(&parser);
        if (!value) { easy_free(key); easy_dict_free(dict); return NULL; }
        easy_dict_set(dict, key, &value);
        easy_free(key);
        skip_whitespace(&parser);
        if (peek(&parser) == ',') consume(&parser, ',');
        else if (peek(&parser) == '}') continue;
        else { easy_dict_free(dict); return NULL; }
    }
    return dict;
}

static char* parse_value(json_parser* p) {
    skip_whitespace(p);
    char c = peek(p);
    if (c == '"') {
        return parse_string(p);
    } else if (c == '-' || isdigit(c)) {
        return parse_number(p);
    } else if (c == 't' || c == 'f') {
        return parse_bool(p);
    } else if (c == 'n') {
        return parse_null(p);
    } else if (c == '{') {
        easy_dict* obj = parse_object(p);
        if (!obj) return NULL;
        char* json = easy_dict_to_json(obj);
        easy_dict_free(obj);
        return json;
    } else if (c == '[') {
        easy_array* arr = parse_array(p);
        if (!arr) return NULL;
        char* json = easy_array_to_json(arr);
        easy_array_free(arr);
        return json;
    }
    return NULL;
}

static easy_dict* parse_object(json_parser* p) {
    if (!consume(p, '{')) return NULL;
    easy_dict* dict = easy_dict_new(16, sizeof(char*));
    while (1) {
        skip_whitespace(p);
        if (peek(p) == '}') {
            consume(p, '}');
            break;
        }
        char* key = parse_string(p);
        if (!key) { easy_dict_free(dict); return NULL; }
        skip_whitespace(p);
        if (!consume(p, ':')) { easy_free(key); easy_dict_free(dict); return NULL; }
        char* value = parse_value(p);
        if (!value) { easy_free(key); easy_dict_free(dict); return NULL; }
        easy_dict_set(dict, key, &value);
        easy_free(key);
        skip_whitespace(p);
        if (peek(p) == ',') consume(p, ',');
        else if (peek(p) == '}') continue;
        else { easy_dict_free(dict); return NULL; }
    }
    return dict;
}

static easy_array* parse_array(json_parser* p) {
    if (!consume(p, '[')) return NULL;
    easy_array* arr = easy_array_new(4, sizeof(char*));
    while (1) {
        skip_whitespace(p);
        if (peek(p) == ']') {
            consume(p, ']');
            break;
        }
        char* value = parse_value(p);
        if (!value) { easy_array_free(arr); return NULL; }
        easy_array_push(arr, &value);
        skip_whitespace(p);
        if (peek(p) == ',') consume(p, ',');
        else if (peek(p) == ']') continue;
        else { easy_array_free(arr); return NULL; }
    }
    return arr;
}

// ------------------------ easy_file_write_all ------------------------
int easy_file_write_all(char* path, char* data, size_t len) {
    FILE* f = fopen(path, "wb");
    if (!f) return -1;
    size_t written = fwrite(data, 1, len, f);
    fclose(f);
    return (written == len) ? 0 : -1;
}

// ------------------------ easy_value implementation ------------------------
easy_value* easy_value_new_null(void) {
    easy_value* v = (easy_value*)easy_alloc(sizeof(easy_value));
    if (!v) return NULL;
    v->type = EASY_VALUE_NULL;
    return v;
}

easy_value* easy_value_new_bool(int b) {
    easy_value* v = (easy_value*)easy_alloc(sizeof(easy_value));
    if (!v) return NULL;
    v->type = EASY_VALUE_BOOL;
    v->u.bool_val = b;
    return v;
}

easy_value* easy_value_new_int(long long i) {
    easy_value* v = (easy_value*)easy_alloc(sizeof(easy_value));
    if (!v) return NULL;
    v->type = EASY_VALUE_INT;
    v->u.int_val = i;
    return v;
}

easy_value* easy_value_new_double(double d) {
    easy_value* v = (easy_value*)easy_alloc(sizeof(easy_value));
    if (!v) return NULL;
    v->type = EASY_VALUE_DOUBLE;
    v->u.double_val = d;
    return v;
}

easy_value* easy_value_new_string(char* s) {
    easy_value* v = (easy_value*)easy_alloc(sizeof(easy_value));
    if (!v) return NULL;
    v->type = EASY_VALUE_STRING;
    v->u.string_val = s ? easy_str_dup(s) : NULL;
    return v;
}

easy_value* easy_value_new_array(easy_array* arr) {
    easy_value* v = (easy_value*)easy_alloc(sizeof(easy_value));
    if (!v) return NULL;
    v->type = EASY_VALUE_ARRAY;
    v->u.array_val = arr;
    return v;
}

easy_value* easy_value_new_object(easy_dict* obj) {
    easy_value* v = (easy_value*)easy_alloc(sizeof(easy_value));
    if (!v) return NULL;
    v->type = EASY_VALUE_OBJECT;
    v->u.object_val = obj;
    return v;
}

void easy_value_free(easy_value* v) {
    if (!v) return;
    switch (v->type) {
        case EASY_VALUE_STRING:
            if (v->u.string_val) easy_free(v->u.string_val);
            break;
        case EASY_VALUE_ARRAY:
            if (v->u.array_val) easy_array_free(v->u.array_val);
            break;
        case EASY_VALUE_OBJECT:
            if (v->u.object_val) easy_dict_free(v->u.object_val);
            break;
        default:
            break;
    }
    easy_free(v);
}

// ------------------------ JSON сериализация easy_value ------------------------
static char* _value_to_json(const easy_value* v) {
    if (!v) return easy_str_dup("null");
    switch (v->type) {
        case EASY_VALUE_NULL: return easy_str_dup("null");
        case EASY_VALUE_BOOL: return easy_str_dup(v->u.bool_val ? "true" : "false");
        case EASY_VALUE_INT: {
            char buf[32];
            snprintf(buf, sizeof(buf), "%lld", v->u.int_val);
            return easy_str_dup(buf);
        }
        case EASY_VALUE_DOUBLE: {
            char buf[64];
            snprintf(buf, sizeof(buf), "%g", v->u.double_val);
            return easy_str_dup(buf);
        }
        case EASY_VALUE_STRING:
            return _jsonify_string(v->u.string_val ? v->u.string_val : "");
        case EASY_VALUE_ARRAY:
            return easy_array_to_json(v->u.array_val);
        case EASY_VALUE_OBJECT:
            return easy_dict_to_json(v->u.object_val);
        default:
            return easy_str_dup("null");
    }
}

char* easy_value_to_json(easy_value* v) {
    return _value_to_json(v);
}

// Парсинг JSON в easy_value (использует существующий парсер из easy_dictify)
easy_value* easy_value_from_json(char* json, size_t* pos) {
    if (!json) return NULL;
    // Пропускаем пробелы
    size_t p = pos ? *pos : 0;
    // Воспользуемся уже готовыми функциями парсинга из easy_dictify, но они возвращают easy_dict.
    // Здесь нужно проанализировать тип: объект, массив или примитив.
    // Упростим: если первый символ '{', то парсим объект и оборачиваем в easy_value.
    // Если '[' — массив.
    // Иначе — примитив (число, строка, булево, null).
    // Для простоты пока поддерживаем только объект.
    // Но в реальном коде нужно обработать все типы.
    // Для демонстрации сделаем так:
    while (isspace(json[p])) p++;
    if (json[p] == '{') {
        easy_dict* dict = easy_dictify(json + p);
        if (dict) return easy_value_new_object(dict);
    }
    // Если массив, вернуть easy_value с массивом (нужен парсер массивов)
    if (json[p] == '[') {
        // Можно вызвать парсер массива из easy_dictify, но он не экспортирован.
        // Вместо этого вернём NULL.
    }
    // Примитивы: число, строка, bool, null — можно распарсить вручную, но для начала вернём NULL.
    return NULL;
}

// // ------------------------ DictServer (упрощённый, с void*) ------------------------
// struct DictHost {
//     easy_dict* dict;
// };

// static void* _dicthost_from_dict(easy_dict* dict) {
//     DictHost* host = (DictHost*)easy_alloc(sizeof(DictHost));
//     if (!host) return NULL;
//     host->dict = dict;
//     return (void*)host;
// }

// void* load(char* path) {
//     size_t len;
//     char* data = easy_file_read_all(path, &len);
//     if (!data) {
//         DictHost* host = (DictHost*)easy_alloc(sizeof(DictHost));
//         if (host) host->dict = easy_dict_new(16, sizeof(char*));
//         return (void*)host;
//     }
//     easy_dict* dict = easy_dictify(data);
//     easy_free(data);
//     if (!dict) {
//         DictHost* host = (DictHost*)easy_alloc(sizeof(DictHost));
//         if (host) host->dict = easy_dict_new(16, sizeof(char*));
//         return (void*)host;
//     }
//     return _dicthost_from_dict(dict);
// }

// void* parse(char* json) {
//     if (!json) return NULL;
//     easy_dict* dict = easy_dictify(json);
//     if (!dict) {
//         DictHost* host = (DictHost*)easy_alloc(sizeof(DictHost));
//         if (host) host->dict = easy_dict_new(16, sizeof(char*));
//         return (void*)host;
//     }
//     return _dicthost_from_dict(dict);
// }

// void save(void* host, char* path) {
//     if (!host) return;
//     DictHost* h = (DictHost*)host;
//     if (!h->dict) return;
//     char* json = easy_dict_to_json(h->dict);
//     if (json) {
//         easy_file_write_all(path, json, strlen(json));
//         easy_free(json);
//     }
// }

// char* getStr(void* host, char* key) {
//     if (!host) return NULL;
//     DictHost* h = (DictHost*)host;
//     if (!h->dict) return NULL;
//     char** val = (char**)easy_dict_get(h->dict, key);
//     return val ? easy_str_dup(*val) : NULL;
// }

// int getInt(void* host, char* key) {
//     if (!host) return 0;
//     DictHost* h = (DictHost*)host;
//     if (!h->dict) return 0;
//     char** val = (char**)easy_dict_get(h->dict, key);
//     if (!val || !*val) return 0;
//     char* end;
//     long long i = my_strtoll(*val, &end, 10);
//     return (*end == '\0') ? (int)i : 0;
// }

// int getBool(void* host, char* key) {
//     if (!host) return 0;
//     DictHost* h = (DictHost*)host;
//     if (!h->dict) return 0;
//     char** val = (char**)easy_dict_get(h->dict, key);
//     if (!val || !*val) return 0;
//     return (strcmp(*val, "true") == 0);
// }

// double getDouble(void* host, char* key) {
//     if (!host) return 0.0;
//     DictHost* h = (DictHost*)host;
//     if (!h->dict) return 0.0;
//     char** val = (char**)easy_dict_get(h->dict, key);
//     if (!val || !*val) return 0.0;
//     return strtod(*val, NULL);
// }

// void* getObj(void* host, char* key) {
//     if (!host) return NULL;
//     DictHost* h = (DictHost*)host;
//     if (!h->dict) return NULL;
//     char** val = (char**)easy_dict_get(h->dict, key);
//     if (!val || !*val) return NULL;
//     easy_dict* subdict = easy_dictify(*val);
//     if (!subdict) return NULL;
//     return _dicthost_from_dict(subdict);
// }

// void setStr(void* host, char* key, char* value) {
//     if (!host) return;
//     DictHost* h = (DictHost*)host;
//     if (!h->dict) return;
//     char* old = NULL;
//     char** oldp = (char**)easy_dict_get(h->dict, key);
//     if (oldp) old = *oldp;
//     char* newval = easy_str_dup(value);
//     easy_dict_set(h->dict, key, &newval);
//     if (old) easy_free(old);
// }

// void setInt(void* host, char* key, int value) {
//     char buf[32];
//     snprintf(buf, sizeof(buf), "%d", value);
//     setStr(host, key, buf);
// }

// void setBool(void* host, char* key, int value) {
//     setStr(host, key, value ? "true" : "false");
// }

// void setDouble(void* host, char* key, double value) {
//     char buf[64];
//     snprintf(buf, sizeof(buf), "%g", value);
//     setStr(host, key, buf);
// }

// void setObj(void* host, char* key, void* value) {
//     if (!host) return;
//     DictHost* h = (DictHost*)host;
//     if (!h->dict) return;
//     if (!value) return;
//     DictHost* v = (DictHost*)value;
//     if (!v->dict) return;
//     char* json = easy_dict_to_json(v->dict);
//     if (json) {
//         setStr(host, key, json);
//         easy_free(json);
//     }
// }

// void del(void* host, char* key) {
//     if (!host) return;
//     DictHost* h = (DictHost*)host;
//     if (!h->dict) return;
//     char** old = (char**)easy_dict_get(h->dict, key);
//     if (old) easy_free(*old);
//     easy_dict_delete(h->dict, key);
// }

// int has(void* host, char* key) {
//     if (!host) return 0;
//     DictHost* h = (DictHost*)host;
//     if (!h->dict) return 0;
//     return easy_dict_has(h->dict, key);
// }

// easy_array* keys(void* host) {
//     if (!host) return easy_array_new(0, sizeof(char*));
//     DictHost* h = (DictHost*)host;
//     if (!h->dict) return easy_array_new(0, sizeof(char*));
//     easy_array* k = easy_array_new(h->dict->size, sizeof(char*));
//     for (size_t i = 0; i < h->dict->capacity; i++) {
//         easy_dict_entry* entry = h->dict->buckets[i];
//         while (entry) {
//             easy_array_push(k, &entry->key);
//             entry = entry->next;
//         }
//     }
//     return k;
// }

// char* toJson(void* host) {
//     if (!host) return easy_str_dup("null");
//     DictHost* h = (DictHost*)host;
//     if (!h->dict) return easy_str_dup("null");
//     return easy_dict_to_json(h->dict);
// }

// void freeDict(void* host) {
//     if (!host) return;
//     DictHost* h = (DictHost*)host;
//     if (h->dict) easy_dict_free(h->dict);
//     easy_free(h);
// }
