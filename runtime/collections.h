#ifndef COLLECTIONS_H
#define COLLECTIONS_H

#include <stddef.h>
#include <stdarg.h>

// ------------------------ easy_value ------------------------
typedef enum {
    EASY_VALUE_NULL,
    EASY_VALUE_BOOL,
    EASY_VALUE_INT,
    EASY_VALUE_DOUBLE,
    EASY_VALUE_STRING,
    EASY_VALUE_ARRAY,
    EASY_VALUE_OBJECT
} easy_value_type;

typedef struct easy_value {
    easy_value_type type;
    union {
        int bool_val;
        long long int_val;
        double double_val;
        char* string_val;
        struct easy_array* array_val;
        struct easy_dict* object_val;
    } u;
} easy_value;

// ------------------------ easy_array ------------------------
typedef struct easy_array {
    void* data;
    size_t size;
    size_t capacity;
    size_t elem_size;
} easy_array;

easy_array* easy_array_new(size_t capacity, size_t elem_size);
void easy_array_free(easy_array* arr);
int easy_array_push(easy_array* arr, void* elem);
void easy_array_pop(easy_array* arr);
void* easy_array_get(easy_array* arr, size_t index);
void easy_array_set(easy_array* arr, size_t index, void* elem);
size_t easy_array_size(easy_array* arr);
easy_array* easy_array_make(size_t count, size_t elem_size, ...);

// ------------------------ easy_dict ------------------------
typedef struct easy_dict_entry {
    char* key;   // храним как char*
    void* value;
    struct easy_dict_entry* next;
} easy_dict_entry;

typedef struct easy_dict {
    easy_dict_entry** buckets;
    size_t size;
    size_t capacity;
    size_t value_size;
} easy_dict;

easy_dict* easy_dict_new(size_t capacity, size_t value_size);
void easy_dict_free(easy_dict* dict);
int easy_dict_set(easy_dict* dict, char* key, void* value);
void* easy_dict_get(easy_dict* dict, char* key);
int easy_dict_has(easy_dict* dict, char* key);
int easy_dict_delete(easy_dict* dict, char* key);
easy_dict* easy_dict_make(size_t count, size_t key_size, size_t value_size, ...);

// ------------------------ easy_value helpers (только конструкторы, без to_json/from_json) ------------------------
easy_value* easy_value_new_null(void);
easy_value* easy_value_new_bool(int b);
easy_value* easy_value_new_int(long long i);
easy_value* easy_value_new_double(double d);
easy_value* easy_value_new_string(char* s);
easy_value* easy_value_new_array(easy_array* arr);
easy_value* easy_value_new_object(easy_dict* obj);
void easy_value_free(easy_value* v);

#endif