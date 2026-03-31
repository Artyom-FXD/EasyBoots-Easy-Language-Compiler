#ifndef COLLECTIONS_H
#define COLLECTIONS_H

#include <stddef.h>
#include <stdarg.h>

// ------------------------ arr (динамический массив) ------------------------
typedef struct arr {
    void* data;
    size_t size;
    size_t capacity;
    size_t elem_size;
} arr;

arr* arr_new(size_t elem_size);
void arr_free(arr* a);
void arr_push(arr* a, void* elem);
void* arr_pop_value(arr* a);
void arr_pop(arr* a);
void* arr_get(arr* a, size_t index);
void arr_set(arr* a, size_t index, void* elem);
size_t arr_len(arr* a);
int arr_remove_value(arr* a, void* value);
int arr_remove_index(arr* a, size_t index);
int arr_insert(arr* a, size_t index, void* elem);
int arr_index(arr* a, void* value);
arr* arr_copy(arr* a);
arr* arr_make(size_t count, size_t elem_size, ...);

// ------------------------ dict (хеш-таблица) ------------------------
typedef struct dict_entry {
    void* key;
    void* value;
    struct dict_entry* next;
} dict_entry;

typedef struct dict {
    dict_entry** buckets;
    size_t size;
    size_t capacity;
    size_t key_size;
    size_t value_size;
    unsigned int (*hash)(void* key);
    int (*key_cmp)(void* a, void* b);
} dict;

dict* dict_new(size_t key_size, size_t value_size,
               unsigned int (*hash)(void*),
               int (*key_cmp)(void*, void*));
void dict_free(dict* d);
void dict_set(dict* d, void* key, void* value);
void* dict_get(dict* d, void* key);
int dict_has(dict* d, void* key);
int dict_delete(dict* d, void* key);
size_t dict_size(dict* d);
arr* dict_keys(dict* d);
arr* dict_values(dict* d);
dict* dict_make(size_t count, size_t key_size, size_t value_size,
                unsigned int (*hash)(void*),
                int (*key_cmp)(void*, void*), ...);

// Удобные обёртки для строковых ключей
unsigned int dict_hash_str(void* key);
int dict_cmp_str(void* a, void* b);
dict* dict_new_str(size_t value_size);
void dict_set_str(dict* d, char* key, void* value);
void* dict_get_str(dict* d, char* key);
int dict_has_str(dict* d, char* key);
int dict_delete_str(dict* d, char* key);
arr* dict_keys_str(dict* d);  // возвращает arr* из char*

void arr_reserve(arr* a, size_t new_cap);

#endif