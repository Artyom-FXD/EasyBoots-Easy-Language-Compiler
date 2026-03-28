#ifndef EASY_RUNTIME_H
#define EASY_RUNTIME_H

#include <stddef.h>
#include <collections.h>

#ifdef __cplusplus
extern "C" {
#endif

int easy_file_write_all(char* path, char* data, size_t len);

// Типы
typedef int             easy_int;
typedef unsigned int    easy_uint;
typedef long long       easy_more;
typedef unsigned long long easy_umore;
typedef float           easy_flt;
typedef double          easy_double;
typedef char            easy_char;
typedef unsigned char   easy_byte;
typedef unsigned char   easy_ubyte;
typedef int             easy_bool;
typedef char*           easy_str;

// ------------------------ Консоль ------------------------
void easy_print(easy_str str);
void easy_print_int(easy_int n);
void easy_print_uint(easy_uint n);
void easy_print_more(easy_more n);
void easy_print_umore(easy_umore n);
void easy_print_flt(easy_flt f);
void easy_print_double(easy_double d);
void easy_print_bool(easy_bool b);
void easy_print_char(easy_char c);
void easy_print_byte(easy_byte b);
void easy_print_ubyte(easy_ubyte b);
void easy_println(easy_str str);

easy_str easy_input(void);
easy_str easy_input_prompt(easy_str prompt);

// ------------------------ Преобразования ------------------------
easy_int    easy_str_to_int(easy_str str);
easy_uint   easy_str_to_uint(easy_str str);
easy_more   easy_str_to_more(easy_str str);
easy_umore  easy_str_to_umore(easy_str str);
easy_flt    easy_str_to_flt(easy_str str);
easy_double easy_str_to_double(easy_str str);

easy_str easy_int_to_str(easy_int n);
easy_str easy_uint_to_str(easy_uint n);
easy_str easy_more_to_str(easy_more n);
easy_str easy_umore_to_str(easy_umore n);
easy_str easy_flt_to_str(easy_flt f);
easy_str easy_double_to_str(easy_double d);
easy_str easy_bool_to_str(easy_bool b);

// ------------------------ Строки ------------------------
size_t      easy_str_len(easy_str str);
easy_str    easy_str_dup(easy_str str);
easy_str    easy_str_concat(easy_str a, easy_str b);
int         easy_str_cmp(easy_str a, easy_str b);
easy_str    easy_str_substr(easy_str str, size_t start, size_t len);
easy_str    easy_str_trim(easy_str str);
easy_str    easy_str_replace(easy_str str, easy_str old, easy_str new);

// ------------------------ Математика ------------------------
easy_int    easy_abs_int(easy_int n);
easy_more   easy_abs_more(easy_more n);
easy_double easy_fabs(easy_double x);
easy_int    easy_min_int(easy_int a, easy_int b);
easy_more   easy_min_more(easy_more a, easy_more b);
easy_double easy_min_double(easy_double a, easy_double b);
easy_int    easy_max_int(easy_int a, easy_int b);
easy_more   easy_max_more(easy_more a, easy_more b);
easy_double easy_max_double(easy_double a, easy_double b);
easy_double easy_pow(easy_double base, easy_double exp);
easy_double easy_sqrt(easy_double x);
easy_double easy_sin(easy_double x);
easy_double easy_cos(easy_double x);
easy_double easy_tan(easy_double x);

// ------------------------ Случайные числа ------------------------
void        easy_srand(easy_uint seed);
easy_int    easy_rand(void);
easy_double easy_rand_double(void);

// ------------------------ Время ------------------------
void        easy_sleep(easy_uint milliseconds);
easy_more   easy_time_now(void);
double      easy_time_diff(easy_more start, easy_more end);

// ------------------------ Файлы ------------------------
typedef struct easy_file easy_file;
easy_file* easy_file_open(char* path, char* mode);
void       easy_file_close(easy_file* f);
int        easy_file_write(easy_file* f, char* data, size_t len);
char*      easy_file_read(easy_file* f, size_t* out_len);
int        easy_file_exists(char* path);
char*      easy_file_read_all(char* path, size_t* out_len);
int        easy_file_remove(char* path);
int        easy_file_rename(char* old, char* new);

// ------------------------ Пути ------------------------
easy_str easy_path_join(easy_str a, easy_str b);
easy_str easy_path_basename(easy_str path);
easy_str easy_path_dirname(easy_str path);
int      easy_path_is_absolute(easy_str path);

// ------------------------ Динамические библиотеки ------------------------
void* easy_load_library(char* path);
void* easy_get_function(void* lib, char* name);
void  easy_close_library(void* lib);
int   easy_call_int_int(void* func, int a, int b);
double easy_call_double_double(void* func, double a);
double easy_call_double_double_double(void* func, double a, double b);
char* easy_call_str_void(void* func);

// ------------------------ Память ------------------------
void* easy_alloc(size_t size);
void  easy_free(void* ptr);

// ------------------------ JSON для сложных типов ------------------------
easy_str easy_dict_to_json(easy_dict* dict);
easy_str easy_array_to_json(easy_array* arr);
easy_str easy_jsonify(easy_dict* dict);
easy_dict* easy_dictify(easy_str json);
easy_str easy_value_to_json(easy_value* v);          // убран const
easy_value* easy_value_from_json(char* json, size_t* pos); // убран const

// ------------------------ Методы массивов ------------------------
void* easy_array_pop_value(easy_array* arr);
size_t easy_array_len(easy_array* arr);
int easy_array_remove_value(easy_array* arr, void* value);
int easy_array_remove_index(easy_array* arr, size_t index);
int easy_array_insert(easy_array* arr, size_t index, void* elem);
int easy_array_index(easy_array* arr, void* value);

// ------------------------ DictServer API (с void*) ------------------------
void* load(char* path);
void save(void* host, char* path);
char* getStr(void* host, char* key);
int getInt(void* host, char* key);
int getBool(void* host, char* key);
double getDouble(void* host, char* key);
void* getObj(void* host, char* key);
void setStr(void* host, char* key, char* value);
void setInt(void* host, char* key, int value);
void setBool(void* host, char* key, int value);
void setDouble(void* host, char* key, double value);
void setObj(void* host, char* key, void* value);
void del(void* host, char* key);
int has(void* host, char* key);
easy_array* keys(void* host);
char* toJson(void* host);
void* parse(char* json);
void freeDict(void* host);

#ifdef __cplusplus
}
#endif

#endif